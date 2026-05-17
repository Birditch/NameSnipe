from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Annotated

import typer
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from .cloudflare import CloudflareRegistrarClient, verify_api_token
from .config import load_config, save_config
from .errors import NameSnipeError
from .i18n import resolve_language, set_language, t
from .models import AppConfig, PurchasePlan
from .planner import create_purchase_plan
from .renderer import (
    console,
    render_check_results,
    render_plan,
    render_registration_results,
    render_search_results,
)
from .security import assert_live_purchase_allowed, reject_ignored_tlds
from .storage import config_path, get_api_token, latest_plan_path, set_api_token


class NameSnipeTyper(typer.Typer):
    def __call__(self, *args: object, **kwargs: object) -> object:
        try:
            return super().__call__(*args, **kwargs)
        except NameSnipeError as exc:
            console.print(f"{t('common.error')}: {exc}")
            raise typer.Exit(1) from exc


app = NameSnipeTyper(help=t("app.subtitle"), no_args_is_help=False, invoke_without_command=True)
COMMAND_HELP_KEYS = {
    "init": "cli.init.help",
    "search": "cli.search.help",
    "check": "cli.check.help",
    "plan": "cli.plan.help",
    "buy": "cli.buy.help",
    "status": "cli.status.help",
    "tui": "cli.tui.help",
    "help": "cli.help.help",
}
DEFAULT_SEARCH_TLDS = ["link", "cc", "xyz", "icu", "dev", "app", "com"]


def _language_option() -> str | None:
    return typer.Option("--lang", help=t("cli.lang.help"))


def _load_configured_language(cli_language: str | None) -> AppConfig:
    config = load_config()
    language = resolve_language(cli_language, config.ui.language)
    set_language(language)
    return config


def _require_cloudflare(config: AppConfig) -> tuple[str, str]:
    if not config.account_id:
        raise NameSnipeError(t("errors.account_id_missing"))
    token = get_api_token()
    if not token:
        raise NameSnipeError(t("errors.token_missing"))
    return config.account_id, token


def _client(config: AppConfig) -> CloudflareRegistrarClient:
    account_id, token = _require_cloudflare(config)
    return CloudflareRegistrarClient(account_id, token)


def _domain_inputs(domains: list[str], file: Path | None) -> list[str]:
    values = [item.strip().lower() for item in domains if item.strip()]
    if file is not None:
        values.extend(
            line.strip().lower() for line in file.read_text(encoding="utf-8").splitlines()
        )
    unique: list[str] = []
    for item in values:
        if item and item not in unique:
            unique.append(item)
    if not unique:
        raise NameSnipeError(t("errors.no_domains"))
    return unique


def _parse_tld_csv(value: str) -> list[str]:
    unique: list[str] = []
    for item in value.split(","):
        tld = item.strip().lower().lstrip(".")
        if tld and tld not in unique:
            unique.append(tld)
    return unique


def _remove_ignored_tlds(tlds: list[str], ignored_tlds: list[str]) -> list[str]:
    ignored = {item.strip().lower().lstrip(".") for item in ignored_tlds if item.strip()}
    return [item for item in tlds if item not in ignored]


def _print_init_explanation(key: str, **kwargs: object) -> None:
    console.print()
    console.print(f"[dim]{t(key, **kwargs)}[/dim]")


@app.callback(invoke_without_command=True)
def root_command(
    ctx: typer.Context,
    lang: Annotated[str | None, _language_option()] = None,
) -> None:
    if ctx.invoked_subcommand is not None:
        return
    config = _load_configured_language(lang)
    from .tui import NameSnipeApp

    NameSnipeApp(config).run()


@app.command("help", help=t("cli.help.help"))
def help_command(
    command: Annotated[str | None, typer.Argument(help=t("cli.help.command.help"))] = None,
    lang: Annotated[str | None, _language_option()] = None,
) -> None:
    _load_configured_language(lang)
    if command is not None:
        if command not in COMMAND_HELP_KEYS:
            raise NameSnipeError(t("errors.unknown_command", command=command))
        console.print(Panel(t(COMMAND_HELP_KEYS[command]), title=f"namesnipe {command}"))
        console.print(t("cli.help.command_usage", command=command))
        return

    table = Table(title=t("cli.help.title"))
    table.add_column(t("cli.help.command"))
    table.add_column(t("common.reason"))
    for name, help_key in COMMAND_HELP_KEYS.items():
        table.add_row(name, t(help_key))
    console.print(table)
    console.print(t("cli.help.footer"))


@app.command("init", help=t("cli.init.help"))
def init_command(
    lang: Annotated[str | None, _language_option()] = None,
) -> None:
    set_language(resolve_language(lang))
    console.print(Panel(t("app.safety_line"), title=t("app.title")))
    console.print(f"{t('config.select_language')}:")
    console.print("1. English")
    console.print("2. 简体中文")
    console.print("3. 日本語")
    choice = Prompt.ask(">", choices=["1", "2", "3"], default="1")
    selected_language = {"1": "en", "2": "zh-CN", "3": "ja-JP"}[choice]
    set_language(selected_language)

    _print_init_explanation("init.explain.account_id")
    account_id = Prompt.ask(t("config.account_id"))

    _print_init_explanation("init.explain.api_token", path=config_path())
    token = Prompt.ask(t("config.api_token"))

    _print_init_explanation("init.explain.max_price")
    max_price = Decimal(Prompt.ask(t("config.max_price_usd"), default="10.00"))

    _print_init_explanation("init.explain.max_total")
    max_total = Decimal(Prompt.ask(t("config.max_total_usd"), default="50.00"))

    _print_init_explanation("init.explain.tld_ignorelist")
    ignored_tlds = Prompt.ask(t("config.tld_ignorelist"), default="")

    _print_init_explanation("init.explain.auto_renew")
    auto_renew = Confirm.ask(t("config.auto_renew"), default=False)

    _print_init_explanation("init.explain.dry_run")
    dry_run = Confirm.ask(t("config.dry_run"), default=True)
    if not dry_run:
        console.print(Panel(t("security.dry_run_enabled"), title=t("common.warning")))
        dry_run = True

    config = AppConfig(
        account_id=account_id,
        max_price_usd=max_price,
        max_total_usd=max_total,
        tld_ignorelist=_parse_tld_csv(ignored_tlds),
        auto_renew=auto_renew,
        dry_run=dry_run,
        ui={"language": selected_language},
    )
    path = save_config(config)
    if token:
        set_api_token(token)
        console.print(t("config.token_saved_local_json", path=path))
        ok, detail = verify_api_token(token)
        if ok:
            console.print(t("config.token_verify_success", detail=detail))
        else:
            console.print(t("config.token_verify_failed", detail=detail))
    console.print(t("config.saved", path=path))


@app.command("search", help=t("cli.search.help"))
def search_command(
    keyword: str,
    tlds: Annotated[
        str,
        typer.Option("--tlds", help=t("cli.tlds.help")),
    ] = ",".join(DEFAULT_SEARCH_TLDS),
    limit: Annotated[int, typer.Option("--limit", min=1, max=100, help=t("cli.limit.help"))] = 20,
    cheap: Annotated[bool, typer.Option("--cheap", help=t("cli.cheap.help"))] = False,
    max_price: Annotated[
        str | None,
        typer.Option("--max-price", help=t("cli.max_price.help")),
    ] = None,
    lang: Annotated[str | None, _language_option()] = None,
) -> None:
    config = _load_configured_language(lang)
    search_tlds = _remove_ignored_tlds(_parse_tld_csv(tlds), config.tld_ignorelist)
    if not search_tlds:
        raise NameSnipeError(t("errors.all_tlds_ignored"))
    with _client(config) as client:
        results = client.search_domains(
            keyword,
            tlds=search_tlds,
            limit=limit,
            cheap=cheap,
            max_price=Decimal(max_price) if max_price is not None else None,
        )
    render_search_results(results)


@app.command("check", help=t("cli.check.help"))
def check_command(
    domains: list[str] = typer.Argument(None),
    file: Annotated[Path | None, typer.Option("--file", help=t("cli.file.help"))] = None,
    max_price: Annotated[
        str | None,
        typer.Option("--max-price", help=t("cli.max_price.help")),
    ] = None,
    reject_premium: Annotated[
        bool,
        typer.Option("--reject-premium", help=t("cli.reject_premium.help")),
    ] = True,
    allow_premium: Annotated[
        bool,
        typer.Option("--allow-premium", help=t("cli.allow_premium.help")),
    ] = False,
    lang: Annotated[str | None, _language_option()] = None,
) -> None:
    config = _load_configured_language(lang)
    if max_price is not None:
        config.max_price_usd = Decimal(max_price)
    names = _domain_inputs(domains or [], file)
    console.print(t("check.real_time_checking"))
    with _client(config) as client:
        results = client.check_domains(names)
    if reject_premium and not allow_premium:
        premium = [item.domain_name for item in results if item.premium]
        if premium:
            console.print(t("errors.premium_rejected", domains=", ".join(premium)))
    render_check_results(results)


@app.command("plan", help=t("cli.plan.help"))
def plan_command(
    domains: list[str] = typer.Argument(None),
    file: Annotated[Path | None, typer.Option("--file", help=t("cli.file.help"))] = None,
    output: Annotated[
        Path,
        typer.Option("--output", "-o", help=t("cli.output.help")),
    ] = latest_plan_path(),
    years: Annotated[int, typer.Option("--years", min=1, max=10, help=t("cli.years.help"))] = 1,
    lang: Annotated[str | None, _language_option()] = None,
) -> None:
    config = _load_configured_language(lang)
    names = _domain_inputs(domains or [], file)
    console.print(t("security.recheck_before_buy"))
    with _client(config) as client:
        results = client.check_domains(names)
    plan = create_purchase_plan(config, results, years=years)
    output.write_text(plan.model_dump_json(indent=2), encoding="utf-8")
    render_plan(plan)
    console.print(t("plan.created", path=output))


@app.command("buy", help=t("cli.buy.help"))
def buy_command(
    plan: Annotated[
        Path,
        typer.Option("--plan", help=t("cli.plan_file.help")),
    ] = latest_plan_path(),
    live: Annotated[bool, typer.Option("--live", help=t("cli.live.help"))] = False,
    lang: Annotated[str | None, _language_option()] = None,
) -> None:
    config = _load_configured_language(lang)
    purchase_plan = PurchasePlan.model_validate_json(plan.read_text(encoding="utf-8"))
    if not live:
        console.print(Panel(t("buy.dry_run_only"), title=t("security.dry_run_enabled")))
        render_plan(purchase_plan)
        return

    console.print(Panel(t("security.live_purchase_warning"), title=t("buy.live_mode_warning")))
    console.print(
        t(
            "buy.confirm_intro",
            count=len(purchase_plan.domains),
            amount=purchase_plan.estimated_total,
            currency=purchase_plan.currency,
        )
    )
    render_plan(purchase_plan)
    console.print(t("security.recheck_before_buy"))
    with _client(config) as client:
        fresh_results = client.check_domains([item.domain_name for item in purchase_plan.domains])
        phrase = Prompt.ask(t("buy.enter_phrase"))
        reject_ignored_tlds(fresh_results, config.tld_ignorelist)
        assert_live_purchase_allowed(purchase_plan, fresh_results, phrase)
        results = [
            client.register_domain(
                item.domain_name,
                years=purchase_plan.years,
                auto_renew=purchase_plan.auto_renew,
                privacy_mode=purchase_plan.privacy_mode,
            )
            for item in purchase_plan.domains
        ]
    render_registration_results(results)
    for result in results:
        if result.status == "accepted":
            result_path = Path(f"namesnipe-result-{result.domain_name}.json")
            result_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
            console.print(t("buy.status_accepted"))
            console.print(t("buy.result_written", path=result_path))


@app.command("status", help=t("cli.status.help"))
def status_command(
    domain: str,
    lang: Annotated[str | None, _language_option()] = None,
) -> None:
    config = _load_configured_language(lang)
    console.print(t("status.querying"))
    with _client(config) as client:
        status = client.get_registration_status(domain)
    console.print_json(status.model_dump_json())


@app.command("tui", help=t("cli.tui.help"))
def tui_command(
    lang: Annotated[str | None, _language_option()] = None,
) -> None:
    config = _load_configured_language(lang)
    from .tui import NameSnipeApp

    NameSnipeApp(config).run()


def main() -> None:
    app()
