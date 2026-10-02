import pytest
import os
import pandas as pd
from database.db_manager import DatabaseManager

def test_database_logging(tmp_path):
    db_file = tmp_path / "test_reconciliation.db"
    db_url = f"sqlite:///{db_file}"
    db = DatabaseManager(db_url=db_url)

    batch_id = "BATCH-TEST-001"
    summary_data = {
        "batch_id": batch_id,
        "status": "COMPLETED_WITH_EXCEPTIONS",
        "total_bank_records": 100,
        "total_ledger_records": 100,
        "total_matched": 95,
        "total_unmatched": 5,
        "exact_matches": 90,
        "tolerance_matches": 5,
        "amount_mismatches": 2,
        "missing_in_ledger": 1,
        "missing_in_bank": 1,
        "duplicate_records": 1,
        "bank_control_total": 50000.0,
        "ledger_control_total": 49800.0,
        "net_variance": 200.0,
        "execution_duration_sec": 0.45,
        "report_file_path": "/path/to/report.xlsx"
    }

    # Save summary
    db.save_batch_summary(summary_data)

    # Save exceptions
    df_ex = pd.DataFrame([
        {
            "reference_id": "TXN-TEST-1",
            "exception_category": "AMOUNT_MISMATCH",
            "bank_date": "2026-01-01",
            "ledger_date": "2026-01-01",
            "bank_amount": 100.0,
            "ledger_amount": 90.0,
            "amount_diff": 10.0,
            "description": "Fee variance"
        }
    ])
    db.save_exceptions(batch_id, df_ex)

    # Fetch history
    history = db.fetch_batch_history(limit=5)
    assert not history.empty
    assert history.iloc[0]["batch_id"] == batch_id
    assert history.iloc[0]["total_matched"] == 95
