from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .i18n import t
from .models import DomainCheckResult, PurchasePlan, RegistrationResult, SearchResult

console = Console()


def render_search_results(results: list[SearchResult]) -> None:
    console.print(Panel(t("search.not_authoritative"), title=t("common.warning")))
    if not results:
        console.print(t("search.no_results"))
        return
    table = Table(title=t("nav.search"))
    table.add_column(t("search.candidate"))
    table.add_column(t("common.price"))
    table.add_column(t("common.currency"))
    table.add_column(t("common.reason"))
    for item in results:
        price = "" if item.registration_price is None else str(item.registration_price)
        table.add_row(item.domain_name, price, item.currency, item.reason or "")
    console.print(table)
    console.print(t("search.run_check_next"))


def render_check_results(results: list[DomainCheckResult]) -> None:
    table = Table(title=t("nav.check"))
    table.add_column(t("common.domain"))
    table.add_column(t("common.status"))
    table.add_column(t("check.registration_price"))
    table.add_column(t("check.renewal_price"))
    table.add_column(t("common.currency"))
    table.add_column(t("check.reason"))
    for item in results:
        status = t("check.buyable") if item.available and item.supported else t("check.not_buyable")
        registration = ""
        renewal = ""
        currency = ""
        if item.pricing is not None:
            registration = str(item.pricing.registration_price)
            renewal = "" if item.pricing.renewal_price is None else str(item.pricing.renewal_price)
            currency = item.pricing.currency
        table.add_row(item.domain_name, status, registration, renewal, currency, item.reason or "")
    console.print(table)


def render_plan(plan: PurchasePlan) -> None:
    table = Table(title=t("nav.plan"))
    table.add_column(t("common.domain"))
    table.add_column(t("common.price"))
    table.add_column(t("common.currency"))
    for item in plan.domains:
        table.add_row(
            item.domain_name,
            str(item.pricing.registration_price),
            item.pricing.currency,
        )
    console.print(table)
    console.print(f"{t('plan.estimated_total')}: {plan.estimated_total} {plan.currency}")
    console.print(f"{t('plan.confirm_phrase')}: {plan.confirm_phrase}")
    console.print(f"{t('config.auto_renew')}: {plan.auto_renew}")
    console.print(f"{t('config.privacy_mode')}: {plan.privacy_mode}")


def render_registration_results(results: list[RegistrationResult]) -> None:
    table = Table(title=t("nav.buy"))
    table.add_column(t("common.domain"))
    table.add_column(t("common.status"))
    table.add_column(t("common.reason"))
    for item in results:
        table.add_row(item.domain_name, item.status, item.message or "")
    console.print(table)
