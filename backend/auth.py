"""
JagatData - Demo role-based authentication.

Simulates a "federated login" broker: a citizen/officer authenticates once
against JagatData, and the resulting token carries their role + department,
which is then honoured by every connected department module - instead of
maintaining separate logins per portal.

NOTE: This is intentionally simple (signed opaque tokens in an in-memory
dict) for hackathon-speed. Real deployment would use OAuth2/OIDC against
each department's IdP (e.g., DigiLocker / Aadhaar-based eKYC / SSO).
"""
import os
import secrets
from fastapi import Header, HTTPException
from backend.database import db

AUTH_SECRET = os.environ.get("AUTH_SECRET", "jagatdata-hackathon-secret")

# token -> {username, role, department}
ACTIVE_SESSIONS = {}

ROLE_PERMISSIONS = {
    "Admin": {"manage_users", "view_all", "upload_data", "resolve_matches", "manage_workflow",
              "grant_consent_view", "export_reports", "manage_connectors"},
    "Officer": {"view_all", "upload_data", "resolve_matches", "manage_workflow", "export_reports"},
    "Reviewer": {"view_all", "resolve_matches", "export_reports"},
}


def authenticate(username: str, password: str):
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username=? AND password=?", (username, password)
        ).fetchone()
    if not row:
        return None
    token = secrets.token_hex(16)
    session = {
        "username": row["username"],
        "role": row["role"],
        "department": row["department"],
        "full_name": row["full_name"],
    }
    ACTIVE_SESSIONS[token] = session
    return token, session


def get_current_user(authorization: str = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization.split(" ", 1)[1]
    session = ACTIVE_SESSIONS.get(token)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session token")
    return session


def require_permission(session: dict, permission: str):
    allowed = ROLE_PERMISSIONS.get(session["role"], set())
    if permission not in allowed:
        raise HTTPException(status_code=403, detail=f"Role '{session['role']}' lacks permission '{permission}'")
