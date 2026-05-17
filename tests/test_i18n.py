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
        "init.explain.account_id",
        "init.explain.api_token",
        "init.explain.max_price",
        "init.explain.max_total",
        "init.explain.tld_ignorelist",
        "init.explain.auto_renew",
        "init.explain.dry_run",
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
    assert "help" in command.commands


def test_help_command_outputs_command_table() -> None:
    result = CliRunner().invoke(app, ["help"], env={"NAMESNIPE_LANG": "en"})
    assert result.exit_code == 0
    assert "NameSnipe help" in result.stdout
    assert "search" in result.stdout


def test_root_command_defaults_to_tui(monkeypatch) -> None:
    called = {}

    class FakeApp:
        def __init__(self, config) -> None:
            called["config"] = config

        def run(self) -> None:
            called["run"] = True

    import namesnipe.tui

    monkeypatch.setattr(namesnipe.tui, "NameSnipeApp", FakeApp)
    result = CliRunner().invoke(app, [], env={"NAMESNIPE_LANG": "en"})
    assert result.exit_code == 0
    assert called["run"] is True
