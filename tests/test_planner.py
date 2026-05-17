from __future__ import annotations

from decimal import Decimal

import pytest

from namesnipe.errors import SecurityError
from namesnipe.models import AppConfig, DomainCheckResult, DomainPricing, SearchResult
from namesnipe.planner import create_purchase_plan


def test_search_results_cannot_directly_enter_buy() -> None:
    config = AppConfig()
    with pytest.raises(SecurityError):
        create_purchase_plan(config, [SearchResult(domain_name="example.link")])  # type: ignore[list-item]


def test_plan_rejects_unsupported_tld() -> None:
    config = AppConfig()
    result = DomainCheckResult(
        domain_name="example.unsupported",
        available=False,
        supported=False,
        reason="extension_not_supported_via_api",
    )
    with pytest.raises(SecurityError):
        create_purchase_plan(config, [result])


def test_plan_rejects_ignored_tld() -> None:
    config = AppConfig(tld_ignorelist=["zip"])
    result = DomainCheckResult(
        domain_name="example.zip",
        available=True,
        supported=True,
        pricing=DomainPricing(registration_price=Decimal("7.20"), renewal_price=Decimal("7.20")),
    )
    with pytest.raises(SecurityError):
        create_purchase_plan(config, [result])


def test_plan_created_from_checked_buyable_domains() -> None:
    config = AppConfig(max_price_usd=Decimal("10.00"), max_total_usd=Decimal("50.00"))
    result = DomainCheckResult(
        domain_name="example.link",
        available=True,
        supported=True,
        pricing=DomainPricing(registration_price=Decimal("7.20"), renewal_price=Decimal("7.20")),
    )
    plan = create_purchase_plan(config, [result])
    assert plan.domains[0].domain_name == "example.link"
    assert plan.confirm_phrase == "BUY 1 DOMAIN FOR 7.20 USD"


def test_plan_total_includes_years() -> None:
    config = AppConfig(max_price_usd=Decimal("10.00"), max_total_usd=Decimal("50.00"))
    result = DomainCheckResult(
        domain_name="example.link",
        available=True,
        supported=True,
        pricing=DomainPricing(registration_price=Decimal("7.20"), renewal_price=Decimal("7.20")),
    )
    plan = create_purchase_plan(config, [result], years=2)
    assert plan.estimated_total == Decimal("14.40")
    assert plan.confirm_phrase == "BUY 1 DOMAIN FOR 14.40 USD"
