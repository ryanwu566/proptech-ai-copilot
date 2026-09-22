"""MOI RIS village population provider (dataset ODRP014).

This module is responsible for *transport and contract enforcement only*:

* URL / request construction for the ODRP014 endpoint.
* Bounded per-request timeout.
* Page-by-page collection using the verified ``page`` query parameter.
* ``responseCode`` validation against the documented success/terminator codes.
* Minimal per-page schema validation (required identity + total fields).
* Complete-page collection with a hard maximum page ceiling.
* Bounded retry for transient transport faults (timeout / connection / 5xx).
* Fail-closed behaviour on duplicate pages and on a final row count that does
  not equal the server-reported ``totalDataSize``.

Normalization (age aggregation, ratios, ROC date conversion, consistency
checks) is intentionally *not* done here; see ``ris_population_dataset``.

Verified live contract (ODRP014, statistic month 11507 / 2026-07):

* Pagination parameter is ``page`` (query string), 1-based. Omitting it is
  equivalent to ``page=1``.
* There is no client page-size parameter; ``pageDataSize`` is server-fixed at
  2000 for full pages and reports the actual row count on the final page.
* Metadata fields (``page``, ``totalPage``, ``totalDataSize``,
  ``pageDataSize``) are returned as *strings*.
* ``responseCode == "OD-0101-S"`` indicates a successful data page.
* Requesting a page beyond ``totalPage`` returns ``responseCode ==
  "OD-0102-S"`` with null metadata and no ``responseData`` (a "no more data"
  terminator rather than an error).
"""

from __future__ import annotations

import time
from typing import Any, Callable

import httpx


DATASET_ID = "ODRP014"
BASE_URL = "https://www.ris.gov.tw/rs-opendata/api/v1/datastore"
PAGE_PARAM = "page"
FIRST_PAGE = 1

# Documented response codes.
RESPONSE_CODE_SUCCESS = "OD-0101-S"
RESPONSE_CODE_NO_MORE_DATA = "OD-0102-S"

# Transport safety limits.
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_MAX_RETRIES = 2  # bounded retries for transient faults only
DEFAULT_RETRY_BACKOFF_SECONDS = 0.5
# Hard ceiling independent of server metadata; guards against a runaway loop
# if totalPage were ever misreported. 11507 uses 4 pages; 64 is generous.
DEFAULT_MAX_PAGES = 64

# Minimal required fields for a raw row to be accepted at the transport layer.
REQUIRED_ROW_FIELDS = (
    "statistic_yyymm",
    "district_code",
    "site_id",
    "village",
    "household_no",
    "people_total",
    "people_total_m",
    "people_total_f",
)

# --- Source-schema compatibility -----------------------------------------
#
# The ODRP014 endpoint is not schema-stable across statistic months. Some
# months (e.g. 11504) return Chinese field names; others (11505+) return the
# canonical English keys. This adapter maps a localized row to the canonical
# English schema so the rest of the provider — and the dataset layer — only
# ever sees canonical keys. The dataset layer's contract is unchanged.

# Static (non-age) Chinese -> canonical English field mapping.
CHINESE_FIELD_MAP = {
    "統計年月": "statistic_yyymm",
    "區域別代碼": "district_code",
    "區域別": "site_id",
    "村里": "village",
    "戶數": "household_no",
    "人口數": "people_total",
    "人口數-男": "people_total_m",
    "人口數-女": "people_total_f",
    "100歲以上-男": "people_age_100up_m",
    "100歲以上-女": "people_age_100up_f",
}

_CHINESE_SEX_SUFFIX = {"男": "m", "女": "f"}


def _map_source_key(key: str) -> str | None:
    """Return the canonical English key for a source key, or ``None`` if unknown.

    Handles the static map plus single-year age buckets of the form
    ``"{N}歲-男"`` / ``"{N}歲-女"`` -> ``"people_age_{NNN}_m|f"``.
    """

    if key in CHINESE_FIELD_MAP:
        return CHINESE_FIELD_MAP[key]
    # Single-year Chinese age buckets: "0歲-男" .. "99歲-女".
    # Only 0..99 map to a single-year canonical field; "100歲以上-男/女" is
    # handled by the static map above. Anything else ("100歲-男", "101歲-女",
    # "999歲-男", ...) is intentionally NOT mapped and falls through to the
    # unknown/extra-field policy, so a malformed source cannot silently
    # fabricate an out-of-range canonical age field.
    if "歲-" in key:
        age_part, _, sex_part = key.partition("歲-")
        if age_part.isdigit() and sex_part in _CHINESE_SEX_SUFFIX:
            age = int(age_part)
            if 0 <= age <= 99:
                return f"people_age_{age:03d}_{_CHINESE_SEX_SUFFIX[sex_part]}"
    return None


def normalize_source_row_schema(row: dict[str, Any]) -> dict[str, Any]:
    """Map a raw source row to the canonical English-key schema.

    * Canonical English keys are preserved as-is (no unnecessary mutation).
    * Chinese keys are translated to their canonical English equivalents.
    * Unknown/extra keys are preserved verbatim (the downstream required-field
      validation is an allow-list of the fields the product needs; extra source
      columns are tolerated, matching the existing provider contract).
    * Mixed bilingual input is only accepted when a Chinese key and its
      canonical English counterpart carry the *same* value. A conflicting value
      raises :class:`RisSchemaError` (fail closed; never silently overwrite).

    Raises :class:`RisSchemaError` if ``row`` is not a mapping.
    """

    if not isinstance(row, dict):
        raise RisSchemaError(
            f"source row must be an object, got {type(row).__name__}"
        )

    canonical: dict[str, Any] = {}
    # Track which source key first produced each canonical key, for clear errors.
    producing_key: dict[str, str] = {}

    for key, value in row.items():
        target = _map_source_key(key)
        if target is None:
            # Unknown/extra source column: preserve verbatim under its own name.
            target = key
        if target in canonical:
            existing = canonical[target]
            if existing != value:
                raise RisSchemaError(
                    "schema conflict for canonical field "
                    f"{target!r}: source keys {producing_key.get(target)!r} and "
                    f"{key!r} disagree ({existing!r} != {value!r})"
                )
            # Same value from two source keys (e.g. bilingual duplicate): keep.
            continue
        canonical[target] = value
        producing_key[target] = key

    return canonical


class RisProviderError(RuntimeError):
    """Base error for RIS population retrieval failures."""


class RisResponseCodeError(RisProviderError):
    """The API returned an unexpected ``responseCode``. Not retried."""


class RisSchemaError(RisProviderError):
    """A page payload failed structural / schema validation. Not retried."""


class RisPaginationError(RisProviderError):
    """Pagination invariants were violated (duplicate page, count mismatch)."""


# Types of transport faults that justify a bounded retry.
_RETRYABLE_HTTP_STATUS_MIN = 500


def build_dataset_url(yyymm: str) -> str:
    """Return the ODRP014 dataset URL for a ROC ``yyymm`` statistic month."""

    cleaned = str(yyymm).strip()
    if not cleaned.isdigit():
        raise ValueError(f"yyymm must be numeric ROC year-month, got {yyymm!r}")
    return f"{BASE_URL}/{DATASET_ID}/{cleaned}"


Fetcher = Callable[[str, int], dict[str, Any]]
"""A page fetcher: ``(url, page) -> parsed JSON dict``.

Injected in tests for offline behaviour. The default implementation performs a
bounded-timeout HTTP GET with bounded retry for transient transport faults.
"""


def _default_fetcher(
    timeout: float,
    max_retries: int,
    backoff: float,
    sleep: Callable[[float], None],
) -> Fetcher:
    def fetch(url: str, page: int) -> dict[str, Any]:
        attempt = 0
        while True:
            try:
                with httpx.Client(timeout=timeout) as client:
                    response = client.get(
                        url,
                        params={PAGE_PARAM: page},
                        headers={"Accept": "application/json"},
                    )
                status = response.status_code
                if status >= _RETRYABLE_HTTP_STATUS_MIN:
                    # Server-side transient fault: retry within budget.
                    raise httpx.HTTPStatusError(
                        f"server error {status}",
                        request=response.request,
                        response=response,
                    )
                if status >= 400:
                    # Client-side error: fail closed, never retried.
                    raise RisResponseCodeError(
                        f"RIS request failed with client status {status} for page {page}"
                    )
                return response.json()
            except (httpx.TimeoutException, httpx.TransportError, httpx.HTTPStatusError) as exc:
                if attempt >= max_retries:
                    raise RisProviderError(
                        f"RIS request for page {page} failed after {attempt + 1} attempts: {exc}"
                    ) from exc
                attempt += 1
                if backoff > 0:
                    sleep(backoff * attempt)

    return fetch


def _validate_rows(rows: Any, page: int) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        raise RisSchemaError(
            f"page {page}: responseData must be a list, got {type(rows).__name__}"
        )
    normalized_rows: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise RisSchemaError(
                f"page {page} row {index}: expected object, got {type(row).__name__}"
            )
        try:
            canonical = normalize_source_row_schema(row)
        except RisSchemaError as exc:
            raise RisSchemaError(f"page {page} row {index}: {exc}") from exc
        missing = [field for field in REQUIRED_ROW_FIELDS if field not in canonical]
        if missing:
            raise RisSchemaError(
                f"page {page} row {index}: missing required fields {missing}"
            )
        normalized_rows.append(canonical)
    return normalized_rows


def _coerce_int(value: Any, field: str) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise RisSchemaError(f"metadata field {field!r} is not an integer: {value!r}") from exc


def fetch_population_pages(
    yyymm: str,
    fetcher: Fetcher | None = None,
    *,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_backoff: float = DEFAULT_RETRY_BACKOFF_SECONDS,
    max_pages: int = DEFAULT_MAX_PAGES,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    """Collect all population rows for one ROC statistic month.

    Returns a dict with the collected rows and verified pagination metadata::

        {
            "yyymm": "11507",
            "url": "...",
            "rows": [ {raw row}, ... ],
            "pages_fetched": 4,
            "total_data_size": 7781,
            "total_page": 4,
        }

    Fail-closed guarantees:

    * A page whose ``responseCode`` is neither the success nor the
      no-more-data terminator raises :class:`RisResponseCodeError`.
    * Structurally invalid payloads raise :class:`RisSchemaError`.
    * A repeated (duplicate) page number raises :class:`RisPaginationError`.
    * If the total collected row count does not equal the server-reported
      ``totalDataSize`` the call raises :class:`RisPaginationError`.
    * Iteration is bounded by ``max_pages`` regardless of server metadata.
    """

    url = build_dataset_url(yyymm)
    fetch = fetcher or _default_fetcher(timeout, max_retries, retry_backoff, sleep)

    rows: list[dict[str, Any]] = []
    seen_pages: set[int] = set()
    total_data_size: int | None = None
    total_page: int | None = None
    pages_fetched = 0

    page = FIRST_PAGE
    while page <= max_pages:
        payload = fetch(url, page)
        if not isinstance(payload, dict):
            raise RisSchemaError(f"page {page}: payload is not a JSON object")

        response_code = payload.get("responseCode")
        if response_code == RESPONSE_CODE_NO_MORE_DATA:
            # Documented terminator: no more data beyond the last page.
            break
        if response_code != RESPONSE_CODE_SUCCESS:
            raise RisResponseCodeError(
                f"page {page}: unexpected responseCode {response_code!r} "
                f"(message: {payload.get('responseMessage')!r})"
            )

        if page in seen_pages:
            raise RisPaginationError(f"duplicate page {page} received; failing closed")
        seen_pages.add(page)

        reported_page = _coerce_int(payload.get("page"), "page")
        if reported_page != page:
            raise RisPaginationError(
                f"requested page {page} but server reported page {reported_page}"
            )

        page_total_data_size = _coerce_int(payload.get("totalDataSize"), "totalDataSize")
        page_total_page = _coerce_int(payload.get("totalPage"), "totalPage")
        if total_data_size is None:
            total_data_size = page_total_data_size
            total_page = page_total_page
        else:
            if page_total_data_size != total_data_size:
                raise RisPaginationError(
                    f"totalDataSize changed across pages: {total_data_size} -> "
                    f"{page_total_data_size}"
                )
            if page_total_page != total_page:
                raise RisPaginationError(
                    f"totalPage changed across pages: {total_page} -> {page_total_page}"
                )

        page_rows = _validate_rows(payload.get("responseData"), page)
        rows.extend(page_rows)
        pages_fetched += 1

        if total_page is not None and page >= total_page:
            break
        page += 1
    else:
        raise RisPaginationError(
            f"exceeded hard maximum of {max_pages} pages without completing collection"
        )

    if total_data_size is None:
        raise RisPaginationError("no successful data page was returned")

    if len(rows) != total_data_size:
        raise RisPaginationError(
            f"collected {len(rows)} rows but server reported totalDataSize "
            f"{total_data_size}; failing closed"
        )

    return {
        "yyymm": str(yyymm).strip(),
        "url": url,
        "rows": rows,
        "pages_fetched": pages_fetched,
        "total_data_size": total_data_size,
        "total_page": total_page,
    }
