from __future__ import annotations

import os
from pathlib import Path

from platformdirs import user_config_path, user_data_path

APP_NAME = "NameSnipe"
TOKEN_SERVICE = "namesnipe.cloudflare"
TOKEN_USERNAME = "cloudflare_api_token"
TOKEN_ENV_VAR = "CLOUDFLARE_API_TOKEN"


def config_dir() -> Path:
    path = user_config_path(APP_NAME, appauthor=False)
    path.mkdir(parents=True, exist_ok=True)
    return path


def data_dir() -> Path:
    path = user_data_path(APP_NAME, appauthor=False)
    path.mkdir(parents=True, exist_ok=True)
    return path


def config_path() -> Path:
    return config_dir() / "config.toml"


def latest_plan_path() -> Path:
    return Path.cwd() / "namesnipe-plan.json"


def get_api_token() -> str | None:
    env_token = os.environ.get(TOKEN_ENV_VAR)
    if env_token:
        return env_token
    try:
        import keyring
    except Exception:
        return None
    try:
        return keyring.get_password(TOKEN_SERVICE, TOKEN_USERNAME)
    except Exception:
        return None


def set_api_token(token: str) -> bool:
    try:
        import keyring
    except Exception:
        return False
    try:
        keyring.set_password(TOKEN_SERVICE, TOKEN_USERNAME, token)
    except Exception:
        return False
    return True
