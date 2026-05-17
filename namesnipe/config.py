from __future__ import annotations

import tomllib
from decimal import Decimal
from pathlib import Path
from typing import Any

from .models import AppConfig
from .storage import config_path


def load_config(path: Path | None = None) -> AppConfig:
    target = path or config_path()
    if not target.exists():
        return AppConfig()
    with target.open("rb") as handle:
        raw = tomllib.load(handle)
    data: dict[str, Any] = dict(raw)
    ui = data.pop("ui", {})
    return AppConfig(**data, ui=ui)


def save_config(config: AppConfig, path: Path | None = None) -> Path:
    target = path or config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(config_to_toml(config), encoding="utf-8")
    return target


def _format_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, Decimal):
        return f'"{value:.2f}"'
    if isinstance(value, int):
        return str(value)
    if isinstance(value, list):
        return "[" + ", ".join(_format_value(item) for item in value) + "]"
    if value is None:
        return '""'
    return '"' + str(value).replace('"', '\\"') + '"'


def config_to_toml(config: AppConfig) -> str:
    lines = [
        f"account_id = {_format_value(config.account_id)}",
        f"max_price_usd = {_format_value(config.max_price_usd)}",
        f"max_total_usd = {_format_value(config.max_total_usd)}",
        f"tld_allowlist = {_format_value(config.tld_allowlist)}",
        f"auto_renew = {_format_value(config.auto_renew)}",
        f"dry_run = {_format_value(config.dry_run)}",
        f"privacy_mode = {_format_value(config.privacy_mode)}",
        f"years = {_format_value(config.years)}",
        "",
        "[ui]",
        f"language = {_format_value(config.ui.language)}",
        "",
    ]
    return "\n".join(lines)
