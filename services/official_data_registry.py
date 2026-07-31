"""Verified official-data metadata shared by Terrain and TaxOracle.

This registry is deliberately metadata-only.  It does not make network calls,
load credentials, or claim that a source is live merely because it is listed.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal


RuntimeStatus = Literal[
    "configured",
    "not_configured",
    "available",
    "unavailable",
    "stale",
    "partial",
    "limited",
    "error",
    "not_checked",
]


@dataclass(frozen=True)
class OfficialDataProvider:
    provider_id: str
    agency: str
    dataset_name: str
    source_url: str
    documentation_url: str
    access_mode: str
    authentication_mode: str
    data_format: str
    coverage: str
    licence_or_attribution: str
    published_version: str | None
    effective_date: str | None
    fetched_at: str | None
    freshness_status: RuntimeStatus
    runtime_status: RuntimeStatus
    limitation_summary: str
    domain: Literal["terrain", "tax"]
    verified_endpoint: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


OFFICIAL_DATA_PROVIDERS: tuple[OfficialDataProvider, ...] = (
    OfficialDataProvider(
        provider_id="nlsc_base_map",
        agency="內政部國土測繪中心",
        dataset_name="國土測繪圖資服務雲／臺灣通用電子地圖",
        source_url="https://maps.nlsc.gov.tw/pro/sysinfo.jsp",
        documentation_url="https://www.nlsc.gov.tw/cp.aspx?Create=1&n=15899",
        access_mode="public_ogc_or_download",
        authentication_mode="none",
        data_format="WMS_WMTS_vector_download",
        coverage="官方圖資服務所公布的圖層範圍；個別風險圖層涵蓋需另行確認",
        licence_or_attribution="依國土測繪中心圖資服務與授權／引用規範標示",
        published_version=None,
        effective_date=None,
        fetched_at=None,
        freshness_status="not_checked",
        runtime_status="not_checked",
        limitation_summary="本 registry 不代表已載入特定風險圖層；未取得圖層不得推論為無風險。",
        domain="terrain",
        verified_endpoint="https://wmts.nlsc.gov.tw/wmts",
    ),
    OfficialDataProvider(
        provider_id="ardswc_debris_flow_reference",
        agency="農業部農村發展及水土保持署",
        dataset_name="土石流潛勢溪流及影響範圍等公開圖資",
        source_url="https://data.ardswc.gov.tw/Data/OpenData/Api",
        documentation_url="https://data.ardswc.gov.tw/Data/OpenData/Api",
        access_mode="manual_download_or_bounded_adapter",
        authentication_mode="none",
        data_format="SHP_MVT",
        coverage="依官方發布之資料集與載入快照範圍判定",
        licence_or_attribution="農業部農村發展及水土保持署；依公開資料使用規範標示",
        published_version=None,
        effective_date=None,
        fetched_at=None,
        freshness_status="not_checked",
        runtime_status="not_checked",
        limitation_summary="資料版本、涵蓋範圍與圖層定義必須隨匯入快照保存；未載入時為 unavailable。",
        domain="terrain",
    ),
    OfficialDataProvider(
        provider_id="ncdr_hazard_potential_reference",
        agency="國家災害防救科技中心",
        dataset_name="災害潛勢資料服務與資料集",
        source_url="https://datahub.ncdr.nat.gov.tw/",
        documentation_url="https://datahub.ncdr.nat.gov.tw/dataset/detail?pid=1f636f3a-b4fb-41c0-8354-4d57d07eb5ff",
        access_mode="manual_download",
        authentication_mode="none",
        data_format="dataset_specific_geospatial_file",
        coverage="依各資料集公告的空間與版本範圍判定",
        licence_or_attribution="國家災害防救科技中心；依資料集公告條款標示",
        published_version=None,
        effective_date=None,
        fetched_at=None,
        freshness_status="not_checked",
        runtime_status="not_checked",
        limitation_summary="不同災害資料集的涵蓋範圍與更新日期不同，不可合併成單一安全分數。",
        domain="terrain",
    ),
    OfficialDataProvider(
        provider_id="mof_house_tax_law",
        agency="財政部賦稅署",
        dataset_name="房屋稅條例與房屋稅相關法規",
        source_url="https://law-out.mof.gov.tw/LawContent.aspx?id=FL006141",
        documentation_url="https://www.etax.nat.gov.tw/etwmain/tax-info/understanding/tax-saving-manual/local/house-tax/5qYVKWW",
        access_mode="official_documentation_or_manual_rule_import",
        authentication_mode="none",
        data_format="legal_text_or_versioned_rule_file",
        coverage="中央法規；地方適用仍須依主管稅捐機關與有效日期確認",
        licence_or_attribution="財政部賦稅署／財政部主管法規共用系統",
        published_version=None,
        effective_date=None,
        fetched_at=None,
        freshness_status="not_checked",
        runtime_status="not_checked",
        limitation_summary="本專案不以中央法規頁面推導地方即時稅率，需有可追溯的版本化規則資料。",
        domain="tax",
    ),
    OfficialDataProvider(
        provider_id="mof_land_tax_law",
        agency="財政部賦稅署",
        dataset_name="土地稅法與土地稅法施行細則",
        source_url="https://law-out.mof.gov.tw/LawContent.aspx?id=FL006135",
        documentation_url="https://law-out.mof.gov.tw/LawContent.aspx?id=FL006136",
        access_mode="official_documentation_or_manual_rule_import",
        authentication_mode="none",
        data_format="legal_text_or_versioned_rule_file",
        coverage="中央土地稅法規；地方適用與個案資料需另行核對",
        licence_or_attribution="財政部賦稅署／財政部主管法規共用系統",
        published_version=None,
        effective_date=None,
        fetched_at=None,
        freshness_status="not_checked",
        runtime_status="not_checked",
        limitation_summary="未提供明確 jurisdiction 與有效日期時，不選用其他地區或其他版本替代。",
        domain="tax",
    ),
)


def provider_registry(domain: str | None = None) -> list[dict[str, object]]:
    """Return a JSON-safe copy of the verified registry."""

    return [
        provider.to_dict()
        for provider in OFFICIAL_DATA_PROVIDERS
        if domain is None or provider.domain == domain
    ]


def provider_ids(domain: str | None = None) -> tuple[str, ...]:
    return tuple(item["provider_id"] for item in provider_registry(domain))


def public_source_status(domain: str) -> dict[str, object]:
    """Expose status metadata without implying source availability."""

    rows = provider_registry(domain)
    return {
        "domain": domain,
        "status": "not_checked",
        "sources": rows,
        "credentials_required": False,
        "message": "來源 metadata 已註冊；尚未執行 live canary 或載入可用快照。",
    }
