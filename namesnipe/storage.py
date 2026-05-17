from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from platformdirs import user_data_path

APP_NAME = "NameSnipe"
TOKEN_ENV_VAR = "CLOUDFLARE_API_TOKEN"
TOKEN_CONFIG_KEY = "cloudflare_api_token"
CONFIG_FILENAME = "namesnipe-config.json"


def data_dir() -> Path:
    path = user_data_path(APP_NAME, appauthor=False)
    path.mkdir(parents=True, exist_ok=True)
    return path


def config_path() -> Path:
    return Path.cwd() / CONFIG_FILENAME


def latest_plan_path() -> Path:
    return Path.cwd() / "namesnipe-plan.json"


def get_api_token() -> str | None:
    env_token = os.environ.get(TOKEN_ENV_VAR)
    if env_token:
        return env_token
    local_token = _read_local_config().get(TOKEN_CONFIG_KEY)
    if isinstance(local_token, str) and local_token:
        return local_token
    return None


def set_api_token(token: str) -> bool:
    data = _read_local_config()
    data[TOKEN_CONFIG_KEY] = token
    _write_local_config(data)
    return True


def _read_local_config() -> dict[str, Any]:
    path = config_path()
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_local_config(data: dict[str, Any]) -> None:
    path = config_path()
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
