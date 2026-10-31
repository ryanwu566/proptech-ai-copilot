"""Provider-independent, capture-date-honest imagery contract."""
from dataclasses import dataclass


CSRSR_MIN_YEAR = 1996
CSRSR_MAX_YEAR = 2025


@dataclass(frozen=True)
class ImageryQuery:
    latitude: float
    longitude: float
    deadline: float
    aoi_radius_m: int = 500
    dimensions: tuple[int, int] = (512, 512)


@dataclass(frozen=True)
class ImageryResult:
    image_bytes: bytes
    provider: str
    source_type: str
    source: str
    dataset_or_layer: str
    processing_method: str
    attribution: str
    limitations: tuple[str, ...]
    bbox: tuple[float, float, float, float]
    vintage: str | None = None
    observation_date: str | None = None
    date_precision: str = 'unknown'
    usage_restriction: str | None = None


class ImageryProviderError(RuntimeError):
    """Stable constructor: ImageryProviderError(reason_code), no raw details."""
    CODES = frozenset({'invalid_query', 'timeout', 'tls_verification_failed', 'transport_failed',
        'invalid_url', 'redirect_rejected', 'http_error', 'unexpected_encoding', 'unexpected_mime',
        'response_too_large', 'invalid_image', 'no_data', 'licensing_not_accepted', 'invalid_configuration',
        'invalid_capabilities', 'layer_unavailable', 'outside_coverage', 'tile_limit_exceeded'})

    def __init__(self, reason_code: str):
        self.reason_code = reason_code if reason_code in self.CODES else 'transport_failed'
        super().__init__(self.reason_code)
