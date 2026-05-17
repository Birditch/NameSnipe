# Security Policy

NameSnipe is local-first. It does not run a server, create a database, sync cloud state, or send telemetry.

## Supported Versions

Security fixes target the latest released version.

## Reporting a Vulnerability

Please report vulnerabilities through GitHub Security Advisories when available, or open a minimal public issue that does not include secrets, tokens, private account IDs, or billable domain targets.

## Secret Handling

- Cloudflare API tokens are stored in system keyring when available.
- `CLOUDFLARE_API_TOKEN` is supported as a local environment fallback.
- Tokens must not be written to `config.toml`.
- Logs and errors must not include full tokens or Authorization headers.

## Billable Action Boundary

Live registration requires:

- `namesnipe buy --live`
- a fresh domain-check immediately before registration
- unchanged price and status
- configured budgets still passing
- exact confirmation phrase input

NameSnipe must not retry billable registration requests automatically.
