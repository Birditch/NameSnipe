from __future__ import annotations

from decimal import Decimal
from pathlib import Path
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
    Switch,
    TabbedContent,
    TabPane,
    TextArea,
)

from .cloudflare import CloudflareRegistrarClient, verify_api_token
from .config import save_config
from .errors import NameSnipeError
from .i18n import get_language, set_language, t
from .models import AppConfig, DomainCheckResult, PurchasePlan, SearchResult
from .planner import create_purchase_plan
from .storage import get_api_token, latest_plan_path, set_api_token

NAV_KEYS = [
    "nav.dashboard",
    "nav.search",
    "nav.check",
    "nav.plan",
    "nav.buy",
    "nav.config",
    "nav.logs",
]
DEFAULT_SEARCH_TLDS = ["link", "cc", "xyz", "icu", "dev", "app", "com"]


class NameSnipeApp(App[None]):
    CSS = """
    Screen { background: $surface; }
    .topline { padding: 1; border: solid $primary; }
    .pane { padding: 1 2; }
    .row { height: auto; margin-bottom: 1; }
    .warning { color: $warning; text-style: bold; }
    .hint { color: $text-muted; }
    .status { padding: 1; border: solid $primary; margin-bottom: 1; }
    .switch-label { width: 26; }
    .switch-state { width: 12; color: $text-muted; }
    Input { margin-right: 1; }
    Switch { margin-right: 1; }
    Button { margin-right: 1; }
    DataTable { height: 11; margin-top: 1; }
    TextArea { height: 8; }
    """

    BINDINGS: ClassVar = [
        ("q", "quit", t("common.cancel")),
        ("s", "focus_search", t("nav.search")),
        ("c", "focus_config", t("nav.config")),
    ]

    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self.config = config
        self.language_notice = Static("")
        self.runtime_log = Log(id="runtime-log")
        self.status_text = Static(t("tui.start_here"), id="page-status", classes="status")
        self.search_results: list[SearchResult] = []
        self.check_results: list[DomainCheckResult] = []
        self.current_plan: PurchasePlan | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static(self._safety_state(), id="safety-state", classes="topline")
        yield self.status_text
        with TabbedContent(initial="dashboard", id="main-tabs"):
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
        self._write_log(t("tui.start_here"))
        self._write_log(t("tui.no_token_logged"))

    def action_focus_search(self) -> None:
        self.query_one("#main-tabs", TabbedContent).active = "search"

    def action_focus_config(self) -> None:
        self.query_one("#main-tabs", TabbedContent).active = "config"

    def _client(self) -> CloudflareRegistrarClient:
        if not self.config.account_id:
            raise NameSnipeError(t("errors.account_id_missing"))
        token = get_api_token()
        if not token:
            raise NameSnipeError(t("errors.token_missing"))
        return CloudflareRegistrarClient(self.config.account_id, token)

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

    def _set_status(self, message: str) -> None:
        self.query_one("#safety-state", Static).update(f"{self._safety_state()} | {message}")
        self.status_text.update(message)
        self._write_log(message)

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
            Label(t("tui.start_here"), classes="warning"),
            Label(t("app.safety_line")),
            Label(f"{t('tui.account_configured')}: {account_status}"),
            Label(f"{token_status}: {t('security.token_never_displayed')}"),
            Label(f"{t('config.max_price_usd')}: {self.config.max_price_usd}"),
            Label(f"{t('config.max_total_usd')}: {self.config.max_total_usd}"),
            Label(f"{t('tui.recent_plan')}: {latest_plan_path()}"),
            Label(t("tui.workflow_hint"), classes="hint"),
            classes="pane",
        )

    def _search(self) -> Container:
        return Container(
            Label(t("tui.search_help"), classes="hint"),
            Label(t("search.not_authoritative"), classes="warning"),
            Horizontal(
                Input(placeholder=t("tui.keyword"), id="search-keyword"),
                Input(
                    value=",".join(self._remove_ignored_tlds(DEFAULT_SEARCH_TLDS)),
                    placeholder=t("search.tlds_to_search"),
                    id="search-tlds",
                ),
                Input(value="20", placeholder=t("tui.limit"), id="search-limit"),
                classes="row",
            ),
            Horizontal(
                Checkbox(t("search.cheap_only"), id="search-cheap"),
                Button(t("tui.run_search"), id="run-search", variant="primary", disabled=False),
                Button(t("tui.add_to_check"), id="add-search-to-check"),
                classes="row",
            ),
            DataTable(id="search-results"),
            Label(t("search.run_check_next")),
            classes="pane",
        )

    def _check(self) -> Container:
        return Container(
            Label(t("tui.check_help"), classes="hint"),
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
            Label(t("tui.plan_help"), classes="hint"),
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
            Label(f"{t('plan.estimated_total')}: -", id="plan-total"),
            Label(f"{t('plan.confirm_phrase')}: -", id="plan-phrase"),
            classes="pane",
        )

    def _buy(self) -> Container:
        return Container(
            Label(t("tui.buy_help"), classes="hint"),
            Label(t("security.live_purchase_warning"), classes="warning"),
            Label(t("security.confirm_phrase_required")),
            Horizontal(
                Input(
                    value=str(latest_plan_path()),
                    placeholder=t("cli.plan_file.help"),
                    id="buy-plan",
                ),
                Button(t("tui.load_plan"), id="load-plan"),
                classes="row",
            ),
            Label(t("buy.dry_run_only"), id="buy-summary"),
            Label("", id="buy-command"),
            classes="pane",
        )

    def _config(self) -> Container:
        self.language_notice.update("")
        return Container(
            Label(t("tui.config_help"), classes="hint"),
            Input(
                value=self.config.account_id or "",
                placeholder=t("config.account_id"),
                id="cfg-account",
            ),
            Input(
                value=get_api_token() or "",
                placeholder=t("config.api_token"),
                id="cfg-token",
            ),
            Horizontal(
                Input(
                    value=str(self.config.max_price_usd),
                    placeholder=t("config.max_price_usd"),
                    id="cfg-max-price",
                ),
                Input(
                    value=str(self.config.max_total_usd),
                    placeholder=t("config.max_total_usd"),
                    id="cfg-max-total",
                ),
                classes="row",
            ),
            Input(
                value=",".join(self.config.tld_ignorelist),
                placeholder=t("config.tld_ignorelist"),
                id="cfg-tlds",
            ),
            Horizontal(
                Label(t("config.auto_renew"), classes="switch-label"),
                Switch(value=self.config.auto_renew, id="cfg-auto-renew"),
                Label(
                    self._switch_text(self.config.auto_renew),
                    id="cfg-auto-renew-state",
                    classes="switch-state",
                ),
                classes="row",
            ),
            Horizontal(
                Label(t("config.dry_run"), classes="switch-label"),
                Switch(value=True, id="cfg-dry-run", disabled=True),
                Label(t("tui.switch_on"), id="cfg-dry-run-state", classes="switch-state"),
                classes="row",
            ),
            Horizontal(
                Button(t("tui.save_config"), id="save-config", variant="primary"),
                Button(t("tui.verify_token"), id="verify-token"),
                Button("English", id="lang-en"),
                Button("简体中文", id="lang-zh-CN"),
                Button("日本語", id="lang-ja-JP"),
                classes="row",
            ),
            self.language_notice,
            Label(t("tui.config_links"), classes="hint"),
            classes="pane",
        )

    def _logs(self) -> Container:
        return Container(Label(t("tui.no_token_logged")), self.runtime_log, classes="pane")

    def _switch_text(self, value: bool) -> str:
        return t("tui.switch_on") if value else t("tui.switch_off")

    def _parse_tld_csv(self, value: str) -> list[str]:
        unique: list[str] = []
        for item in value.split(","):
            tld = item.strip().lower().lstrip(".")
            if tld and tld not in unique:
                unique.append(tld)
        return unique

    def _remove_ignored_tlds(self, tlds: list[str]) -> list[str]:
        ignored = {item.strip().lower().lstrip(".") for item in self.config.tld_ignorelist}
        return [item for item in tlds if item not in ignored]

    def _read_check_domains(self) -> list[str]:
        text = self.query_one("#check-domains", TextArea).text
        raw = text.replace(",", "\n").splitlines()
        domains = [item.strip().lower() for item in raw if item.strip()]
        if not domains:
            raise NameSnipeError(t("errors.no_domains"))
        return list(dict.fromkeys(domains))

    def _save_config_from_inputs(self) -> None:
        self.config.account_id = self.query_one("#cfg-account", Input).value.strip() or None
        self.config.max_price_usd = Decimal(self.query_one("#cfg-max-price", Input).value.strip())
        self.config.max_total_usd = Decimal(self.query_one("#cfg-max-total", Input).value.strip())
        self.config.tld_ignorelist = self._parse_tld_csv(self.query_one("#cfg-tlds", Input).value)
        self.config.auto_renew = self.query_one("#cfg-auto-renew", Switch).value
        self.config.dry_run = True
        token = self.query_one("#cfg-token", Input).value.strip()
        path = save_config(self.config)
        if token:
            set_api_token(token)
        self.query_one("#safety-state", Static).update(self._safety_state())
        self._set_status(t("config.saved", path=path))

    def _run_search(self) -> None:
        keyword = self.query_one("#search-keyword", Input).value.strip()
        if not keyword:
            raise NameSnipeError(t("errors.no_domains"))
        tlds = self._remove_ignored_tlds(
            self._parse_tld_csv(self.query_one("#search-tlds", Input).value)
        )
        if not tlds:
            raise NameSnipeError(t("errors.all_tlds_ignored"))
        limit = int(self.query_one("#search-limit", Input).value or "20")
        cheap = self.query_one("#search-cheap", Checkbox).value
        with self._client() as client:
            self.search_results = client.search_domains(
                keyword,
                tlds=tlds,
                limit=limit,
                cheap=cheap,
            )
        table = self.query_one("#search-results", DataTable)
        table.clear()
        for item in self.search_results:
            price = "" if item.registration_price is None else str(item.registration_price)
            table.add_row(item.domain_name, price, item.currency, item.reason or "")
        if not self.search_results:
            self._set_status(t("search.no_results"))
            return
        self._set_status(t("tui.search_done", count=len(self.search_results)))

    def _add_search_to_check(self) -> None:
        domains = [item.domain_name for item in self.search_results]
        if not domains:
            raise NameSnipeError(t("search.no_results"))
        self.query_one("#check-domains", TextArea).text = "\n".join(domains)
        self.query_one("#main-tabs", TabbedContent).active = "check"
        self._set_status(t("tui.added_to_check", count=len(domains)))

    def _run_check(self) -> None:
        domains = self._read_check_domains()
        only_buyable = self.query_one("#filter-buyable", Checkbox).value
        with self._client() as client:
            self.check_results = client.check_domains(domains)
        table = self.query_one("#check-results", DataTable)
        table.clear()
        for item in self.check_results:
            if only_buyable and not (item.available and item.supported and not item.premium):
                continue
            status = (
                t("check.buyable") if item.available and item.supported else t("check.not_buyable")
            )
            registration = "" if item.pricing is None else str(item.pricing.registration_price)
            renewal = (
                ""
                if item.pricing is None or item.pricing.renewal_price is None
                else str(item.pricing.renewal_price)
            )
            table.add_row(item.domain_name, status, registration, renewal, item.reason or "")
        if not self.check_results:
            self._set_status(t("errors.no_domains"))
            return
        self._set_status(t("tui.check_done", count=len(self.check_results)))

    def _create_plan(self) -> None:
        domains = self._read_check_domains()
        with self._client() as client:
            self.check_results = client.check_domains(domains)
        self.current_plan = create_purchase_plan(self.config, self.check_results)
        output = Path(self.query_one("#plan-path", Input).value or str(latest_plan_path()))
        output.write_text(self.current_plan.model_dump_json(indent=2), encoding="utf-8")
        table = self.query_one("#plan-items", DataTable)
        table.clear()
        for item in self.current_plan.domains:
            table.add_row(
                item.domain_name,
                str(item.pricing.registration_price),
                item.pricing.currency,
            )
        self.query_one("#plan-total", Label).update(
            f"{t('plan.estimated_total')}: "
            f"{self.current_plan.estimated_total} {self.current_plan.currency}"
        )
        self.query_one("#plan-phrase", Label).update(
            f"{t('plan.confirm_phrase')}: {self.current_plan.confirm_phrase}"
        )
        self._set_status(t("plan.created", path=output))

    def _load_plan(self) -> None:
        path = Path(self.query_one("#buy-plan", Input).value or str(latest_plan_path()))
        plan = PurchasePlan.model_validate_json(path.read_text(encoding="utf-8"))
        self.query_one("#buy-summary", Label).update(
            t(
                "buy.confirm_intro",
                count=len(plan.domains),
                amount=plan.estimated_total,
                currency=plan.currency,
            )
        )
        self.query_one("#buy-command", Label).update(t("tui.buy_cli_command", path=path))
        self._set_status(t("tui.plan_loaded", path=path))

    def _verify_token(self) -> None:
        token = self.query_one("#cfg-token", Input).value.strip() or get_api_token()
        if not token:
            raise NameSnipeError(t("errors.token_missing"))
        ok, detail = verify_api_token(token)
        if ok:
            self._set_status(t("config.token_verify_success", detail=detail))
        else:
            self._set_status(t("config.token_verify_failed", detail=detail))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id in {
            "verify-token",
            "run-search",
            "run-check",
            "create-plan",
            "load-plan",
        }:
            event.button.disabled = True
            self._set_status(t("tui.working"))

            def work() -> None:
                try:
                    if button_id == "verify-token":
                        self._verify_token()
                    elif button_id == "run-search":
                        self._run_search()
                    elif button_id == "run-check":
                        self._run_check()
                    elif button_id == "create-plan":
                        self._create_plan()
                    elif button_id == "load-plan":
                        self._load_plan()
                except Exception as exc:
                    self.call_from_thread(self._set_status, f"{t('common.error')}: {exc}")
                finally:
                    self.call_from_thread(setattr, event.button, "disabled", False)

            self.run_worker(work, thread=True, exclusive=False, exit_on_error=False)
            return

        try:
            mapping = {"lang-en": "en", "lang-zh-CN": "zh-CN", "lang-ja-JP": "ja-JP"}
            if event.button.id in mapping:
                language = mapping[event.button.id]
                self.config.ui.language = language
                save_config(self.config)
                set_language(language)
                self.language_notice.update(t("tui.restart_required"))
                self.query_one("#safety-state", Static).update(self._safety_state())
                self._write_log(t("tui.restart_required"))
            elif event.button.id == "save-config":
                self._save_config_from_inputs()
            elif event.button.id == "add-search-to-check":
                self._add_search_to_check()
        except Exception as exc:
            self._set_status(f"{t('common.error')}: {exc}")

    def on_switch_changed(self, event: Switch.Changed) -> None:
        if event.switch.id == "cfg-auto-renew":
            self.query_one("#cfg-auto-renew-state", Label).update(self._switch_text(event.value))
