"""
JagatData - SQLite database layer.
Uses plain sqlite3 (no heavy ORM) to keep the hackathon MVP fast and transparent.
"""
import sqlite3
import os
import json
from contextlib import contextmanager
from datetime import datetime

DB_PATH = os.environ.get("DATABASE_URL", os.path.join(os.path.dirname(__file__), "jagatdata.db"))


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db():
    conn = get_conn()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


SCHEMA = """
-- Unified Citizen Master (golden record + linked source records)
CREATE TABLE IF NOT EXISTS citizens (
    citizen_id TEXT PRIMARY KEY,
    full_name TEXT,
    dob TEXT,
    gender TEXT,
    phone TEXT,
    address TEXT,
    aadhaar_last4 TEXT,
    created_at TEXT,
    updated_at TEXT
);

-- Every raw record ingested from a department, linked (or not yet linked) to a citizen
CREATE TABLE IF NOT EXISTS source_records (
    record_id TEXT PRIMARY KEY,
    department TEXT,
    source_ref_id TEXT,
    citizen_id TEXT,
    raw_name TEXT,
    raw_dob TEXT,
    raw_gender TEXT,
    raw_phone TEXT,
    raw_address TEXT,
    raw_aadhaar_last4 TEXT,
    extra_json TEXT,
    ingested_at TEXT,
    FOREIGN KEY (citizen_id) REFERENCES citizens(citizen_id)
);

-- Candidate duplicate/match pairs awaiting or resolved by officer review
CREATE TABLE IF NOT EXISTS match_candidates (
    match_id TEXT PRIMARY KEY,
    record_id_a TEXT,
    record_id_b TEXT,
    score REAL,
    decision TEXT,           -- 'probable_duplicate' | 'manual_review' | 'probably_different'
    reason TEXT,
    status TEXT DEFAULT 'pending',   -- 'pending' | 'confirmed' | 'rejected'
    reviewed_by TEXT,
    reviewed_at TEXT,
    created_at TEXT
);

-- Applications (service requests) tracked across departments
CREATE TABLE IF NOT EXISTS applications (
    application_id TEXT PRIMARY KEY,
    citizen_id TEXT,
    department TEXT,
    service_name TEXT,
    status TEXT,              -- configurable workflow status
    priority TEXT DEFAULT 'normal',
    submitted_at TEXT,
    updated_at TEXT,
    assigned_officer TEXT,
    notes TEXT
);

-- Workflow status history for applications (configurable workflow tracking)
CREATE TABLE IF NOT EXISTS workflow_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id TEXT,
    from_status TEXT,
    to_status TEXT,
    changed_by TEXT,
    changed_at TEXT,
    comment TEXT
);

-- Grievances
CREATE TABLE IF NOT EXISTS grievances (
    grievance_id TEXT PRIMARY KEY,
    citizen_id TEXT,
    department TEXT,
    subject TEXT,
    description TEXT,
    status TEXT DEFAULT 'open',
    priority TEXT DEFAULT 'normal',
    filed_at TEXT,
    resolved_at TEXT,
    assigned_officer TEXT
);

-- Beneficiary / scheme outcome tracking
CREATE TABLE IF NOT EXISTS beneficiaries (
    beneficiary_id TEXT PRIMARY KEY,
    citizen_id TEXT,
    department TEXT,
    scheme_name TEXT,
    status TEXT,
    benefit_value TEXT,
    start_date TEXT,
    last_updated TEXT
);

-- Consent records before cross-department data sharing
CREATE TABLE IF NOT EXISTS consents (
    consent_id TEXT PRIMARY KEY,
    citizen_id TEXT,
    requesting_department TEXT,
    data_scope TEXT,
    purpose TEXT,
    status TEXT DEFAULT 'pending',   -- pending | granted | denied | revoked
    requested_at TEXT,
    responded_at TEXT,
    expires_at TEXT
);

-- Audit log for every significant system action
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    actor TEXT,
    role TEXT,
    action TEXT,
    entity_type TEXT,
    entity_id TEXT,
    details TEXT,
    timestamp TEXT
);

-- API / sync monitoring log (connector health, failed syncs)
CREATE TABLE IF NOT EXISTS api_monitor_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    connector TEXT,
    status TEXT,        -- success | failed
    records_processed INTEGER,
    records_failed INTEGER,
    error_detail TEXT,
    started_at TEXT,
    finished_at TEXT
);

-- Users for role-based access (demo only - plaintext for hackathon simplicity)
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password TEXT,
    role TEXT,           -- Admin | Officer | Reviewer
    department TEXT,
    full_name TEXT
);
"""

DEFAULT_USERS = [
    ("admin", "admin123", "Admin", "All", "System Administrator"),
    ("officer1", "officer123", "Officer", "Health", "Officer - Health Dept"),
    ("officer2", "officer123", "Officer", "Welfare", "Officer - Welfare Dept"),
    ("reviewer1", "reviewer123", "Reviewer", "All", "Data Quality Reviewer"),
]


def init_db():
    with db() as conn:
        conn.executescript(SCHEMA)
        cur = conn.execute("SELECT COUNT(*) c FROM users")
        if cur.fetchone()["c"] == 0:
            conn.executemany(
                "INSERT INTO users (username, password, role, department, full_name) VALUES (?,?,?,?,?)",
                DEFAULT_USERS,
            )


def now_iso():
    return datetime.utcnow().isoformat()


def log_audit(actor, role, action, entity_type, entity_id, details=""):
    with db() as conn:
        conn.execute(
            "INSERT INTO audit_logs (actor, role, action, entity_type, entity_id, details, timestamp) "
            "VALUES (?,?,?,?,?,?,?)",
            (actor, role, action, entity_type, entity_id,
             json.dumps(details) if not isinstance(details, str) else details, now_iso()),
        )


def log_monitor(connector, status, processed, failed, error_detail, started_at, finished_at):
    with db() as conn:
        conn.execute(
            "INSERT INTO api_monitor_logs (connector, status, records_processed, records_failed, "
            "error_detail, started_at, finished_at) VALUES (?,?,?,?,?,?,?)",
            (connector, status, processed, failed, error_detail, started_at, finished_at),
        )
