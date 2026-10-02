import logging
from typing import Tuple, List, Dict, Any
import pandas as pd
import numpy as np
from engine.models import DQCheckResult

logger = logging.getLogger("DataValidator")

class DataQualityValidator:
    """
    Performs comprehensive data hygiene and integrity checks:
    - Null / Missing field validations
    - Duplicate Reference ID detection
    - Data format normalization (Dates, Numeric Amounts)
    - Control total reconciliation checksums
    """

    @staticmethod
    def validate_and_clean(
        df_bank_raw: pd.DataFrame,
        df_ledger_raw: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.DataFrame, List[DQCheckResult], Dict[str, float]]:
        """
        Validates, sanitizes, and computes control totals for Bank and Ledger datasets.
        """
        dq_results: List[DQCheckResult] = []
        df_bank = df_bank_raw.copy()
        df_ledger = df_ledger_raw.copy()

        # -------------------------------------------------------------
        # 1. Null / Missing Checks
        # -------------------------------------------------------------
        bank_nulls = df_bank[["reference_id", "amount", "transaction_date"]].isnull().sum().to_dict()
        ledger_nulls = df_ledger[["reference_id", "amount", "posting_date"]].isnull().sum().to_dict()

        total_bank_nulls = sum(bank_nulls.values())
        total_ledger_nulls = sum(ledger_nulls.values())

        if total_bank_nulls > 0:
            dq_results.append(DQCheckResult(
                source_name="BANK",
                check_name="NULL_VALUE_CHECK",
                check_status="WARNING",
                records_affected=int(total_bank_nulls),
                details=f"Found null values in bank records: {bank_nulls}"
            ))
        else:
            dq_results.append(DQCheckResult(
                source_name="BANK",
                check_name="NULL_VALUE_CHECK",
                check_status="PASSED",
                records_affected=0,
                details="Zero nulls found in critical fields (reference_id, amount, transaction_date)."
            ))

        if total_ledger_nulls > 0:
            dq_results.append(DQCheckResult(
                source_name="LEDGER",
                check_name="NULL_VALUE_CHECK",
                check_status="WARNING",
                records_affected=int(total_ledger_nulls),
                details=f"Found null values in ledger records: {ledger_nulls}"
            ))
        else:
            dq_results.append(DQCheckResult(
                source_name="LEDGER",
                check_name="NULL_VALUE_CHECK",
                check_status="PASSED",
                records_affected=0,
                details="Zero nulls found in critical fields (reference_id, amount, posting_date)."
            ))

        # Drop any completely unidentifiable records with null reference_id
        df_bank = df_bank.dropna(subset=["reference_id", "amount"])
        df_ledger = df_ledger.dropna(subset=["reference_id", "amount"])

        # -------------------------------------------------------------
        # 2. Type Standardizations & Date Parsing
        # -------------------------------------------------------------
        df_bank["reference_id"] = df_bank["reference_id"].astype(str).str.strip()
        df_ledger["reference_id"] = df_ledger["reference_id"].astype(str).str.strip()

        df_bank["amount"] = pd.to_numeric(df_bank["amount"], errors="coerce").fillna(0.0)
        df_ledger["amount"] = pd.to_numeric(df_ledger["amount"], errors="coerce").fillna(0.0)

        df_bank["transaction_date"] = pd.to_datetime(df_bank["transaction_date"], errors="coerce")
        df_ledger["posting_date"] = pd.to_datetime(df_ledger["posting_date"], errors="coerce")

        # -------------------------------------------------------------
        # 3. Duplicate ID Checks
        # -------------------------------------------------------------
        bank_dupes_count = int(df_bank.duplicated(subset=["reference_id"], keep=False).sum())
        ledger_dupes_count = int(df_ledger.duplicated(subset=["reference_id"], keep=False).sum())

        if bank_dupes_count > 0:
            dq_results.append(DQCheckResult(
                source_name="BANK",
                check_name="DUPLICATE_ID_CHECK",
                check_status="WARNING",
                records_affected=bank_dupes_count,
                details=f"Detected {bank_dupes_count} bank rows sharing duplicate reference IDs."
            ))
        else:
            dq_results.append(DQCheckResult(
                source_name="BANK",
                check_name="DUPLICATE_ID_CHECK",
                check_status="PASSED",
                records_affected=0,
                details="All bank reference IDs are unique."
            ))

        if ledger_dupes_count > 0:
            dq_results.append(DQCheckResult(
                source_name="LEDGER",
                check_name="DUPLICATE_ID_CHECK",
                check_status="WARNING",
                records_affected=ledger_dupes_count,
                details=f"Detected {ledger_dupes_count} ledger rows sharing duplicate reference IDs."
            ))
        else:
            dq_results.append(DQCheckResult(
                source_name="LEDGER",
                check_name="DUPLICATE_ID_CHECK",
                check_status="PASSED",
                records_affected=0,
                details="All ledger reference IDs are unique."
            ))

        # -------------------------------------------------------------
        # 4. Control Totals & Checksums
        # -------------------------------------------------------------
        bank_total_sum = float(df_bank["amount"].sum())
        ledger_total_sum = float(df_ledger["amount"].sum())
        control_variance = bank_total_sum - ledger_total_sum

        control_totals = {
            "bank_control_total": bank_total_sum,
            "ledger_control_total": ledger_total_sum,
            "net_variance": control_variance,
            "bank_row_count": len(df_bank),
            "ledger_row_count": len(df_ledger)
        }

        dq_results.append(DQCheckResult(
            source_name="RECONCILIATION",
            check_name="CONTROL_TOTAL_CHECKSUM",
            check_status="PASSED" if abs(control_variance) < 1e-4 else "FLAGGED_VARIANCE",
            records_affected=0,
            details=f"Bank Total: ${bank_total_sum:,.2f} | Ledger Total: ${ledger_total_sum:,.2f} | Variance: ${control_variance:,.2f}"
        ))

        logger.info(f"Data Quality Validation complete. Bank Rows: {len(df_bank):,}, Ledger Rows: {len(df_ledger):,}")
        return df_bank, df_ledger, dq_results, control_totals
