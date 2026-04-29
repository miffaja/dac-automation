
# DAC Inception Automation

[![CI](https://github.com/miffaja/dac-automation/actions/workflows/ci.yml/badge.svg)](https://github.com/miffaja/dac-automation/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Node](https://img.shields.io/badge/node-18%2B-green)
![License: MIT](https://img.shields.io/badge/license-MIT-yellow)

Production-style, agent-ready automation toolkit for DAC Inception testnet.

## Highlights
- 🔐 Env-based secret handling (`.env`), no hardcoded runtime secrets required
- 🤖 Agent-friendly CLI (`profile`, `faucet`, `crates`, `tx`, `sendto`, `full`)
- 🧩 Works with MetaMask auth capture via Playwright
- 🛡️ Includes CI, SECURITY policy, bootstrap script, changelog

## Quickstart
```bash
git clone https://github.com/miffaja/dac-automation.git
cd dac-automation
./scripts/bootstrap.sh
cp .env.example .env
# edit .env
python3 automation/python/dac_auto.py profile
```

## Auth Flow
```bash
npm run auth
python3 automation/python/dac_auto.py bootstrap-session
python3 automation/python/dac_auto.py profile
```

## CLI Commands
```bash
python3 automation/python/dac_auto.py profile
python3 automation/python/dac_auto.py faucet
python3 automation/python/dac_auto.py crates 3
python3 automation/python/dac_auto.py tx 5 --amount 0.001
python3 automation/python/dac_auto.py sendto --addresses-file automation/config/addresses.txt --amount 0.001
python3 automation/python/dac_auto.py full
```

## Repository Structure
```text
.
├── automation/
│   ├── python/dac_auto.py
│   ├── js/dac-auth.js
│   ├── js/dac-refresh.js
│   ├── js/config.js
│   └── config/addresses.txt
├── scripts/bootstrap.sh
├── .env.example
├── requirements.txt
├── SECURITY.md
├── SKILL.md
└── .github/workflows/ci.yml
```

## Security Notes
- Never commit `.env` or real cookies/private keys.
- This repo is intended for **testnet** usage.

## License
MIT
