"""Bounded NLSC WMS and CSRSR annual SPOT WMTS imagery adapters."""
import io
import math
import time
import warnings

from defusedxml import ElementTree as ET
from PIL import Image, ImageStat
from pyproj import Geod, Transformer

from services.imagery_http import ImageryHTTP
from services.imagery_reference import CSRSR_MIN_YEAR, CSRSR_MAX_YEAR, ImageryProviderError, ImageryQuery, ImageryResult

WORLD = 20037508.3427892
NS = {'w': 'http://www.opengis.net/wmts/1.0', 'o': 'http://www.opengis.net/ows/1.1'}


def _deadline(query):
    if time.monotonic() >= query.deadline:
        raise ImageryProviderError('timeout')


def _bbox(query):
    if (not all(isinstance(v, (float, int)) and math.isfinite(v) for v in (query.latitude, query.longitude, query.deadline))
        or not -85 < query.latitude < 85 or not -180 <= query.longitude <= 180
        or query.aoi_radius_m != 500 or query.dimensions != (512, 512)):
        raise ImageryProviderError('invalid_query')
    _deadline(query)
    geod = Geod(ellps='WGS84')
    points = [geod.fwd(query.longitude, query.latitude, bearing, query.aoi_radius_m)[:2] for bearing in (0, 90, 180, 270)]
    transform = Transformer.from_crs('EPSG:4326', 'EPSG:3857', always_xy=True)
    xy = [transform.transform(*p) for p in points]
    return min(p[0] for p in xy), min(p[1] for p in xy), max(p[0] for p in xy), max(p[1] for p in xy)


def _decode(data, mime, size):
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as check:
                if check.format != {'image/jpeg': 'JPEG', 'image/png': 'PNG'}[mime] or check.size != size or check.width * check.height > 512 * 512:
                    raise ImageryProviderError('invalid_image')
                check.verify()
            with Image.open(io.BytesIO(data)) as original:
                original.load()
                if ('A' in original.getbands() or 'transparency' in original.info) and original.convert('RGBA').getchannel('A').getextrema()[0] < 255:
                    raise ImageryProviderError('no_data')
                result = original.convert('RGB')
        if max(ImageStat.Stat(result).stddev) < 2.0:
            raise ImageryProviderError('no_data')
        return result
    except ImageryProviderError:
        raise
    except Exception:
        raise ImageryProviderError('invalid_image') from None


def _jpeg(image, query):
    _deadline(query)
    if max(ImageStat.Stat(image).stddev) < 2.0:
        raise ImageryProviderError('no_data')
    for quality in (90, 80, 70, 60, 45, 30):
        out = io.BytesIO()
        image.save(out, 'JPEG', quality=quality)
        _deadline(query)
        if len(out.getvalue()) <= 250000:
            return out.getvalue()
    raise ImageryProviderError('response_too_large')


class NLSCOrthophotoAdapter:
    def __init__(self, transport=None):
        self.http = ImageryHTTP('nlsc_photo2', transport)

    def fetch(self, query: ImageryQuery) -> ImageryResult:
        bbox = _bbox(query)
        # Audited NLSC service extent; avoid global or antimeridian WMS requests.
        if not (13124165 <= bbox[0] < bbox[2] <= 13622663 and 2441815 <= bbox[1] < bbox[3] <= 3055804):
            raise ImageryProviderError('outside_coverage')
        params = {'SERVICE': 'WMS', 'VERSION': '1.3.0', 'REQUEST': 'GetMap', 'LAYERS': 'PHOTO2',
                  'STYLES': '', 'CRS': 'EPSG:3857', 'BBOX': ','.join(str(v) for v in bbox),
                  'WIDTH': 512, 'HEIGHT': 512, 'FORMAT': 'image/jpeg', 'TRANSPARENT': 'FALSE'}
        data, mime = self.http.get('https://wms.nlsc.gov.tw/wms', params=params, deadline=query.deadline,
                                   max_bytes=2000000, mime_types={'image/jpeg'})
        image = _decode(data, mime, (512, 512))
        return ImageryResult(_jpeg(image, query), 'nlsc_photo2', 'orthophoto', 'https://wms.nlsc.gov.tw/wms',
            'PHOTO2', 'WMS GetMap; validated and reencoded JPEG', '內政部國土測繪中心（NLSC）正射影像',
            ('Contextual reference only; not a statutory survey or property boundary determination.',
             'Capture date and cloud coverage are unknown; retrieval time is not observation time.',
             'Service coverage and mosaic acquisition dates vary.'), bbox)


class CSRSRSpotAdapter:
    def __init__(self, year=2025, noncommercial_use=False, transport=None):
        self.year = year
        self.noncommercial_use = noncommercial_use
        self.http = ImageryHTTP('csrsr_spot', transport)

    def _capabilities(self, query):
        data, _ = self.http.get('https://data.csrsr.ncu.edu.tw/SP/wmts',
            params={'SERVICE': 'WMTS', 'REQUEST': 'GetCapabilities', 'VERSION': '1.0.0'},
            deadline=query.deadline, max_bytes=2000000,
            mime_types={'application/xml', 'text/xml', 'application/vnd.ogc.wmts_xml'})
        try:
            root = ET.fromstring(data)
            if root.tag != '{http://www.opengis.net/wmts/1.0}Capabilities':
                raise ValueError()
            layer_name = f'SP{self.year}NC_3857'
            layers = [e for e in root.findall('w:Contents/w:Layer', NS) if e.findtext('o:Identifier', namespaces=NS) == layer_name]
            if not layers:
                raise ImageryProviderError('layer_unavailable')
            if len(layers) != 1:
                raise ValueError()
            layer = layers[0]
            coverage = layer.findall('o:WGS84BoundingBox', NS)
            if len(coverage) > 1:
                raise ValueError()
            if coverage:
                lower = [float(v) for v in coverage[0].findtext('o:LowerCorner', namespaces=NS).split()]
                upper = [float(v) for v in coverage[0].findtext('o:UpperCorner', namespaces=NS).split()]
                if (len(lower) != 2 or len(upper) != 2 or not all(math.isfinite(v) for v in lower + upper)
                    or not -180 <= lower[0] < upper[0] <= 180 or not -85 < lower[1] < upper[1] < 85):
                    raise ValueError()
                projected = Transformer.from_crs('EPSG:4326', 'EPSG:3857', always_xy=True)
                minx, miny = projected.transform(*lower)
                maxx, maxy = projected.transform(*upper)
                area = _bbox(query)
                if not (minx <= area[0] < area[2] <= maxx and miny <= area[1] < area[3] <= maxy):
                    raise ImageryProviderError('outside_coverage')
            resources = layer.findall('w:ResourceURL', NS)
            if len(resources) != 1 or layer.findall('w:Format', NS)[0].text != 'image/png' or layer.findall('w:Dimension', NS):
                raise ValueError()
            for resource in resources:
                expected = f'https://data.csrsr.ncu.edu.tw/SP/wmts/{layer_name}/GoogleMapsCompatible/{{TileMatrix}}/{{TileCol}}/{{TileRow}}.png'
                if resource.get('template') != expected or resource.get('format') != 'image/png' or resource.get('resourceType') != 'tile':
                    raise ValueError()
            links = [e for e in layer.findall('w:TileMatrixSetLink', NS) if e.findtext('w:TileMatrixSet', namespaces=NS) == 'GoogleMapsCompatible']
            sets = [e for e in root.findall('w:Contents/w:TileMatrixSet', NS) if e.findtext('o:Identifier', namespaces=NS) == 'GoogleMapsCompatible']
            if len(links) != 1 or len(sets) != 1:
                raise ValueError()
            matrix_set = sets[0]
            if matrix_set.findtext('o:SupportedCRS', namespaces=NS) not in ('urn:ogc:def:crs:EPSG::3857', 'EPSG:3857', 'http://www.opengis.net/def/crs/EPSG/0/3857'):
                raise ValueError()
            max_zoom = 14 if self.year <= 2003 else 16 if self.year <= 2012 else 17
            matrices = {}
            seen_zooms = set()
            for matrix in matrix_set.findall('w:TileMatrix', NS):
                zoom = int(matrix.findtext('o:Identifier', namespaces=NS))
                if zoom in seen_zooms:
                    raise ValueError()
                seen_zooms.add(zoom)
                if not 0 <= zoom <= max_zoom:
                    continue
                def number(name):
                    return int(matrix.findtext('w:' + name, namespaces=NS))
                corner = [float(n) for n in matrix.findtext('w:TopLeftCorner', namespaces=NS).split()]
                scale = float(matrix.findtext('w:ScaleDenominator', namespaces=NS))
                expected_scale = (2 * WORLD / (256 * 2 ** zoom)) / .00028
                if (number('TileWidth') != 256 or number('TileHeight') != 256
                    or number('MatrixWidth') != 2 ** zoom or number('MatrixHeight') != 2 ** zoom
                    or len(corner) != 2 or not all(math.isfinite(v) for v in corner) or abs(corner[0] + WORLD) > .01 or abs(corner[1] - WORLD) > .01
                    or not math.isfinite(scale) or abs(scale / expected_scale - 1) > .00001):
                    raise ValueError()
                matrices[zoom] = None
            limits = {}
            for entry in links[0].findall('w:TileMatrixSetLimits/w:TileMatrixLimits', NS):
                zoom = int(entry.findtext('w:TileMatrix', namespaces=NS))
                vals = tuple(int(entry.findtext('w:' + name, namespaces=NS)) for name in ('MinTileCol', 'MinTileRow', 'MaxTileCol', 'MaxTileRow'))
                if zoom in limits or not 0 <= zoom <= 30 or not (0 <= vals[0] <= vals[2] < 2 ** zoom and 0 <= vals[1] <= vals[3] < 2 ** zoom):
                    raise ValueError()
                limits[zoom] = vals
            if not matrices:
                raise ValueError()
            return matrices, limits
        except ImageryProviderError:
            raise
        except Exception:
            raise ImageryProviderError('invalid_capabilities') from None

    def fetch(self, query: ImageryQuery) -> ImageryResult:
        if self.noncommercial_use is not True:
            raise ImageryProviderError('licensing_not_accepted')
        if isinstance(self.year, bool) or not isinstance(self.year, int) or not CSRSR_MIN_YEAR <= self.year <= CSRSR_MAX_YEAR:
            raise ImageryProviderError('invalid_configuration')
        bbox = _bbox(query)
        matrices, limits = self._capabilities(query)
        # Select the closest advertised resolution to output pixels, bounded by annual maximum.
        target = max(bbox[2] - bbox[0], bbox[3] - bbox[1]) / 512
        zoom = min(matrices, key=lambda z: abs(math.log2((2 * WORLD / (256 * 2 ** z)) / target)))
        span = 2 * WORLD / 2 ** zoom
        left = math.floor((bbox[0] + WORLD) / span)
        right = math.floor((bbox[2] + WORLD) / span)
        top = math.floor((WORLD - bbox[3]) / span)
        bottom = math.floor((WORLD - bbox[1]) / span)
        if (right-left+1)*(bottom-top+1) > 9:
            raise ImageryProviderError('tile_limit_exceeded')
        allowed = limits.get(zoom, (0, 0, 2 ** zoom - 1, 2 ** zoom - 1))
        if limits and zoom not in limits or left < allowed[0] or top < allowed[1] or right > allowed[2] or bottom > allowed[3]:
            raise ImageryProviderError('outside_coverage')
        mosaic = Image.new('RGB', ((right-left+1)*256, (bottom-top+1)*256))
        # Sequential fetches are intentionally below the two-concurrent-call ceiling and preserve contextvars.
        for row in range(top, bottom+1):
            for col in range(left, right+1):
                _deadline(query)
                url = f'https://data.csrsr.ncu.edu.tw/SP/wmts/SP{self.year}NC_3857/GoogleMapsCompatible/{zoom}/{col}/{row}.png'
                data, mime = self.http.get(url, deadline=query.deadline, max_bytes=1000000, mime_types={'image/png'})
                mosaic.paste(_decode(data, mime, (256, 256)), ((col-left)*256, (row-top)*256))
        crop = ((bbox[0] + WORLD - left * span) / span * 256,
                (WORLD - bbox[3] - top * span) / span * 256,
                (bbox[2] + WORLD - left * span) / span * 256,
                (WORLD - bbox[1] - top * span) / span * 256)
        image = mosaic.resize((512, 512), Image.Resampling.LANCZOS, box=crop)
        return ImageryResult(_jpeg(image, query), 'csrsr_spot', 'satellite', 'https://data.csrsr.ncu.edu.tw/SP/wmts',
            f'SP{self.year}NC_3857', 'WMTS tiles composed, cropped, resampled and reencoded JPEG',
            f'國立中央大學太空及遙測研究中心（CSRSR）SPOT {self.year}',
            ('Annual mosaic; not a single-date observation.', 'Cloud coverage and exact acquisition date are unknown.',
             'Contextual reference only; not a statutory survey or property boundary determination.'), bbox,
            vintage=str(self.year), date_precision='year',
            usage_restriction='Noncommercial competition use only; CSRSR attribution and year required.')
