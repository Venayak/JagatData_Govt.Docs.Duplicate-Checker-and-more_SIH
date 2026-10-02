# JagatData — Quick Start (30 seconds)

## 1️⃣ Install dependencies
```bash
cd JagatData
python3 -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 2️⃣ Run (pick one)

### Option A: VS Code (Easiest)
1. Open JagatData folder in VS Code
2. Press **Ctrl+`** (backtick) to open integrated terminal
3. Split terminal: click split icon or press **Ctrl+Shift+5**
4. Left pane: `python3 -m uvicorn backend.main:app --reload`
5. Right pane: `streamlit run streamlit_app/app.py`

### Option B: Terminal (Two windows)
```bash
# Window 1
python3 -m uvicorn backend.main:app --reload

# Window 2
streamlit run streamlit_app/app.py
```

### Option C: Shell scripts (Two windows)
```bash
# Window 1
bash run_backend.sh

# Window 2
bash run_dashboard.sh
```

## 3️⃣ Access & demo
- Backend: http://127.0.0.1:8000 (API + Swagger docs at `/docs`)
- Dashboard: http://127.0.0.1:8501
- Login: `admin` / `admin123`

**Sample data auto-loads on first backend startup.** No manual CSV uploads needed.

## 🚀 Demo flow (2 min)
1. **Login** as `admin`
2. Go to **Duplicate Detection** tab → click "Run Duplicate Detection"
3. See 39 candidate pairs → **Confirm** the first one
4. Go to **Unified Profile** tab → view the merged citizen record
5. Go to **Audit & Monitoring** → see full action history
6. Go to **Reports** → export a CSV

Done! 🎉
