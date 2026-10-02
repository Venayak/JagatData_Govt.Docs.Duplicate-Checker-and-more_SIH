# 🏛️ JagatData

**Connecting Government Systems. Simplifying Public Services.**

SIH 2026 MVP for: *"System integration and interoperability among government digital
platforms, resulting in fragmented service delivery."*

JagatData is an interoperability **middleware** that connects existing Health,
Education, and Welfare department systems (mock APIs/CSVs in this MVP) — mapping
their data into a common schema, detecting cross-department duplicate records with
an **explainable** fuzzy-matching score, unifying citizen profiles, and tracking
applications/grievances/beneficiaries end-to-end, without replacing any legacy system.

---

## 🧱 Stack

`Python 3.10+ · FastAPI · SQLite · Pandas · RapidFuzz · Streamlit · n8n (webhooks)`

## 📁 Project structure

```
JagatData/
├── backend/
│   ├── main.py            # FastAPI app — all REST endpoints
│   ├── database.py        # SQLite schema + helpers
│   ├── connectors.py      # Per-department schema mapping + validation
│   ├── matching.py        # Explainable duplicate-detection engine
│   └── auth.py             # Demo role-based auth (federated login simulation)
├── streamlit_app/
│   └── app.py               # Unified dashboard (all roles)
├── data/
│   ├── generate_data.py     # Generates the sample CSVs below
│   ├── health_department.csv
│   ├── education_department.csv
│   └── welfare_department.csv
├── n8n/
│   └── jagatdata_workflow.json   # Importable n8n workflow for event notifications
├── docs/
│   ├── architecture.md      # Architecture diagram + data flow
│   ├── API.md                 # Full API reference
│   └── presentation.md      # Problem / Solution / Impact (SIH pitch-ready)
├── requirements.txt
├── .env.example
├── run_backend.sh
└── run_dashboard.sh
```

## ⚡ Quick setup (30 seconds)

### Via VS Code (Recommended)

```bash
cd JagatData
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Then:
1. Press **Ctrl+`** to open VS Code's integrated terminal
2. Split the terminal (**Ctrl+Shift+5**)
3. **Left pane**: `python3 -m uvicorn backend.main:app --reload`
4. **Right pane**: `streamlit run streamlit_app/app.py`

Sample data auto-loads on first backend startup. Done.

- Backend API: http://127.0.0.1:8000 (Swagger docs at `/docs`)
- Dashboard: http://127.0.0.1:8501

### Via command line (2 terminals)

```bash
cd JagatData
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Terminal A
python3 -m uvicorn backend.main:app --reload

# Terminal B
streamlit run streamlit_app/app.py
```

**No manual data loading needed** — sample CSVs (Health, Education, Welfare) auto-load on first backend startup.

## 🔑 Demo credentials

| Username | Password | Role | Department |
|---|---|---|---|
| `admin` | `admin123` | Admin | All |
| `officer1` | `officer123` | Officer | Health |
| `officer2` | `officer123` | Officer | Welfare |
| `reviewer1` | `reviewer123` | Reviewer | All |

## 🚀 Demo flow (matches SIH judging flow)

1. **Login** as `admin` on the dashboard.
2. Go to **Connectors & Ingestion** → click "⚡ Load sample data" for Health,
   Education, and Welfare (or upload your own CSVs in the same schema).
3. Go to **Duplicate Detection** → click "Run Duplicate Detection" → review
   candidate pairs, each with an explainable score and reason string → **Confirm**
   a probable duplicate to create a unified citizen profile.
4. Go to **Unified Profile** → select the newly unified citizen → see all linked
   department records together.
5. Go to **Applications** → file a cross-department application for that citizen →
   move it through workflow statuses.
6. Go to **Consent** → request consent for one department to view another
   department's data about that citizen → grant it.
7. Go to **Grievances** → file and resolve a grievance for the same citizen.
8. Go to **Audit & Monitoring** → see the full audit trail, connector sync health,
   and data-quality scores.
9. Go to **Reports** → export any report as CSV.
10. (Optional) Import `n8n/jagatdata_workflow.json` into a running n8n instance,
    point `N8N_WEBHOOK_URL` in `.env` to its webhook, and watch notifications
    fire live as you do steps 3–8.

## 🧬 Duplicate-detection scoring (explainable, no ML)

```
score = 0.40 × name_similarity
      + 0.30 × phone_or_id_similarity
      + 0.20 × address_similarity
      + 0.10 × document_detail_similarity
```
Weights are **redistributed proportionally** across whichever fields are actually
present on both records. Decision bands:

| Score | Decision |
|---|---|
| ≥ 85 | Probable duplicate |
| 65–84 | Manual review |
| < 65 | Probably different |

Records are **never** auto-merged or deleted — only an authorized Officer/Reviewer
can confirm or reject a candidate match from the dashboard.

Normalization rules applied before comparison:
- **Names**: lowercased, punctuation removed, titles stripped (Mr/Mrs/Shri/Smt/etc.), whitespace collapsed.
- **Phone**: non-digits removed, compared on last 10 digits (handles `+91`, spaces, dashes).
- **Address**: lowercased, punctuation removed, standardized terms (`H.No`→`house no`, `Sec`→`sector`, `Rd`→`road`, etc.).
- **IDs/documents**: whitespace/dashes stripped, uppercased, compared exactly or via fuzzy ratio.

## 📊 Sample data

`data/generate_data.py` generates realistic Indian citizen records across three
**intentionally different schemas** (Health, Education, Welfare) with deliberate
name/phone/address format variations for the *same* underlying people — so the
duplicate-detection demo has real cross-department matches to find. Re-run it any
time to regenerate fresh sample data:

```bash
cd data && python3 generate_data.py
```

## 🔮 Future scope (not in this MVP by design)

- ML-based entity resolution layered on top of today's explainable rules.
- OCR for scanned ID/certificate verification.
- Real integrations: DigiLocker, Aadhaar eKYC / API Setu.
- Production OAuth2/OIDC federated login per department IdP.
- PostgreSQL + queue-based ingestion for production data volumes.

See `docs/architecture.md` and `docs/presentation.md` for full details.
