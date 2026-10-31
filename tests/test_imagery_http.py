import time
import httpx
import pytest
from services.imagery_http import ImageryHTTP
from services.imagery_reference import ImageryProviderError


@pytest.mark.parametrize('url', [
    'http://wms.nlsc.gov.tw/wms', 'https://wms.nlsc.gov.tw:443/wms',
    'https://a@wms.nlsc.gov.tw/wms','https://wms.nlsc.gov.tw/wms?url=x',
    'https://wms.nlsc.gov.tw/wms#fragment','https://wms.nlsc.gov.tw.evil/wms',
    'https://wms.nlsc.gov.tw/other', 'https://data.csrsr.ncu.edu.tw/SP/wmts',
])
def test_exact_url_allowlist_before_transport(url):
    def fail(req):
        pytest.fail('network call')
    with pytest.raises(ImageryProviderError,match='invalid_url'):
        ImageryHTTP('nlsc_photo2',httpx.MockTransport(fail)).get(url,deadline=time.monotonic()+1,max_bytes=10,mime_types={'image/jpeg'})


@pytest.mark.parametrize('headers,body,reason', [
    ({'content-length':'100'},b'a','response_too_large'),
    ({'content-encoding':'gzip'},b'a','unexpected_encoding'),
    ({},b'a'*11,'response_too_large'),
])
def test_transport_bounds(headers,body,reason,monkeypatch):
    monkeypatch.setattr('services.imagery_http.PROVIDER_COST_METRICS.record',lambda *a,**kw:None)
    def respond(req):
        return httpx.Response(200,headers={'content-type':'image/jpeg',**headers},content=body)
    with pytest.raises(ImageryProviderError,match=reason):
        ImageryHTTP('nlsc_photo2',httpx.MockTransport(respond)).get('https://wms.nlsc.gov.tw/wms',deadline=time.monotonic()+1,max_bytes=10,mime_types={'image/jpeg'})


def test_physical_call_is_counted_once(monkeypatch):
    records=[]
    monkeypatch.setattr('services.imagery_http.PROVIDER_COST_METRICS.record',lambda *a,**kw: records.append((a,kw)))
    transport=httpx.MockTransport(lambda req:httpx.Response(200,headers={'content-type':'image/jpeg'},content=b'a'))
    ImageryHTTP('nlsc_photo2',transport).get('https://wms.nlsc.gov.tw/wms',deadline=time.monotonic()+1,max_bytes=10,mime_types={'image/jpeg'})
    assert records==[(('satellite','physical_calls'),{'provider':'nlsc_photo2'})]


def test_streamed_bytes_are_bounded_without_content_length(monkeypatch):
    monkeypatch.setattr('services.imagery_http.PROVIDER_COST_METRICS.record',lambda *a,**kw:None)
    consumed=[]
    class Chunks(httpx.AsyncByteStream):
        async def __aiter__(self):
            for chunk in (b'a'*6,b'b'*6,b'not consumed'):
                consumed.append(chunk)
                yield chunk
    transport=httpx.MockTransport(lambda req:httpx.Response(200,headers={'content-type':'image/jpeg'},stream=Chunks()))
    with pytest.raises(ImageryProviderError,match='response_too_large'):
        ImageryHTTP('nlsc_photo2',transport).get('https://wms.nlsc.gov.tw/wms',deadline=time.monotonic()+1,max_bytes=10,mime_types={'image/jpeg'})
    assert len(consumed)==2


def test_absolute_deadline_rechecked_during_stream(monkeypatch):
    monkeypatch.setattr('services.imagery_http.PROVIDER_COST_METRICS.record',lambda *a,**kw:None)
    clock=[10.0]
    monkeypatch.setattr('services.imagery_http.time.monotonic',lambda:clock[0])
    class Chunks(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b'a'
            clock[0]=12.0
            yield b'b'
    transport=httpx.MockTransport(lambda req:httpx.Response(200,headers={'content-type':'image/jpeg'},stream=Chunks()))
    with pytest.raises(ImageryProviderError,match='timeout'):
        ImageryHTTP('nlsc_photo2',transport).get('https://wms.nlsc.gov.tw/wms',deadline=11,max_bytes=10,mime_types={'image/jpeg'})


@pytest.mark.parametrize('stall', ['headers','next_chunk'])
def test_total_network_deadline_cancels_stall_before_late_data(stall,monkeypatch):
    import asyncio
    import contextvars
    marker=contextvars.ContextVar('imagery_deadline_test',default=False)
    marker.set(True)
    events=[]
    monkeypatch.setattr('services.imagery_http.PROVIDER_COST_METRICS.record',lambda *a,**kw: events.append(('metric',marker.get())))
    class StalledStream(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b'early'
            try:
                await asyncio.sleep(.3)
                events.append(('late_chunk',True))
                yield b'late'
            finally:
                events.append(('cancelled_body',True))
        async def aclose(self):
            events.append(('closed_body',True))
    async def respond(req):
        assert marker.get()
        if stall=='headers':
            try:
                await asyncio.sleep(.3)
                events.append(('late_headers',True))
            finally:
                events.append(('cancelled_headers',True))
        return httpx.Response(200,headers={'content-type':'image/jpeg'},stream=StalledStream())
    started=time.monotonic()
    with pytest.raises(ImageryProviderError,match='timeout'):
        ImageryHTTP('nlsc_photo2',httpx.MockTransport(respond)).get('https://wms.nlsc.gov.tw/wms',deadline=started+.05,max_bytes=100,mime_types={'image/jpeg'})
    assert time.monotonic()-started < .2
    assert ('metric',True) in events
    assert not any(name.startswith('late_') for name,_ in events)
    assert (f'cancelled_{"headers" if stall=="headers" else "body"}',True) in events
    if stall=='next_chunk':
        assert ('closed_body',True) in events
