"""Offline, streaming credential gate for Docker-save and OCI image archives.

SecretScanner(values) accepts caller-provided strings only; it performs no file,
network, environment or Docker access. check_bytes/check_stream raise ScanRefused
on a known credential variant or literal provider/private-key material.
scan_image_archive consumes a binary stream once, never extracts, and returns
only format/counts. It scans every retained layer, including whiteouted history,
and checks referenced configs, SHA-256 blobs and config rootfs diff_ids.

Limits below fail explicitly; no scan is truncated. Metadata and reference tables
are bounded. gzip and zstd layers stream through decompression; zstd needs Python
3.14 compression.zstd or the optional zstandard package. Unsupported archive,
media/digest formats, sparse members and incomplete references fail closed.
Exceptions and repr never include input contents, names, or hashes.
"""
from __future__ import annotations

import base64
import gzip
import hashlib
import json
import re
import tarfile
from urllib.parse import quote, unquote, urlsplit

CHUNK_SIZE = 65536
MAX_ARCHIVE_BYTES = 64 * 1024**3
MAX_LAYER_BYTES = 32 * 1024**3
MAX_METADATA_BYTES = 32 * 1024**2
MAX_JSON_BYTES = 2 * 1024**2
MAX_MEMBERS = 500_000
MAX_RECORDS = 20_000
MAX_SECRET_BYTES = 65536
MAX_SECRET_VALUES = 1024
MAX_SECRET_VARIANT_BYTES = 8 * 1024**2

_REASON_CODES = frozenset({'credential_detected', 'scan_input_invalid', 'scan_limit_exceeded',
    'archive_invalid', 'archive_unsupported', 'archive_reference_invalid', 'archive_digest_mismatch',
    'archive_path_unsafe', 'archive_decode_failed'})


class ScanRefused(Exception):
    """A fixed, sanitized reason_code is the complete public error payload."""
    def __init__(self, reason_code):
        self.reason_code = reason_code if reason_code in _REASON_CODES else 'scan_input_invalid'
        super().__init__(self.reason_code)


class _Secrets:
    def __init__(self, values):
        self.values = tuple(values)
    def __repr__(self):
        return '<credential variants redacted>'


# Exact non-secret AWS documentation examples in public botocore IAM/STS
# examples-1.json. These exceptions NEVER apply to caller-supplied known values.
_PUBLIC_EXAMPLE_KEYS = frozenset((b'AKIA111111111EXAMPLE', b'AKIA222222222EXAMPLE', b'AKIAI44QH8DHBEXAMPLE', b'AKIAIOSFODNN7EXAMPLE'))

# Require token boundaries to avoid matching substrings of identifiers, prose or
# embedded font/base64 data. Literal PEM blocks use their own delimiter syntax.
# Regex source text does not match these patterns itself.
_PATTERNS = tuple(re.compile(value if index == 0 else
    rb'(?<![A-Za-z0-9_-])(?:' + value + rb')(?![A-Za-z0-9_-])')
    for index, value in enumerate((
    rb'-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----[\r\n]+[A-Za-z0-9+/=\r\n]{4,}',
    rb'AKIA[A-Z0-9]{16}', rb'ASIA[A-Z0-9]{16}',
    rb'AIza[0-9A-Za-z_-]{35}', rb'gh[pousr]_[A-Za-z0-9]{36}',
    rb'github_pat_[A-Za-z0-9_]{60,255}',
    rb'sk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{32,255}',
    rb'xox[baprs]-[A-Za-z0-9-]{20,255}',
)))


class SecretScanner:
    def __init__(self, values):
        variants = set()
        try:
            for count, value in enumerate(values):
                if count >= MAX_SECRET_VALUES or not isinstance(value, str) or not value:
                    raise ScanRefused('scan_input_invalid')
                if len(value.encode('utf-8')) > MAX_SECRET_BYTES:
                    raise ScanRefused('scan_limit_exceeded')
                roots = {value, unquote(value)}
                parsed = urlsplit(value)
                if parsed.password:
                    roots.update((parsed.password, unquote(parsed.password)))
                for root in roots:
                    encoded = root.encode('utf-8')
                    variants.update((encoded, quote(root, safe='').encode(),
                        json.dumps(root, ensure_ascii=True)[1:-1].encode(),
                        json.dumps(root, ensure_ascii=False)[1:-1].encode(),
                        base64.b64encode(encoded), base64.urlsafe_b64encode(encoded),
                        base64.b64encode(encoded).rstrip(b'='),
                        base64.urlsafe_b64encode(encoded).rstrip(b'=')))
                if sum(map(len, variants)) > MAX_SECRET_VARIANT_BYTES:
                    raise ScanRefused('scan_limit_exceeded')
        except ScanRefused:
            raise
        except Exception:
            pass
        else:
            self._secrets = _Secrets(variants)
            self._overlap = max([1024] + [len(v) for v in variants])
            return
        raise ScanRefused('scan_input_invalid')

    def __repr__(self):
        return '<SecretScanner credentials redacted>'

    def check_bytes(self, data: bytes) -> None:
        self._check_bytes(data, at_start=True, at_end=True)

    def _check_bytes(self, data, *, at_start, at_end):
        if not isinstance(data, bytes):
            raise ScanRefused('scan_input_invalid')
        # Known installed credentials take precedence over every public-example
        # exception and boundary rule, including encoded variants and substrings.
        if any(value in data for value in self._secrets.values):
            raise ScanRefused('credential_detected')
        if any(match.group() not in _PUBLIC_EXAMPLE_KEYS
               for index, pattern in enumerate(_PATTERNS) for match in pattern.finditer(data)
               if index == 0 or ((at_start or match.start() > 0) and
                                  (at_end or match.end() < len(data)))):
            raise ScanRefused('credential_detected')

    def check_stream(self, stream) -> None:
        """Scan to EOF with overlap; an explicit byte limit refuses, never passes."""
        try:
            reader = _Checked(stream, self, MAX_ARCHIVE_BYTES)
            while reader.read(CHUNK_SIZE):
                pass
            return
        except ScanRefused:
            raise
        except Exception:
            pass
        raise ScanRefused('scan_input_invalid')

    def scan_image_archive(self, stream) -> dict:
        try:
            return self._scan_image_archive(stream)
        except ScanRefused:
            raise
        except Exception:
            pass
        raise ScanRefused('archive_decode_failed')

    def _scan_image_archive(self, stream):
        records = {}
        metadata_bytes = 0
        layer_members = 0
        decoded_bytes = 0
        archive_members = 0
        reader = _Checked(stream, self, MAX_ARCHIVE_BYTES)
        for name, info, body in _tar(reader, self):
            archive_members += 1
            if archive_members > MAX_RECORDS:
                raise ScanRefused('scan_limit_exceeded')
            if info.isdir():
                continue
            if not info.isfile() or name in records:
                raise ScanRefused('archive_invalid')
            raw = _Checked(body, self, MAX_LAYER_BYTES)
            prefix = _read_exact(raw, min(512, info.size))
            prefixed = _Prefixed(prefix, raw)
            is_blob = bool(re.fullmatch(r'blobs/sha256/[0-9a-f]{64}', name))
            compressed = prefix.startswith((b'\x1f\x8b', b'\x28\xb5\x2f\xfd'))
            is_layer = name.endswith('/layer.tar') or compressed or (is_blob and (_tar_header(prefix) or (len(prefix) == 512 and not any(prefix))))
            record = {'size': info.size}
            if is_layer:
                decoded, encoding = _decode(prefixed, prefix)
                checked = _Checked(decoded, self, MAX_LAYER_BYTES)
                count = 0
                for _, _, member_body in _tar(checked, self):
                    count += 1
                    _drain(member_body)
                # Ensure decompressor validates footer/trailing data too.
                _drain(checked)
                _drain(prefixed)
                decoded_bytes += checked.total
                if decoded_bytes > MAX_ARCHIVE_BYTES:
                    raise ScanRefused('scan_limit_exceeded')
                record.update(kind='layer', encoding=encoding, diff=checked.digest.hexdigest())
                layer_members += count
            else:
                if info.size > MAX_JSON_BYTES:
                    raise ScanRefused('scan_limit_exceeded')
                data = _read_all(prefixed)
                metadata_bytes += len(data)
                if metadata_bytes > MAX_METADATA_BYTES:
                    raise ScanRefused('scan_limit_exceeded')
                # Docker legacy repositories/VERSION metadata is scanned but not JSON-required.
                if name == 'repositories' or name.endswith('/VERSION'):
                    record.update(kind='aux')
                else:
                    record.update(kind='json', json=_json(data))
            record['digest'] = raw.digest.hexdigest()
            if is_blob and record['digest'] != name.rsplit('/', 1)[1]:
                raise ScanRefused('archive_digest_mismatch')
            records[name] = record
        if 'manifest.json' in records and 'index.json' not in records:
            images, configs, layers, _ = _docker(records)
            format_name = 'docker'
        elif 'index.json' in records and 'oci-layout' in records and 'manifest.json' not in records:
            images, configs, layers, _ = _oci(records)
            format_name = 'oci'
        elif {'manifest.json', 'index.json', 'oci-layout'} <= records.keys():
            docker_count, docker_configs, docker_layers, docker_contracts = _docker(records, mixed=True)
            images, configs, layers, oci_contracts = _oci(records)
            if docker_contracts != oci_contracts:
                raise ScanRefused('archive_reference_invalid')
            configs |= docker_configs
            layers |= docker_layers
            format_name = 'docker_oci'
        else:
            raise ScanRefused('archive_unsupported')
        inspected = {name for name, record in records.items() if record['kind'] == 'layer'}
        if inspected != layers:
            raise ScanRefused('archive_reference_invalid')
        return {'format': format_name, 'images': images, 'layers': len(layers),
                'config_files': len(configs), 'layer_members': layer_members,
                'archive_members': archive_members}


class _Checked:
    def __init__(self, stream, scanner, limit):
        self.stream, self.scanner, self.limit = stream, scanner, limit
        self.total, self.tail = 0, b''
        self.digest = hashlib.sha256()
    def read(self, size=CHUNK_SIZE):
        data = self.stream.read(min(size, CHUNK_SIZE) if size >= 0 else CHUNK_SIZE)
        if not isinstance(data, bytes):
            raise ScanRefused('scan_input_invalid')
        previous_total = self.total
        self.total += len(data)
        if self.total > self.limit:
            raise ScanRefused('scan_limit_exceeded')
        # Keep real context around token matches. A rolling-buffer boundary is
        # neither a token boundary nor EOF; the next read resolves its suffix.
        self.scanner._check_bytes(self.tail + data,
            at_start=previous_total == len(self.tail), at_end=not data)
        self.tail = (self.tail + data)[-self.scanner._overlap:]
        self.digest.update(data)
        return data


class _Limited:
    def __init__(self, stream, size):
        self.stream, self.left = stream, size
    def read(self, size=CHUNK_SIZE):
        if not self.left:
            return b''
        data = self.stream.read(min(self.left, size if size >= 0 else CHUNK_SIZE))
        if not data:
            raise ScanRefused('archive_invalid')
        self.left -= len(data)
        return data


class _Prefixed:
    def __init__(self, prefix, stream):
        self.prefix, self.stream = prefix, stream
    def read(self, size=CHUNK_SIZE):
        if size < 0:
            size = CHUNK_SIZE
        if self.prefix:
            data, self.prefix = self.prefix[:size], self.prefix[size:]
            return data
        return self.stream.read(size)


def _read_exact(stream, size):
    result = bytearray()
    while len(result) < size:
        piece = stream.read(size - len(result))
        if not piece:
            raise ScanRefused('archive_invalid')
        result.extend(piece)
    return bytes(result)


def _read_all(stream):
    result = bytearray()
    while data := stream.read(CHUNK_SIZE):
        result.extend(data)
        if len(result) > MAX_JSON_BYTES:
            raise ScanRefused('scan_limit_exceeded')
    return bytes(result)


def _drain(stream):
    while stream.read(CHUNK_SIZE):
        pass


def _path(name):
    if not name or name.startswith('/') or '\\' in name or '..' in name.split('/'):
        raise ScanRefused('archive_path_unsafe')
    while name.startswith('./'):
        name = name[2:]
    return name.rstrip('/') or '.'


def _tar_header(data):
    if len(data) != 512 or not any(data):
        return False
    try:
        tarfile.TarInfo.frombuf(data, 'utf-8', 'surrogateescape')
        return True
    except Exception:
        return False


def _pax(data):
    result = {}
    pos = 0
    while pos < len(data):
        space = data.find(b' ', pos)
        if space < 0:
            raise ScanRefused('archive_invalid')
        length = int(data[pos:space])
        if length <= space - pos + 1 or pos + length > len(data):
            raise ScanRefused('archive_invalid')
        value = data[space + 1:pos + length]
        if not value.endswith(b'\n') or b'=' not in value:
            raise ScanRefused('archive_invalid')
        key, value = value[:-1].split(b'=', 1)
        key = key.decode('utf-8')
        if 'sparse' in key.lower():
            raise ScanRefused('archive_unsupported')
        result[key] = value.decode('utf-8')
        pos += length
    return result


def _tar(stream, scanner):
    pending, global_pax = {}, {}
    count = 0
    extension_bytes = 0
    while True:
        header = _read_exact(stream, 512)
        if not any(header):
            if any(_read_exact(stream, 512)) or pending:
                raise ScanRefused('archive_invalid')
            while data := stream.read(CHUNK_SIZE):
                if any(data):
                    raise ScanRefused('archive_invalid')
            return
        info = tarfile.TarInfo.frombuf(header, 'utf-8', 'surrogateescape')
        count += 1
        if count > MAX_MEMBERS or info.size < 0 or info.size > MAX_LAYER_BYTES:
            raise ScanRefused('scan_limit_exceeded')
        if info.type in (tarfile.XHDTYPE, tarfile.XGLTYPE, tarfile.GNUTYPE_LONGNAME, tarfile.GNUTYPE_LONGLINK):
            extension_bytes += info.size
            if info.size > MAX_JSON_BYTES or extension_bytes > MAX_METADATA_BYTES:
                raise ScanRefused('scan_limit_exceeded')
            data = _read_exact(stream, info.size)
            _read_exact(stream, (-info.size) % 512)
            if info.type == tarfile.XGLTYPE:
                global_pax.update(_pax(data))
            elif info.type == tarfile.XHDTYPE:
                pending.update(_pax(data))
            else:
                pending['path' if info.type == tarfile.GNUTYPE_LONGNAME else 'linkpath'] = data.rstrip(b'\0').decode('utf-8')
            continue
        pax = {**global_pax, **pending}
        pending = {}
        info.name = pax.get('path', info.name)
        info.linkname = pax.get('linkpath', info.linkname)
        if 'size' in pax:
            info.size = int(pax['size'])
        if info.size < 0 or info.size > MAX_LAYER_BYTES:
            raise ScanRefused('scan_limit_exceeded')
        if info.type not in (tarfile.REGTYPE, tarfile.AREGTYPE, tarfile.DIRTYPE, tarfile.SYMTYPE,
                             tarfile.LNKTYPE, tarfile.CHRTYPE, tarfile.BLKTYPE, tarfile.FIFOTYPE):
            raise ScanRefused('archive_unsupported')
        if not info.isfile() and info.size:
            raise ScanRefused('archive_invalid')
        scanner.check_bytes(info.name.encode('utf-8', 'surrogateescape'))
        scanner.check_bytes(info.linkname.encode('utf-8', 'surrogateescape'))
        name = _path(info.name)
        body = _Limited(stream, info.size)
        yield name, info, body
        _drain(body)
        _read_exact(stream, (-info.size) % 512)


def _decode(stream, prefix):
    if prefix.startswith(b'\x1f\x8b'):
        return gzip.GzipFile(fileobj=stream, mode='rb'), 'gzip'
    if prefix.startswith(b'\x28\xb5\x2f\xfd'):
        try:
            from compression import zstd
            return zstd.ZstdFile(stream, mode='rb'), 'zstd'
        except ImportError:
            try:
                import zstandard
                return zstandard.ZstdDecompressor().stream_reader(stream, read_across_frames=True), 'zstd'
            except ImportError:
                raise ScanRefused('archive_unsupported') from None
    return stream, 'none'


def _json(data):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ScanRefused('archive_invalid')
            result[key] = value
        return result
    return json.loads(data, object_pairs_hook=unique)


def _config(record, layers, records):
    if record['kind'] != 'json':
        raise ScanRefused('archive_reference_invalid')
    config = record['json']
    rootfs = config['rootfs']
    if rootfs['type'] != 'layers' or len(rootfs['diff_ids']) != len(layers):
        raise ScanRefused('archive_reference_invalid')
    for digest, name in zip(rootfs['diff_ids'], layers):
        if digest != 'sha256:' + records[name]['diff']:
            raise ScanRefused('archive_digest_mismatch')


def _docker(records, mixed=False):
    manifest = records['manifest.json']['json']
    if not isinstance(manifest, list) or not manifest:
        raise ScanRefused('archive_reference_invalid')
    configs, layers, contracts = set(), set(), set()
    for image in manifest:
        config_name = _path(image['Config'])
        names = [_path(name) for name in image['Layers']]
        record = records[config_name]
        classic_name = re.fullmatch(r'[0-9a-f]{64}\.json', config_name)
        blob_name = mixed and re.fullmatch(r'blobs/sha256/[0-9a-f]{64}', config_name)
        expected_digest = config_name[:-5] if classic_name else config_name.rsplit('/', 1)[-1]
        if not (classic_name or blob_name) or record['digest'] != expected_digest:
            raise ScanRefused('archive_digest_mismatch')
        if any(records[name]['kind'] != 'layer' or (not mixed and records[name]['encoding'] != 'none') for name in names):
            raise ScanRefused('archive_reference_invalid')
        _config(record, names, records)
        configs.add(config_name)
        layers.update(names)
        contracts.add((record['digest'], tuple(records[name]['diff'] for name in names)))
    return len(manifest), configs, layers, contracts


_OCI_MANIFEST = {'application/vnd.oci.image.manifest.v1+json',
                 'application/vnd.docker.distribution.manifest.v2+json'}
_OCI_INDEX = {'application/vnd.oci.image.index.v1+json',
              'application/vnd.docker.distribution.manifest.list.v2+json'}
_OCI_CONFIG = {'application/vnd.oci.image.config.v1+json',
               'application/vnd.docker.container.image.v1+json'}
_ATTESTATION = 'application/vnd.docker.attestation.manifest.v1+json'
_EMPTY_CONFIG = 'application/vnd.oci.empty.v1+json'
_IN_TOTO = 'application/vnd.in-toto+json'
_EMPTY_DIGEST = 'sha256:' + hashlib.sha256(b'{}').hexdigest()
_LAYER_MEDIA = {
    'application/vnd.oci.image.layer.v1.tar': 'none',
    'application/vnd.oci.image.layer.v1.tar+gzip': 'gzip',
    'application/vnd.oci.image.layer.v1.tar+zstd': 'zstd',
    'application/vnd.docker.image.rootfs.diff.tar': 'none',
    'application/vnd.docker.image.rootfs.diff.tar.gzip': 'gzip',
}


def _oci(records):
    if records['oci-layout']['json'] != {'imageLayoutVersion': '1.0.0'}:
        raise ScanRefused('archive_unsupported')
    configs, layers, visiting, visited, contracts = set(), set(), set(), set(), set()
    roles, runnable, attestations = {}, {}, []
    images = 0
    def descriptor(desc, media):
        digest = desc['digest']
        if desc['mediaType'] not in media or not re.fullmatch(r'sha256:[0-9a-f]{64}', digest):
            raise ScanRefused('archive_unsupported')
        path = 'blobs/sha256/' + digest[7:]
        record = records[path]
        if type(desc['size']) is not int or desc['size'] != record['size']:
            raise ScanRefused('archive_reference_invalid')
        if 'data' in desc:
            embedded = base64.b64decode(desc['data'], validate=True)
            if len(embedded) != record['size'] or hashlib.sha256(embedded).hexdigest() != record['digest']:
                raise ScanRefused('archive_digest_mismatch')
        return path, record
    def index(value, depth=0):
        if depth > 16 or value['schemaVersion'] != 2 or not value['manifests'] or 'artifactType' in value or 'subject' in value:
            raise ScanRefused('archive_reference_invalid')
        for desc in value['manifests']:
            path, record = descriptor(desc, _OCI_INDEX | _OCI_MANIFEST)
            annotations = desc.get('annotations', {})
            marker = annotations.get('vnd.docker.reference.type')
            target = annotations.get('vnd.docker.reference.digest')
            if marker is not None and marker != 'attestation-manifest':
                raise ScanRefused('archive_unsupported')
            if (marker is None) != (target is None):
                raise ScanRefused('archive_reference_invalid')
            if marker is not None and desc.get('platform') != {'architecture': 'unknown', 'os': 'unknown'}:
                raise ScanRefused('archive_reference_invalid')
            if 'artifactType' in desc and desc['artifactType'] != (_ATTESTATION if marker else None):
                raise ScanRefused('archive_unsupported')
            role = (desc['mediaType'], marker, target)
            if path in roles and roles[path] != role:
                raise ScanRefused('archive_reference_invalid')
            roles[path] = role
            if path in visiting:
                raise ScanRefused('archive_reference_invalid')
            if path in visited:
                continue
            if record['kind'] != 'json':
                raise ScanRefused('archive_reference_invalid')
            if record['json'].get('mediaType', desc['mediaType']) != desc['mediaType']:
                raise ScanRefused('archive_reference_invalid')
            visiting.add(path)
            if desc['mediaType'] in _OCI_INDEX:
                if marker is not None:
                    raise ScanRefused('archive_reference_invalid')
                index(record['json'], depth + 1)
            elif marker == 'attestation-manifest':
                attestation(record['json'], desc)
            else:
                manifest(record['json'])
                runnable[desc['digest']] = record['json']
            visiting.remove(path)
            visited.add(path)
    def manifest(value):
        nonlocal images
        if value['schemaVersion'] != 2 or 'artifactType' in value or 'subject' in value:
            raise ScanRefused('archive_reference_invalid')
        config_name, config_record = descriptor(value['config'], _OCI_CONFIG)
        names = []
        for desc in value['layers']:
            name, record = descriptor(desc, _LAYER_MEDIA)
            if record['kind'] != 'layer' or record['encoding'] != _LAYER_MEDIA[desc['mediaType']]:
                raise ScanRefused('archive_reference_invalid')
            names.append(name)
        _config(config_record, names, records)
        configs.add(config_name)
        layers.update(names)
        contracts.add((config_record['digest'], tuple(records[name]['diff'] for name in names)))
        images += 1

    def attestation(value, desc):
        # Only the documented OCI 1.1 BuildKit artifact is supported. This is
        # metadata, never a runnable rootfs or an exemption from byte scanning.
        if (desc['mediaType'] != 'application/vnd.oci.image.manifest.v1+json'
                or value['schemaVersion'] != 2 or value.get('artifactType') != _ATTESTATION):
            raise ScanRefused('archive_unsupported')
        if desc.get('platform') != {'architecture': 'unknown', 'os': 'unknown'}:
            raise ScanRefused('archive_reference_invalid')
        if 'artifactType' in desc and desc['artifactType'] != _ATTESTATION:
            raise ScanRefused('archive_reference_invalid')
        config_name, config = descriptor(value['config'], {_EMPTY_CONFIG})
        if (value['config']['digest'] != _EMPTY_DIGEST or config['size'] != 2
                or config['kind'] != 'json' or config['json'] != {}):
            raise ScanRefused('archive_reference_invalid')
        subject = value['subject']
        target, target_record = descriptor(subject, {'application/vnd.oci.image.manifest.v1+json'})
        if subject['digest'] != desc['annotations']['vnd.docker.reference.digest']:
            raise ScanRefused('archive_reference_invalid')
        if target_record['kind'] != 'json' or not isinstance(value['layers'], list) or not value['layers']:
            raise ScanRefused('archive_reference_invalid')
        payloads = []
        for payload in value['layers']:
            _, record = descriptor(payload, {_IN_TOTO})
            if record['kind'] != 'json':
                raise ScanRefused('archive_reference_invalid')
            statement = record['json']
            if statement['_type'] not in {'https://in-toto.io/Statement/v0.1', 'https://in-toto.io/Statement/v1'}:
                raise ScanRefused('archive_unsupported')
            if (set(statement) != {'_type', 'subject', 'predicateType', 'predicate'}
                    or not isinstance(statement['predicate'], dict)
                    or not isinstance(statement['subject'], list) or not statement['subject']):
                raise ScanRefused('archive_reference_invalid')
            uri = urlsplit(statement['predicateType'])
            if uri.scheme not in {'http', 'https'} or not uri.netloc or uri.username or uri.password:
                raise ScanRefused('archive_reference_invalid')
            predicate_annotation = payload.get('annotations', {}).get('in-toto.io/predicate-type')
            if predicate_annotation is not None and predicate_annotation != statement['predicateType']:
                raise ScanRefused('archive_reference_invalid')
            payloads.append(statement)
        configs.add(config_name)
        attestations.append((subject['digest'], payloads))

    index(records['index.json']['json'])
    if not images:
        raise ScanRefused('archive_reference_invalid')
    # Resolve after traversal so index order and repeated image aliases cannot
    # change linkage. An attestation may only describe a reachable runnable image
    # or one of its digest-bound config/layer objects, never another artifact.
    for target, statements in attestations:
        if target not in runnable:
            raise ScanRefused('archive_reference_invalid')
        image = runnable[target]
        allowed = {target[7:], image['config']['digest'][7:]}
        for layer in image['layers']:
            name, record = descriptor(layer, _LAYER_MEDIA)
            allowed.update((record['digest'], record['diff']))
        for statement in statements:
            for subject in statement['subject']:
                if (not isinstance(subject['name'], str) or not subject['name']
                        or set(subject['digest']) != {'sha256'}
                        or subject['digest']['sha256'] not in allowed):
                    raise ScanRefused('archive_reference_invalid')
    return images, configs, layers, contracts
