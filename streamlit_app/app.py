"""
JagatData - Streamlit Unified Dashboard
Connecting Government Systems. Simplifying Public Services.
"""
import os
import io
import requests
import pandas as pd
import streamlit as st
import plotly.express as px

API_BASE = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="JagatData", page_icon="🏛️", layout="wide")

# ---------------------------------------------------------------- styling ---
st.markdown("""
<style>
.main-header {
    background: linear-gradient(90deg, #0b3d91 0%, #1a5fb4 60%, #ff9933 100%);
    padding: 1.4rem 2rem; border-radius: 12px; color: #f4f8ff; margin-bottom: 1.2rem;
}
.main-header h1 { margin: 0; font-size: 2rem; color: #f4f8ff; }
.main-header p { margin: 0.2rem 0 0 0; opacity: 0.92; color: #f4f8ff; }
div[data-testid="stMetric"] {
    background: linear-gradient(180deg, #f5f7f3 0%, #edf2f7 100%);
    border: 1px solid #cfe0d9;
    border-radius: 12px;
    padding: 0.8rem;
    color: #0b1f5b;
    box-shadow: 0 6px 16px rgba(22, 50, 72, 0.12), 0 2px 6px rgba(22, 50, 72, 0.08), inset 0 1px 0 rgba(255,255,255,0.9);
}
div[data-testid="stMetric"] * {
    color: #0b1f5b !important;
}
.badge-dup { background:#fde2e1; color:#b3261e; padding:2px 8px; border-radius:8px; font-size:0.8rem;}
.badge-rev { background:#fff3cd; color:#8a6100; padding:2px 8px; border-radius:8px; font-size:0.8rem;}
.badge-dif { background:#e2f4e2; color:#1e7d32; padding:2px 8px; border-radius:8px; font-size:0.8rem;}
</style>
<div class="main-header">
<h1>🏛️ JagatData</h1>
<p>Connecting Government Systems. Simplifying Public Services. — SIH 2026 Interoperability MVP</p>
</div>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------- helpers ---
def api(method, path, **kwargs):
    headers = kwargs.pop("headers", {})
    if st.session_state.get("token"):
        headers["Authorization"] = f"Bearer {st.session_state['token']}"
    url = f"{API_BASE}{path}"
    try:
        resp = requests.request(method, url, headers=headers, timeout=15, **kwargs)
        if resp.status_code >= 400:
            st.error(f"API error ({resp.status_code}): {resp.text}")
            return None
        return resp.json()
    except requests.exceptions.ConnectionError:
        st.error(f"⚠️ Cannot reach JagatData API at {API_BASE}. Start the backend with: "
                 f"`uvicorn backend.main:app --reload`")
        return None


def badge(decision):
    cls = {"probable_duplicate": "badge-dup", "manual_review": "badge-rev",
           "probably_different": "badge-dif"}.get(decision, "badge-dif")
    label = {"probable_duplicate": "Probable Duplicate", "manual_review": "Manual Review",
              "probably_different": "Probably Different"}.get(decision, decision)
    return f'<span class="{cls}">{label}</span>'


# ---------------------------------------------------------------- login -----
if "token" not in st.session_state:
    st.session_state["token"] = None
    st.session_state["session"] = None

with st.sidebar:
    st.header("🔐 Login")
    if st.session_state["token"] is None:
        demo = api("GET", "/api/auth/roles")
        if demo:
            with st.expander("Demo credentials"):
                for acc in demo["accounts"]:
                    st.code(f"{acc['username']} / {acc['password']}  ({acc['role']})")
        u = st.text_input("Username", value="admin")
        p = st.text_input("Password", value="admin123", type="password")
        if st.button("Login", use_container_width=True):
            result = api("POST", "/api/auth/login", json={"username": u, "password": p})
            if result:
                st.session_state["token"] = result["token"]
                st.session_state["session"] = result["session"]
                st.rerun()
    else:
        sess = st.session_state["session"]
        st.success(f"Logged in as **{sess['full_name']}**")
        st.caption(f"Role: {sess['role']} | Dept: {sess['department']}")
        if st.button("Logout", use_container_width=True):
            st.session_state["token"] = None
            st.session_state["session"] = None
            st.rerun()

if not st.session_state["token"]:
    st.info("👈 Please log in from the sidebar to access the JagatData platform.")
    st.stop()

sess = st.session_state["session"]

TABS = st.tabs([
    "📊 Dashboard", "🔌 Connectors & Ingestion", "🧬 Duplicate Detection",
    "👤 Unified Profile", "📝 Applications", "📢 Grievances",
    "🎁 Beneficiaries", "✅ Consent", "🛡️ Audit & Monitoring", "📤 Reports"
])

# ============================================================== DASHBOARD ==
with TABS[0]:
    st.subheader("Unified Service Delivery Dashboard")
    summary = api("GET", "/api/dashboard/summary")
    if summary:
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Total Source Records", summary["total_source_records"])
        c2.metric("Unified Citizens", summary["unified_citizens"])
        c3.metric("Pending Match Reviews", summary["pending_match_reviews"])
        c4.metric("Open Grievances", summary["open_grievances"])
        c5.metric("Pending Applications", summary["pending_applications"])

        col1, col2 = st.columns(2)
        with col1:
            if summary["records_by_department"]:
                df = pd.DataFrame(summary["records_by_department"])
                fig = px.pie(df, names="department", values="c", title="Records by Department",
                             color_discrete_sequence=px.colors.sequential.Blues_r)
                st.plotly_chart(fig, use_container_width=True)
        with col2:
            if summary["application_status_breakdown"]:
                df2 = pd.DataFrame(summary["application_status_breakdown"])
                fig2 = px.bar(df2, x="status", y="c", title="Applications by Status",
                              color="status")
                st.plotly_chart(fig2, use_container_width=True)

        st.markdown("##### Recent Activity")
        if summary["recent_activity"]:
            st.dataframe(pd.DataFrame(summary["recent_activity"])[["timestamp","actor","role","action","entity_type","entity_id"]],
                         use_container_width=True, hide_index=True)

        st.caption(f"💡 Duplicate submission rate observed: **{summary['duplicate_submission_rate_pct']}%** "
                   f"of ingested records identified as confirmed cross-department duplicates.")

# ======================================================= CONNECTORS TAB ====
with TABS[1]:
    st.subheader("Department Connectors — Bring Data In Without Replacing Legacy Systems")
    st.write("Each department publishes data in its **own** format. JagatData connectors map every "
             "format into a common citizen schema (name, DOB, gender, phone, address, ID) automatically.")

    dept = st.selectbox("Department", ["Health", "Education", "Welfare"])
    colA, colB = st.columns(2)
    with colA:
        st.markdown("**Option A: Load bundled sample dataset (fastest)**")
        if st.button(f"⚡ Load sample {dept} data", use_container_width=True):
            result = api("POST", f"/api/connectors/{dept}/load-sample")
            if result:
                st.success(f"Ingested {result['records_inserted']} records "
                           f"(quality score: {result['quality_report']['quality_score']}%)")
                st.json(result["quality_report"])
    with colB:
        st.markdown("**Option B: Upload your own CSV**")
        upload = st.file_uploader(f"Upload {dept} CSV", type=["csv"], key=f"upload_{dept}")
        if upload and st.button("Upload & Ingest", use_container_width=True):
            files = {"file": (upload.name, upload.getvalue(), "text/csv")}
            resp = requests.post(f"{API_BASE}/api/connectors/{dept}/upload", files=files,
                                 headers={"Authorization": f"Bearer {st.session_state['token']}"})
            if resp.status_code < 400:
                st.success("Uploaded and ingested successfully")
                st.json(resp.json()["quality_report"])
            else:
                st.error(resp.text)

    st.divider()
    st.markdown("##### Recent Sync / Connector Health Log")
    conn_data = api("GET", "/api/connectors")
    if conn_data and conn_data["recent_syncs"]:
        st.dataframe(pd.DataFrame(conn_data["recent_syncs"]), use_container_width=True, hide_index=True)
    else:
        st.caption("No syncs yet. Load sample data above to get started.")

# ===================================================== DUPLICATE DETECTION =
with TABS[2]:
    st.subheader("Explainable Duplicate / Record-Linkage Detection")
    st.write("Weighted formula: **0.40 × name + 0.30 × phone/ID + 0.20 × address + 0.10 × document details** "
             "(weights redistribute automatically when fields are missing).")
    st.caption("Decision bands — 85+: Probable Duplicate · 65–84: Manual Review · <65: Probably Different. "
               "**Records are never auto-merged or deleted** — an authorized reviewer must confirm.")

    if st.button("🔍 Run Duplicate Detection Across All Departments", type="primary"):
        result = api("POST", "/api/matching/run")
        if result:
            st.success(f"Compared {result['records_compared']} records → "
                       f"{result['candidate_pairs_found']} candidate pairs found "
                       f"({result['new_candidates_created']} new).")

    status_filter = st.selectbox("Filter by review status", ["pending", "confirmed", "rejected", "All"])
    candidates = api("GET", "/api/matching/candidates",
                      params=None if status_filter == "All" else {"status": status_filter})
    if candidates:
        for c in candidates:
            ra, rb = c["record_a"], c["record_b"]
            with st.container(border=True):
                col1, col2, col3 = st.columns([2, 2, 1.2])
                with col1:
                    st.markdown(f"**{ra['department']}** — {ra['raw_name']}")
                    st.caption(f"📞 {ra['raw_phone']} | 🏠 {ra['raw_address'][:50]}...")
                with col2:
                    st.markdown(f"**{rb['department']}** — {rb['raw_name']}")
                    st.caption(f"📞 {rb['raw_phone']} | 🏠 {rb['raw_address'][:50]}...")
                with col3:
                    st.metric("Score", f"{c['score']:.1f}")
                    st.markdown(badge(c["decision"]), unsafe_allow_html=True)
                st.info(f"**Why:** {c['reason']}")
                if c["status"] == "pending":
                    b1, b2, _ = st.columns([1, 1, 4])
                    if b1.button("✅ Confirm Duplicate", key=f"conf_{c['match_id']}"):
                        api("POST", f"/api/matching/candidates/{c['match_id']}/resolve",
                            json={"action": "confirm", "comment": "Confirmed via dashboard"})
                        st.rerun()
                    if b2.button("❌ Reject", key=f"rej_{c['match_id']}"):
                        api("POST", f"/api/matching/candidates/{c['match_id']}/resolve",
                            json={"action": "reject", "comment": "Rejected via dashboard"})
                        st.rerun()
                else:
                    st.caption(f"Reviewed by {c['reviewed_by']} — status: **{c['status']}**")
    else:
        st.caption("No candidate pairs yet. Ingest data from multiple departments then run detection.")

# ============================================================ PROFILE TAB ==
with TABS[3]:
    st.subheader("360° Unified Citizen Profile")
    citizens = api("GET", "/api/citizens")
    if citizens:
        options = {f"{c['full_name']} ({c['citizen_id']})": c["citizen_id"] for c in citizens}
        choice = st.selectbox("Select unified citizen", list(options.keys()))
        if choice:
            profile = api("GET", f"/api/citizens/{options[choice]}/profile")
            if profile:
                cz = profile["citizen"]
                c1, c2, c3 = st.columns(3)
                c1.metric("Name", cz["full_name"])
                c2.metric("Departments Linked", len(profile["departments_linked"]))
                c3.metric("Phone", cz["phone"])
                st.write(f"**DOB:** {cz['dob']} | **Gender:** {cz['gender']} | **Address:** {cz['address']}")

                st.markdown("##### Linked Department Records")
                if profile["linked_department_records"]:
                    st.dataframe(pd.DataFrame(profile["linked_department_records"])[
                        ["department", "source_ref_id", "raw_name", "raw_phone"]],
                        use_container_width=True, hide_index=True)

                cols = st.columns(3)
                cols[0].markdown("##### Applications")
                cols[0].dataframe(pd.DataFrame(profile["applications"]) if profile["applications"] else
                                  pd.DataFrame(columns=["No applications"]), use_container_width=True, hide_index=True)
                cols[1].markdown("##### Grievances")
                cols[1].dataframe(pd.DataFrame(profile["grievances"]) if profile["grievances"] else
                                  pd.DataFrame(columns=["No grievances"]), use_container_width=True, hide_index=True)
                cols[2].markdown("##### Consents")
                cols[2].dataframe(pd.DataFrame(profile["consents"]) if profile["consents"] else
                                  pd.DataFrame(columns=["No consent records"]), use_container_width=True, hide_index=True)
    else:
        st.caption("No unified citizens yet — confirm at least one duplicate match to create a golden record.")

# =============================================================== APPLICATIONS
with TABS[4]:
    st.subheader("Cross-Department Application Tracking")
    citizens = api("GET", "/api/citizens") or []
    with st.expander("➕ File a new application"):
        if citizens:
            cz_choice = st.selectbox("Citizen", [f"{c['full_name']} ({c['citizen_id']})" for c in citizens],
                                      key="app_cz")
            cz_id = cz_choice.split("(")[-1].rstrip(")")
            dept = st.selectbox("Department", ["Health", "Education", "Welfare"], key="app_dept")
            service = st.text_input("Service name", "Ayushman Bharat Card Issuance")
            priority = st.selectbox("Priority", ["normal", "high", "low"], key="app_prio")
            if st.button("Submit Application"):
                r = api("POST", "/api/applications", json={"citizen_id": cz_id, "department": dept,
                                                             "service_name": service, "priority": priority})
                if r:
                    st.success(f"Application {r['application_id']} submitted")
                    st.rerun()
        else:
            st.caption("Create a unified citizen first (resolve a duplicate match) to file applications.")

    apps = api("GET", "/api/applications")
    if apps:
        df = pd.DataFrame(apps)
        st.dataframe(df[["application_id", "department", "service_name", "status", "priority", "submitted_at"]],
                     use_container_width=True, hide_index=True)
        st.markdown("##### Update Workflow Status")
        sel_app = st.selectbox("Application", df["application_id"].tolist())
        new_status = st.selectbox("New status", ["submitted", "under_review", "additional_info_requested",
                                                    "approved", "rejected", "completed"])
        comment = st.text_input("Comment", "")
        if st.button("Update Status"):
            r = api("PATCH", f"/api/applications/{sel_app}/status",
                    json={"new_status": new_status, "comment": comment})
            if r:
                st.success("Status updated")
                st.rerun()
    else:
        st.caption("No applications yet.")

# =============================================================== GRIEVANCES =
with TABS[5]:
    st.subheader("Grievance Tracking")
    citizens = api("GET", "/api/citizens") or []
    with st.expander("➕ File a new grievance"):
        if citizens:
            cz_choice = st.selectbox("Citizen", [f"{c['full_name']} ({c['citizen_id']})" for c in citizens],
                                      key="grv_cz")
            cz_id = cz_choice.split("(")[-1].rstrip(")")
            dept = st.selectbox("Department", ["Health", "Education", "Welfare"], key="grv_dept")
            subject = st.text_input("Subject", "Delayed application processing")
            description = st.text_area("Description", "My application has been pending for over 30 days.")
            priority = st.selectbox("Priority", ["normal", "high", "low"], key="grv_prio")
            if st.button("File Grievance"):
                r = api("POST", "/api/grievances", json={"citizen_id": cz_id, "department": dept,
                                                           "subject": subject, "description": description,
                                                           "priority": priority})
                if r:
                    st.success(f"Grievance {r['grievance_id']} filed")
                    st.rerun()

    grievances = api("GET", "/api/grievances")
    if grievances:
        df = pd.DataFrame(grievances)
        st.dataframe(df[["grievance_id", "department", "subject", "status", "priority", "filed_at"]],
                     use_container_width=True, hide_index=True)
        sel = st.selectbox("Grievance", df["grievance_id"].tolist())
        new_status = st.selectbox("New status", ["open", "in_progress", "resolved", "escalated"])
        if st.button("Update Grievance"):
            r = api("PATCH", f"/api/grievances/{sel}", json={"status": new_status})
            if r:
                st.success("Updated")
                st.rerun()
    else:
        st.caption("No grievances yet.")

# ============================================================= BENEFICIARIES
with TABS[6]:
    st.subheader("Beneficiary & Service Outcome Tracking")
    st.caption("Populated from department connector data (e.g. Welfare scheme enrolments).")
    bens = api("GET", "/api/beneficiaries")
    if bens:
        st.dataframe(pd.DataFrame(bens), use_container_width=True, hide_index=True)
    else:
        st.info("Beneficiary outcomes are linked once citizen records are unified via duplicate resolution. "
                "Welfare scheme details live in each source record's `extra` fields today "
                "(view them under Unified Profile → Linked Department Records).")

# ==================================================================== CONSENT
with TABS[7]:
    st.subheader("Consent-Based Data Sharing")
    st.write("Before one department can view another department's data about a citizen, "
             "a consent record must be requested and granted.")
    citizens = api("GET", "/api/citizens") or []
    with st.expander("➕ Request consent"):
        if citizens:
            cz_choice = st.selectbox("Citizen", [f"{c['full_name']} ({c['citizen_id']})" for c in citizens],
                                      key="consent_cz")
            cz_id = cz_choice.split("(")[-1].rstrip(")")
            req_dept = st.selectbox("Requesting department", ["Health", "Education", "Welfare"], key="consent_dept")
            scope = st.text_input("Data scope", "Address, Phone, Aadhaar last 4 digits")
            purpose = st.text_input("Purpose", "Cross-verification for scholarship eligibility")
            if st.button("Request Consent"):
                r = api("POST", "/api/consents/request", json={"citizen_id": cz_id, "requesting_department": req_dept,
                                                                 "data_scope": scope, "purpose": purpose})
                if r:
                    st.success(f"Consent {r['consent_id']} requested")
                    st.rerun()

    consents = api("GET", "/api/consents")
    if consents:
        df = pd.DataFrame(consents)
        st.dataframe(df[["consent_id", "citizen_id", "requesting_department", "purpose", "status", "requested_at"]],
                     use_container_width=True, hide_index=True)
        pending = df[df["status"] == "pending"]
        if len(pending):
            sel = st.selectbox("Pending consent to decide", pending["consent_id"].tolist())
            d1, d2, d3 = st.columns(3)
            if d1.button("✅ Grant"):
                api("POST", f"/api/consents/{sel}/decide", json={"decision": "granted"}); st.rerun()
            if d2.button("🚫 Deny"):
                api("POST", f"/api/consents/{sel}/decide", json={"decision": "denied"}); st.rerun()
            if d3.button("↩️ Revoke"):
                api("POST", f"/api/consents/{sel}/decide", json={"decision": "revoked"}); st.rerun()
    else:
        st.caption("No consent records yet.")

# ============================================================== AUDIT/MONITOR
with TABS[8]:
    st.subheader("Audit Trail & API/Connector Monitoring")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("##### Audit Log")
        logs = api("GET", "/api/audit-logs")
        if logs:
            st.dataframe(pd.DataFrame(logs)[["timestamp", "actor", "role", "action", "entity_type", "entity_id"]],
                         use_container_width=True, hide_index=True, height=350)
    with col2:
        st.markdown("##### Connector Sync Health (incl. Failed Syncs)")
        sync_logs = api("GET", "/api/monitoring/sync-logs")
        if sync_logs:
            df = pd.DataFrame(sync_logs)
            st.dataframe(df, use_container_width=True, hide_index=True, height=350)

    st.markdown("##### Data Quality Report by Department")
    dq = api("GET", "/api/monitoring/data-quality")
    if dq:
        df = pd.DataFrame(dq)
        st.dataframe(df, use_container_width=True, hide_index=True)
        fig = px.bar(df, x="department", y="quality_score_pct", title="Data Quality Score by Department (%)",
                     color="department")
        st.plotly_chart(fig, use_container_width=True)

# ===================================================================== REPORTS
with TABS[9]:
    st.subheader("Exportable Reports")
    report_type = st.selectbox("Report", ["applications", "grievances", "citizens", "matches", "audit"])
    if st.button("Generate Export"):
        r = api("GET", f"/api/reports/export/{report_type}")
        if r:
            st.success(f"Generated report with {r['row_count']} rows")
            st.download_button("⬇️ Download CSV", data=r["csv"], file_name=f"jagatdata_{report_type}.csv",
                               mime="text/csv")
            st.dataframe(pd.read_csv(io.StringIO(r["csv"])), use_container_width=True, hide_index=True)
