#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
if [ ! -f ".env" ]; then cp .env.example .env; fi
export $(grep -v '^#' .env | xargs)
echo "Starting JagatData FastAPI backend on http://127.0.0.1:8000 ..."
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
