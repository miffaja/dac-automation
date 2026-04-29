# Troubleshooting Guide

## Common Issues

### 401 Unauthorized / Session Expired

**Symptom**: API calls return `{"error": "HTTP 401"}`

**Cause**: Session cookies expired.

**Fix**:
```bash
# Re-authenticate with MetaMask
xvfb-run node dac-auth.js

# Copy new tokens from /tmp/dac-auth.json to dac_auto.py COOKIE and CSRF
```

### MetaMask Popup Not Detected

**Symptom**: Script hangs at "Waiting for MetaMask popup..."

**Fix**:
1. Check screenshots in `/tmp/` for the current UI state
2. The DAC site may have updated their UI — selectors may need updating
3. Try clicking manually and check `/tmp/dac-*-*.png` screenshots

### Faucet Not Available

**Symptom**: `"faucet_available": false`

**Cause**: Cooldown not finished (typically 8 hours between claims).

**Output**: Script will show:
```
Faucet in: 7h 23m
```

**Fix**: Wait for cooldown, or check `/api/inception/faucet/status/` for exact timer.

### Chromium Sandbox Error

**Symptom**: `Error: Unable to launch Chrome!`

**Fix**:
```bash
# Install dependencies
npx playwright install-deps chromium
npx playwright install chromium

# Or run with sandbox disabled
xvfb-run --server-args="-screen 0 1280x900x24" node dac-auth.js
```

### Private Key / Transaction Errors

**Symptom**: `ValueError: Could not identify transaction`

**Cause**: Nonce mismatch or insufficient balance.

**Fix**:
```python
# Manually sync nonce
nonce = w3.eth.get_transaction_count(acct.address)
```

### Playwright Browser Path Issues

**Symptom**: `Browser not found` or empty screenshots

**Fix**:
```bash
# Set browser path explicitly
PLAYWRIGHT_BROWSERS_PATH=~/.cache/ms-playwright npx playwright install chromium
```

## Debug Mode

For detailed logs, add `--verbose` flags or check:

```bash
# View recent screenshots
ls -lt /tmp/*.png | head

# Watch cookie changes
cat /tmp/dac-auth.json

# Watch cron logs
tail -f ~/dac-automation/cron.log
```

## Getting Help

1. Run: `python3 dac_auto.py profile` — shows current account state
2. Run: `xvfb-run node dac-auth.js` — full browser debug
3. Check `/tmp/` for screenshots at each step
4. Include these when reporting issues:
   - OS version
   - Python version (`python3 --version`)
   - Node version (`node --version`)
   - Full error output
