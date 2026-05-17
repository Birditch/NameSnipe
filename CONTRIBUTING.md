# Contributing to NameSnipe

NameSnipe is safety-first software. Changes that can trigger billable Cloudflare Registrar actions must preserve dry-run defaults, explicit human confirmation, and final real-time checks.

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest
python -m ruff check .
python -m ruff format .
```

## Safety Rules

- Never store Cloudflare API tokens in source files, tests, logs, screenshots, issues, or PR bodies.
- Never make live purchase the default.
- Never retry registration requests blindly.
- Always keep search results separate from checked, buyable domains.
- Keep confirmation phrases stable and language-independent.
- Tests must mock Cloudflare API calls.

## Translations

Add new languages by copying `namesnipe/locales/en.json`, translating values, and keeping keys unchanged. Safety warnings must be clear in every supported language.
