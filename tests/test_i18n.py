from __future__ import annotations

from typer.main import get_command
from typer.testing import CliRunner

from namesnipe.cli import app
from namesnipe.i18n import catalog_keys, missing_keys, t
from namesnipe.tui import NAV_KEYS


def test_all_non_english_catalogs_have_required_safety_keys() -> None:
    required = {
        "security.dry_run_enabled",
        "security.live_purchase_warning",
        "security.confirm_phrase_required",
        "errors.token_missing",
        "errors.premium_rejected",
        "buy.price_changed_abort",
    }
    for language in ("zh-CN", "ja-JP"):
        assert required <= catalog_keys(language)


def test_non_english_catalogs_are_complete_for_first_party_keys() -> None:
    assert missing_keys("zh-CN") == set()
    assert missing_keys("ja-JP") == set()


def test_tui_nav_labels_have_translations() -> None:
    for key in NAV_KEYS:
        assert t(key) != key


def test_cli_help_text_has_i18n_coverage_where_reasonable() -> None:
    result = CliRunner().invoke(app, ["search", "--help"])
    assert result.exit_code == 0
    assert "Search candidate domains." in result.stdout
    command = get_command(app)
    search = command.commands["search"]
    option_names = {option for parameter in search.params for option in parameter.opts}
    assert "--lang" in option_names
