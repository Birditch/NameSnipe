# NameSnipe

A safe local-first Python TUI/CLI for searching, checking, and registering domains through Cloudflare Registrar API.

No web dashboard. No database. No telemetry. Dry-run by default.

NameSnipe is designed for developers who want a careful local workflow before spending money on domain registrations. It searches for candidates, performs authoritative real-time checks, creates a local purchase plan, and requires explicit human confirmation before any billable Cloudflare Registrar registration request.

## Why NameSnipe

Domain search tools often mix discovery, pricing, and purchase into one flow. NameSnipe keeps those steps separate:

- `search` returns candidates only.
- `check` performs real-time availability and price checks.
- `plan` creates a local JSON purchase plan after re-checking.
- `buy` defaults to dry-run and requires `--live` plus a confirmation phrase.
- `status` checks Cloudflare registration status without retrying purchases.

## Safety Design

- Local-first: all configuration and plan files stay on your machine.
- No database: plan files are one-time JSON artifacts.
- No web dashboard: the app is terminal-only.
- No telemetry: NameSnipe does not upload analytics or usage data.
- Dry-run by default: `namesnipe buy` does not register domains unless `--live` is passed.
- Human confirmation before billable actions.
- Price is re-checked immediately before live registration.
- Premium domains are rejected by default.
- Unsupported TLDs are rejected.
- Domains above budget are rejected.
- Batch totals above budget are rejected.
- Billable registration is never retried blindly, including `202 Accepted` responses.
- Cloudflare API settings are stored in `./namesnipe-config.json` in the directory where you run NameSnipe. The file is ignored by git by default and token values are never printed.

NameSnipe is local-first and safe by default in every language.

## Installation

Python 3.12+ is required.

With `pipx`:

```bash
pipx install namesnipe
```

From a checkout:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Using `uv` is supported but not required:

```bash
uv venv
uv pip install -e ".[dev]"
```

## Initialize

```bash
namesnipe init
```

The initializer asks for:

- Cloudflare Account ID
- Cloudflare API Token
- per-domain budget
- batch budget
- default TLD allowlist
- auto-renew default
- dry-run default
- UI language

The API token and non-sensitive settings are written to `./namesnipe-config.json` in the current working directory. This is a local JSON file intended for your machine only.

Example shape:

```json
{
  "account_id": "your-cloudflare-account-id",
  "max_price_usd": "10.00",
  "max_total_usd": "50.00",
  "tld_allowlist": ["link", "cc", "xyz", "icu", "dev", "app", "com"],
  "auto_renew": false,
  "dry_run": true,
  "privacy_mode": "redaction",
  "years": 1,
  "ui": {
    "language": "en"
  },
  "cloudflare_api_token": "your-local-token"
}
```

`namesnipe-config.json` is listed in `.gitignore`. Do not commit it. For a temporary token override, set:

```bash
export CLOUDFLARE_API_TOKEN="..."
```

## CLI Examples

Search candidates:

```bash
namesnipe search birditch --tlds link,cc,xyz,dev,app,com --limit 20 --cheap --max-price 10
```

Search results are not authoritative. Always check before planning:

```bash
namesnipe check birditch.link birditch.dev --max-price 10
```

Create a local purchase plan:

```bash
namesnipe plan birditch.link --output namesnipe-plan.json
```

Dry-run purchase:

```bash
namesnipe buy --plan namesnipe-plan.json
```

Live purchase requires an explicit flag and exact confirmation phrase:

```bash
namesnipe buy --plan namesnipe-plan.json --live
```

Example confirmation phrase:

```text
BUY 1 DOMAIN FOR 7.20 USD
```

Check registration status:

```bash
namesnipe status birditch.link
```

## TUI

Open the Textual interface:

```bash
namesnipe tui
```

The TUI includes:

- Dashboard
- Search
- Check
- Plan
- Buy
- Config
- Logs

The first version keeps Cloudflare operations in the CLI workflow while exposing safety state and configuration in the TUI. Live purchase areas show explicit warnings and confirmation requirements.

## Cloudflare API Token

Create a Cloudflare API token with the minimum Registrar permissions required by your account. NameSnipe needs access to:

- Registrar domain search
- Registrar domain check
- Registrar registrations
- Registrar registration status

Do not use a broader token unless your Cloudflare account policy requires it. NameSnipe never prints the token and redacts secrets in error handling.

## Internationalization

Built-in languages:

- `en`
- `zh-CN`
- `ja-JP`

Language priority:

1. CLI `--lang`
2. `NAMESNIPE_LANG`
3. `namesnipe-config.json` `ui.language`
4. system locale
5. `en`

Examples:

```bash
namesnipe tui --lang zh-CN
namesnipe tui --lang ja-JP
NAMESNIPE_LANG=zh-CN namesnipe check example.link
```

To add a new language:

1. Copy `namesnipe/locales/en.json` to `namesnipe/locales/<lang>.json`.
2. Translate every value and keep every key unchanged.
3. Add the language code to `SUPPORTED_LANGUAGES` in `namesnipe/i18n.py`.
4. Add tests that verify required safety keys exist.
5. Run `pytest`.

Translation contribution rules:

- Keep safety warnings clear and direct.
- Do not translate the confirmation phrase format.
- Do not include secrets or tokens in translation files.
- Keep missing translations falling back to English.

## Not Supported

NameSnipe intentionally does not provide:

- Web UI
- Database
- User accounts
- Cloud sync
- Telemetry
- Automatic infinite retries
- Bypassing Cloudflare Registrar limitations
- Cloud token storage
- Default live purchase mode

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check .
ruff format .
```

## Roadmap

- Fully interactive TUI search/check/plan flow.
- Import/export candidate lists.
- Optional local history without sensitive data.
- More Registrar status detail.
- More languages.
- Shell completions.

## License

MIT
