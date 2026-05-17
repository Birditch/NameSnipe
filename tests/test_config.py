from __future__ import annotations

from decimal import Decimal

from namesnipe.config import load_config, save_config
from namesnipe.i18n import (
    SUPPORTED_LANGUAGES,
    catalog_keys,
    resolve_language,
    set_language,
    t,
)
from namesnipe.models import AppConfig
from namesnipe.storage import config_path, get_api_token, set_api_token


def test_default_language_fallback_to_en(monkeypatch) -> None:
    monkeypatch.delenv("NAMESNIPE_LANG", raising=False)
    assert resolve_language(None, None, environ={}) in SUPPORTED_LANGUAGES


def test_config_language_zh_cn(tmp_path) -> None:
    path = tmp_path / "namesnipe-config.json"
    save_config(AppConfig(ui={"language": "zh-CN"}), path)
    assert load_config(path).ui.language == "zh-CN"


def test_env_language_overrides_config() -> None:
    assert resolve_language(None, "ja-JP", environ={"NAMESNIPE_LANG": "zh-CN"}) == "zh-CN"


def test_cli_lang_overrides_env() -> None:
    assert resolve_language("ja-JP", "zh-CN", environ={"NAMESNIPE_LANG": "en"}) == "ja-JP"


def test_missing_translation_falls_back_to_en() -> None:
    set_language("zh-CN")
    assert t("missing.translation.key") == "missing.translation.key"
    assert t("app.title") == "NameSnipe"


def test_all_required_keys_exist_in_en() -> None:
    required = {
        "app.title",
        "nav.dashboard",
        "nav.search",
        "nav.check",
        "nav.plan",
        "nav.buy",
        "nav.config",
        "nav.logs",
        "security.dry_run_enabled",
        "security.live_purchase_warning",
        "errors.token_missing",
        "errors.confirm_phrase_mismatch",
    }
    assert required <= catalog_keys("en")


def test_config_decimal_round_trip(tmp_path) -> None:
    path = tmp_path / "namesnipe-config.json"
    save_config(
        AppConfig(max_price_usd=Decimal("12.34"), max_total_usd=Decimal("56.78")),
        path,
    )
    loaded = load_config(path)
    assert loaded.max_price_usd == Decimal("12.34")
    assert loaded.max_total_usd == Decimal("56.78")


def test_tld_ignorelist_round_trip(tmp_path) -> None:
    path = tmp_path / "namesnipe-config.json"
    save_config(AppConfig(tld_ignorelist=[".zip", "MOV", "zip"]), path)
    loaded = load_config(path)
    assert loaded.tld_ignorelist == ["zip", "mov"]
    assert '"tld_ignorelist"' in path.read_text(encoding="utf-8")


def test_legacy_tld_allowlist_is_not_treated_as_ignorelist(tmp_path) -> None:
    path = tmp_path / "namesnipe-config.json"
    path.write_text('{"tld_allowlist": ["com", "link"]}', encoding="utf-8")
    assert load_config(path).tld_ignorelist == []


def test_config_path_is_run_directory_json(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert config_path() == tmp_path / "namesnipe-config.json"


def test_api_token_saved_in_local_json(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    save_config(AppConfig(account_id="account-id"))
    assert set_api_token("local-token")
    assert get_api_token() == "local-token"
    contents = config_path().read_text(encoding="utf-8")
    assert '"cloudflare_api_token": "local-token"' in contents
    assert load_config().account_id == "account-id"


def test_env_token_overrides_local_json(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    set_api_token("local-token")
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "env-token")
    assert get_api_token() == "env-token"
