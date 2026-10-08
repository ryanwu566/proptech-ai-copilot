"""Explicit evidence quality and conservative public-information availability."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from . import lineage as l, semantics as s

VERSION='plvr-evidence-qualified-availability-v1'
TAIPEI=ZoneInfo('Asia/Taipei')
QUALITIES={'EXACT_PUBLICATION_TIME','DATE_ONLY_PUBLICATION','CONSERVATIVE_UPPER_BOUND',
           'SYSTEM_FIRST_SEEN','UNKNOWN'}


def resolve_availability(record: dict | None, release_id: str, archive_sha256: str) -> dict:
    record=record or {}
    quality=record.get('quality','UNKNOWN')
    if quality not in QUALITIES:
        quality='UNKNOWN'
    result={'quality':quality,'available_at':None,'publication_at':None,
            'publication_date':None,'version':VERSION}
    if (record.get('release_id')!=release_id or record.get('archive_sha256')!=archive_sha256
            or not s.evidence_valid(record.get('evidence'))):
        return result
    value=record.get('value')
    if quality=='DATE_ONLY_PUBLICATION':
        try:
            day=date.fromisoformat(value)
            bound=datetime.combine(day+timedelta(days=1),datetime.min.time(),TAIPEI)
        except (ValueError,TypeError,OverflowError):
            return result
        result['publication_date']=day.isoformat()
    elif quality in {'EXACT_PUBLICATION_TIME','CONSERVATIVE_UPPER_BOUND'}:
        bound=l.timestamp(value)
        if bound is None:
            return result
        if quality=='EXACT_PUBLICATION_TIME':
            result['publication_at']=bound.astimezone(timezone.utc).isoformat()
    else:
        # System first-seen does not by itself establish public availability.
        return result
    result['available_at']=bound.astimezone(timezone.utc).isoformat()
    return result


def available_by(resolved: dict, cutoff: str) -> bool:
    boundary=l.timestamp(cutoff)
    if boundary is None:
        raise ValueError('cutoff_requires_timezone')
    available=l.timestamp(resolved.get('available_at'))
    return available is not None and available<=boundary


def retrieval_evidence(source: dict, *, manifest_sha256: str) -> dict:
    """A checksum-verified HTTPS capture supplies only its own late upper bound."""
    http=source.get('http_download') or {}
    start=l.timestamp(source.get('retrieval_started_at'))
    end=l.timestamp(source.get('retrieved_at'))
    if (source.get('checksum_status')!='EXACT_MATCH' or source.get('package_valid') is not True
            or source.get('sha256')!=source.get('expected_sha256')
            or http.get('status_code')!=200 or http.get('final_url')!=source.get('official_url')
            or not str(source.get('official_url','')).startswith('https://plvr.land.moi.gov.tw/')
            or start is None or end is None or start>end or source.get('download_attempts')!=1):
        return {'quality':'UNKNOWN'}
    return {'quality':'CONSERVATIVE_UPPER_BOUND','value':end.isoformat(),
            'archive_sha256':source['sha256'],'release_id':source['source_archive_id'],
            'evidence':{'sha256':manifest_sha256,'locator':'verified-http-retrieval-manifest',
                        'version':VERSION},'historical_publication_proven':False}
