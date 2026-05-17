from __future__ import annotations

from typing import ClassVar

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import (
    Button,
    Checkbox,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Log,
    Static,
    TabbedContent,
    TabPane,
    TextArea,
)

from .config import save_config
from .i18n import get_language, set_language, t
from .models import AppConfig
from .storage import get_api_token, latest_plan_path

NAV_KEYS = [
    "nav.dashboard",
    "nav.search",
    "nav.check",
    "nav.plan",
    "nav.buy",
    "nav.config",
    "nav.logs",
]


class NameSnipeApp(App[None]):
    CSS = """
    Screen {
        background: $surface;
    }
    .topline {
        padding: 1;
        border: solid $primary;
    }
    .pane {
        padding: 1 2;
    }
    .row {
        height: auto;
        margin-bottom: 1;
    }
    .warning {
        color: $warning;
        text-style: bold;
    }
    Input {
        margin-right: 1;
    }
    Button {
        margin-right: 1;
    }
    DataTable {
        height: 12;
        margin-top: 1;
    }
    TextArea {
        height: 8;
    }
    """

    BINDINGS: ClassVar = [("q", "quit", t("common.cancel"))]

    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self.config = config
        self.language_notice = Static("")
        self.runtime_log = Log(id="runtime-log")

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static(self._safety_state(), id="safety-state", classes="topline")
        with TabbedContent(initial="dashboard"):
            with TabPane(t("nav.dashboard"), id="dashboard"):
                yield self._dashboard()
            with TabPane(t("nav.search"), id="search"):
                yield self._search()
            with TabPane(t("nav.check"), id="check"):
                yield self._check()
            with TabPane(t("nav.plan"), id="plan"):
                yield self._plan()
            with TabPane(t("nav.buy"), id="buy"):
                yield self._buy()
            with TabPane(t("nav.config"), id="config"):
                yield self._config()
            with TabPane(t("nav.logs"), id="logs"):
                yield self._logs()
        yield Footer()

    def on_mount(self) -> None:
        self._init_tables()
        self._write_log(t("app.safety_line"))
        self._write_log(t("tui.no_token_logged"))

    def _init_tables(self) -> None:
        self.query_one("#search-results", DataTable).add_columns(
            t("search.candidate"),
            t("common.price"),
            t("common.currency"),
            t("common.status"),
        )
        self.query_one("#check-results", DataTable).add_columns(
            t("common.domain"),
            t("common.status"),
            t("check.registration_price"),
            t("check.renewal_price"),
            t("common.reason"),
        )
        self.query_one("#plan-items", DataTable).add_columns(
            t("common.domain"),
            t("common.price"),
            t("common.currency"),
        )

    def _write_log(self, message: str) -> None:
        self.runtime_log.write_line(message)

    def _safety_state(self) -> str:
        return " | ".join(
            [
                t("app.title"),
                t("tui.current_language", language=get_language()),
                t(
                    "tui.dry_run_visible",
                    value=t("common.yes") if self.config.dry_run else t("common.no"),
                ),
                t("security.token_never_displayed"),
            ]
        )

    def _dashboard(self) -> Container:
        token_status = t("config.token_present") if get_api_token() else t("config.token_missing")
        account_status = t("common.yes") if self.config.account_id else t("common.no")
        return Container(
            Label(t("app.safety_line")),
            Label(f"{t('tui.account_configured')}: {account_status}"),
            Label(f"{token_status}: {t('security.token_never_displayed')}"),
            Label(f"{t('security.dry_run_enabled')} {self.config.dry_run}"),
            Label(f"{t('config.max_price_usd')}: {self.config.max_price_usd}"),
            Label(f"{t('config.max_total_usd')}: {self.config.max_total_usd}"),
            Label(f"{t('tui.recent_plan')}: {latest_plan_path()}"),
            classes="pane",
        )

    def _search(self) -> Container:
        return Container(
            Label(t("search.not_authoritative"), classes="warning"),
            Horizontal(
                Input(placeholder=t("tui.keyword"), id="search-keyword"),
                Input(
                    value=",".join(self.config.tld_allowlist),
                    placeholder=t("config.tld_allowlist"),
                    id="search-tlds",
                ),
                Input(value="20", placeholder=t("tui.limit"), id="search-limit"),
                classes="row",
            ),
            Horizontal(
                Checkbox(t("search.cheap_only"), id="search-cheap"),
                Button(t("tui.run_search"), id="run-search", variant="primary"),
                Button(t("tui.add_to_check"), id="add-search-to-check"),
                classes="row",
            ),
            DataTable(id="search-results"),
            Label(t("search.run_check_next")),
            classes="pane",
        )

    def _check(self) -> Container:
        return Container(
            Label(t("check.real_time_checking")),
            TextArea("", id="check-domains"),
            Horizontal(
                Checkbox(t("check.buyable"), id="filter-buyable"),
                Button(t("tui.run_check"), id="run-check", variant="primary"),
                classes="row",
            ),
            DataTable(id="check-results"),
            classes="pane",
        )

    def _plan(self) -> Container:
        return Container(
            Label(t("security.recheck_before_buy"), classes="warning"),
            Horizontal(
                Input(
                    value=str(latest_plan_path()),
                    placeholder=t("cli.output.help"),
                    id="plan-path",
                ),
                Button(t("tui.create_plan"), id="create-plan", variant="primary"),
                classes="row",
            ),
            DataTable(id="plan-items"),
            Label(f"{t('plan.estimated_total')}: -"),
            Label(f"{t('plan.confirm_phrase')}: -"),
            classes="pane",
        )

    def _buy(self) -> Container:
        return Container(
            Label(t("security.live_purchase_warning"), classes="warning"),
            Label(t("security.confirm_phrase_required")),
            Label(t("security.recheck_before_buy")),
            Label(t("buy.dry_run_only")),
            Horizontal(
                Input(
                    value=str(latest_plan_path()),
                    placeholder=t("cli.plan_file.help"),
                    id="buy-plan",
                ),
                Checkbox(t("tui.live_purchase"), id="buy-live"),
                Button(t("tui.load_plan"), id="load-plan"),
                classes="row",
            ),
            Input(placeholder=t("plan.confirm_phrase"), id="buy-confirm-phrase"),
            classes="pane",
        )

    def _config(self) -> Container:
        self.language_notice.update("")
        return Container(
            Label(t("config.language")),
            Horizontal(
                Button("English", id="lang-en"),
                Button("简体中文", id="lang-zh-CN"),
                Button("日本語", id="lang-ja-JP"),
                classes="row",
            ),
            self.language_notice,
            Label(t("config.token_env_required")),
            Label(t("tui.local_state_only")),
            classes="pane",
        )

    def _logs(self) -> Container:
        return Container(
            Label(t("tui.no_token_logged")),
            self.runtime_log,
            classes="pane",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        mapping = {
            "lang-en": "en",
            "lang-zh-CN": "zh-CN",
            "lang-ja-JP": "ja-JP",
        }
        if event.button.id in mapping:
            language = mapping[event.button.id]
            self.config.ui.language = language
            save_config(self.config)
            set_language(language)
            self.language_notice.update(t("tui.restart_required"))
            self.query_one("#safety-state", Static).update(self._safety_state())
            self._write_log(t("tui.restart_required"))
            return

        if event.button.id == "run-search":
            self._write_log(t("search.not_authoritative"))
        elif event.button.id == "add-search-to-check":
            self._write_log(t("tui.local_state_only"))
        elif event.button.id == "run-check":
            self._write_log(t("check.real_time_checking"))
        elif event.button.id == "create-plan":
            self._write_log(t("security.recheck_before_buy"))
        elif event.button.id == "load-plan":
            self._write_log(t("security.confirm_phrase_required"))
