from __future__ import annotations

import json
import locale
import os
from functools import cache
from importlib import resources
from typing import Any

SUPPORTED_LANGUAGES = ("en", "zh-CN", "ja-JP")
DEFAULT_LANGUAGE = "en"
ENV_LANGUAGE = "NAMESNIPE_LANG"

_current_language = DEFAULT_LANGUAGE


def normalize_language(language: str | None) -> str | None:
    if not language:
        return None
    value = language.strip().replace("_", "-")
    lower = value.lower()
    if lower.startswith("zh"):
        return "zh-CN"
    if lower.startswith("ja"):
        return "ja-JP"
    if lower.startswith("en"):
        return "en"
    return value if value in SUPPORTED_LANGUAGES else None


def resolve_language(
    cli_language: str | None = None,
    config_language: str | None = None,
    environ: dict[str, str] | None = None,
) -> str:
    env = environ if environ is not None else os.environ
    for candidate in (
        cli_language,
        env.get(ENV_LANGUAGE),
        config_language,
        *_system_locale_candidates(env),
    ):
        normalized = normalize_language(candidate)
        if normalized in SUPPORTED_LANGUAGES:
            return normalized
    return DEFAULT_LANGUAGE


def _system_locale_candidates(env: dict[str, str]) -> tuple[str | None, ...]:
    return (
        env.get("LC_ALL"),
        env.get("LC_MESSAGES"),
        env.get("LANG"),
        locale.getlocale()[0],
    )


def set_language(language: str | None) -> str:
    global _current_language
    _current_language = normalize_language(language) or DEFAULT_LANGUAGE
    return _current_language


def get_language() -> str:
    return _current_language


@cache
def _load_catalog(language: str) -> dict[str, str]:
    normalized = normalize_language(language) or DEFAULT_LANGUAGE
    path = resources.files("namesnipe") / "locales" / f"{normalized}.json"
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return {str(key): str(value) for key, value in data.items()}


def t(key: str, **kwargs: Any) -> str:
    catalog = _load_catalog(_current_language)
    fallback = _load_catalog(DEFAULT_LANGUAGE)
    template = catalog.get(key) or fallback.get(key) or key
    if kwargs:
        return template.format(**kwargs)
    return template


def catalog_keys(language: str) -> set[str]:
    return set(_load_catalog(language).keys())


def missing_keys(language: str) -> set[str]:
    return catalog_keys(DEFAULT_LANGUAGE) - catalog_keys(language)
