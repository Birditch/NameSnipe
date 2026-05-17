from __future__ import annotations

from collections.abc import Iterable

from .errors import SecurityError
from .i18n import t
from .models import AppConfig, DomainCheckResult, PurchasePlan, PurchasePlanItem, SearchResult
from .security import (
    build_confirm_phrase,
    reject_ignored_tlds,
    reject_premium_domains,
    require_recent_check,
    validate_budget,
)


def create_purchase_plan(
    config: AppConfig,
    check_results: Iterable[DomainCheckResult],
    *,
    years: int | None = None,
    dry_run: bool | None = None,
) -> PurchasePlan:
    results = list(check_results)
    if any(isinstance(item, SearchResult) for item in results):
        raise SecurityError(t("errors.search_results_not_buyable"))
    if not results:
        raise SecurityError(t("errors.no_domains"))

    require_recent_check(results)
    reject_ignored_tlds(results, config.tld_ignorelist)
    reject_premium_domains(results)

    rejected = [
        item for item in results if not item.available or not item.supported or item.pricing is None
    ]
    if rejected:
        reasons = ", ".join(
            f"{item.domain_name}: {item.reason or 'not_buyable'}" for item in rejected
        )
        raise SecurityError(t("errors.domain_not_buyable", reasons=reasons))

    plan_years = years or config.years
    total = validate_budget(
        results,
        config.max_price_usd,
        config.max_total_usd,
        years=plan_years,
    )
    currency = results[0].pricing.currency if results[0].pricing else "USD"
    if any(item.pricing and item.pricing.currency != currency for item in results):
        raise SecurityError(t("errors.mixed_currency"))
    items = [
        PurchasePlanItem(
            domain_name=item.domain_name,
            pricing=item.pricing,
            checked_at=item.checked_at,
            years=plan_years,
        )
        for item in results
        if item.pricing is not None
    ]
    estimated_total = total
    return PurchasePlan(
        dry_run=config.dry_run if dry_run is None else dry_run,
        max_price_usd=config.max_price_usd,
        max_total_usd=config.max_total_usd,
        years=plan_years,
        auto_renew=config.auto_renew,
        privacy_mode=config.privacy_mode,
        domains=items,
        estimated_total=estimated_total,
        currency=currency,
        confirm_phrase=build_confirm_phrase(len(items), estimated_total, currency),
    )
