import pytest
import pandas as pd
from engine.reconciler import ReconciliationEngine

@pytest.fixture
def reconciler():
    return ReconciliationEngine(date_tolerance_days=3, amount_tolerance=0.0)

def test_exact_match(reconciler):
    df_bank = pd.DataFrame([
        {"reference_id": "TXN-EXACT-1", "amount": 1250.00, "transaction_date": "2026-03-15", "description": "Payment"}
    ])
    df_ledger = pd.DataFrame([
        {"reference_id": "TXN-EXACT-1", "amount": 1250.00, "posting_date": "2026-03-15", "description": "Payment"}
    ])

    summary = reconciler.reconcile(df_bank, df_ledger)
    assert summary.total_matched == 1
    assert summary.exact_matches == 1
    assert summary.total_unmatched == 0

def test_date_tolerance_match(reconciler):
    df_bank = pd.DataFrame([
        {"reference_id": "TXN-TOL-1", "amount": 800.00, "transaction_date": "2026-03-17", "description": "ACH Clear"}
    ])
    df_ledger = pd.DataFrame([
        {"reference_id": "TXN-TOL-1", "amount": 800.00, "posting_date": "2026-03-15", "description": "ACH Post"}
    ])

    summary = reconciler.reconcile(df_bank, df_ledger)
    assert summary.total_matched == 1
    assert summary.tolerance_matches == 1
    assert summary.total_unmatched == 0

def test_amount_mismatch_exception(reconciler):
    df_bank = pd.DataFrame([
        {"reference_id": "TXN-AMT-1", "amount": 500.00, "transaction_date": "2026-03-15", "description": "Bank Fee included"}
    ])
    df_ledger = pd.DataFrame([
        {"reference_id": "TXN-AMT-1", "amount": 475.00, "posting_date": "2026-03-15", "description": "Invoice"}
    ])

    summary = reconciler.reconcile(df_bank, df_ledger)
    assert summary.total_matched == 0
    assert summary.amount_mismatches == 1
    assert summary.df_exceptions.iloc[0]["exception_category"] == "AMOUNT_MISMATCH"
    assert round(summary.df_exceptions.iloc[0]["amount_diff"], 2) == 25.00

def test_missing_in_ledger_exception(reconciler):
    df_bank = pd.DataFrame([
        {"reference_id": "TXN-BANK-ONLY", "amount": 150.00, "transaction_date": "2026-03-15", "description": "Interest"}
    ])
    df_ledger = pd.DataFrame(columns=["reference_id", "amount", "posting_date", "description"])

    summary = reconciler.reconcile(df_bank, df_ledger)
    assert summary.missing_in_ledger == 1
    assert summary.df_exceptions.iloc[0]["exception_category"] == "MISSING_IN_LEDGER"

def test_missing_in_bank_exception(reconciler):
    df_bank = pd.DataFrame(columns=["reference_id", "amount", "transaction_date", "description"])
    df_ledger = pd.DataFrame([
        {"reference_id": "TXN-LEDGER-ONLY", "amount": 320.00, "posting_date": "2026-03-15", "description": "Unpresented Cheque"}
    ])

    summary = reconciler.reconcile(df_bank, df_ledger)
    assert summary.missing_in_bank == 1
    assert summary.df_exceptions.iloc[0]["exception_category"] == "MISSING_IN_BANK"
