import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import pandas as pd
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, DateTime, Text, Numeric, Index, inspect
)
from sqlalchemy.orm import declarative_base, sessionmaker
from config.settings import settings

logger = logging.getLogger("ReconciliationDB")
Base = declarative_base()

def get_utc_now():
    return datetime.now(timezone.utc)

class BatchRunModel(Base):
    __tablename__ = "reconciliation_batches"

    batch_id = Column(String(64), primary_key=True)
    run_timestamp = Column(DateTime, default=get_utc_now)
    status = Column(String(32), nullable=False)
    total_bank_records = Column(Integer, nullable=False)
    total_ledger_records = Column(Integer, nullable=False)
    total_matched = Column(Integer, nullable=False)
    total_unmatched = Column(Integer, nullable=False)
    exact_matches = Column(Integer, nullable=False)
    tolerance_matches = Column(Integer, nullable=False)
    amount_mismatches = Column(Integer, nullable=False)
    missing_in_ledger = Column(Integer, nullable=False)
    missing_in_bank = Column(Integer, nullable=False)
    duplicate_records = Column(Integer, nullable=False)
    bank_control_total = Column(Float, nullable=False)
    ledger_control_total = Column(Float, nullable=False)
    net_variance = Column(Float, nullable=False)
    execution_duration_sec = Column(Float, nullable=False)
    report_file_path = Column(String(255), nullable=True)

class ExceptionModel(Base):
    __tablename__ = "reconciliation_exceptions"

    exception_id = Column(Integer, primary_key=True, autoincrement=True)
    batch_id = Column(String(64), nullable=False, index=True)
    reference_id = Column(String(64), nullable=True, index=True)
    exception_category = Column(String(64), nullable=False, index=True)
    bank_date = Column(String(32), nullable=True)
    ledger_date = Column(String(32), nullable=True)
    bank_amount = Column(Float, nullable=True)
    ledger_amount = Column(Float, nullable=True)
    amount_difference = Column(Float, nullable=True)
    description = Column(Text, nullable=True)
    resolution_status = Column(String(32), default="PENDING_REVIEW")
    created_at = Column(DateTime, default=get_utc_now)

class DQLogModel(Base):
    __tablename__ = "dq_audit_logs"

    log_id = Column(Integer, primary_key=True, autoincrement=True)
    batch_id = Column(String(64), nullable=False, index=True)
    source_name = Column(String(32), nullable=False)
    check_name = Column(String(64), nullable=False)
    check_status = Column(String(16), nullable=False)
    records_affected = Column(Integer, default=0)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=get_utc_now)



class DatabaseManager:
    """
    Handles persisting reconciliation audit trails, batches, and exception logs.
    Gracefully connects to MySQL with automatic fallback to SQLite for local standalone runs.
    """
    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or settings.database_url
        try:
            self.engine = create_engine(self.db_url, echo=False, pool_pre_ping=True)
            self._init_db()
        except Exception as e:
            logger.warning(f"Could not connect to configured DB ({self.db_url}): {e}. Falling back to SQLite.")
            fallback_url = f"sqlite:///{settings.SQLITE_PATH}"
            self.engine = create_engine(fallback_url, echo=False)
            self._init_db()

        self.Session = sessionmaker(bind=self.engine)

    def _init_db(self):
        """Creates tables if they don't exist."""
        Base.metadata.create_all(self.engine)

    def save_batch_summary(self, summary_data: Dict[str, Any]):
        """Saves overall batch execution metrics."""
        session = self.Session()
        try:
            batch = BatchRunModel(**summary_data)
            session.merge(batch)
            session.commit()
            logger.info(f"Saved batch summary for ID: {summary_data.get('batch_id')}")
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save batch summary: {e}")
            raise
        finally:
            session.close()

    def save_exceptions(self, batch_id: str, df_exceptions: pd.DataFrame):
        """Saves classified exceptions into the database for audit trail."""
        if df_exceptions.empty:
            return

        session = self.Session()
        try:
            records = []
            for _, row in df_exceptions.iterrows():
                rec = ExceptionModel(
                    batch_id=batch_id,
                    reference_id=str(row.get("reference_id", "")),
                    exception_category=str(row.get("exception_category", "UNKNOWN")),
                    bank_date=str(row.get("bank_date", "")),
                    ledger_date=str(row.get("ledger_date", "")),
                    bank_amount=float(row.get("bank_amount", 0.0)) if pd.notnull(row.get("bank_amount")) else None,
                    ledger_amount=float(row.get("ledger_amount", 0.0)) if pd.notnull(row.get("ledger_amount")) else None,
                    amount_difference=float(row.get("amount_diff", 0.0)) if pd.notnull(row.get("amount_diff")) else None,
                    description=str(row.get("description", ""))
                )
                records.append(rec)
            
            session.bulk_save_objects(records)
            session.commit()
            logger.info(f"Saved {len(records)} exception records to audit trail database.")
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save exceptions: {e}")
            raise
        finally:
            session.close()

    def save_dq_logs(self, batch_id: str, dq_results: List[Dict[str, Any]]):
        """Logs data quality check results."""
        if not dq_results:
            return

        session = self.Session()
        try:
            records = []
            for item in dq_results:
                rec = DQLogModel(
                    batch_id=batch_id,
                    source_name=item.get("source_name", "UNKNOWN"),
                    check_name=item.get("check_name", "UNKNOWN"),
                    check_status=item.get("check_status", "UNKNOWN"),
                    records_affected=item.get("records_affected", 0),
                    details=item.get("details", "")
                )
                records.append(rec)
            
            session.bulk_save_objects(records)
            session.commit()
            logger.info(f"Saved {len(records)} Data Quality check logs.")
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save DQ logs: {e}")
            raise
        finally:
            session.close()

    def fetch_batch_history(self, limit: int = 10) -> pd.DataFrame:
        """Fetches recent batch runs."""
        query = f"SELECT * FROM {BatchRunModel.__tablename__} ORDER BY run_timestamp DESC LIMIT {limit}"
        return pd.read_sql(query, self.engine)
