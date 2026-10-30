import io
import time

import httpx
import pytest
from PIL import Image

from services.imagery_reference import ImageryQuery, ImageryProviderError
from services.imagery_providers import NLSCOrthophotoAdapter, CSRSRSpotAdapter


def picture(size=(512, 512), fmt='JPEG', blank=False):
    im = Image.new('RGB', size)
    if not blank:
        im.putdata([((x * 17) % 256, (x // size[0] * 29) % 256, (x * 7) % 256) for x in range(size[0] * size[1])])
    out = io.BytesIO()
    im.save(out, fmt)
    return out.getvalue()


def query(**kw):
    return ImageryQuery(25.03, 121.56, time.monotonic() + 10, **kw)


@pytest.fixture(autouse=True)
def metrics(monkeypatch):
    monkeypatch.setattr('services.imagery_http.PROVIDER_COST_METRICS.record', lambda *a, **kw: None)


def test_nlsc_geometry_and_unknown_vintage():
    calls = []
    def respond(request):
        calls.append(request)
        return httpx.Response(200, headers={'content-type': 'image/jpeg'}, content=picture())
    adapter = NLSCOrthophotoAdapter(transport=httpx.MockTransport(respond))
    assert not calls
    result = adapter.fetch(query())
    params = calls[0].url.params
    assert params['LAYERS'] == 'PHOTO2'
    assert params['CRS'] == 'EPSG:3857'
    assert params['VERSION'] == '1.3.0'
    assert params['WIDTH'] == params['HEIGHT'] == '512'
    assert result.bbox[0] < result.bbox[2] and result.bbox[1] < result.bbox[3]
    assert 1090 < result.bbox[2] - result.bbox[0] < 1120
    assert result.vintage is result.observation_date is None
    assert result.date_precision == 'unknown'
    assert result.source_type == 'orthophoto'
    assert len(result.image_bytes) <= 250000


@pytest.mark.parametrize('mime,body,reason', [
    ('text/html', b'no', 'unexpected_mime'),
    ('image/jpeg', picture(blank=True), 'no_data'),
    ('image/png', picture(), 'unexpected_mime'),
    ('image/jpeg', picture((513,512)), 'invalid_image'),
    ('image/jpeg', b'x' * 2000001, 'response_too_large'),
])
def test_rejects_invalid_nlsc(mime, body, reason):
    adapter = NLSCOrthophotoAdapter(transport=httpx.MockTransport(lambda req: httpx.Response(200, headers={'content-type':mime}, content=body)))
    with pytest.raises(ImageryProviderError) as error:
        adapter.fetch(query())
    assert error.value.reason_code == reason
    assert str(error.value) == reason


@pytest.mark.parametrize('exception,reason', [(httpx.ConnectError('CERTIFICATE_VERIFY_FAILED secret'), 'tls_verification_failed'), (httpx.ReadTimeout('secret'), 'timeout')])
def test_network_errors_sanitized(exception, reason):
    def fail(req):
        raise exception
    with pytest.raises(ImageryProviderError) as error:
        NLSCOrthophotoAdapter(transport=httpx.MockTransport(fail)).fetch(query())
    assert str(error.value) == reason


def test_redirect_is_not_followed():
    calls=[]
    def respond(req):
        calls.append(req)
        return httpx.Response(302, headers={'location':'https://evil.test/'})
    with pytest.raises(ImageryProviderError, match='redirect_rejected'):
        NLSCOrthophotoAdapter(transport=httpx.MockTransport(respond)).fetch(query())
    assert len(calls)==1


def capabilities(layer='SP2025NC_3857', template=None, maxcol=65535, zoom=16):
    template = template or f'https://data.csrsr.ncu.edu.tw/SP/wmts/{layer}/GoogleMapsCompatible/{{TileMatrix}}/{{TileCol}}/{{TileRow}}.png'
    resource = f'<ResourceURL format="image/png" resourceType="tile" template="{template}"/>'
    return f'''<Capabilities xmlns="http://www.opengis.net/wmts/1.0" xmlns:ows="http://www.opengis.net/ows/1.1"><Contents><Layer><ows:Identifier>{layer}</ows:Identifier><Format>image/png</Format>{resource}<TileMatrixSetLink><TileMatrixSet>GoogleMapsCompatible</TileMatrixSet><TileMatrixSetLimits><TileMatrixLimits><TileMatrix>{zoom}</TileMatrix><MinTileRow>0</MinTileRow><MaxTileRow>{2**zoom-1}</MaxTileRow><MinTileCol>0</MinTileCol><MaxTileCol>{maxcol}</MaxTileCol></TileMatrixLimits></TileMatrixSetLimits></TileMatrixSetLink></Layer><TileMatrixSet><ows:Identifier>GoogleMapsCompatible</ows:Identifier><ows:SupportedCRS>urn:ogc:def:crs:EPSG::3857</ows:SupportedCRS><TileMatrix><ows:Identifier>{zoom}</ows:Identifier><ScaleDenominator>{559082264.0287178 / 2**zoom}</ScaleDenominator><TopLeftCorner>-20037508.3427892 20037508.3427892</TopLeftCorner><TileWidth>256</TileWidth><TileHeight>256</TileHeight><MatrixWidth>{2**zoom}</MatrixWidth><MatrixHeight>{2**zoom}</MatrixHeight></TileMatrix></TileMatrixSet></Contents></Capabilities>'''.encode()


def test_spot_requires_explicit_license_without_http():
    calls=[]
    adapter=CSRSRSpotAdapter(transport=httpx.MockTransport(lambda r: calls.append(r)))
    with pytest.raises(ImageryProviderError, match='licensing_not_accepted'):
        adapter.fetch(query())
    assert not calls


def test_spot_annual_mosaic_tiles_and_output():
    calls=[]
    def respond(req):
        calls.append(req)
        if req.url.params:
            return httpx.Response(200,headers={'content-type':'application/xml'},content=capabilities())
        return httpx.Response(200,headers={'content-type':'image/png'},content=picture((256,256),'PNG'))
    result=CSRSRSpotAdapter(noncommercial_use=True,transport=httpx.MockTransport(respond)).fetch(query())
    assert 1 < len(calls) <= 10
    assert all('/SP2025NC_3857/GoogleMapsCompatible/16/' in str(c.url) for c in calls[1:])
    assert result.vintage=='2025' and result.date_precision=='year'
    assert result.observation_date is None
    assert result.usage_restriction and result.source_type=='satellite'
    assert Image.open(io.BytesIO(result.image_bytes)).size==(512,512)


@pytest.mark.parametrize('cap,reason', [(capabilities('SP2024NC_3857'),'layer_unavailable'),(capabilities(template='https://evil.test/{TileRow}.png'),'invalid_capabilities'),(capabilities(maxcol=1),'outside_coverage')])
def test_spot_fails_closed(cap,reason):
    calls=[]
    def respond(req):
        calls.append(req)
        return httpx.Response(200,headers={'content-type':'application/xml'},content=cap)
    with pytest.raises(ImageryProviderError,match=reason):
        CSRSRSpotAdapter(noncommercial_use=True,transport=httpx.MockTransport(respond)).fetch(query())
    assert len(calls)==1


def test_expired_deadline_and_invalid_geometry_do_not_call():
    def unexpected(req):
        pytest.fail('unexpected network')
    adapter=NLSCOrthophotoAdapter(transport=httpx.MockTransport(unexpected))
    with pytest.raises(ImageryProviderError,match='timeout'):
        adapter.fetch(ImageryQuery(25,121,0))
    with pytest.raises(ImageryProviderError,match='invalid_query'):
        adapter.fetch(query(aoi_radius_m=100000))


def test_tile_ceiling_checked_before_tiles():
    calls=[]
    def respond(req):
        calls.append(req)
        return httpx.Response(200,headers={'content-type':'application/xml'},content=capabilities(zoom=17))
    with pytest.raises(ImageryProviderError,match='tile_limit_exceeded'):
        CSRSRSpotAdapter(noncommercial_use=True,transport=httpx.MockTransport(respond)).fetch(query())
    assert len(calls)==1


@pytest.mark.parametrize('year', [1995,2026,'2025',True])
def test_invalid_annual_configuration_never_requests(year):
    def unexpected(req):
        pytest.fail('unexpected request')
    with pytest.raises(ImageryProviderError,match='invalid_configuration'):
        CSRSRSpotAdapter(year=year,noncommercial_use=True,transport=httpx.MockTransport(unexpected)).fetch(query())


@pytest.mark.parametrize('body', [b'<html>error</html>', b'<!DOCTYPE x [<!ENTITY a SYSTEM "file:///etc/passwd">]><Capabilities>&a;</Capabilities>'])
def test_capabilities_reject_errors_and_entities(body):
    def respond(req):
        return httpx.Response(200,headers={'content-type':'application/xml'},content=body)
    with pytest.raises(ImageryProviderError,match='invalid_capabilities'):
        CSRSRSpotAdapter(noncommercial_use=True,transport=httpx.MockTransport(respond)).fetch(query())


def test_mime_payload_mismatch_and_transparency():
    from services.imagery_providers import _decode
    with pytest.raises(ImageryProviderError,match='invalid_image'):
        _decode(picture(fmt='PNG'), 'image/jpeg', (512,512))
    im=Image.open(io.BytesIO(picture((256,256),'PNG'))).convert('RGBA')
    im.putalpha(0)
    out=io.BytesIO()
    im.save(out,'PNG')
    with pytest.raises(ImageryProviderError,match='no_data'):
        _decode(out.getvalue(),'image/png',(256,256))


def test_palette_transparency_is_no_data():
    from services.imagery_providers import _decode
    im=Image.open(io.BytesIO(picture((256,256),'PNG'))).quantize(colors=128)
    out=io.BytesIO()
    im.save(out,'PNG',transparency=0)
    with pytest.raises(ImageryProviderError,match='no_data'):
        _decode(out.getvalue(),'image/png',(256,256))


def test_blank_composed_output_is_no_data():
    from services.imagery_providers import _jpeg
    with pytest.raises(ImageryProviderError,match='no_data'):
        _jpeg(Image.new('RGB',(512,512)),query())


@pytest.mark.parametrize('latitude,longitude', [(25,180),(25,-180),(0,0),(30,121)])
def test_nlsc_outside_audited_coverage_never_requests(latitude,longitude):
    def unexpected(req):
        pytest.fail('outside-coverage network')
    with pytest.raises(ImageryProviderError,match='outside_coverage'):
        NLSCOrthophotoAdapter(transport=httpx.MockTransport(unexpected)).fetch(ImageryQuery(latitude,longitude,time.monotonic()+10))


@pytest.mark.parametrize('mutation', ['resource','format','duplicate','dimension'])
def test_capabilities_missing_or_ambiguous_schema_fails(mutation):
    cap=capabilities().decode()
    if mutation=='resource':
        import re
        cap=re.sub(r'<ResourceURL[^>]*/>','',cap)
    elif mutation=='format':
        cap=cap.replace('<Format>image/png</Format>','<Format>image/jpeg</Format>')
    elif mutation=='duplicate':
        start=cap.index('<TileMatrix>')
        # Duplicate the matrix definition, not the layer limit identifier.
        start=cap.index('<TileMatrix><ows:Identifier>')
        end=cap.index('</TileMatrix>',start)+len('</TileMatrix>')
        cap=cap[:end]+cap[start:end]+cap[end:]
    else:
        cap=cap.replace('<Format>image/png</Format>','<Format>image/png</Format><Dimension><ows:Identifier>time</ows:Identifier></Dimension>')
    transport=httpx.MockTransport(lambda req:httpx.Response(200,headers={'content-type':'text/xml'},content=cap.encode()))
    with pytest.raises(ImageryProviderError,match='invalid_capabilities'):
        CSRSRSpotAdapter(noncommercial_use=True,transport=transport).fetch(query())


@pytest.mark.parametrize('lower,upper,reason', [('nan 21','122 26','invalid_capabilities'),('119 21','120 26','outside_coverage'),('122 21','119 26','invalid_capabilities')])
def test_advertised_wgs84_coverage_is_enforced(lower,upper,reason):
    cap=capabilities().decode().replace('<Format>image/png</Format>',f'<Format>image/png</Format><ows:WGS84BoundingBox><ows:LowerCorner>{lower}</ows:LowerCorner><ows:UpperCorner>{upper}</ows:UpperCorner></ows:WGS84BoundingBox>')
    calls=[]
    def respond(req):
        calls.append(req)
        return httpx.Response(200,headers={'content-type':'text/xml'},content=cap.encode())
    with pytest.raises(ImageryProviderError,match=reason):
        CSRSRSpotAdapter(noncommercial_use=True,transport=httpx.MockTransport(respond)).fetch(query())
    assert len(calls)==1


@pytest.mark.parametrize('corner',['NaN 20037508.3427892','-20037508.3427892 NaN'])
def test_nonfinite_matrix_origin_rejected_before_tiles(corner):
    cap=capabilities().decode().replace('-20037508.3427892 20037508.3427892',corner)
    calls=[]
    def respond(req):
        calls.append(req)
        return httpx.Response(200,headers={'content-type':'text/xml'},content=cap.encode())
    with pytest.raises(ImageryProviderError,match='invalid_capabilities'):
        CSRSRSpotAdapter(noncommercial_use=True,transport=httpx.MockTransport(respond)).fetch(query())
    assert len(calls)==1
