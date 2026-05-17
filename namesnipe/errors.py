from __future__ import annotations


class NameSnipeError(Exception):
    """Base application error with a user-safe message."""


class ConfigError(NameSnipeError):
    """Configuration is missing or invalid."""


class SecurityError(NameSnipeError):
    """A safety guard rejected the operation."""


class CloudflareAPIError(NameSnipeError):
    """Cloudflare API returned an error."""
