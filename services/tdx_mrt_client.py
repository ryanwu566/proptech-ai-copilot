"""Backend-only TDX MRT client used by protected manual refresh."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import httpx


TDX_TOKEN_URL = "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"
TDX_STATION_URL = "https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/Station/TRTC"
TDX_LINE_URL = "https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/Line/TRTC"


class TdxMrtClientError(RuntimeError):
    """Raised for sanitized TDX client failures."""


@dataclass(frozen=True)
class TdxMrtPayload:
    station_records: list[dict[str, Any]]
    line_records: list[dict[str, Any]]


class TdxMrtClient:
    """Fetch minimal TDX MRT station and line payloads with backend credentials."""

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        self.client_id = (client_id if client_id is not None else os.getenv("TDX_CLIENT_ID", "")).strip()
        self.client_secret = (client_secret if client_secret is not None else os.getenv("TDX_CLIENT_SECRET", "")).strip()
        self.timeout_seconds = timeout_seconds

    @property
    def configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def refresh_payload(self) -> TdxMrtPayload:
        if not self.configured:
            raise TdxMrtClientError("TDX credentials are not configured")
        token = self._fetch_access_token()
        station_records = self._fetch_json_array(TDX_STATION_URL, token)
        line_records = self._fetch_json_array(TDX_LINE_URL, token)
        return TdxMrtPayload(station_records=station_records, line_records=line_records)

    def _fetch_access_token(self) -> str:
        try:
            response = httpx.post(
                TDX_TOKEN_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                headers={"content-type": "application/x-www-form-urlencoded"},
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.TimeoutException, httpx.HTTPError, ValueError) as exc:
            raise TdxMrtClientError("TDX authentication failed") from exc
        token = payload.get("access_token") if isinstance(payload, dict) else None
        if not isinstance(token, str) or not token.strip():
            raise TdxMrtClientError("TDX authentication response was unavailable")
        return token.strip()

    def _fetch_json_array(self, url: str, token: str) -> list[dict[str, Any]]:
        try:
            response = httpx.get(
                url,
                params={"$format": "JSON"},
                headers={"authorization": f"Bearer {token}"},
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.TimeoutException, httpx.HTTPError, ValueError) as exc:
            raise TdxMrtClientError("TDX MRT payload fetch failed") from exc
        if not isinstance(payload, list):
            raise TdxMrtClientError("TDX MRT payload shape was unavailable")
        records: list[dict[str, Any]] = []
        for item in payload:
            if not isinstance(item, dict):
                raise TdxMrtClientError("TDX MRT payload item shape was unavailable")
            records.append(item)
        return records
