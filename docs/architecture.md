# JagatData — Architecture

## High-level architecture diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              EXISTING GOVERNMENT SYSTEMS                       │
│                        (kept as-is — never replaced)                          │
│                                                                                │
│   ┌───────────────┐     ┌───────────────┐     ┌───────────────┐              │
│   │ Health Dept    │     │ Education Dept │     │ Welfare Dept   │   ...more   │
│   │ (ABHA-style    │     │ (Student /     │     │ (Pension /     │  legacy     │
│   │ registry, CSV/ │     │ Scholarship    │     │ Subsidy        │  systems    │
│   │ API exports)   │     │ registry CSV)  │     │ registry CSV)  │             │
│   └───────┬───────┘     └───────┬───────┘     └───────┬───────┘              │
└───────────┼─────────────────────┼─────────────────────┼──────────────────────┘
            │                     │                     │
            ▼                     ▼                     ▼
   ┌────────────────┐   ┌────────────────┐   ┌────────────────┐
   │ Health Connector│  │ Education      │   │ Welfare        │   <- pluggable
   │ (map_health)    │  │ Connector      │   │ Connector      │      per-dept
   └────────┬────────┘   └───────┬────────┘   └───────┬────────┘   adapters
            └─────────────────────┼─────────────────────┘
                                   ▼
                    ┌───────────────────────────────┐
                    │   COMMON CITIZEN/BUSINESS      │
                    │   SCHEMA MAPPING + VALIDATION  │
                    │   (name, dob, gender, phone,   │
                    │   address, aadhaar_last4, id)  │
                    └───────────────┬─────────────────┘
                                     ▼
       ┌─────────────────────────────────────────────────────────┐
       │                 JagatData MIDDLEWARE (FastAPI)            │
       │                                                           │
       │  ┌───────────────┐  ┌────────────────┐  ┌──────────────┐ │
       │  │ Duplicate/     │  │ Consent        │  │ Federated     │ │
       │  │ Record Linkage │  │ Management     │  │ Login (RBAC)  │ │
       │  │ (RapidFuzz,    │  │ (grant/deny/   │  │ Admin/Officer/│ │
       │  │ explainable    │  │ revoke, scope) │  │ Reviewer      │ │
       │  │ scoring)       │  │                │  │               │ │
       │  └───────────────┘  └────────────────┘  └──────────────┘ │
       │  ┌───────────────┐  ┌────────────────┐  ┌──────────────┐ │
       │  │ Application /  │  │ Grievance      │  │ Beneficiary / │ │
       │  │ Configurable   │  │ Tracking       │  │ Outcome       │ │
       │  │ Workflow Engine│  │                │  │ Tracking      │ │
       │  └───────────────┘  └────────────────┘  └──────────────┘ │
       │  ┌───────────────┐  ┌────────────────┐                   │
       │  │ Audit Logs +   │  │ Event Publisher │                  │
       │  │ API Monitoring │  │ (webhooks)      │                  │
       │  └───────────────┘  └───────┬────────┘                   │
       │                              │                             │
       │         SQLite: citizens · source_records · match_candidates│
       │         applications · workflow_history · grievances ·      │
       │         beneficiaries · consents · audit_logs · api_monitor │
       └──────────────────────────────┬──────────────────────────────┘
                                       │
                        ┌──────────────┼───────────────┐
                        ▼                              ▼
              ┌──────────────────┐          ┌────────────────────┐
              │ Streamlit Unified │          │ n8n Webhook          │
              │ Dashboard         │          │ (event notifications:│
              │ (citizens,        │          │ SMS/Email/Telegram/  │
              │ officers, admin)  │          │ Slack to officers &  │
              │                   │          │ citizens)             │
              └──────────────────┘          └────────────────────┘
```

## Data flow (demo)

1. **Ingest** — Department CSV/API data flows through a per-department **connector**
   that maps native fields into the common schema and flags data-quality issues.
2. **Standardize** — Names, phone numbers, addresses and IDs are normalized using
   deterministic rules (title stripping, digit-only phone comparison, address term
   standardization, ID uppercasing).
3. **Detect duplicates** — Candidate record pairs are blocked (by name prefix / phone
   suffix) then scored with the weighted RapidFuzz formula, producing an explainable
   reason string and a decision band.
4. **Review** — An Officer/Reviewer confirms or rejects each candidate from the
   dashboard. Confirming links both source records to one **golden citizen record**;
   nothing is ever auto-merged or deleted.
5. **Unified profile** — Once linked, a citizen's Health/Education/Welfare records,
   applications, grievances, and consent history appear together in one profile view.
6. **Consent** — Before one department's data is exposed to another via the platform,
   a consent record is requested and must be explicitly granted by/on behalf of the
   citizen.
7. **Track** — Applications move through a configurable workflow
   (`submitted → under_review → additional_info_requested → approved/rejected → completed`),
   with full history retained.
8. **Notify** — Every significant event (new duplicate candidates, grievance filed,
   application status change, consent requested) fires a webhook to n8n, which routes
   to the right notification channel.
9. **Audit & monitor** — All actions are logged; connector sync health (including
   failed syncs) and data-quality scores are visible to Admins.
10. **Export** — Reports (applications, grievances, citizens, matches, audit) can be
    exported as CSV at any time.

## Why this satisfies "interoperability without replacement"

- Legacy department systems are **only read from** (via CSV export or API pull) —
  JagatData never writes back into or requires modification of source systems.
- Each connector is an independent, pluggable adapter — adding a new department
  (e.g., Transport, Revenue) means writing one new `map_<dept>()` function, not
  redesigning the platform.
- The common schema + master citizen record is additive middleware, not a
  system-of-record replacement.

## Future scope (explicitly out of MVP)

- **ML-based matching**: learned entity-resolution models (e.g. Splink, dedupe.io)
  on top of today's explainable rules, used to catch weaker linkage signals.
- **OCR + document intelligence**: automatic text extraction from scanned ID
  documents/certificates for the "document similarity" component (currently uses
  structured extra-fields as a proxy).
- **Real government integration**: DigiLocker, Aadhaar eKYC/API Setu, UPI-linked
  ID verification, and direct REST/SOAP connectors into live department systems
  instead of CSV batch ingestion.
- **Production-grade auth**: OAuth2/OIDC federated login against each department's
  identity provider, replacing the demo token store.
- **Horizontal scaling**: move from SQLite to PostgreSQL + message queue (Kafka)
  for real ingestion volumes; async connector workers.
