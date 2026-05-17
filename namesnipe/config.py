from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import AppConfig
from .storage import config_path

SENSITIVE_CONFIG_KEYS = {"cloudflare_api_token"}


def load_config(path: Path | None = None) -> AppConfig:
    target = path or config_path()
    if not target.exists():
        return AppConfig()
    raw = json.loads(target.read_text(encoding="utf-8"))
    data: dict[str, Any] = dict(raw)
    for key in SENSITIVE_CONFIG_KEYS:
        data.pop(key, None)
    ui = data.pop("ui", {})
    return AppConfig(**data, ui=ui)


def save_config(config: AppConfig, path: Path | None = None) -> Path:
    target = path or config_path()
    existing = _read_config_dict(target)
    sensitive = {key: existing[key] for key in SENSITIVE_CONFIG_KEYS if key in existing}
    data = config.model_dump(mode="json")
    data.update(sensitive)
    _write_config_dict(target, data)
    return target


def _read_config_dict(path: Path | None = None) -> dict[str, Any]:
    target = path or config_path()
    if not target.exists():
        return {}
    return json.loads(target.read_text(encoding="utf-8"))


def _write_config_dict(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
