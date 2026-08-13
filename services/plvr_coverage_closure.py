"""Evidence-based PLVR release coverage for clean-shadow reconciliation.

Coverage is derived from verified artifact release metadata. Calendar time is
never used as a substitute for the latest official publication window.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date
from enum import StrEnum
from typing import Any, Iterable, Mapping

from services.plvr_import_service import FILE_CITY_MAP


class CoverageState(StrEnum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    MISSING = "MISSING"
    NOT_YET_EXPECTED = "NOT_YET_EXPECTED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass(frozen=True)
class CoverageCell:
    city: str
    period: str
    state: CoverageState
    reason_code: str
    evidence_release: str = ""


@dataclass(frozen=True)
class ArtifactScopeAudit:
    artifact_id: str
    release: str
    kind: str
    expected_scope: str
    actual_city_count: int
    omitted_city_members: tuple[str, ...]
    classification: str
    reason: str
    can_reacquire_full_artifact: bool
    alternate_authoritative_source: bool


ROC_WINDOW_PATTERN = re.compile(
    r"登記日期(?:自)?\s*(?P<start_year>\d{3})年(?P<start_month>\d{1,2})月"
    r"(?P<start_day>\d{1,2})?\s*(?:日)?\s*至\s*"
    r"(?P<end_year>\d{3})年(?P<end_month>\d{1,2})月(?P<end_day>\d{1,2})日"
)
PERIOD_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
SEASON_PATTERN = re.compile(r"^(?P<year>\d{3})S(?P<quarter>[1-4])$")
EXPECTED_CITIES = tuple(sorted(set(FILE_CITY_MAP.values())))


def build_coverage_report(
    manifest: Mapping[str, Any],
    *,
    since: str,
    until: str,
) -> dict[str, Any]:
    """Build city-period coverage without treating unpublished months as gaps."""

    _validate_period(since)
    _validate_period(until)
    entries = tuple(item for item in manifest.get("artifacts", ()) if isinstance(item, Mapping))
    verified = tuple(item for item in entries if item.get("verification_status") == "VERIFIED")
    release_ceiling = expected_official_availability_ceiling(verified)
    complete_through = latest_complete_season_period(verified)
    if not release_ceiling:
        release_ceiling = latest_season_release_ceiling(verified)
    if not release_ceiling or not complete_through:
        raise ValueError("authoritative_release_metadata_incomplete")

    seasons = {
        str(item.get("release") or ""): item
        for item in verified
        if str(item.get("kind") or "") == "season"
    }
    cells: list[CoverageCell] = []
    for city in EXPECTED_CITIES:
        for period in _iter_periods(since, until):
            cells.append(
                _coverage_cell(
                    city,
                    period,
                    release_ceiling=release_ceiling,
                    complete_through=complete_through,
                    seasons=seasons,
                    verified=verified,
                    required_artifact_unavailable=any(
                        item.get("verification_status") != "VERIFIED" for item in entries
                    ),
                )
            )

    counts = Counter(cell.state.value for cell in cells)
    expected_denominator = sum(
        counts[state.value]
        for state in (CoverageState.COMPLETE, CoverageState.PARTIAL, CoverageState.MISSING)
    )
    calendar_denominator = len(cells)
    artifact_audit = [asdict(item) for item in audit_artifact_scopes(entries)]
    return {
        "schema_version": "plvr-expected-official-coverage-v1",
        "basis": "verified artifact release metadata and embedded official package scope",
        "expected_release_ceiling": release_ceiling,
        "complete_through": complete_through,
        "counts": {
            "COMPLETE": counts[CoverageState.COMPLETE.value],
            "PARTIAL": counts[CoverageState.PARTIAL.value],
            "MISSING": counts[CoverageState.MISSING.value],
            "NOT_YET_EXPECTED": counts[CoverageState.NOT_YET_EXPECTED.value],
            "NOT_APPLICABLE": counts[CoverageState.NOT_APPLICABLE.value],
        },
        "raw_calendar_coverage_percent": _percent(
            counts[CoverageState.COMPLETE.value], calendar_denominator
        ),
        "expected_official_coverage_percent": _percent(
            counts[CoverageState.COMPLETE.value], expected_denominator
        ),
        "expected_scope_count": expected_denominator,
        "calendar_scope_count": calendar_denominator,
        "matrix": [
            {
                "city": cell.city,
                "period": cell.period,
                "coverage_state": cell.state.value,
                "reason_code": cell.reason_code,
                "evidence_release": cell.evidence_release,
            }
            for cell in cells
        ],
        "artifact_scope_audit": artifact_audit,
    }


def expected_official_availability_ceiling(
    entries: Iterable[Mapping[str, Any]],
) -> str:
    """Return the latest sale registration month proven by artifact metadata."""

    periods: list[str] = []
    for entry in entries:
        parsed = parse_sale_registration_window(str(entry.get("source_window_description") or ""))
        if parsed:
            periods.append(parsed[1][:7])
    return max(periods, default="")


def latest_complete_season_period(entries: Iterable[Mapping[str, Any]]) -> str:
    """Return the conservative transaction-period ceiling settled by a season."""

    periods: list[str] = []
    for entry in entries:
        if entry.get("verification_status") != "VERIFIED":
            continue
        release = str(entry.get("release") or "")
        match = SEASON_PATTERN.fullmatch(release)
        if not match or str(entry.get("coverage_status") or "") != "COMPLETE":
            continue
        year = int(match.group("year")) + 1911
        settled_month = int(match.group("quarter")) * 3 - 1
        periods.append(f"{year:04d}-{settled_month:02d}")
    return max(periods, default="")


def latest_season_release_ceiling(entries: Iterable[Mapping[str, Any]]) -> str:
    periods: list[str] = []
    for entry in entries:
        match = SEASON_PATTERN.fullmatch(str(entry.get("release") or ""))
        if not match or entry.get("verification_status") != "VERIFIED":
            continue
        year = int(match.group("year")) + 1911
        month = int(match.group("quarter")) * 3
        periods.append(f"{year:04d}-{month:02d}")
    return max(periods, default="")


def parse_sale_registration_window(description: str) -> tuple[str, str] | None:
    match = ROC_WINDOW_PATTERN.search(description)
    if not match:
        return None
    start = _roc_date(
        match.group("start_year"), match.group("start_month"), match.group("start_day") or "1"
    )
    end = _roc_date(match.group("end_year"), match.group("end_month"), match.group("end_day"))
    return start.isoformat(), end.isoformat()


def audit_artifact_scopes(
    entries: Iterable[Mapping[str, Any]],
) -> tuple[ArtifactScopeAudit, ...]:
    audits: list[ArtifactScopeAudit] = []
    for entry in entries:
        actual = tuple(sorted(str(value) for value in (entry.get("coverage_cities") or ())))
        omitted = tuple(sorted(str(value) for value in (entry.get("missing_cities") or ())))
        verified = entry.get("verification_status") == "VERIFIED"
        if not verified:
            classification = "MISSING_OR_REJECTED"
            reason = "artifact_not_verified"
        elif omitted and str(entry.get("kind") or "") in {"history", "current"}:
            classification = "PARTIAL_BY_OFFICIAL_RELEASE"
            reason = "official_embedded_manifest_omits_city_member"
        elif omitted:
            classification = "MISSING"
            reason = "required_nationwide_season_member_missing"
        else:
            classification = "COMPLETE"
            reason = "all_embedded_manifest_city_members_verified"
        audits.append(
            ArtifactScopeAudit(
                artifact_id=str(entry.get("artifact_id") or ""),
                release=str(entry.get("release") or ""),
                kind=str(entry.get("kind") or ""),
                expected_scope="official_embedded_manifest",
                actual_city_count=len(actual),
                omitted_city_members=omitted,
                classification=classification,
                reason=reason,
                can_reacquire_full_artifact=False,
                alternate_authoritative_source=False,
            )
        )
    return tuple(audits)


def _coverage_cell(
    city: str,
    period: str,
    *,
    release_ceiling: str,
    complete_through: str,
    seasons: Mapping[str, Mapping[str, Any]],
    verified: tuple[Mapping[str, Any], ...],
    required_artifact_unavailable: bool,
) -> CoverageCell:
    if period > release_ceiling:
        return CoverageCell(
            city, period, CoverageState.NOT_YET_EXPECTED, "beyond_latest_official_release", release_ceiling
        )
    season = _season_for_transaction_period(period)
    if period <= complete_through:
        if required_artifact_unavailable:
            return CoverageCell(
                city,
                period,
                CoverageState.MISSING,
                "required_artifact_not_verified",
                season,
            )
        artifact = seasons.get(season)
        if artifact is None or artifact.get("verification_status") != "VERIFIED":
            return CoverageCell(city, period, CoverageState.MISSING, "required_season_not_verified", season)
        covered = {_city_key(value) for value in artifact.get("coverage_cities") or ()}
        if _city_key(city) not in covered:
            return CoverageCell(city, period, CoverageState.MISSING, "required_season_city_member_missing", season)
        return CoverageCell(city, period, CoverageState.COMPLETE, "complete_season_scope_verified", season)

    incremental = [
        item
        for item in verified
        if str(item.get("kind") or "") in {"history", "current"}
        and parse_sale_registration_window(str(item.get("source_window_description") or ""))
    ]
    if incremental:
        latest = max(incremental, key=lambda item: str(item.get("release") or ""))
        return CoverageCell(
            city,
            period,
            CoverageState.PARTIAL,
            "recent_period_not_settled_by_complete_season",
            str(latest.get("release") or ""),
        )
    if seasons:
        latest_season = max(seasons)
        return CoverageCell(
            city,
            period,
            CoverageState.PARTIAL,
            "recent_period_not_settled_by_complete_season",
            latest_season,
        )
    return CoverageCell(city, period, CoverageState.MISSING, "incremental_release_missing")


def _season_for_transaction_period(period: str) -> str:
    year, month = (int(value) for value in period.split("-"))
    if month in {12, 1, 2}:
        season_year = year + (1 if month == 12 else 0)
        quarter = 1
    elif month in {3, 4, 5}:
        season_year, quarter = year, 2
    elif month in {6, 7, 8}:
        season_year, quarter = year, 3
    else:
        season_year, quarter = year, 4
    return f"{season_year - 1911:03d}S{quarter}"


def _roc_date(year: str, month: str, day: str) -> date:
    return date(int(year) + 1911, int(month), int(day))


def _iter_periods(since: str, until: str) -> Iterable[str]:
    year, month = (int(value) for value in since.split("-"))
    end_year, end_month = (int(value) for value in until.split("-"))
    while (year, month) <= (end_year, end_month):
        yield f"{year:04d}-{month:02d}"
        month += 1
        if month == 13:
            year += 1
            month = 1


def _validate_period(value: str) -> None:
    if not PERIOD_PATTERN.fullmatch(value):
        raise ValueError("invalid_period")


def _city_key(value: Any) -> str:
    return str(value or "").strip().replace("臺", "台")


def _percent(numerator: int, denominator: int) -> float:
    return round(numerator / denominator * 100, 2) if denominator else 0.0
