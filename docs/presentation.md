# JagatData — Presentation Content
### Connecting Government Systems. Simplifying Public Services.
**SIH 2026 | Problem Statement: System integration and interoperability among government digital platforms, resulting in fragmented service delivery.**

---

## 1. Problem

- Government departments (Health, Education, Welfare, and more) run **independent
  portals, apps, registries, and databases**, each with its own data formats,
  identifiers, and authentication.
- Citizens repeatedly submit the **same KYC information** to every department, and
  must track applications separately across multiple portals or visit multiple offices.
- Officials have **no single view** of a beneficiary's applications, approvals,
  grievances, and outcomes across departments — leading to duplicate benefit
  disbursal, slow grievance resolution, and poor coordination.

## 2. Solution — JagatData

JagatData is an **interoperability middleware / federated-service platform** that sits
**on top of existing systems** — it does not replace any department's system of record.

**Core capabilities delivered in this MVP:**
1. **Pluggable connectors** that map each department's native data format into a
   common citizen/business schema, with built-in validation and data-quality scoring.
2. **Explainable duplicate/record-linkage detection** using normalized fields
   (name, phone, address, ID/document) and a transparent weighted RapidFuzz score
   — never auto-merges; always routes to a human reviewer.
3. **Unified 360° citizen profile** aggregating linked records, applications,
   grievances, beneficiary status, and consent history from every connected department.
4. **Consent-based data sharing** — a department must request and receive explicit
   consent before viewing another department's data about a citizen.
5. **Federated login with role-based access** (Admin / Officer / Reviewer).
6. **Unified application tracking with a configurable workflow** (submitted → under
   review → additional info requested → approved/rejected → completed), with full
   audit history of every status change.
7. **Grievance and beneficiary/outcome tracking** integrated into the same profile.
8. **Event-driven notifications** via n8n webhooks — officers and citizens are
   notified the moment a duplicate needs review, a grievance is filed, or an
   application status changes.
9. **Audit logs, API/connector monitoring, and failed-sync handling** for
   operational transparency.
10. **Exportable CSV reports** for applications, grievances, citizens, matches, and audit trail.

## 3. Tech Stack (fast, hackathon-ready)

`Python · FastAPI · SQLite · Pandas · RapidFuzz · Streamlit · n8n (event automation)`

No ML dependency in the MVP — all matching logic is **explainable, rule-based fuzzy
matching**, which is easier to justify to auditors and citizens ("why was my record
flagged?") than a black-box model.

## 4. Demo Flow

1. Upload/Load Health, Education, and Welfare department sample data through
   department-specific connectors.
2. Data is automatically standardized into the common schema; a data-quality
   report flags incomplete/invalid rows.
3. Run duplicate detection — see candidate matches with an explainable reason
   string, e.g. *"Phone and document number matched; name similarity 92%;
   address similarity 78%."*
4. Officer reviews and **confirms** a match → both department records are linked
   into one unified citizen profile (never auto-merged).
5. Citizen's unified profile now shows linked Health + Welfare records together.
6. A department requests consent to view the citizen's Education record;
   consent is granted.
7. Citizen's application is tracked end-to-end across departments with full
   workflow history.
8. Every key event (duplicate found, grievance filed, status changed) fires a
   webhook → n8n → notifies the right officer/citizen.
9. Admin exports an audit report and a data-quality report for compliance review.

## 5. Impact

- **Fewer repeated submissions** — once a citizen's identity is unified, departments
  reuse verified data instead of re-collecting it.
- **Faster processing** — unified application tracking + configurable workflow
  reduces manual status-chasing and file movement across offices.
- **Consistent records** — explainable duplicate detection catches format-driven
  mismatches (spelling, phone formatting, address wording) that legacy systems miss.
- **Improved citizen experience** — one profile, one application tracker, one
  grievance channel instead of N separate department portals.
- **Better coordination** — officials get a cross-department view of beneficiaries,
  applications, approvals, and outcomes instead of siloed dashboards.
- **Measurable service-level compliance** — audit logs, data-quality scores, and
  workflow timestamps give a concrete basis for SLA tracking and reporting.

## 6. Future Scope

- ML-based entity resolution layered on top of today's rule-based matching for
  higher recall on weak-signal duplicates.
- OCR-based document verification for scanned certificates/IDs.
- Real integrations: DigiLocker, Aadhaar eKYC / API Setu, UPI-linked verification.
- Production-grade OAuth2/OIDC federated login against each department's IdP.
- PostgreSQL + message-queue-based ingestion for real government data volumes.
