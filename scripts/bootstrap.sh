
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
npm install

echo "✅ bootstrap complete"
echo "Next: cp .env.example .env && edit values"

python3 -m py_compile automation/python/dac_auto.py
