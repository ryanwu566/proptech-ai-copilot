"""Small HTTPS-only streaming transport; no redirects, proxies, or image cache."""
import asyncio
import re
import ssl
import time
from urllib.parse import urlsplit

import httpx

from services.imagery_reference import ImageryProviderError
from services.provider_cost_metrics import PROVIDER_COST_METRICS


class ImageryHTTP:
    def __init__(self, provider, transport=None):
        self.provider = provider
        self.transport = transport

    def get(self, url, *, params=None, deadline, max_bytes, mime_types):
        parsed = urlsplit(url)
        allowed = (
            self.provider == 'nlsc_photo2' and parsed.netloc == 'wms.nlsc.gov.tw' and parsed.path == '/wms'
        ) or (
            self.provider == 'csrsr_spot' and parsed.netloc == 'data.csrsr.ncu.edu.tw' and (
                parsed.path == '/SP/wmts' or re.fullmatch(r'/SP/wmts/SP(?:199[6-9]|20(?:0\d|1\d|2[0-5]))NC_3857/GoogleMapsCompatible/\d{1,2}/\d{1,6}/\d{1,6}\.png', parsed.path)
            )
        )
        if parsed.scheme != 'https' or not allowed or parsed.query or parsed.fragment or parsed.username or parsed.password:
            raise ImageryProviderError('invalid_url')
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ImageryProviderError('timeout')
        return asyncio.run(self._get_async(url, params=params, deadline=deadline,
                                           max_bytes=max_bytes, mime_types=mime_types))

    async def _get_async(self, url, *, params, deadline, max_bytes, mime_types):
        try:
            # Cancellation closes the active HTTPX/httpcore connection at the shared total
            # deadline, including stalled headers or successive reads. No helper thread
            # survives cancellation; asyncio.run preserves the calling contextvars.
            async with asyncio.timeout(max(0, deadline - time.monotonic())):
                return await self._stream(url, params=params, deadline=deadline,
                                          max_bytes=max_bytes, mime_types=mime_types)
        except TimeoutError:
            raise ImageryProviderError('timeout') from None

    async def _stream(self, url, *, params, deadline, max_bytes, mime_types):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ImageryProviderError('timeout')
        try:
            async with httpx.AsyncClient(transport=self.transport, trust_env=False, follow_redirects=False,
                              timeout=min(remaining, 5.0)) as client:
                PROVIDER_COST_METRICS.record('satellite', 'physical_calls', provider=self.provider)
                async with client.stream('GET', url, params=params, headers={'Accept-Encoding': 'identity'}) as response:
                    if 300 <= response.status_code < 400:
                        raise ImageryProviderError('redirect_rejected')
                    if response.status_code != 200:
                        raise ImageryProviderError('http_error')
                    if response.headers.get('content-encoding', 'identity').lower() != 'identity':
                        raise ImageryProviderError('unexpected_encoding')
                    mime = response.headers.get('content-type', '').split(';', 1)[0].strip().lower()
                    if mime not in mime_types:
                        raise ImageryProviderError('unexpected_mime')
                    length = response.headers.get('content-length')
                    if length is not None and (not length.isdigit() or int(length) > max_bytes):
                        raise ImageryProviderError('response_too_large')
                    chunks, count = [], 0
                    # HTTPX handles pre-read content as a bounded single chunk too.
                    async for chunk in _raw_chunks(response):
                        if time.monotonic() >= deadline:
                            raise ImageryProviderError('timeout')
                        count += len(chunk)
                        if count > max_bytes:
                            raise ImageryProviderError('response_too_large')
                        chunks.append(chunk)
                    return b''.join(chunks), mime
        except ImageryProviderError:
            raise
        except httpx.TimeoutException:
            raise ImageryProviderError('timeout') from None
        except (httpx.HTTPError, ssl.SSLError) as error:
            # Detect certificate failures through wrapped transport exceptions, never expose their text.
            current = error
            tls = False
            while current is not None:
                tls = tls or isinstance(current, ssl.SSLError) or 'CERTIFICATE_VERIFY_FAILED' in str(current)
                current = current.__cause__ or current.__context__
            raise ImageryProviderError('tls_verification_failed' if tls else 'transport_failed') from None


async def _raw_chunks(response):
    if response.is_stream_consumed:
        yield response.content
    else:
        async for chunk in response.aiter_raw():
            yield chunk
