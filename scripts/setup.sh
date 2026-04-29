#!/usr/bin/env bash
set -euo pipefail
python3 -m venv .venv || true
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -r requirements.txt
npm install
cp -n .env.example .env || true
echo "Setup complete. Edit .env then run: python3 scripts/run.py profile"
