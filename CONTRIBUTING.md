# Contributing to DAC Inception Automation

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/yourname/dac-automation.git`
3. Create a branch: `git checkout -b feature/your-feature-name`

## Development Workflow

### Testing Changes

```bash
# Test individual functions
python3 dac_auto.py profile

# Test with xvfb (headless)
xvfb-run node dac-auth.js

# Run specific command
python3 dac_auto.py badges
```

### Code Style

- **Python**: Follow PEP 8. Max line length: 100 chars.
- **JavaScript**: Use async/await, no callback chains.
- **Comments**: English only. Document WHY, not WHAT.

### Adding New API Endpoints

1. Add the endpoint to `ENDPOINTS` dict in `dac_auto.py`
2. Create a function `api_get()` or `api_post()` call
3. Test with `python3 dac_auto.py <new_command>`
4. Update `README.md` API Endpoints table

### Adding New Features

1. Create a new function in `dac_auto.py`
2. Add CLI argument handler in `if __name__ == "__main__"`
3. Document in README.md
4. Test end-to-end

## Pull Request Process

1. Update README.md if behavior changed
2. Run full automation: `python3 dac_auto.py`
3. Ensure no hardcoded credentials (use env vars)
4. PR description must include: what changed, why, test results

## Reporting Issues

- Include: OS, Python version, Node version, exact error message
- Attach screenshots from `/tmp/` if browser-related
- Include output of: `python3 dac_auto.py profile`

## Security

- **NEVER** commit private keys or seed phrases
- Use environment variables for credentials
- Report vulnerabilities privately, not in issues
