CREATE DATABASE IF NOT EXISTS reconciliation_db;
USE reconciliation_db;

CREATE TABLE IF NOT EXISTS reconciliation_batches (
    batch_id VARCHAR(64) PRIMARY KEY,
    run_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(32) NOT NULL,
    total_bank_records INT NOT NULL,
    total_ledger_records INT NOT NULL,
    total_matched INT NOT NULL,
    total_unmatched INT NOT NULL,
    exact_matches INT NOT NULL,
    tolerance_matches INT NOT NULL,
    amount_mismatches INT NOT NULL,
    missing_in_ledger INT NOT NULL,
    missing_in_bank INT NOT NULL,
    duplicate_records INT NOT NULL,
    bank_control_total DECIMAL(18, 2) NOT NULL,
    ledger_control_total DECIMAL(18, 2) NOT NULL,
    net_variance DECIMAL(18, 2) NOT NULL,
    execution_duration_sec DECIMAL(8, 3) NOT NULL,
    report_file_path VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS reconciliation_exceptions (
    exception_id INT AUTO_INCREMENT PRIMARY KEY,
    batch_id VARCHAR(64) NOT NULL,
    reference_id VARCHAR(64),
    exception_category VARCHAR(64) NOT NULL,
    bank_date VARCHAR(32),
    ledger_date VARCHAR(32),
    bank_amount DECIMAL(18, 2),
    ledger_amount DECIMAL(18, 2),
    amount_difference DECIMAL(18, 2),
    description TEXT,
    resolution_status VARCHAR(32) DEFAULT 'PENDING_REVIEW',
    resolved_by VARCHAR(64),
    resolved_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_batch (batch_id),
    INDEX idx_category (exception_category),
    INDEX idx_ref (reference_id)
);

CREATE TABLE IF NOT EXISTS dq_audit_logs (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    batch_id VARCHAR(64) NOT NULL,
    source_name VARCHAR(32) NOT NULL,
    check_name VARCHAR(64) NOT NULL,
    check_status VARCHAR(16) NOT NULL,
    records_affected INT DEFAULT 0,
    details TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_batch (batch_id)
);
