import pytest
import pandas as pd
from engine.validator import DataQualityValidator

def test_null_value_check():
    df_bank = pd.DataFrame([
        {"reference_id": "TXN-001", "amount": 100.0, "transaction_date": "2026-01-01"},
        {"reference_id": None, "amount": 200.0, "transaction_date": "2026-01-02"},
    ])
    df_ledger = pd.DataFrame([
        {"reference_id": "TXN-001", "amount": 100.0, "posting_date": "2026-01-01"},
    ])

    clean_bank, clean_ledger, dq_results, totals = DataQualityValidator.validate_and_clean(df_bank, df_ledger)

    assert len(clean_bank) == 1
    null_dq = [r for r in dq_results if r.check_name == "NULL_VALUE_CHECK" and r.source_name == "BANK"]
    assert len(null_dq) == 1
    assert null_dq[0].check_status == "WARNING"

def test_duplicate_id_check():
    df_bank = pd.DataFrame([
        {"reference_id": "TXN-DUP-1", "amount": 50.0, "transaction_date": "2026-01-01"},
        {"reference_id": "TXN-DUP-1", "amount": 50.0, "transaction_date": "2026-01-01"},
    ])
    df_ledger = pd.DataFrame([
        {"reference_id": "TXN-DUP-1", "amount": 50.0, "posting_date": "2026-01-01"},
    ])

    clean_bank, clean_ledger, dq_results, totals = DataQualityValidator.validate_and_clean(df_bank, df_ledger)
    dup_dq = [r for r in dq_results if r.check_name == "DUPLICATE_ID_CHECK" and r.source_name == "BANK"]
    assert len(dup_dq) == 1
    assert dup_dq[0].check_status == "WARNING"
    assert dup_dq[0].records_affected == 2

def test_control_totals():
    df_bank = pd.DataFrame([
        {"reference_id": "TXN-1", "amount": 500.50, "transaction_date": "2026-01-01"},
        {"reference_id": "TXN-2", "amount": 250.25, "transaction_date": "2026-01-02"},
    ])
    df_ledger = pd.DataFrame([
        {"reference_id": "TXN-1", "amount": 500.50, "posting_date": "2026-01-01"},
        {"reference_id": "TXN-2", "amount": 200.00, "posting_date": "2026-01-02"},
    ])

    _, _, _, totals = DataQualityValidator.validate_and_clean(df_bank, df_ledger)
    assert round(totals["bank_control_total"], 2) == 750.75
    assert round(totals["ledger_control_total"], 2) == 700.50
    assert round(totals["net_variance"], 2) == 50.25
