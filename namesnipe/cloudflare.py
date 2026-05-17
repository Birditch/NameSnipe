from __future__ import annotations

from decimal import Decimal
from typing import Any

import httpx

from .errors import CloudflareAPIError
from .i18n import t
from .models import (
    DomainCheckResult,
    DomainPricing,
    RegistrationResult,
    RegistrationStatus,
    SearchResult,
)
from .security import redact_secret

DEFAULT_BASE_URL = "https://api.cloudflare.com/client/v4"


def verify_api_token(
    api_token: str,
    *,
    base_url: str = DEFAULT_BASE_URL,
    timeout: float = 20.0,
    client: httpx.Client | None = None,
) -> tuple[bool, str]:
    http_client = client or httpx.Client(
        base_url=base_url.rstrip("/"),
        timeout=timeout,
        headers={"Authorization": f"Bearer {api_token}"},
    )
    close_client = client is None
    try:
        response = http_client.get("/user/tokens/verify")
        try:
            payload = response.json()
        except ValueError:
            return False, f"HTTP {response.status_code}"
        if payload.get("success") and not response.is_error:
            result = payload.get("result", {})
            status = result.get("status") if isinstance(result, dict) else None
            return True, str(status or "active")
        return False, _safe_error_detail(payload, response.status_code, api_token)
    except httpx.HTTPError as exc:
        return False, str(exc).replace(api_token, redact_secret(api_token))
    finally:
        if close_client:
            http_client.close()


class CloudflareRegistrarClient:
    def __init__(
        self,
        account_id: str,
        api_token: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 20.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.account_id = account_id
        self.api_token = api_token
        self.base_url = base_url.rstrip("/")
        self._client = client or httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {api_token}",
                "Content-Type": "application/json",
            },
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> CloudflareRegistrarClient:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def _path(self, suffix: str) -> str:
        return f"/accounts/{self.account_id}/registrar/{suffix.lstrip('/')}"

    def _parse_response(self, response: httpx.Response) -> Any:
        try:
            payload = response.json()
        except ValueError as exc:
            raise CloudflareAPIError(
                t("errors.cloudflare_api", detail=f"HTTP {response.status_code}")
            ) from exc

        success = payload.get("success", response.is_success)
        if not success or response.is_error:
            detail = _safe_error_detail(payload, response.status_code, self.api_token)
            raise CloudflareAPIError(t("errors.cloudflare_api", detail=detail))
        return payload.get("result", payload)

    def search_domains(
        self,
        keyword: str,
        *,
        tlds: list[str],
        limit: int = 20,
        cheap: bool = False,
        max_price: Decimal | None = None,
    ) -> list[SearchResult]:
        response = self._client.get(
            self._path("domain-search"),
            params={
                "query": keyword,
                "tlds": ",".join(tlds),
                "limit": limit,
                "cheap": str(cheap).lower(),
                "max_price": str(max_price) if max_price is not None else None,
            },
        )
        result = self._parse_response(response)
        rows = result if isinstance(result, list) else result.get("domains", [])
        return [_parse_search_result(row) for row in rows[:limit]]

    def check_domains(self, domains: list[str]) -> list[DomainCheckResult]:
        all_results: list[DomainCheckResult] = []
        for start in range(0, len(domains), 20):
            batch = domains[start : start + 20]
            response = self._client.post(self._path("domain-check"), json={"domains": batch})
            result = self._parse_response(response)
            rows = result if isinstance(result, list) else result.get("domains", result)
            if isinstance(rows, dict):
                rows = [{"domain_name": key, **value} for key, value in rows.items()]
            all_results.extend(_parse_check_result(row) for row in rows)
        return all_results

    def register_domain(
        self,
        domain_name: str,
        *,
        years: int,
        auto_renew: bool,
        privacy_mode: str,
    ) -> RegistrationResult:
        response = self._client.post(
            self._path("registrations"),
            json={
                "domain_name": domain_name,
                "years": years,
                "auto_renew": auto_renew,
                "privacy_mode": privacy_mode,
            },
        )
        result = self._parse_response(response)
        status = "accepted" if response.status_code == 202 else "succeeded"
        if isinstance(result, dict):
            status = result.get("status", status)
            message = result.get("message")
            cloudflare_id = result.get("id")
        else:
            message = None
            cloudflare_id = None
        return RegistrationResult(
            domain_name=domain_name,
            status=status,
            message=message,
            cloudflare_id=cloudflare_id,
        )

    def get_registration_status(self, domain_name: str) -> RegistrationStatus:
        response = self._client.get(self._path(f"registrations/{domain_name}/registration-status"))
        result = self._parse_response(response)
        if isinstance(result, dict):
            return RegistrationStatus(
                domain_name=domain_name,
                status=str(result.get("status", "unknown")),
                message=result.get("message"),
                updated_at=result.get("updated_at"),
            )
        return RegistrationStatus(domain_name=domain_name, status=str(result))


def _safe_error_detail(payload: dict[str, Any], status_code: int, token: str) -> str:
    parts: list[str] = [f"HTTP {status_code}"]
    for field in ("errors", "messages"):
        for item in payload.get(field, []) or []:
            if isinstance(item, dict):
                message = str(item.get("message", item))
            else:
                message = str(item)
            parts.append(message.replace(token, redact_secret(token)))
    return "; ".join(parts)


def _parse_price(value: Any) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


def _parse_search_result(row: dict[str, Any]) -> SearchResult:
    domain = row.get("domain_name") or row.get("domain") or row.get("name")
    price = _parse_price(row.get("registration_price") or row.get("price"))
    return SearchResult(
        domain_name=str(domain),
        available=row.get("available"),
        premium=row.get("premium"),
        registration_price=price,
        currency=str(row.get("currency", "USD")),
        reason=row.get("reason"),
    )


def _parse_check_result(row: dict[str, Any]) -> DomainCheckResult:
    domain = row.get("domain_name") or row.get("domain") or row.get("name")
    available = bool(row.get("available", row.get("status") == "available"))
    premium = bool(row.get("premium", row.get("is_premium", False)))
    reason = row.get("reason") or row.get("status")
    supported = reason != "extension_not_supported_via_api" and bool(row.get("supported", True))
    pricing_data = row.get("pricing") or row
    registration_price = _parse_price(
        pricing_data.get("registration_price")
        or pricing_data.get("register")
        or pricing_data.get("price")
    )
    renewal_price = _parse_price(
        pricing_data.get("renewal_price")
        or pricing_data.get("renew")
        or pricing_data.get("renewal")
    )
    pricing = None
    if registration_price is not None:
        pricing = DomainPricing(
            registration_price=registration_price,
            renewal_price=renewal_price,
            currency=str(pricing_data.get("currency", row.get("currency", "USD"))),
        )
    return DomainCheckResult(
        domain_name=str(domain),
        available=available,
        premium=premium,
        supported=supported,
        pricing=pricing,
        reason=reason,
    )
