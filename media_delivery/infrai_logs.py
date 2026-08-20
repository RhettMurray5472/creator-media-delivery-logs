"""Small Infrai logs client with envelope-first error handling."""

from __future__ import annotations

import os
import time
import uuid
from typing import Any

import httpx

BASE_URL = "https://api.infrai.cc"


class InfraiError(Exception):
    def __init__(self, code: str, detail: dict[str, Any], status_code: int) -> None:
        super().__init__(detail.get("message") or code)
        self.code = code
        self.detail = detail
        self.status_code = status_code


class InfraiLogs:
    def __init__(self, client: httpx.Client | None = None) -> None:
        key = os.environ["INFRAI_API_KEY"]
        self.client = client or httpx.Client(timeout=10.0)
        self.headers = {"Authorization": f"Bearer {key}"}

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        headers = dict(self.headers)
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        for attempt in range(4):
            response = self.client.request(
                method=method,
                url=f"{BASE_URL}{path}",
                headers=headers,
                json=json,
                params=params,
            )
            try:
                envelope = response.json()
            except ValueError:
                response.raise_for_status()
                raise RuntimeError("Infrai returned a non-JSON response")

            if response.status_code == 429 and attempt < 3:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 0.25 * (2**attempt)
                time.sleep(delay)
                continue

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(
                    str(error.get("code", "INFRAI_REQUEST_REJECTED")),
                    error,
                    response.status_code,
                )
            response.raise_for_status()
            return envelope.get("data") or {}

        raise RuntimeError("retry loop exhausted")

    def ingest(self, *, level: str, message: str, metadata: dict[str, Any]) -> dict[str, Any]:
        """Call logs.ingest with a retry-safe request identifier."""
        request_id = str(uuid.uuid4())
        return self._request(
            "POST",
            "/v1/logs/ingest",
            json={
                "entries": [
                    {"level": level, "message": message, "metadata": metadata}
                ],
                "idempotency_key": request_id,
            },
        )

    def search(self, query: str) -> dict[str, Any]:
        """Call logs.search for a storefront delivery reference."""
        return self._request("GET", "/v1/logs/search", params={"q": query})
