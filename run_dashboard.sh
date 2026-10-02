#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
if [ ! -f ".env" ]; then cp .env.example .env; fi
export $(grep -v '^#' .env | xargs)
echo "Starting JagatData Streamlit dashboard on http://127.0.0.1:8501 ..."
streamlit run streamlit_app/app.py
