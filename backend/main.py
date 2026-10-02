"""
JagatData - Interoperability Middleware MVP
FastAPI backend: connectors, unified schema, duplicate detection, consent,
application/grievance/beneficiary tracking, audit, monitoring, and
event-driven n8n notifications.
"""
import os
import io
import json
import uuid
from datetime import datetime, timedelta
from typing import Optional, List

import pandas as pd
import requests
from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.database import db, init_db, now_iso, log_audit, log_monitor
from backend import connectors, matching, auth

N8N_WEBHOOK_URL = os.environ.get("N8N_WEBHOOK_URL", "http://localhost:5678/webhook/jagatdata-alerts")

app = FastAPI(title="JagatData API", description="Connecting Government Systems. Simplifying Public Services.",
              version="1.0.0")

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    """Initialize database and auto-load sample data on first run."""
    init_db()
    
    # Check if we have sample data already loaded
    with db() as conn:
        count = conn.execute("SELECT COUNT(*) FROM source_records").fetchone()[0]
    
    if count == 0:
        print("\n" + "="*70)
        print("🏛️  JagatData: First startup detected — auto-loading sample data...")
        print("="*70)
        
        # Auto-load sample data for all three departments
        for department, filename in [
            ("Health", "health_department.csv"),
            ("Education", "education_department.csv"),
            ("Welfare", "welfare_department.csv"),
        ]:
            try:
                data_path = os.path.join(os.path.dirname(__file__), "..", "data", filename)
                if os.path.exists(data_path):
                    df = pd.read_csv(data_path)
                    records, quality_report = connectors.run_connector(department, df)
                    
                    inserted, failed = 0, 0
                    with db() as conn:
                        for rec in records:
                            try:
                                record_id = f"REC-{department[:3].upper()}-{uuid.uuid4().hex[:10]}"
                                conn.execute(
                                    "INSERT INTO source_records (record_id, department, source_ref_id, citizen_id, "
                                    "raw_name, raw_dob, raw_gender, raw_phone, raw_address, raw_aadhaar_last4, "
                                    "extra_json, ingested_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                                    (record_id, department, str(rec.get("source_ref_id") or ""), None,
                                     str(rec.get("name") or ""), str(rec.get("dob") or ""), str(rec.get("gender") or ""),
                                     str(rec.get("phone") or ""), str(rec.get("address") or ""),
                                     str(rec.get("aadhaar_last4") or ""),
                                     json.dumps({**(rec.get("extra") or {}), "_issues": rec.get("_issues", [])}),
                                     now_iso()),
                                )
                                inserted += 1
                            except Exception as e:
                                failed += 1
                    
                    print(f"  ✅ {department:12} — loaded {inserted} records (quality: {quality_report['quality_score']}%)")
                else:
                    print(f"  ⚠️  {department:12} — sample file not found at {data_path}")
            except Exception as e:
                print(f"  ❌ {department:12} — error: {e}")
        
        print("\n✨ Sample data loaded! Ready to demo duplicate detection.\n")
    else:
        print(f"\n📊 JagatData backend ready (already have {count} source records).\n")


def notify_n8n(event_type: str, payload: dict):
    """Fire-and-forget event notification to n8n webhook. Never blocks the API on failure."""
    try:
        requests.post(N8N_WEBHOOK_URL, json={"event": event_type, "payload": payload,
                                              "timestamp": now_iso()}, timeout=2)
    except Exception:
        pass  # demo-grade: swallow network errors, event delivery is best-effort


# --------------------------------------------------------------------------------
# AUTH
# --------------------------------------------------------------------------------
class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/api/auth/login")
def login(req: LoginRequest):
    result = auth.authenticate(req.username, req.password)
    if not result:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token, session = result
    log_audit(session["username"], session["role"], "login", "session", token[:8], "User logged in")
    return {"token": token, "session": session}


@app.get("/api/auth/roles")
def list_demo_roles():
    return {
        "note": "Demo credentials for hackathon jury / testing",
        "accounts": [
            {"username": "admin", "password": "admin123", "role": "Admin"},
            {"username": "officer1", "password": "officer123", "role": "Officer (Health)"},
            {"username": "officer2", "password": "officer123", "role": "Officer (Welfare)"},
            {"username": "reviewer1", "password": "reviewer123", "role": "Reviewer"},
        ],
    }


# --------------------------------------------------------------------------------
# CONNECTORS / DATA INGESTION
# --------------------------------------------------------------------------------
@app.get("/api/connectors")
def list_connectors():
    with db() as conn:
        rows = conn.execute(
            "SELECT connector, status, records_processed, records_failed, error_detail, "
            "started_at, finished_at FROM api_monitor_logs ORDER BY id DESC LIMIT 25"
        ).fetchall()
    return {"registered_connectors": list(connectors.CONNECTOR_REGISTRY.keys()),
            "recent_syncs": [dict(r) for r in rows]}


@app.post("/api/connectors/{department}/upload")
async def upload_department_csv(department: str, file: UploadFile = File(...),
                                 session=Depends(auth.get_current_user)):
    auth.require_permission(session, "upload_data")
    started = now_iso()
    try:
        raw_bytes = await file.read()
        df = pd.read_csv(io.BytesIO(raw_bytes))
        records, quality_report = connectors.run_connector(department, df)

        inserted, failed = 0, 0
        with db() as conn:
            for rec in records:
                try:
                    record_id = f"REC-{department[:3].upper()}-{uuid.uuid4().hex[:10]}"
                    conn.execute(
                        "INSERT INTO source_records (record_id, department, source_ref_id, citizen_id, "
                        "raw_name, raw_dob, raw_gender, raw_phone, raw_address, raw_aadhaar_last4, "
                        "extra_json, ingested_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                        (record_id, department, str(rec.get("source_ref_id") or ""), None,
                         str(rec.get("name") or ""), str(rec.get("dob") or ""), str(rec.get("gender") or ""),
                         str(rec.get("phone") or ""), str(rec.get("address") or ""),
                         str(rec.get("aadhaar_last4") or ""),
                         json.dumps({**(rec.get("extra") or {}), "_issues": rec.get("_issues", [])}),
                         now_iso()),
                    )
                    inserted += 1
                except Exception:
                    failed += 1

        finished = now_iso()
        log_monitor(f"{department}_csv_connector", "success" if failed == 0 else "partial_failure",
                    inserted, failed, "" if failed == 0 else f"{failed} rows failed to insert",
                    started, finished)
        log_audit(session["username"], session["role"], "upload_csv", "department", department,
                  f"Uploaded {inserted} records, {quality_report['flagged_rows']} flagged for quality issues")

        notify_n8n("data_ingested", {"department": department, "records_inserted": inserted,
                                      "quality_score": quality_report["quality_score"]})

        return {"status": "success", "department": department, "records_inserted": inserted,
                "records_failed": failed, "quality_report": quality_report}
    except connectors.ConnectorError as e:
        finished = now_iso()
        log_monitor(f"{department}_csv_connector", "failed", 0, 0, str(e), started, finished)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        finished = now_iso()
        log_monitor(f"{department}_csv_connector", "failed", 0, 0, str(e), started, finished)
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {e}")


@app.post("/api/connectors/{department}/load-sample")
def load_sample_data(department: str, session=Depends(auth.get_current_user)):
    """Loads bundled sample CSV for the given department (fast demo path)."""
    auth.require_permission(session, "upload_data")
    sample_map = {
        "Health": "health_department.csv",
        "Education": "education_department.csv",
        "Welfare": "welfare_department.csv",
    }
    if department not in sample_map:
        raise HTTPException(status_code=404, detail="No sample data for this department")
    path = os.path.join(os.path.dirname(__file__), "..", "data", sample_map[department])
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Sample file not found on server")
    with open(path, "rb") as f:
        content = f.read()

    class _FakeUpload:
        async def read(self_inner):
            return content
    import asyncio
    return asyncio.get_event_loop().run_until_complete(
        upload_department_csv(department, file=_FakeUpload(), session=session)
    ) if False else _sync_upload(department, content, session)


def _sync_upload(department, content, session):
    started = now_iso()
    df = pd.read_csv(io.BytesIO(content))
    records, quality_report = connectors.run_connector(department, df)
    inserted, failed = 0, 0
    with db() as conn:
        for rec in records:
            try:
                record_id = f"REC-{department[:3].upper()}-{uuid.uuid4().hex[:10]}"
                conn.execute(
                    "INSERT INTO source_records (record_id, department, source_ref_id, citizen_id, "
                    "raw_name, raw_dob, raw_gender, raw_phone, raw_address, raw_aadhaar_last4, "
                    "extra_json, ingested_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (record_id, department, str(rec.get("source_ref_id") or ""), None,
                     str(rec.get("name") or ""), str(rec.get("dob") or ""), str(rec.get("gender") or ""),
                     str(rec.get("phone") or ""), str(rec.get("address") or ""),
                     str(rec.get("aadhaar_last4") or ""),
                     json.dumps({**(rec.get("extra") or {}), "_issues": rec.get("_issues", [])}),
                     now_iso()),
                )
                inserted += 1
            except Exception:
                failed += 1
    finished = now_iso()
    log_monitor(f"{department}_csv_connector", "success" if failed == 0 else "partial_failure",
                inserted, failed, "" if failed == 0 else f"{failed} rows failed", started, finished)
    log_audit(session["username"], session["role"], "load_sample", "department", department,
              f"Loaded {inserted} sample records")
    notify_n8n("data_ingested", {"department": department, "records_inserted": inserted,
                                  "quality_score": quality_report["quality_score"]})
    return {"status": "success", "department": department, "records_inserted": inserted,
            "records_failed": failed, "quality_report": quality_report}


# --------------------------------------------------------------------------------
# DUPLICATE DETECTION
# --------------------------------------------------------------------------------
@app.post("/api/matching/run")
def run_duplicate_detection(session=Depends(auth.get_current_user)):
    auth.require_permission(session, "resolve_matches")
    with db() as conn:
        rows = conn.execute("SELECT * FROM source_records").fetchall()

    records = []
    for r in rows:
        extra = json.loads(r["extra_json"] or "{}")
        records.append({
            "record_id": r["record_id"],
            "citizen_id": r["citizen_id"],
            "name": r["raw_name"],
            "phone": r["raw_phone"],
            "address": r["raw_address"],
            "id_value": r["raw_aadhaar_last4"],
            "doc_text": extra.get("scheme_enrolled") or extra.get("scheme_name") or "",
        })

    pairs = matching.find_candidate_pairs(records)
    created = 0
    with db() as conn:
        for a, b, result in pairs:
            existing = conn.execute(
                "SELECT match_id FROM match_candidates WHERE "
                "(record_id_a=? AND record_id_b=?) OR (record_id_a=? AND record_id_b=?)",
                (a["record_id"], b["record_id"], b["record_id"], a["record_id"]),
            ).fetchone()
            if existing:
                continue
            match_id = f"MATCH-{uuid.uuid4().hex[:10]}"
            conn.execute(
                "INSERT INTO match_candidates (match_id, record_id_a, record_id_b, score, decision, "
                "reason, status, created_at) VALUES (?,?,?,?,?,?,?,?)",
                (match_id, a["record_id"], b["record_id"], result["score"], result["decision"],
                 "; ".join(result["reasons"]), "pending", now_iso()),
            )
            created += 1

    log_audit(session["username"], session["role"], "run_matching", "system", "-",
              f"Compared {len(records)} records, found {len(pairs)} candidate pairs, {created} new")

    if created:
        notify_n8n("duplicate_candidates_found", {"new_candidates": created, "total_pairs": len(pairs)})

    return {"records_compared": len(records), "candidate_pairs_found": len(pairs), "new_candidates_created": created}


@app.get("/api/matching/candidates")
def list_match_candidates(status: Optional[str] = None, session=Depends(auth.get_current_user)):
    with db() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM match_candidates WHERE status=? ORDER BY score DESC", (status,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM match_candidates ORDER BY score DESC").fetchall()

        results = []
        for r in rows:
            rec_a = conn.execute("SELECT * FROM source_records WHERE record_id=?", (r["record_id_a"],)).fetchone()
            rec_b = conn.execute("SELECT * FROM source_records WHERE record_id=?", (r["record_id_b"],)).fetchone()
            results.append({
                **dict(r),
                "record_a": dict(rec_a) if rec_a else None,
                "record_b": dict(rec_b) if rec_b else None,
            })
    return results


class ResolveMatchRequest(BaseModel):
    action: str  # "confirm" or "reject"
    comment: Optional[str] = None


@app.post("/api/matching/candidates/{match_id}/resolve")
def resolve_match(match_id: str, req: ResolveMatchRequest, session=Depends(auth.get_current_user)):
    auth.require_permission(session, "resolve_matches")
    if req.action not in ("confirm", "reject"):
        raise HTTPException(status_code=400, detail="action must be 'confirm' or 'reject'")

    with db() as conn:
        match = conn.execute("SELECT * FROM match_candidates WHERE match_id=?", (match_id,)).fetchone()
        if not match:
            raise HTTPException(status_code=404, detail="Match candidate not found")

        new_status = "confirmed" if req.action == "confirm" else "rejected"
        conn.execute(
            "UPDATE match_candidates SET status=?, reviewed_by=?, reviewed_at=? WHERE match_id=?",
            (new_status, session["username"], now_iso(), match_id),
        )

        if req.action == "confirm":
            # Merge both source records under a single golden citizen record (never delete raw records)
            rec_a = conn.execute("SELECT * FROM source_records WHERE record_id=?", (match["record_id_a"],)).fetchone()
            rec_b = conn.execute("SELECT * FROM source_records WHERE record_id=?", (match["record_id_b"],)).fetchone()

            citizen_id = rec_a["citizen_id"] or rec_b["citizen_id"]
            if not citizen_id:
                citizen_id = f"CIT-{uuid.uuid4().hex[:10]}"
                conn.execute(
                    "INSERT INTO citizens (citizen_id, full_name, dob, gender, phone, address, "
                    "aadhaar_last4, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
                    (citizen_id, rec_a["raw_name"] or rec_b["raw_name"], rec_a["raw_dob"] or rec_b["raw_dob"],
                     rec_a["raw_gender"] or rec_b["raw_gender"], rec_a["raw_phone"] or rec_b["raw_phone"],
                     rec_a["raw_address"] or rec_b["raw_address"],
                     rec_a["raw_aadhaar_last4"] or rec_b["raw_aadhaar_last4"], now_iso(), now_iso()),
                )
            conn.execute("UPDATE source_records SET citizen_id=? WHERE record_id IN (?,?)",
                        (citizen_id, match["record_id_a"], match["record_id_b"]))

    log_audit(session["username"], session["role"], f"resolve_match_{req.action}", "match_candidate",
              match_id, req.comment or "")
    notify_n8n("match_resolved", {"match_id": match_id, "action": req.action, "by": session["username"]})
    return {"status": "ok", "match_id": match_id, "new_status": new_status}


# --------------------------------------------------------------------------------
# UNIFIED CITIZEN PROFILE / DASHBOARD
# --------------------------------------------------------------------------------
@app.get("/api/citizens")
def list_citizens(q: Optional[str] = None, session=Depends(auth.get_current_user)):
    with db() as conn:
        if q:
            rows = conn.execute(
                "SELECT * FROM citizens WHERE full_name LIKE ? OR phone LIKE ? ORDER BY updated_at DESC",
                (f"%{q}%", f"%{q}%"),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM citizens ORDER BY updated_at DESC").fetchall()
    return [dict(r) for r in rows]


@app.get("/api/citizens/{citizen_id}/profile")
def unified_profile(citizen_id: str, session=Depends(auth.get_current_user)):
    with db() as conn:
        citizen = conn.execute("SELECT * FROM citizens WHERE citizen_id=?", (citizen_id,)).fetchone()
        if not citizen:
            raise HTTPException(status_code=404, detail="Citizen not found")
        records = conn.execute("SELECT * FROM source_records WHERE citizen_id=?", (citizen_id,)).fetchall()
        applications = conn.execute("SELECT * FROM applications WHERE citizen_id=?", (citizen_id,)).fetchall()
        grievances = conn.execute("SELECT * FROM grievances WHERE citizen_id=?", (citizen_id,)).fetchall()
        beneficiaries = conn.execute("SELECT * FROM beneficiaries WHERE citizen_id=?", (citizen_id,)).fetchall()
        consents = conn.execute("SELECT * FROM consents WHERE citizen_id=?", (citizen_id,)).fetchall()

    return {
        "citizen": dict(citizen),
        "linked_department_records": [dict(r) for r in records],
        "applications": [dict(r) for r in applications],
        "grievances": [dict(r) for r in grievances],
        "beneficiary_records": [dict(r) for r in beneficiaries],
        "consents": [dict(r) for r in consents],
        "departments_linked": sorted(list(set(r["department"] for r in records))),
    }


@app.get("/api/dashboard/summary")
def dashboard_summary(session=Depends(auth.get_current_user)):
    with db() as conn:
        def count(sql, params=()):
            return conn.execute(sql, params).fetchone()[0]

        total_records = count("SELECT COUNT(*) FROM source_records")
        total_citizens = count("SELECT COUNT(*) FROM citizens")
        pending_matches = count("SELECT COUNT(*) FROM match_candidates WHERE status='pending'")
        confirmed_dupes = count("SELECT COUNT(*) FROM match_candidates WHERE status='confirmed'")
        open_grievances = count("SELECT COUNT(*) FROM grievances WHERE status!='resolved'")
        total_applications = count("SELECT COUNT(*) FROM applications")
        pending_apps = count("SELECT COUNT(*) FROM applications WHERE status NOT IN ('approved','rejected','completed')")
        by_dept = conn.execute(
            "SELECT department, COUNT(*) c FROM source_records GROUP BY department"
        ).fetchall()
        app_status_breakdown = conn.execute(
            "SELECT status, COUNT(*) c FROM applications GROUP BY status"
        ).fetchall()
        recent_audit = conn.execute(
            "SELECT * FROM audit_logs ORDER BY id DESC LIMIT 15"
        ).fetchall()

    duplicates_prevented_pct = round(100 * confirmed_dupes / max(total_records, 1), 1)

    return {
        "total_source_records": total_records,
        "unified_citizens": total_citizens,
        "pending_match_reviews": pending_matches,
        "confirmed_duplicates_resolved": confirmed_dupes,
        "open_grievances": open_grievances,
        "total_applications": total_applications,
        "pending_applications": pending_apps,
        "duplicate_submission_rate_pct": duplicates_prevented_pct,
        "records_by_department": [dict(r) for r in by_dept],
        "application_status_breakdown": [dict(r) for r in app_status_breakdown],
        "recent_activity": [dict(r) for r in recent_audit],
    }


# --------------------------------------------------------------------------------
# CONSENT MANAGEMENT
# --------------------------------------------------------------------------------
class ConsentRequest(BaseModel):
    citizen_id: str
    requesting_department: str
    data_scope: str
    purpose: str
    validity_days: int = 30


@app.post("/api/consents/request")
def request_consent(req: ConsentRequest, session=Depends(auth.get_current_user)):
    consent_id = f"CONSENT-{uuid.uuid4().hex[:10]}"
    with db() as conn:
        conn.execute(
            "INSERT INTO consents (consent_id, citizen_id, requesting_department, data_scope, purpose, "
            "status, requested_at, expires_at) VALUES (?,?,?,?,?,?,?,?)",
            (consent_id, req.citizen_id, req.requesting_department, req.data_scope, req.purpose,
             "pending", now_iso(), (datetime.utcnow() + timedelta(days=req.validity_days)).isoformat()),
        )
    log_audit(session["username"], session["role"], "request_consent", "consent", consent_id,
              f"Requested {req.data_scope} for {req.purpose} from {req.requesting_department}")
    notify_n8n("consent_requested", {"consent_id": consent_id, "citizen_id": req.citizen_id,
                                      "department": req.requesting_department})
    return {"status": "ok", "consent_id": consent_id}


class ConsentDecision(BaseModel):
    decision: str  # granted | denied | revoked


@app.post("/api/consents/{consent_id}/decide")
def decide_consent(consent_id: str, req: ConsentDecision, session=Depends(auth.get_current_user)):
    if req.decision not in ("granted", "denied", "revoked"):
        raise HTTPException(status_code=400, detail="decision must be granted, denied, or revoked")
    with db() as conn:
        existing = conn.execute("SELECT * FROM consents WHERE consent_id=?", (consent_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Consent record not found")
        conn.execute("UPDATE consents SET status=?, responded_at=? WHERE consent_id=?",
                    (req.decision, now_iso(), consent_id))
    log_audit(session["username"], session["role"], f"consent_{req.decision}", "consent", consent_id, "")
    notify_n8n("consent_decision", {"consent_id": consent_id, "decision": req.decision})
    return {"status": "ok", "consent_id": consent_id, "decision": req.decision}


@app.get("/api/consents")
def list_consents(citizen_id: Optional[str] = None, session=Depends(auth.get_current_user)):
    with db() as conn:
        if citizen_id:
            rows = conn.execute("SELECT * FROM consents WHERE citizen_id=? ORDER BY requested_at DESC",
                                (citizen_id,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM consents ORDER BY requested_at DESC").fetchall()
    return [dict(r) for r in rows]


# --------------------------------------------------------------------------------
# APPLICATIONS (Unified tracking + configurable workflow)
# --------------------------------------------------------------------------------
WORKFLOW_STATES = ["submitted", "under_review", "additional_info_requested", "approved", "rejected", "completed"]


class ApplicationCreate(BaseModel):
    citizen_id: str
    department: str
    service_name: str
    priority: str = "normal"
    notes: Optional[str] = None


@app.post("/api/applications")
def create_application(req: ApplicationCreate, session=Depends(auth.get_current_user)):
    app_id = f"APP-{uuid.uuid4().hex[:10]}"
    with db() as conn:
        conn.execute(
            "INSERT INTO applications (application_id, citizen_id, department, service_name, status, "
            "priority, submitted_at, updated_at, notes) VALUES (?,?,?,?,?,?,?,?,?)",
            (app_id, req.citizen_id, req.department, req.service_name, "submitted", req.priority,
             now_iso(), now_iso(), req.notes or ""),
        )
        conn.execute(
            "INSERT INTO workflow_history (application_id, from_status, to_status, changed_by, changed_at, comment) "
            "VALUES (?,?,?,?,?,?)", (app_id, None, "submitted", session["username"], now_iso(), "Application created"),
        )
    log_audit(session["username"], session["role"], "create_application", "application", app_id,
              f"{req.department}/{req.service_name}")
    notify_n8n("application_submitted", {"application_id": app_id, "department": req.department,
                                          "service_name": req.service_name})
    return {"status": "ok", "application_id": app_id}


@app.get("/api/applications")
def list_applications(citizen_id: Optional[str] = None, department: Optional[str] = None,
                       status: Optional[str] = None, session=Depends(auth.get_current_user)):
    query = "SELECT * FROM applications WHERE 1=1"
    params = []
    if citizen_id:
        query += " AND citizen_id=?"; params.append(citizen_id)
    if department:
        query += " AND department=?"; params.append(department)
    if status:
        query += " AND status=?"; params.append(status)
    query += " ORDER BY submitted_at DESC"
    with db() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


class StatusUpdate(BaseModel):
    new_status: str
    comment: Optional[str] = None
    assigned_officer: Optional[str] = None


@app.patch("/api/applications/{application_id}/status")
def update_application_status(application_id: str, req: StatusUpdate, session=Depends(auth.get_current_user)):
    auth.require_permission(session, "manage_workflow")
    if req.new_status not in WORKFLOW_STATES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of {WORKFLOW_STATES}")
    with db() as conn:
        current = conn.execute("SELECT * FROM applications WHERE application_id=?", (application_id,)).fetchone()
        if not current:
            raise HTTPException(status_code=404, detail="Application not found")
        conn.execute(
            "UPDATE applications SET status=?, updated_at=?, assigned_officer=COALESCE(?, assigned_officer) "
            "WHERE application_id=?", (req.new_status, now_iso(), req.assigned_officer, application_id),
        )
        conn.execute(
            "INSERT INTO workflow_history (application_id, from_status, to_status, changed_by, changed_at, comment) "
            "VALUES (?,?,?,?,?,?)",
            (application_id, current["status"], req.new_status, session["username"], now_iso(), req.comment or ""),
        )
    log_audit(session["username"], session["role"], "update_status", "application", application_id,
              f"{current['status']} -> {req.new_status}")
    notify_n8n("application_status_changed", {"application_id": application_id,
                                               "from": current["status"], "to": req.new_status})
    return {"status": "ok", "application_id": application_id, "new_status": req.new_status}


@app.get("/api/applications/{application_id}/history")
def application_history(application_id: str, session=Depends(auth.get_current_user)):
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM workflow_history WHERE application_id=? ORDER BY id ASC", (application_id,)
        ).fetchall()
    return [dict(r) for r in rows]


# --------------------------------------------------------------------------------
# GRIEVANCES
# --------------------------------------------------------------------------------
class GrievanceCreate(BaseModel):
    citizen_id: str
    department: str
    subject: str
    description: str
    priority: str = "normal"


@app.post("/api/grievances")
def create_grievance(req: GrievanceCreate, session=Depends(auth.get_current_user)):
    gid = f"GRV-{uuid.uuid4().hex[:10]}"
    with db() as conn:
        conn.execute(
            "INSERT INTO grievances (grievance_id, citizen_id, department, subject, description, status, "
            "priority, filed_at) VALUES (?,?,?,?,?,?,?,?)",
            (gid, req.citizen_id, req.department, req.subject, req.description, "open", req.priority, now_iso()),
        )
    log_audit(session["username"], session["role"], "file_grievance", "grievance", gid, req.subject)
    notify_n8n("grievance_filed", {"grievance_id": gid, "department": req.department,
                                    "priority": req.priority, "subject": req.subject})
    return {"status": "ok", "grievance_id": gid}


@app.get("/api/grievances")
def list_grievances(citizen_id: Optional[str] = None, status: Optional[str] = None,
                     session=Depends(auth.get_current_user)):
    query = "SELECT * FROM grievances WHERE 1=1"
    params = []
    if citizen_id:
        query += " AND citizen_id=?"; params.append(citizen_id)
    if status:
        query += " AND status=?"; params.append(status)
    query += " ORDER BY filed_at DESC"
    with db() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


class GrievanceUpdate(BaseModel):
    status: str
    assigned_officer: Optional[str] = None


@app.patch("/api/grievances/{grievance_id}")
def update_grievance(grievance_id: str, req: GrievanceUpdate, session=Depends(auth.get_current_user)):
    auth.require_permission(session, "manage_workflow")
    resolved_at = now_iso() if req.status == "resolved" else None
    with db() as conn:
        conn.execute(
            "UPDATE grievances SET status=?, assigned_officer=COALESCE(?, assigned_officer), "
            "resolved_at=COALESCE(?, resolved_at) WHERE grievance_id=?",
            (req.status, req.assigned_officer, resolved_at, grievance_id),
        )
    log_audit(session["username"], session["role"], "update_grievance", "grievance", grievance_id, req.status)
    notify_n8n("grievance_status_changed", {"grievance_id": grievance_id, "status": req.status})
    return {"status": "ok"}


# --------------------------------------------------------------------------------
# BENEFICIARIES / SERVICE OUTCOMES
# --------------------------------------------------------------------------------
@app.get("/api/beneficiaries")
def list_beneficiaries(citizen_id: Optional[str] = None, department: Optional[str] = None,
                        session=Depends(auth.get_current_user)):
    query = "SELECT * FROM beneficiaries WHERE 1=1"
    params = []
    if citizen_id:
        query += " AND citizen_id=?"; params.append(citizen_id)
    if department:
        query += " AND department=?"; params.append(department)
    with db() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


# --------------------------------------------------------------------------------
# DATA QUALITY / API MONITORING / AUDIT
# --------------------------------------------------------------------------------
@app.get("/api/monitoring/sync-logs")
def sync_logs(session=Depends(auth.get_current_user)):
    with db() as conn:
        rows = conn.execute("SELECT * FROM api_monitor_logs ORDER BY id DESC LIMIT 50").fetchall()
    return [dict(r) for r in rows]


@app.get("/api/monitoring/data-quality")
def data_quality_report(session=Depends(auth.get_current_user)):
    with db() as conn:
        by_dept = conn.execute(
            "SELECT department, COUNT(*) total, "
            "SUM(CASE WHEN json_extract(extra_json,'$._issues') = '[]' THEN 1 ELSE 0 END) clean "
            "FROM source_records GROUP BY department"
        ).fetchall()
    report = []
    for r in by_dept:
        total, clean = r["total"], (r["clean"] or 0)
        report.append({
            "department": r["department"], "total_records": total, "clean_records": clean,
            "flagged_records": total - clean,
            "quality_score_pct": round(100 * clean / max(total, 1), 1),
        })
    return report


@app.get("/api/audit-logs")
def get_audit_logs(entity_type: Optional[str] = None, limit: int = Query(100, le=1000),
                    session=Depends(auth.get_current_user)):
    with db() as conn:
        if entity_type:
            rows = conn.execute(
                "SELECT * FROM audit_logs WHERE entity_type=? ORDER BY id DESC LIMIT ?", (entity_type, limit)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


# --------------------------------------------------------------------------------
# EXPORT REPORTS
# --------------------------------------------------------------------------------
@app.get("/api/reports/export/{report_type}")
def export_report(report_type: str, session=Depends(auth.get_current_user)):
    auth.require_permission(session, "export_reports")
    with db() as conn:
        if report_type == "applications":
            rows = conn.execute("SELECT * FROM applications").fetchall()
        elif report_type == "grievances":
            rows = conn.execute("SELECT * FROM grievances").fetchall()
        elif report_type == "citizens":
            rows = conn.execute("SELECT * FROM citizens").fetchall()
        elif report_type == "audit":
            rows = conn.execute("SELECT * FROM audit_logs").fetchall()
        elif report_type == "matches":
            rows = conn.execute("SELECT * FROM match_candidates").fetchall()
        else:
            raise HTTPException(status_code=400, detail="Unknown report_type")
    df = pd.DataFrame([dict(r) for r in rows])
    csv_data = df.to_csv(index=False)
    log_audit(session["username"], session["role"], "export_report", "report", report_type, "")
    return {"report_type": report_type, "row_count": len(df), "csv": csv_data}


@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "JagatData API", "time": now_iso()}

