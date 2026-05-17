from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from decimal import Decimal
from hmac import compare_digest

from .errors import SecurityError
from .i18n import t
from .models import DomainCheckResult, PurchasePlan


def _money(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01'))}"


def build_confirm_phrase(count: int, amount: Decimal, currency: str) -> str:
    noun = "DOMAIN" if count == 1 else "DOMAINS"
    return f"BUY {count} {noun} FOR {_money(amount)} {currency.upper()}"


def verify_confirm_phrase(expected: str, actual: str) -> None:
    if not compare_digest(expected.strip(), actual.strip()):
        raise SecurityError(t("errors.confirm_phrase_mismatch"))


def redact_secret(secret: str | None) -> str:
    if not secret:
        return ""
    if len(secret) <= 8:
        return "********"
    return f"{secret[:3]}...{secret[-3:]}"


def reject_premium_domains(results: Iterable[DomainCheckResult]) -> None:
    premium = [item.domain_name for item in results if item.premium]
    if premium:
        raise SecurityError(t("errors.premium_rejected", domains=", ".join(premium)))


def domain_tld(domain_name: str) -> str:
    return domain_name.rsplit(".", 1)[-1].lower() if "." in domain_name else ""


def reject_ignored_tlds(
    results: Iterable[DomainCheckResult],
    ignored_tlds: Iterable[str],
) -> None:
    ignored = {item.strip().lower().lstrip(".") for item in ignored_tlds if item.strip()}
    if not ignored:
        return
    blocked = [item.domain_name for item in results if domain_tld(item.domain_name) in ignored]
    if blocked:
        raise SecurityError(t("errors.ignored_tld", domains=", ".join(blocked)))


def validate_budget(
    results: Iterable[DomainCheckResult],
    max_price_usd: Decimal,
    max_total_usd: Decimal,
    *,
    years: int = 1,
) -> Decimal:
    total = Decimal("0.00")
    for item in results:
        if item.pricing is None:
            raise SecurityError(t("errors.price_missing", domain=item.domain_name))
        price = item.pricing.registration_price
        if price > max_price_usd:
            raise SecurityError(
                t(
                    "errors.budget_exceeded",
                    domain=item.domain_name,
                    price=_money(price),
                    budget=_money(max_price_usd),
                )
            )
        total += price * Decimal(years)
    total = total.quantize(Decimal("0.01"))
    if total > max_total_usd:
        raise SecurityError(
            t("errors.total_budget_exceeded", total=_money(total), budget=_money(max_total_usd))
        )
    return total


def require_recent_check(
    results: Iterable[DomainCheckResult],
    max_age_seconds: int = 300,
    now: datetime | None = None,
) -> None:
    current = now or datetime.now(UTC)
    for item in results:
        checked_at = item.checked_at
        if checked_at.tzinfo is None:
            checked_at = checked_at.replace(tzinfo=UTC)
        age = (current - checked_at).total_seconds()
        if age > max_age_seconds:
            raise SecurityError(t("errors.recent_check_required", domain=item.domain_name))


def assert_live_purchase_allowed(
    plan: PurchasePlan,
    fresh_results: list[DomainCheckResult],
    confirm_phrase: str,
) -> None:
    verify_confirm_phrase(plan.confirm_phrase, confirm_phrase)
    require_recent_check(fresh_results)
    reject_premium_domains(fresh_results)
    validate_budget(fresh_results, plan.max_price_usd, plan.max_total_usd, years=plan.years)

    fresh_by_domain = {item.domain_name: item for item in fresh_results}
    plan_domains = [item.domain_name for item in plan.domains]
    if set(fresh_by_domain) != set(plan_domains):
        raise SecurityError(t("errors.domain_status_changed"))

    for planned in plan.domains:
        fresh = fresh_by_domain[planned.domain_name]
        if not fresh.available or not fresh.supported:
            raise SecurityError(t("errors.domain_status_changed"))
        if (
            fresh.pricing is None
            or fresh.pricing.registration_price != planned.pricing.registration_price
            or fresh.pricing.currency != planned.pricing.currency
        ):
            raise SecurityError(t("buy.price_changed_abort"))
