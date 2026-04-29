# DAC Automation

[![CI](https://github.com/miffaja/dac-automation/actions/workflows/ci.yml/badge.svg)](https://github.com/miffaja/dac-automation/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Node](https://img.shields.io/badge/node-18%2B-green)
![License](https://img.shields.io/badge/license-MIT-yellow)

Minimal, serious, agent-friendly DAC Inception testnet automation project.

## Structure
```text
dac-automation/
├── core/                 # engine, scheduler, wallet, network, logger
├── modules/              # faucet, transaction, dac, mint, account
├── strategies/           # daily & aggressive flow
├── config/               # yaml/json project config
├── scripts/              # entrypoint + setup
├── utils/                # retry/helper/proxy
├── logs/                 # runtime log output
├── tests/                # basic tests
├── automation/js/        # browser auth capture (Playwright + MetaMask)
└── .github/workflows/    # CI
```

## Quick Start
```bash
git clone https://github.com/miffaja/dac-automation.git
cd dac-automation
./scripts/setup.sh
cp .env.example .env
# edit .env
python3 scripts/run.py profile
```

## Cara Ambil Cookies (sessionid + csrftoken)
1. Isi `.env` minimal:
   - `METAMASK_SEED`
   - `METAMASK_PASSWORD`
   - `METAMASK_EXTENSION_PATH`
2. Jalankan auth capture:
```bash
npm run auth
```
3. Hasil disimpan otomatis ke:
   - `/tmp/dac-auth.json` (sessionid + csrftoken)
   - `/tmp/dac-cookies.json` (raw DAC cookies)
4. Inject sesi ke `.env`:
```bash
python3 automation/python/dac_auto.py bootstrap-session
```
5. Verifikasi:
```bash
python3 scripts/run.py profile
```

## Commands
```bash
python3 scripts/run.py profile
python3 scripts/run.py faucet
python3 scripts/run.py tx 5 --amount 0.001
python3 scripts/run.py daily
python3 scripts/run.py aggressive
```

## Security
- Never commit real `.env`, session cookies, or private keys.
- Testnet only.
