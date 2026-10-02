import os
from pathlib import Path
from datetime import datetime
import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from config.settings import settings
from engine.models import ReconciliationSummary

class ExcelReportGenerator:
    """
    Generates an executive-grade, multi-tab Excel Reconciliation Exception Report
    with custom styling, summary KPI dashboards, categorized exception breakdowns,
    data quality audit results, and embedded VBA automation instructions.
    """

    NAVY_FILL = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
    SLATE_FILL = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    HEADER_FONT = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    TITLE_FONT = Font(name="Calibri", size=16, bold=True, color="1F497D")
    SUBTITLE_FONT = Font(name="Calibri", size=11, italic=True, color="595959")
    CARD_TITLE_FONT = Font(name="Calibri", size=9, bold=True, color="595959")
    CARD_VALUE_FONT = Font(name="Calibri", size=16, bold=True, color="1F497D")
    
    # Category Fills
    MISMATCH_FILL = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
    MISSING_LEDGER_FILL = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")
    MISSING_BANK_FILL = PatternFill(start_color="F8CBAD", end_color="F8CBAD", fill_type="solid")
    DUPLICATE_FILL = PatternFill(start_color="E1D5E7", end_color="E1D5E7", fill_type="solid")
    PASS_FILL = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")

    THIN_BORDER = Border(
        left=Side(style="thin", color="D9D9D9"),
        right=Side(style="thin", color="D9D9D9"),
        top=Side(style="thin", color="D9D9D9"),
        bottom=Side(style="thin", color="D9D9D9")
    )

    @classmethod
    def generate_report(
        cls,
        summary: ReconciliationSummary,
        output_filepath: Path = None
    ) -> Path:
        """
        Creates and styles the complete Excel exception report.
        """
        if output_filepath is None:
            filename = f"Reconciliation_Report_{summary.batch_id}.xlsx"
            output_filepath = settings.OUTPUT_DATA_DIR / filename

        output_filepath = Path(output_filepath)
        wb = openpyxl.Workbook()
        # Remove default sheet
        wb.remove(wb.active)

        # 1. Executive Dashboard
        ws_dash = wb.create_sheet(title="Executive Dashboard")
        cls._build_dashboard(ws_dash, summary)

        # 2. Exceptions Breakdown
        ws_ex = wb.create_sheet(title="Exceptions Breakdown")
        cls._build_exceptions_sheet(ws_ex, summary.df_exceptions)

        # 3. Matched Records (sample top 5,000 for fast workbook rendering)
        ws_match = wb.create_sheet(title="Matched Records")
        cls._build_matched_sheet(ws_match, summary.df_matched)

        # 4. Data Quality Audit
        ws_dq = wb.create_sheet(title="Data Quality Audit")
        cls._build_dq_sheet(ws_dq, summary.dq_results)

        # 5. VBA Automation Helper
        ws_vba = wb.create_sheet(title="VBA Automation & Macro")
        cls._build_vba_info_sheet(ws_vba)

        # Auto-adjust column widths across all sheets
        for sheet in wb.worksheets:
            cls._autofit_columns(sheet)

        wb.save(output_filepath)
        summary.report_file_path = str(output_filepath)
        return output_filepath

    @classmethod
    def _build_dashboard(cls, ws, summary: ReconciliationSummary):
        ws.views.sheetView[0].showGridLines = True

        # Header Title
        ws.merge_cells("A2:H2")
        ws["A2"] = "AUTOMATED TRANSACTION RECONCILIATION DASHBOARD"
        ws["A2"].font = cls.TITLE_FONT
        ws["A2"].alignment = Alignment(vertical="center")

        ws.merge_cells("A3:H3")
        ws["A3"] = f"Batch ID: {summary.batch_id} | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Execution Time: {summary.execution_duration_sec:.2f}s"
        ws["A3"].font = cls.SUBTITLE_FONT

        # KPI Summary Cards in Rows 5-7
        kpis = [
            ("TOTAL TRANSACTIONS", f"{summary.total_bank_records + summary.total_ledger_records:,}", "A", "B"),
            ("MATCH RATE", f"{(summary.total_matched / max(1, (summary.total_matched + summary.total_unmatched))) * 100:.1f}%", "C", "D"),
            ("TOTAL EXCEPTIONS", f"{summary.total_unmatched:,}", "E", "F"),
            ("NET VARIANCE ($)", f"${summary.net_variance:,.2f}", "G", "H"),
        ]

        for label, val, c_start, c_end in kpis:
            top_left = f"{c_start}5"
            bot_right = f"{c_end}7"
            ws.merge_cells(f"{c_start}5:{c_end}5")
            ws.merge_cells(f"{c_start}6:{c_end}7")

            ws[top_left] = label
            ws[top_left].font = cls.CARD_TITLE_FONT
            ws[top_left].alignment = Alignment(horizontal="center", vertical="center")
            ws[top_left].fill = PatternFill(start_color="F2F2F2", fill_type="solid")

            ws[f"{c_start}6"] = val
            ws[f"{c_start}6"].font = cls.CARD_VALUE_FONT
            ws[f"{c_start}6"].alignment = Alignment(horizontal="center", vertical="center")
            ws[f"{c_start}6"].fill = PatternFill(start_color="FFFFFF", fill_type="solid")

            # Border
            for r in range(5, 8):
                for c in [openpyxl.utils.column_index_from_string(c_start), openpyxl.utils.column_index_from_string(c_end)]:
                    ws.cell(row=r, column=c).border = cls.THIN_BORDER

        # Reconciliation Summary Breakdown Table (Row 10+)
        headers = ["Reconciliation Metric", "Count", "Percentage", "Status / Classification"]
        ws.row_dimensions[10].height = 24
        for col_idx, h in enumerate(headers, start=2):
            cell = ws.cell(row=10, column=col_idx, value=h)
            cell.font = cls.HEADER_FONT
            cell.fill = cls.NAVY_FILL
            cell.alignment = Alignment(horizontal="center", vertical="center")

        total_tx = max(1, summary.total_matched + summary.total_unmatched)
        rows_data = [
            ("Exact Matches (Ref ID + Amount + Date)", summary.exact_matches, f"{(summary.exact_matches/total_tx)*100:.2f}%", "RECONCILED"),
            ("Tolerance Matches (+/- 3 Days Clearance)", summary.tolerance_matches, f"{(summary.tolerance_matches/total_tx)*100:.2f}%", "RECONCILED"),
            ("Amount Mismatches (Ref ID match, $ variance)", summary.amount_mismatches, f"{(summary.amount_mismatches/total_tx)*100:.2f}%", "EXCEPTION - DISPUTED"),
            ("Missing in General Ledger (Bank Only)", summary.missing_in_ledger, f"{(summary.missing_in_ledger/total_tx)*100:.2f}%", "EXCEPTION - UNPOSTED"),
            ("Missing in Bank Statement (Ledger Only)", summary.missing_in_bank, f"{(summary.missing_in_bank/total_tx)*100:.2f}%", "EXCEPTION - OUTSTANDING"),
            ("Duplicate Records Detected", summary.duplicate_records, f"{(summary.duplicate_records/total_tx)*100:.2f}%", "EXCEPTION - DUPLICATE"),
        ]

        curr_r = 11
        for label, count, pct, stat in rows_data:
            ws.cell(row=curr_r, column=2, value=label)
            ws.cell(row=curr_r, column=3, value=count).number_format = "#,##0"
            ws.cell(row=curr_r, column=4, value=pct).alignment = Alignment(horizontal="center")
            
            c_stat = ws.cell(row=curr_r, column=5, value=stat)
            c_stat.alignment = Alignment(horizontal="center")
            if "RECONCILED" in stat:
                c_stat.fill = cls.PASS_FILL
            elif "DISPUTED" in stat:
                c_stat.fill = cls.MISMATCH_FILL
            elif "UNPOSTED" in stat:
                c_stat.fill = cls.MISSING_LEDGER_FILL
            elif "OUTSTANDING" in stat:
                c_stat.fill = cls.MISSING_BANK_FILL
            else:
                c_stat.fill = cls.DUPLICATE_FILL

            for c in range(2, 6):
                ws.cell(row=curr_r, column=c).border = cls.THIN_BORDER
            curr_r += 1

        # Control Totals Section (Row curr_r + 2)
        curr_r += 2
        ws.merge_cells(f"B{curr_r}:E{curr_r}")
        ws[f"B{curr_r}"] = "FINANCIAL CONTROL TOTALS & CHECKSUM"
        ws[f"B{curr_r}"].font = Font(bold=True, color="1F497D")

        curr_r += 1
        ctrl_data = [
            ("Bank Statement Control Total", summary.bank_control_total),
            ("General Ledger Control Total", summary.ledger_control_total),
            ("Net Financial Variance", summary.net_variance)
        ]
        for name, amt in ctrl_data:
            ws.cell(row=curr_r, column=2, value=name)
            amt_cell = ws.cell(row=curr_r, column=3, value=amt)
            amt_cell.number_format = "$#,##0.00"
            amt_cell.font = Font(bold=(name == "Net Financial Variance"))
            for c in range(2, 4):
                ws.cell(row=curr_r, column=c).border = cls.THIN_BORDER
            curr_r += 1

    @classmethod
    def _build_exceptions_sheet(cls, ws, df_exceptions: pd.DataFrame):
        ws.views.sheetView[0].showGridLines = True
        if df_exceptions is None or df_exceptions.empty:
            ws["A1"] = "No exceptions detected. Reconciliation perfectly balanced."
            return

        headers = [
            "Reference ID", "Exception Category", "Bank Date", "Ledger Date",
            "Bank Amount ($)", "Ledger Amount ($)", "Amount Variance ($)", "Exception Description"
        ]

        ws.row_dimensions[1].height = 24
        for col_idx, h in enumerate(headers, start=1):
            cell = ws.cell(row=1, column=col_idx, value=h)
            cell.font = cls.HEADER_FONT
            cell.fill = cls.NAVY_FILL
            cell.alignment = Alignment(horizontal="center", vertical="center")

        for r_idx, row in df_exceptions.iterrows():
            curr_r = r_idx + 2
            ws.cell(row=curr_r, column=1, value=str(row.get("reference_id", "")))
            
            cat_cell = ws.cell(row=curr_r, column=2, value=str(row.get("exception_category", "")))
            cat_cell.alignment = Alignment(horizontal="center")
            cat_val = str(row.get("exception_category", ""))
            if "MISMATCH" in cat_val:
                cat_cell.fill = cls.MISMATCH_FILL
            elif "MISSING_IN_LEDGER" in cat_val:
                cat_cell.fill = cls.MISSING_LEDGER_FILL
            elif "MISSING_IN_BANK" in cat_val:
                cat_cell.fill = cls.MISSING_BANK_FILL
            elif "DUPLICATE" in cat_val:
                cat_cell.fill = cls.DUPLICATE_FILL

            ws.cell(row=curr_r, column=3, value=str(row.get("bank_date", ""))).alignment = Alignment(horizontal="center")
            ws.cell(row=curr_r, column=4, value=str(row.get("ledger_date", ""))).alignment = Alignment(horizontal="center")
            
            c_bamt = ws.cell(row=curr_r, column=5, value=float(row.get("bank_amount", 0.0)))
            c_bamt.number_format = "$#,##0.00"

            c_lamt = ws.cell(row=curr_r, column=6, value=float(row.get("ledger_amount", 0.0)))
            c_lamt.number_format = "$#,##0.00"

            c_diff = ws.cell(row=curr_r, column=7, value=float(row.get("amount_diff", 0.0)))
            c_diff.number_format = "$#,##0.00"
            if abs(float(row.get("amount_diff", 0.0))) >= 1000.0:
                c_diff.font = Font(color="9C0006", bold=True)

            ws.cell(row=curr_r, column=8, value=str(row.get("description", "")))

            for c in range(1, 9):
                ws.cell(row=curr_r, column=c).border = cls.THIN_BORDER

        ws.auto_filter.ref = f"A1:H{len(df_exceptions) + 1}"

    @classmethod
    def _build_matched_sheet(cls, ws, df_matched: pd.DataFrame):
        ws.views.sheetView[0].showGridLines = True
        if df_matched is None or df_matched.empty:
            ws["A1"] = "No matched records available."
            return

        headers = [
            "Reference ID", "Match Type", "Bank Date", "Ledger Date",
            "Date Variance (Days)", "Bank Amount ($)", "Ledger Amount ($)", "Description"
        ]

        ws.row_dimensions[1].height = 24
        for col_idx, h in enumerate(headers, start=1):
            cell = ws.cell(row=1, column=col_idx, value=h)
            cell.font = cls.HEADER_FONT
            cell.fill = cls.SLATE_FILL
            cell.alignment = Alignment(horizontal="center", vertical="center")

        # Display sample for quick workbook responsiveness (up to 10,000)
        display_df = df_matched.head(10000)
        for r_idx, row in display_df.iterrows():
            curr_r = r_idx + 2
            ws.cell(row=curr_r, column=1, value=str(row.get("reference_id", "")))
            
            m_type = ws.cell(row=curr_r, column=2, value=str(row.get("match_type", "")))
            m_type.alignment = Alignment(horizontal="center")
            if row.get("match_type") == "EXACT_MATCH":
                m_type.fill = cls.PASS_FILL

            ws.cell(row=curr_r, column=3, value=str(row.get("bank_date", ""))).alignment = Alignment(horizontal="center")
            ws.cell(row=curr_r, column=4, value=str(row.get("ledger_date", ""))).alignment = Alignment(horizontal="center")
            ws.cell(row=curr_r, column=5, value=int(row.get("date_variance_days", 0))).alignment = Alignment(horizontal="center")

            c_bamt = ws.cell(row=curr_r, column=6, value=float(row.get("bank_amount", 0.0)))
            c_bamt.number_format = "$#,##0.00"

            c_lamt = ws.cell(row=curr_r, column=7, value=float(row.get("ledger_amount", 0.0)))
            c_lamt.number_format = "$#,##0.00"

            ws.cell(row=curr_r, column=8, value=str(row.get("description", "")))

            for c in range(1, 9):
                ws.cell(row=curr_r, column=c).border = cls.THIN_BORDER

        ws.auto_filter.ref = f"A1:H{len(display_df) + 1}"

    @classmethod
    def _build_dq_sheet(cls, ws, dq_results):
        ws.views.sheetView[0].showGridLines = True
        headers = ["Source Feed", "Data Quality Check", "Status", "Records Affected", "Validation Details"]
        
        ws.row_dimensions[1].height = 24
        for col_idx, h in enumerate(headers, start=1):
            cell = ws.cell(row=1, column=col_idx, value=h)
            cell.font = cls.HEADER_FONT
            cell.fill = cls.NAVY_FILL
            cell.alignment = Alignment(horizontal="center", vertical="center")

        for r_idx, res in enumerate(dq_results, start=2):
            ws.cell(row=r_idx, column=1, value=res.source_name)
            ws.cell(row=r_idx, column=2, value=res.check_name)
            
            s_cell = ws.cell(row=r_idx, column=3, value=res.check_status)
            s_cell.alignment = Alignment(horizontal="center")
            if res.check_status == "PASSED":
                s_cell.fill = cls.PASS_FILL
            else:
                s_cell.fill = cls.MISMATCH_FILL

            ws.cell(row=r_idx, column=4, value=res.records_affected).alignment = Alignment(horizontal="center")
            ws.cell(row=r_idx, column=5, value=res.details)

            for c in range(1, 6):
                ws.cell(row=r_idx, column=c).border = cls.THIN_BORDER

    @classmethod
    def _build_vba_info_sheet(cls, ws):
        ws.views.sheetView[0].showGridLines = True
        ws["A2"] = "EXCEL VBA MACRO AUTOMATION GUIDE"
        ws["A2"].font = cls.TITLE_FONT

        instructions = [
            "This workbook is paired with an Excel VBA Macro module (reports/vba_macro.bas) to cut manual checking to under 10 seconds per run.",
            "",
            "HOW TO ENABLE AND RUN IN EXCEL:",
            "1. Press [ALT + F11] to open the Visual Basic for Applications Editor.",
            "2. Click File -> Import File... and select 'reports/vba_macro.bas' (or copy the code below into a new Module).",
            "3. Close the VBA Editor and return to Excel.",
            "4. Press [ALT + F8], select 'RunQuickReconciliationAudit', and click Run.",
            "",
            "VBA MACRO CAPABILITIES:",
            "• Instant 1-click filtering by Exception Category (Amount Mismatches, Missing Ledger, Missing Bank, Duplicates)",
            "• Automated Red Highlighting on High-Variance Transactions (> $1,000)",
            "• Auto-fitting columns and active dynamic filters across all worksheets",
            "• Execution duration tracker demonstrating < 10-second verification time"
        ]

        for idx, line in enumerate(instructions, start=4):
            ws.cell(row=idx, column=1, value=line).font = Font(name="Calibri", size=11, bold=line.startswith("HOW TO") or line.startswith("VBA MACRO"))

    @staticmethod
    def _autofit_columns(ws):
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                if cell.value:
                    val_str = str(cell.value)
                    # Limit multi-line cell width calculation
                    lines = val_str.split("\n")
                    longest_line = max(len(l) for l in lines)
                    max_len = max(max_len, longest_line)
            ws.column_dimensions[col_letter].width = min(max(max_len + 4, 12), 48)
