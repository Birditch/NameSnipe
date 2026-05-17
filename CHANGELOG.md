# Changelog

## 0.1.0

- Initial public release.
- Typer CLI for init, search, check, plan, buy, status, and tui.
- Textual TUI with safety dashboard, workflow pages, configuration, and logs.
- Rich tables and panels for terminal output.
- Cloudflare Registrar client wrapper using httpx.
- Local run-directory JSON config via `namesnipe-config.json`, including Cloudflare API settings, with environment fallback.
- Safety guards for dry-run defaults, premium rejection, budget limits, recent checks, confirmation phrases, and final price/status validation.
- Built-in i18n for English, Simplified Chinese, and Japanese.
- pytest and ruff CI.
