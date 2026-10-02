from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
import pandas as pd

@dataclass
class DQCheckResult:
    source_name: str
    check_name: str
    check_status: str
    records_affected: int
    details: str

@dataclass
class ReconciliationSummary:
    batch_id: str
    status: str
    total_bank_records: int
    total_ledger_records: int
    total_matched: int
    total_unmatched: int
    exact_matches: int
    tolerance_matches: int
    amount_mismatches: int
    missing_in_ledger: int
    missing_in_bank: int
    duplicate_records: int
    bank_control_total: float
    ledger_control_total: float
    net_variance: float
    execution_duration_sec: float
    df_matched: Optional[pd.DataFrame] = None
    df_exceptions: Optional[pd.DataFrame] = None
    dq_results: List[DQCheckResult] = field(default_factory=list)
    report_file_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "status": self.status,
            "total_bank_records": self.total_bank_records,
            "total_ledger_records": self.total_ledger_records,
            "total_matched": self.total_matched,
            "total_unmatched": self.total_unmatched,
            "exact_matches": self.exact_matches,
            "tolerance_matches": self.tolerance_matches,
            "amount_mismatches": self.amount_mismatches,
            "missing_in_ledger": self.missing_in_ledger,
            "missing_in_bank": self.missing_in_bank,
            "duplicate_records": self.duplicate_records,
            "bank_control_total": round(self.bank_control_total, 2),
            "ledger_control_total": round(self.ledger_control_total, 2),
            "net_variance": round(self.net_variance, 2),
            "execution_duration_sec": round(self.execution_duration_sec, 3),
            "report_file_path": self.report_file_path
        }
