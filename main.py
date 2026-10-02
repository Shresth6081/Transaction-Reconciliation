import os
import sys
import argparse
import time
from pathlib import Path
import pandas as pd
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from config.settings import settings
from data.generate_datasets import generate_transaction_datasets
from engine.reconciler import ReconciliationEngine
from engine.validator import DataQualityValidator
from reports.excel_generator import ExcelReportGenerator
from database.db_manager import DatabaseManager

console = Console()

def run_reconciliation_pipeline(
    bank_csv_path: Path = None,
    ledger_csv_path: Path = None,
    generate_sample_count: int = 50000,
    force_generate: bool = False
):
    """
    End-to-End Transaction Reconciliation Pipeline
    """
    console.print(Panel.fit(
        "[bold cyan]AUTOMATED TRANSACTION RECONCILIATION SYSTEM[/bold cyan]\n"
        "[dim]High-Performance Matching | Exception Classification | MySQL Audit Trail | Excel VBA[/dim]",
        border_style="cyan"
    ))

    # 1. Dataset verification or generation
    bank_file = bank_csv_path or (settings.RAW_DATA_DIR / "bank_transactions.csv")
    ledger_file = ledger_csv_path or (settings.RAW_DATA_DIR / "ledger_transactions.csv")

    if force_generate or not (bank_file.exists() and ledger_file.exists()):
        console.print(f"[bold yellow]>> Generating {generate_sample_count:,} synthetic transaction records...[/bold yellow]")
        bank_file, ledger_file = generate_transaction_datasets(
            total_records=generate_sample_count,
            output_dir=settings.RAW_DATA_DIR
        )

    # 2. Ingest Data Feeds
    console.print(f"[bold green][OK] Loading transaction feeds...[/bold green]")
    t_read_start = time.time()
    df_bank = pd.read_csv(bank_file)
    df_ledger = pd.read_csv(ledger_file)
    console.print(f"  * Bank Statement Records:   [cyan]{len(df_bank):,}[/cyan]")
    console.print(f"  * General Ledger Records:   [cyan]{len(df_ledger):,}[/cyan]")
    console.print(f"  * Total Volume:             [cyan]{len(df_bank) + len(df_ledger):,}[/cyan] transactions loaded in {time.time() - t_read_start:.2f}s")

    # 3. Execute Reconciliation Engine
    console.print("\n[bold yellow]>> Executing Reconciliation Engine (Exact + Tolerance Matching)...[/bold yellow]")
    engine = ReconciliationEngine(
        date_tolerance_days=settings.DATE_TOLERANCE_DAYS,
        amount_tolerance=settings.AMOUNT_TOLERANCE
    )
    
    summary = engine.reconcile(df_bank, df_ledger)

    # 4. Generate Excel Report
    console.print("\n[bold yellow]>> Generating Styled Multi-Tab Excel Exception Report...[/bold yellow]")
    report_path = ExcelReportGenerator.generate_report(summary)
    console.print(f"  * Excel Report created: {report_path.name}")

    # 5. Store in Database Audit Trail
    console.print("\n[bold yellow]>> Persisting Audit Trail to Database...[/bold yellow]")
    db = DatabaseManager()
    db.save_batch_summary(summary.to_dict())
    if summary.df_exceptions is not None and not summary.df_exceptions.empty:
        db.save_exceptions(summary.batch_id, summary.df_exceptions)
    if summary.dq_results:
        db.save_dq_logs(summary.batch_id, [res.__dict__ for res in summary.dq_results])
    console.print(f"  * Run results and {len(summary.df_exceptions):,} exceptions saved to audit database successfully.")


    # 6. Display Executive Summary Table
    print_terminal_summary(summary, report_path)

def print_terminal_summary(summary, report_path: Path):
    table = Table(title=f"Reconciliation Run Results - Batch {summary.batch_id}", box=box.ROUNDED)
    table.add_column("Category / Metric", style="cyan", no_wrap=True)
    table.add_column("Count", justify="right", style="magenta")
    table.add_column("Percentage", justify="right", style="green")
    table.add_column("Classification", style="yellow")

    tot = max(1, summary.total_matched + summary.total_unmatched)
    table.add_row("Exact Matches (Ref + Amount + Date)", f"{summary.exact_matches:,}", f"{(summary.exact_matches/tot)*100:.1f}%", "[green]RECONCILED[/green]")
    table.add_row(f"Date Tolerance Matches (+/- {settings.DATE_TOLERANCE_DAYS} Days)", f"{summary.tolerance_matches:,}", f"{(summary.tolerance_matches/tot)*100:.1f}%", "[green]RECONCILED[/green]")
    table.add_row("Amount Mismatches", f"{summary.amount_mismatches:,}", f"{(summary.amount_mismatches/tot)*100:.1f}%", "[red]DISPUTE / EXCEPTION[/red]")
    table.add_row("Missing in Ledger (Bank Only)", f"{summary.missing_in_ledger:,}", f"{(summary.missing_in_ledger/tot)*100:.1f}%", "[yellow]UNPOSTED ENTRY[/yellow]")
    table.add_row("Missing in Bank (Ledger Only)", f"{summary.missing_in_bank:,}", f"{(summary.missing_in_bank/tot)*100:.1f}%", "[yellow]OUTSTANDING ITEM[/yellow]")
    table.add_row("Duplicate Records Detected", f"{summary.duplicate_records:,}", f"{(summary.duplicate_records/tot)*100:.1f}%", "[magenta]DUPLICATE[/magenta]")
    
    console.print(table)

    # Financial Control Totals Panel
    ctrl_text = (
        f"[bold]Bank Control Total:[/bold]   ${summary.bank_control_total:,.2f}\n"
        f"[bold]Ledger Control Total:[/bold] ${summary.ledger_control_total:,.2f}\n"
        f"[bold]Net Variance:[/bold]          ${summary.net_variance:,.2f}\n"
        f"[bold]Execution Duration:[/bold]    {summary.execution_duration_sec:.2f} seconds\n"
        f"[bold]Excel Exception File:[/bold]  {report_path}"
    )
    console.print(Panel(ctrl_text, title="[bold green]Financial Integrity & Control Totals[/bold green]", border_style="green"))


def main():
    parser = argparse.ArgumentParser(description="Transaction Reconciliation Automation Engine")
    parser.add_argument("--bank", type=str, help="Path to Bank transactions CSV", default=None)
    parser.add_argument("--ledger", type=str, help="Path to General Ledger transactions CSV", default=None)
    parser.add_argument("--records", type=int, help="Number of records to generate if creating sample data", default=50000)
    parser.add_argument("--generate", action="store_true", help="Force regenerate synthetic datasets")

    args = parser.parse_args()

    bank_path = Path(args.bank) if args.bank else None
    ledger_path = Path(args.ledger) if args.ledger else None

    run_reconciliation_pipeline(
        bank_csv_path=bank_path,
        ledger_csv_path=ledger_path,
        generate_sample_count=args.records,
        force_generate=args.generate
    )

if __name__ == "__main__":
    main()
