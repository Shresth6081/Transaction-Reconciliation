import os
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import numpy as np
from faker import Faker

fake = Faker()
Faker.seed(42)
random.seed(42)
np.random.seed(42)

def generate_transaction_datasets(
    total_records: int = 50000,
    output_dir: Path = None,
    exact_match_ratio: float = 0.88,
    date_shifted_ratio: float = 0.05,
    amount_mismatch_ratio: float = 0.025,
    missing_in_ledger_ratio: float = 0.02,
    missing_in_bank_ratio: float = 0.02,
    duplicate_ratio: float = 0.005
):
    """
    Generates synthetic 50,000+ Bank and General Ledger datasets with realistic
    reconciliation challenges (timing differences, amount typos, missing records, duplicates).
    """
    if output_dir is None:
        from config.settings import settings
        output_dir = settings.RAW_DATA_DIR

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    start_date = datetime(2026, 1, 1)
    end_date = datetime(2026, 6, 30)
    date_range_days = (end_date - start_date).days

    num_exact = int(total_records * exact_match_ratio)
    num_shifted = int(total_records * date_shifted_ratio)
    num_amount_diff = int(total_records * amount_mismatch_ratio)
    num_missing_ledger = int(total_records * missing_in_ledger_ratio)
    num_missing_bank = int(total_records * missing_in_bank_ratio)
    num_duplicates = int(total_records * duplicate_ratio)

    bank_rows = []
    ledger_rows = []

    descriptions = [
        "Vendor Payment - AWS Cloud Services",
        "Client Settlement - Stripe Payout",
        "Payroll Direct Deposit - Tech Staff",
        "Office Supplies - Staples Corp",
        "Consulting Services - McKinsey & Co",
        "Subscription Fee - Bloomberg Terminal",
        "Corporate Card Settlement - Amex",
        "Utility Bill - ConEdison Electric",
        "Software License - Salesforce CRM",
        "Legal Retainer - Baker McKenzie",
        "Logistics & Freight - FedEx Express",
        "Marketing Agency - Omnicom Media"
    ]

    tx_types = ["DEBIT", "CREDIT"]

    # Helper to generate random timestamp
    def rand_date():
        return start_date + timedelta(days=random.randint(0, date_range_days), hours=random.randint(8, 18), minutes=random.randint(0, 59))

    # Helper to format reference ID
    def make_ref_id(idx):
        return f"TXN-2026-{idx:07d}"

    current_idx = 1000000

    # 1. Exact Matches (Ref ID, Amount, and Date match)
    for _ in range(num_exact):
        ref_id = make_ref_id(current_idx)
        current_idx += 1
        dt = rand_date()
        amt = round(random.uniform(15.00, 150000.00), 2)
        desc = random.choice(descriptions)
        ttype = random.choice(tx_types)

        bank_rows.append({
            "bank_tx_id": f"BNK-{uuid.uuid4().hex[:8].upper()}",
            "reference_id": ref_id,
            "transaction_date": dt.strftime("%Y-%m-%d"),
            "amount": amt,
            "type": ttype,
            "description": desc,
            "bank_account": "ACC-99281001",
            "currency": "USD"
        })

        ledger_rows.append({
            "ledger_entry_id": f"GL-{uuid.uuid4().hex[:8].upper()}",
            "reference_id": ref_id,
            "posting_date": dt.strftime("%Y-%m-%d"),
            "amount": amt,
            "type": ttype,
            "description": desc,
            "account_code": "GL-1010-CASH",
            "currency": "USD"
        })

    # 2. Date Shifted Matches (Bank clearance delayed by 1 to 3 days within tolerance)
    for _ in range(num_shifted):
        ref_id = make_ref_id(current_idx)
        current_idx += 1
        ledger_dt = rand_date()
        # Delay bank date by 1 to 3 days
        day_offset = random.choice([-2, -1, 1, 2, 3])
        bank_dt = ledger_dt + timedelta(days=day_offset)
        amt = round(random.uniform(50.00, 85000.00), 2)
        desc = random.choice(descriptions)
        ttype = random.choice(tx_types)

        bank_rows.append({
            "bank_tx_id": f"BNK-{uuid.uuid4().hex[:8].upper()}",
            "reference_id": ref_id,
            "transaction_date": bank_dt.strftime("%Y-%m-%d"),
            "amount": amt,
            "type": ttype,
            "description": f"{desc} [ACH Clear]",
            "bank_account": "ACC-99281001",
            "currency": "USD"
        })

        ledger_rows.append({
            "ledger_entry_id": f"GL-{uuid.uuid4().hex[:8].upper()}",
            "reference_id": ref_id,
            "posting_date": ledger_dt.strftime("%Y-%m-%d"),
            "amount": amt,
            "type": ttype,
            "description": desc,
            "account_code": "GL-1010-CASH",
            "currency": "USD"
        })

    # 3. Amount Mismatch (Same Ref ID, different amounts due to bank fee, forex, or manual typo)
    for _ in range(num_amount_diff):
        ref_id = make_ref_id(current_idx)
        current_idx += 1
        dt = rand_date()
        base_amt = round(random.uniform(100.00, 50000.00), 2)
        # Bank amount has fee or typo (e.g. +/- $5 to $150 or decimal transposition)
        diff = round(random.choice([-150.00, -25.50, -10.00, 12.00, 45.75, 100.00]), 2)
        bank_amt = max(1.0, round(base_amt + diff, 2))
        desc = random.choice(descriptions)
        ttype = random.choice(tx_types)

        bank_rows.append({
            "bank_tx_id": f"BNK-{uuid.uuid4().hex[:8].upper()}",
            "reference_id": ref_id,
            "transaction_date": dt.strftime("%Y-%m-%d"),
            "amount": bank_amt,
            "type": ttype,
            "description": f"{desc} [Disputed Amt]",
            "bank_account": "ACC-99281001",
            "currency": "USD"
        })

        ledger_rows.append({
            "ledger_entry_id": f"GL-{uuid.uuid4().hex[:8].upper()}",
            "reference_id": ref_id,
            "posting_date": dt.strftime("%Y-%m-%d"),
            "amount": base_amt,
            "type": ttype,
            "description": desc,
            "account_code": "GL-1010-CASH",
            "currency": "USD"
        })

    # 4. Missing in Ledger (Bank has entry, ledger missing -> bank fee, direct deposit, unrecorded wire)
    for _ in range(num_missing_ledger):
        ref_id = make_ref_id(current_idx)
        current_idx += 1
        dt = rand_date()
        amt = round(random.uniform(25.00, 12000.00), 2)
        desc = random.choice(["Direct Wire Credit", "Bank Service Charge", "Merchant Terminal Fee", "Interest Income"])
        ttype = "DEBIT" if "Fee" in desc or "Charge" in desc else "CREDIT"

        bank_rows.append({
            "bank_tx_id": f"BNK-{uuid.uuid4().hex[:8].upper()}",
            "reference_id": ref_id,
            "transaction_date": dt.strftime("%Y-%m-%d"),
            "amount": amt,
            "type": ttype,
            "description": desc,
            "bank_account": "ACC-99281001",
            "currency": "USD"
        })

    # 5. Missing in Bank (Ledger has entry, bank missing -> outstanding check, unpresented draft)
    for _ in range(num_missing_bank):
        ref_id = make_ref_id(current_idx)
        current_idx += 1
        dt = rand_date()
        amt = round(random.uniform(50.00, 20000.00), 2)
        desc = random.choice(["Outstanding Supplier Check #4091", "Unpresented Warrant", "Manual Journal Draft"])
        ttype = "DEBIT"

        ledger_rows.append({
            "ledger_entry_id": f"GL-{uuid.uuid4().hex[:8].upper()}",
            "reference_id": ref_id,
            "posting_date": dt.strftime("%Y-%m-%d"),
            "amount": amt,
            "type": ttype,
            "description": desc,
            "account_code": "GL-1010-CASH",
            "currency": "USD"
        })

    # 6. Duplicates (Duplicate entries in Ledger or Bank)
    for _ in range(num_duplicates):
        ref_id = make_ref_id(current_idx)
        current_idx += 1
        dt = rand_date()
        amt = round(random.uniform(100.00, 5000.00), 2)
        desc = "Duplicate Vendor Invoice Submission"
        ttype = "DEBIT"

        # Bank has 1 entry, Ledger accidentally posted twice
        bank_rows.append({
            "bank_tx_id": f"BNK-{uuid.uuid4().hex[:8].upper()}",
            "reference_id": ref_id,
            "transaction_date": dt.strftime("%Y-%m-%d"),
            "amount": amt,
            "type": ttype,
            "description": desc,
            "bank_account": "ACC-99281001",
            "currency": "USD"
        })

        # Entry 1
        ledger_rows.append({
            "ledger_entry_id": f"GL-{uuid.uuid4().hex[:8].upper()}",
            "reference_id": ref_id,
            "posting_date": dt.strftime("%Y-%m-%d"),
            "amount": amt,
            "type": ttype,
            "description": desc,
            "account_code": "GL-1010-CASH",
            "currency": "USD"
        })

        # Duplicate Entry 2
        ledger_rows.append({
            "ledger_entry_id": f"GL-{uuid.uuid4().hex[:8].upper()}",
            "reference_id": ref_id,
            "posting_date": dt.strftime("%Y-%m-%d"),
            "amount": amt,
            "type": ttype,
            "description": f"{desc} (Duplicate Entry)",
            "account_code": "GL-1010-CASH",
            "currency": "USD"
        })

    # Shuffle datasets to simulate realistic unsorted transaction feeds
    random.shuffle(bank_rows)
    random.shuffle(ledger_rows)

    df_bank = pd.DataFrame(bank_rows)
    df_ledger = pd.DataFrame(ledger_rows)

    bank_file = output_dir / "bank_transactions.csv"
    ledger_file = output_dir / "ledger_transactions.csv"

    df_bank.to_csv(bank_file, index=False)
    df_ledger.to_csv(ledger_file, index=False)

    print(f"[Dataset Generator] Successfully generated:")
    print(f" - Bank records:   {len(df_bank):,} rows -> {bank_file}")
    print(f" - Ledger records: {len(df_ledger):,} rows -> {ledger_file}")
    print(f" - Total simulated transactions: {len(df_bank) + len(df_ledger):,}")
    
    return bank_file, ledger_file

if __name__ == "__main__":
    generate_transaction_datasets(total_records=50000)
