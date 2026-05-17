from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from namesnipe.errors import SecurityError
from namesnipe.i18n import set_language, t
from namesnipe.models import DomainCheckResult, DomainPricing, PurchasePlan, PurchasePlanItem
from namesnipe.security import (
    build_confirm_phrase,
    redact_secret,
    reject_premium_domains,
    require_recent_check,
    validate_budget,
    verify_confirm_phrase,
)


def check_result(
    domain: str = "example.link",
    price: str = "7.20",
    *,
    premium: bool = False,
    checked_at: datetime | None = None,
) -> DomainCheckResult:
    return DomainCheckResult(
        domain_name=domain,
        available=True,
        premium=premium,
        supported=True,
        pricing=DomainPricing(registration_price=Decimal(price), renewal_price=Decimal(price)),
        checked_at=checked_at or datetime.now(UTC),
    )


def test_confirm_phrase_generation() -> None:
    assert build_confirm_phrase(1, Decimal("7.20"), "USD") == "BUY 1 DOMAIN FOR 7.20 USD"
    assert build_confirm_phrase(2, Decimal("14.40"), "usd") == "BUY 2 DOMAINS FOR 14.40 USD"


def test_confirm_phrase_mismatch_rejects() -> None:
    with pytest.raises(SecurityError):
        verify_confirm_phrase("BUY 1 DOMAIN FOR 7.20 USD", "buy 1 domain for 7.20 usd")


def test_over_budget_rejects() -> None:
    with pytest.raises(SecurityError):
        validate_budget([check_result(price="12.00")], Decimal("10.00"), Decimal("50.00"))


def test_total_budget_includes_registration_years() -> None:
    with pytest.raises(SecurityError):
        validate_budget(
            [check_result(price="9.00"), check_result("example.dev", price="9.00")],
            Decimal("10.00"),
            Decimal("20.00"),
            years=2,
        )


def test_premium_default_rejects() -> None:
    with pytest.raises(SecurityError):
        reject_premium_domains([check_result(premium=True)])


def test_buy_requires_recent_check() -> None:
    stale = check_result(checked_at=datetime.now(UTC) - timedelta(minutes=10))
    with pytest.raises(SecurityError):
        require_recent_check([stale], max_age_seconds=300)


def test_token_redaction() -> None:
    token = "secret-token-value"
    redacted = redact_secret(token)
    assert token not in redacted
    assert redacted != token


def test_sensitive_token_never_appears_in_translated_errors() -> None:
    token = "super-secret-token"
    for language in ("en", "zh-CN", "ja-JP"):
        set_language(language)
        assert token not in t("errors.token_missing")
        assert token not in t("config.token_env_required")


def test_confirm_phrase_is_language_independent_or_safely_generated() -> None:
    phrases = []
    for language in ("en", "zh-CN", "ja-JP"):
        set_language(language)
        phrases.append(build_confirm_phrase(1, Decimal("7.20"), "USD"))
    assert phrases == ["BUY 1 DOMAIN FOR 7.20 USD"] * 3


def test_plan_json_serialization() -> None:
    result = check_result()
    plan = PurchasePlan(
        dry_run=True,
        max_price_usd=Decimal("10.00"),
        max_total_usd=Decimal("50.00"),
        domains=[
            PurchasePlanItem(
                domain_name=result.domain_name,
                pricing=result.pricing,
                checked_at=result.checked_at,
            )
        ],
        estimated_total=Decimal("7.20"),
        currency="USD",
        confirm_phrase="BUY 1 DOMAIN FOR 7.20 USD",
    )
    serialized = plan.model_dump_json()
    assert "BUY 1 DOMAIN FOR 7.20 USD" in serialized
    assert PurchasePlan.model_validate_json(serialized).estimated_total == Decimal("7.20")
