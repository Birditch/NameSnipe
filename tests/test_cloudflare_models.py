from __future__ import annotations

from decimal import Decimal

import httpx

from namesnipe.cloudflare import CloudflareRegistrarClient, verify_api_token


class FakeHTTPClient:
    def __init__(self) -> None:
        self.posts: list[tuple[str, dict]] = []

    def get(self, path: str, params: dict | None = None) -> httpx.Response:
        if path.endswith("domain-search"):
            return httpx.Response(
                200,
                json={
                    "success": True,
                    "result": {
                        "domains": [
                            {
                                "domain_name": "example.link",
                                "registration_price": "7.20",
                                "currency": "USD",
                            }
                        ]
                    },
                },
            )
        return httpx.Response(
            200,
            json={"success": True, "result": {"status": "pending", "message": "accepted"}},
        )

    def post(self, path: str, json: dict) -> httpx.Response:
        self.posts.append((path, json))
        if path.endswith("domain-check"):
            return httpx.Response(
                200,
                json={
                    "success": True,
                    "result": [
                        {
                            "domain_name": "example.link",
                            "available": True,
                            "premium": False,
                            "registration_price": "7.20",
                            "renewal_price": "8.00",
                            "currency": "USD",
                        }
                    ],
                },
            )
        return httpx.Response(202, json={"success": True, "result": {"status": "accepted"}})

    def close(self) -> None:
        return None


def test_cloudflare_search_and_check_are_parsed_without_real_api() -> None:
    fake = FakeHTTPClient()
    client = CloudflareRegistrarClient("account", "token", client=fake)  # type: ignore[arg-type]
    search = client.search_domains("example", tlds=["link"])
    checked = client.check_domains(["example.link"])
    assert search[0].domain_name == "example.link"
    assert checked[0].pricing is not None
    assert checked[0].pricing.registration_price == Decimal("7.20")


def test_cloudflare_register_accepted_is_not_retried() -> None:
    fake = FakeHTTPClient()
    client = CloudflareRegistrarClient("account", "token", client=fake)  # type: ignore[arg-type]
    result = client.register_domain(
        "example.link",
        years=1,
        auto_renew=False,
        privacy_mode="redaction",
    )
    registration_posts = [path for path, _payload in fake.posts if path.endswith("registrations")]
    assert result.status == "accepted"
    assert registration_posts == ["/accounts/account/registrar/registrations"]


def test_verify_api_token_uses_cloudflare_verify_endpoint() -> None:
    fake = FakeHTTPClient()
    ok, detail = verify_api_token("token", client=fake)  # type: ignore[arg-type]
    assert ok is True
    assert detail == "pending"
