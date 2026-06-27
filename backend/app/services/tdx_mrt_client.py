from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import httpx

from app.core.config import settings

TDX_TOKEN_URL = "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"
TDX_STATION_URL = "https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/Station/TRTC"
TDX_STATION_OF_LINE_URL = "https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/StationOfLine/TRTC"

TdxFailureClass = Literal[
    "credentials_unavailable",
    "authentication_failed",
    "service_unavailable",
    "invalid_response",
    "unknown",
]


class TdxMrtClientError(RuntimeError):
    def __init__(self, failure_class: TdxFailureClass) -> None:
        super().__init__(failure_class)
        self.failure_class = failure_class


@dataclass(slots=True)
class TdxMrtClient:
    client_id: str | None
    client_secret: str | None
    timeout_seconds: float = 20.0

    def fetch_station_and_line_records(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        token = self._fetch_access_token()
        station_records = self._fetch_json_list(TDX_STATION_URL, token)
        line_records = self._fetch_json_list(TDX_STATION_OF_LINE_URL, token)
        return station_records, line_records

    def _fetch_access_token(self) -> str:
        if not self.client_id or not self.client_secret:
            raise TdxMrtClientError("credentials_unavailable")

        try:
            response = httpx.post(
                TDX_TOKEN_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                timeout=self.timeout_seconds,
            )
        except httpx.HTTPError as exc:
            raise TdxMrtClientError("service_unavailable") from exc

        if response.status_code in {400, 401, 403}:
            raise TdxMrtClientError("authentication_failed")
        if response.status_code >= 500:
            raise TdxMrtClientError("service_unavailable")
        if response.status_code != 200:
            raise TdxMrtClientError("unknown")

        try:
            payload = response.json()
        except ValueError as exc:
            raise TdxMrtClientError("invalid_response") from exc
        if not isinstance(payload, dict):
            raise TdxMrtClientError("invalid_response")

        access_token = payload.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            raise TdxMrtClientError("invalid_response")
        return access_token

    def _fetch_json_list(self, url: str, access_token: str) -> list[dict[str, Any]]:
        try:
            response = httpx.get(
                url,
                params={"$format": "JSON"},
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=self.timeout_seconds,
            )
        except httpx.HTTPError as exc:
            raise TdxMrtClientError("service_unavailable") from exc

        if response.status_code in {401, 403}:
            raise TdxMrtClientError("authentication_failed")
        if response.status_code >= 500:
            raise TdxMrtClientError("service_unavailable")
        if response.status_code != 200:
            raise TdxMrtClientError("unknown")

        try:
            payload = response.json()
        except ValueError as exc:
            raise TdxMrtClientError("invalid_response") from exc
        if not isinstance(payload, list) or not all(isinstance(item, dict) for item in payload):
            raise TdxMrtClientError("invalid_response")
        return payload


def build_tdx_mrt_client() -> TdxMrtClient:
    return TdxMrtClient(
        client_id=settings.tdx_client_id,
        client_secret=settings.tdx_client_secret,
    )
