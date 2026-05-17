from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator


def utc_now() -> datetime:
    return datetime.now(UTC)


class UIConfig(BaseModel):
    language: str | None = None


class AppConfig(BaseModel):
    account_id: str | None = None
    max_price_usd: Decimal = Decimal("10.00")
    max_total_usd: Decimal = Decimal("50.00")
    tld_allowlist: list[str] = Field(
        default_factory=lambda: ["link", "cc", "xyz", "icu", "dev", "app", "com"]
    )
    auto_renew: bool = False
    dry_run: bool = True
    privacy_mode: Literal["redaction", "none"] = "redaction"
    years: int = Field(default=1, ge=1, le=10)
    ui: UIConfig = Field(default_factory=UIConfig)

    @field_validator("tld_allowlist")
    @classmethod
    def normalize_tlds(cls, value: list[str]) -> list[str]:
        return [item.strip().lower().lstrip(".") for item in value if item.strip()]


class SearchResult(BaseModel):
    domain_name: str
    available: bool | None = None
    premium: bool | None = None
    registration_price: Decimal | None = None
    currency: str = "USD"
    source: Literal["search"] = "search"
    reason: str | None = None


class DomainPricing(BaseModel):
    registration_price: Decimal
    renewal_price: Decimal | None = None
    currency: str = "USD"


class DomainCheckResult(BaseModel):
    domain_name: str
    available: bool
    premium: bool = False
    supported: bool = True
    pricing: DomainPricing | None = None
    reason: str | None = None
    checked_at: datetime = Field(default_factory=utc_now)
    source: Literal["check"] = "check"


class PurchasePlanItem(BaseModel):
    domain_name: str
    pricing: DomainPricing
    checked_at: datetime
    years: int = 1


class PurchasePlan(BaseModel):
    created_at: datetime = Field(default_factory=utc_now)
    dry_run: bool = True
    max_price_usd: Decimal
    max_total_usd: Decimal
    years: int = 1
    auto_renew: bool = False
    privacy_mode: Literal["redaction", "none"] = "redaction"
    domains: list[PurchasePlanItem]
    estimated_total: Decimal
    currency: str = "USD"
    confirm_phrase: str


class RegistrationResult(BaseModel):
    domain_name: str
    status: Literal["accepted", "succeeded", "failed", "dry_run"]
    message: str | None = None
    cloudflare_id: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class RegistrationStatus(BaseModel):
    domain_name: str
    status: str
    message: str | None = None
    updated_at: datetime | None = None
