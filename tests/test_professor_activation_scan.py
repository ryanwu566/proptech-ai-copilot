"""Synthetic-only, hermetic tests: no deployment, provider or credential reads."""
import base64
import gzip
import hashlib
import io
import json
import tarfile
import unittest
from urllib.parse import quote


def tar_bytes(entries):
    result = io.BytesIO()
    with tarfile.open(fileobj=result, mode='w') as archive:
        for name, body in entries:
            info = tarfile.TarInfo(name)
            if isinstance(body, tarfile.TarInfo):
                info = body
                archive.addfile(info)
            else:
                info.size = len(body)
                archive.addfile(info, io.BytesIO(body))
    return result.getvalue()


def docker_image(layers, *, config=None, before=False):
    config = json.dumps(config or {'rootfs': {'type': 'layers', 'diff_ids': [
        'sha256:' + hashlib.sha256(layer).hexdigest() for layer in layers]}}).encode()
    config_name = hashlib.sha256(config).hexdigest() + '.json'
    manifest = json.dumps([{'Config': config_name, 'RepoTags': ['synthetic:test'],
                           'Layers': [f'{i}/layer.tar' for i in range(len(layers))]}]).encode()
    entries = [(f'{i}/layer.tar', layer) for i, layer in enumerate(layers)]
    metadata = [(config_name, config), ('manifest.json', manifest)]
    return tar_bytes(metadata + entries if before else entries + metadata)


def oci_image(layer, compression='gzip'):
    encoded = gzip.compress(layer) if compression == 'gzip' else layer
    if compression == 'zstd':
        try:
            from compression import zstd
            encoded = zstd.compress(layer)
        except ImportError:
            import zstandard
            encoded = zstandard.ZstdCompressor().compress(layer)
    blobs = []
    def descriptor(body, media):
        digest = hashlib.sha256(body).hexdigest()
        blobs.append(('blobs/sha256/' + digest, body))
        return {'mediaType': media, 'digest': 'sha256:' + digest, 'size': len(body)}
    layer_desc = descriptor(encoded, 'application/vnd.oci.image.layer.v1.tar' +
                            ('' if compression == 'none' else '+' + compression))
    config_desc = descriptor(json.dumps({'rootfs': {'type': 'layers', 'diff_ids': [
        'sha256:' + hashlib.sha256(layer).hexdigest()]}}).encode(),
        'application/vnd.oci.image.config.v1+json')
    manifest_desc = descriptor(json.dumps({'schemaVersion': 2, 'config': config_desc,
                                           'layers': [layer_desc]}).encode(),
        'application/vnd.oci.image.manifest.v1+json')
    return tar_bytes(blobs + [('oci-layout', b'{"imageLayoutVersion":"1.0.0"}'),
                             ('index.json', json.dumps({'schemaVersion': 2,
                              'manifests': [manifest_desc]}).encode())])


def mixed_image(layer, *, mismatch=False):
    with tarfile.open(fileobj=io.BytesIO(oci_image(layer))) as archive:
        entries = [(member.name, archive.extractfile(member).read()) for member in archive]
    for name, body in entries:
        if name.startswith('blobs/'):
            try:
                value = json.loads(body)
            except (ValueError, UnicodeDecodeError):
                continue
            if 'config' in value and 'layers' in value:
                config_path = 'blobs/sha256/' + value['config']['digest'][7:]
                layer_paths = ['blobs/sha256/' + item['digest'][7:] for item in value['layers']]
                break
    if mismatch:
        config = json.loads(next(body for name, body in entries if name == config_path))
        config['config'] = {'Env': ['SAFE=different']}
        body = json.dumps(config).encode()
        config_path = hashlib.sha256(body).hexdigest() + '.json'
        entries.append((config_path, body))
    entries.append(('manifest.json', json.dumps([{'Config': config_path,
                    'Layers': layer_paths, 'RepoTags': ['synthetic:test']}]).encode()))
    return tar_bytes(entries)


def attested_image(*, mixed=True, version='v1', mutate=None, secret=None, layer_secret=None):
    """OCI 1.1 BuildKit artifact; nested index mirrors Docker's containerd export."""
    layer = tar_bytes([('file', (layer_secret or 'public').encode())])
    source = mixed_image(layer) if mixed else oci_image(layer)
    with tarfile.open(fileobj=io.BytesIO(source)) as archive:
        entries = {m.name: archive.extractfile(m).read() for m in archive}
    index = json.loads(entries['index.json'])
    target = index['manifests'][0]
    def blob(value, media):
        body = json.dumps(value, separators=(',', ':')).encode()
        digest = hashlib.sha256(body).hexdigest()
        entries['blobs/sha256/' + digest] = body
        return {'mediaType': media, 'digest': 'sha256:' + digest, 'size': len(body)}
    statement = {'_type': 'https://in-toto.io/Statement/' + version,
                 'subject': [{'name': 'pkg:docker/synthetic@sha256:public',
                              'digest': {'sha256': target['digest'][7:]}}],
                 'predicateType': 'https://slsa.dev/provenance/v0.2',
                 'predicate': {'buildType': 'public'}}
    if secret:
        statement['predicate']['canary'] = secret
    empty = {'mediaType': 'application/vnd.oci.empty.v1+json',
             'digest': 'sha256:' + hashlib.sha256(b'{}').hexdigest(), 'size': 2, 'data': 'e30='}
    value = {'schemaVersion': 2, 'mediaType': 'application/vnd.oci.image.manifest.v1+json',
             'artifactType': 'application/vnd.docker.attestation.manifest.v1+json',
             'config': empty, 'subject': dict(target), 'layers': []}
    desc = {'platform': {'architecture': 'unknown', 'os': 'unknown'},
            'annotations': {'vnd.docker.reference.type': 'attestation-manifest',
                            'vnd.docker.reference.digest': target['digest']}}
    extra = {}
    if mutate:
        mutate(value, desc, statement, target, extra)
    if extra.get('unreachable_target'):
        alternate = json.loads(entries['blobs/sha256/' + target['digest'][7:]])
        alternate['annotations'] = {'test': 'not-in-image-index'}
        dangling = blob(alternate, 'application/vnd.oci.image.manifest.v1+json')
        value['subject'] = dangling
        desc['annotations']['vnd.docker.reference.digest'] = dangling['digest']
        statement['subject'][0]['digest']['sha256'] = dangling['digest'][7:]
    payload = blob(statement, 'application/vnd.in-toto+json')
    payload['annotations'] = {'in-toto.io/predicate-type': statement.get('predicateType')}
    payload.update(extra.get('payload', {}))
    value['layers'] = extra.get('layers', [payload])
    entries['blobs/sha256/' + empty['digest'][7:]] = extra.get('empty_body', b'{}')
    attestation = blob(value, 'application/vnd.oci.image.manifest.v1+json')
    attestation.update(desc)
    child = blob({'schemaVersion': 2, 'mediaType': 'application/vnd.oci.image.index.v1+json',
                  'manifests': [target, attestation]}, 'application/vnd.oci.image.index.v1+json')
    # Alias the runnable manifest after its nested reference, like modern exports.
    index['manifests'] = extra.get('manifests', [child, target])
    if extra.get('conflicting_alias'):
        index['manifests'].append({**attestation, 'annotations': {}})
    if extra.get('bad_platform_alias'):
        index['manifests'].append({**attestation, 'platform': {'architecture': 'amd64', 'os': 'linux'}})
    if extra.get('attestation_first'):
        nested = blob({'schemaVersion': 2, 'manifests': [attestation, target]},
                      'application/vnd.oci.image.index.v1+json')
        # Remove the old, now-unreferenced index blob.
        del entries['blobs/sha256/' + child['digest'][7:]]
        index['manifests'] = [nested, target]
    entries['index.json'] = json.dumps(index).encode()
    return tar_bytes(list(entries.items()))


class ScannerTests(unittest.TestCase):
    def scanner(self, values=()):
        from services.professor_activation_scan import SecretScanner
        return SecretScanner(values)

    def refused(self, callable_, *args):
        from services.professor_activation_scan import ScanRefused
        with self.assertRaises(ScanRefused) as caught:
            callable_(*args)
        self.assertRegex(caught.exception.reason_code, r'^[a-z_]+$')
        self.assertEqual(str(caught.exception), caught.exception.reason_code)
        return caught.exception

    def test_known_variants_are_redacted_and_detected(self):
        value = 'synthetic:pa ss"word\\098765'
        scanner = self.scanner([value, 'postgresql://role:synthetic%21password987@db/app'])
        for encoded in (value.encode(), json.dumps(value)[1:-1].encode(),
                        base64.b64encode(value.encode()), quote(value, safe='').encode(),
                        b'synthetic!password987'):
            self.refused(scanner.check_bytes, encoded)
        self.assertNotIn(value, repr(scanner))
        self.assertNotIn(value, repr(vars(scanner)))

    def test_stream_overlap_and_no_truncation(self):
        scanner = self.scanner(['synthetic-secret-987654321'])
        class SmallReads(io.BytesIO):
            def read(self, size=-1):
                return super().read(min(7, size) if size >= 0 else 7)
        self.refused(scanner.check_stream, SmallReads(b'a' * 200000 + b'synthetic-secret-987654321'))
        scanner.check_stream(SmallReads(b'clean payload' * 10000))

    def test_provider_and_pem_literals_but_not_regex_source(self):
        scanner = self.scanner()
        for value in (b'-----BEGIN PRIVATE KEY-----\nYWJj\n-----END PRIVATE KEY-----',
                      b'AKIA' + b'A' * 16, b'ghp_' + b'A' * 36,
                      b'AIza' + b'a' * 35):
            self.refused(scanner.check_bytes, value)
        scanner.check_bytes(rb're.compile(rb"AKIA[A-Z0-9]{16}|AIza[0-9A-Za-z_-]{35}")')
        scanner.check_bytes(rb're.compile(rb"-----BEGIN (?:RSA )?PRIVATE KEY-----")')

    def test_documented_public_examples_do_not_trigger_generic_patterns(self):
        # Exact public documentation examples from installed botocore IAM/STS.
        examples = (b'AKIA111111111EXAMPLE', b'AKIA222222222EXAMPLE', b'AKIAI44QH8DHBEXAMPLE', b'AKIAIOSFODNN7EXAMPLE')
        for example in examples:
            self.scanner().check_bytes(b'ACCESS_KEY="' + example + b'"')
            self.refused(self.scanner([example.decode()]).check_bytes, example)
            self.refused(self.scanner([example.decode()]).check_bytes,
                         base64.b64encode(example))
        self.refused(self.scanner().check_bytes, b'AKIA' + b'Q7' * 8)

    def test_provider_patterns_require_tokens_but_known_values_match_substrings(self):
        public_font_fragment = b'base64data' + b'AKIA' + b'A' * 16 + b'morebase64'
        public_module_identifier = b'dask-' + b'a' * 40
        self.scanner().check_bytes(public_font_fragment + b' ' + public_module_identifier)
        self.refused(self.scanner(['AKIA' + 'A' * 16]).check_bytes, public_font_fragment)
        for token in (b'AKIA' + b'A' * 16, b'sk-' + b'Q7' * 20):
            self.refused(self.scanner().check_bytes, b'key="' + token + b'"')

    def test_stream_overlap_does_not_invent_identifier_boundaries(self):
        # Trimming overlap must not turn the middle of a clean identifier into
        # an apparent provider-key prefix at the start of the next scan buffer.
        prefix = b'a' * (65536 - 1024 - 2)
        payload = prefix + b'dask-' + b'b' * 40 + b' '
        payload += b'a' * (65536 - len(payload))
        self.scanner().check_stream(io.BytesIO(payload))
        # End-of-chunk is not end-of-token; the next chunk supplies context.
        token = b'AKIA' + b'A' * 16
        payload = b'a' * (65536 - 1 - len(token)) + b' ' + token + b'identifier_suffix'
        self.scanner().check_stream(io.BytesIO(payload))
        self.refused(self.scanner().check_stream, io.BytesIO(b' ' + token))

    def test_large_pem_block_stream_is_not_deferred_past_header(self):
        pem = b'-----BEGIN PRIVATE KEY-----\n' + b'A' * 100000 + b'\n-----END PRIVATE KEY-----'
        self.refused(self.scanner().check_stream, io.BytesIO(pem))

    def test_docker_manifest_after_layers_and_sanitized_counts(self):
        result = self.scanner().scan_image_archive(io.BytesIO(docker_image([
            tar_bytes([('safe/file', b'hello')]), tar_bytes([('.wh.file', b'')]) ])))
        self.assertEqual(result['format'], 'docker')
        self.assertEqual(result['layers'], 2)
        self.assertEqual(result['images'], 1)
        self.assertNotIn('safe/file', json.dumps(result))
        self.assertTrue(all(isinstance(v, int) for k, v in result.items() if k != 'format'))

    def test_deleted_previous_layer_secret_is_refused(self):
        archive = docker_image([tar_bytes([('old', b'synthetic-secret-987654321')]),
                                tar_bytes([('.wh.old', b'')])])
        self.refused(self.scanner(['synthetic-secret-987654321']).scan_image_archive, io.BytesIO(archive))

    def test_config_secret_and_member_metadata_are_scanned(self):
        scanner = self.scanner(['synthetic-secret-987654321'])
        config = {'rootfs': {'type': 'layers', 'diff_ids': []},
                  'config': {'Env': ['TOKEN=synthetic-secret-987654321']}}
        self.refused(scanner.scan_image_archive, io.BytesIO(docker_image([], config=config)))
        link = tarfile.TarInfo('link')
        link.type = tarfile.SYMTYPE
        link.linkname = 'synthetic-secret-987654321'
        for layer in [tar_bytes([('synthetic-secret-987654321', b'clean')]),
                      tar_bytes([('link', link)])]:
            self.refused(scanner.scan_image_archive, io.BytesIO(docker_image([layer])))

    def test_unsafe_paths_are_refused_without_extraction(self):
        for name in ('../escape', '/absolute', 'a/../../escape'):
            self.refused(self.scanner().scan_image_archive,
                         io.BytesIO(docker_image([tar_bytes([(name, b'hello')])])))

    def test_malformed_missing_unknown_duplicate_and_truncated_archives_refused(self):
        fixtures = [b'not tar', tar_bytes([('unknown', b'payload')]),
                    tar_bytes([('manifest.json', b'[]')]),
                    tar_bytes([('manifest.json', b'[')]),
                    tar_bytes([('manifest.json', json.dumps([{'Config':'missing.json', 'Layers': ['missing/layer.tar']}]).encode())]),
                    tar_bytes([('same', b'a'), ('same', b'b')]),
                    docker_image([tar_bytes([('ok', b'hello')])])[:800]]
        for fixture in fixtures:
            self.refused(self.scanner().scan_image_archive, io.BytesIO(fixture))

    def test_oci_gzip_and_plain_layers_are_verified(self):
        for compression in ('gzip', 'none'):
            archive = oci_image(tar_bytes([('file', b'hello')]), compression)
            result = self.scanner().scan_image_archive(io.BytesIO(archive))
            self.assertEqual(result['format'], 'oci')
            self.assertEqual(result['layers'], 1)
            self.assertEqual(result['config_files'], 1)
        self.refused(self.scanner(['synthetic-secret-987654321']).scan_image_archive,
            io.BytesIO(oci_image(tar_bytes([('hidden', b'synthetic-secret-987654321')]))))

    def test_oci_zstd_is_scanned_or_explicitly_refused_when_unavailable(self):
        try:
            from compression import zstd
        except ImportError:
            try:
                import zstandard
            except ImportError:
                self.skipTest('no zstd decoder available')
        result = self.scanner().scan_image_archive(io.BytesIO(oci_image(
            tar_bytes([('file', b'hello')]), 'zstd')))
        self.assertEqual(result['layers'], 1)

    def test_blob_digest_mismatch_refused(self):
        archive = oci_image(tar_bytes([('file', b'hello')]))
        archive = archive.replace(b'hello', b'jello') if b'hello' in archive else archive.replace(b'"rootfs"', b'"rootfz"')
        self.refused(self.scanner().scan_image_archive, io.BytesIO(archive))


    def test_mixed_modern_docker_oci_contracts_must_agree(self):
        layer = tar_bytes([('file', b'hello')])
        result = self.scanner().scan_image_archive(io.BytesIO(mixed_image(layer)))
        self.assertEqual(result['format'], 'docker_oci')
        self.assertEqual(result['layers'], 1)
        self.assertEqual(result['config_files'], 1)
        self.refused(self.scanner().scan_image_archive, io.BytesIO(mixed_image(layer, mismatch=True)))

    def test_buildkit_oci_empty_config_attestation_in_mixed_and_oci_archives(self):
        for mixed in (True, False):
            for version in ('v0.1', 'v1'):
                with self.subTest(mixed=mixed, version=version):
                    result = self.scanner().scan_image_archive(io.BytesIO(
                        attested_image(mixed=mixed, version=version)))
                    self.assertEqual(result['format'], 'docker_oci' if mixed else 'oci')
                    self.assertEqual(result['images'], 1)
                    self.assertEqual(result['layers'], 1)
                    self.assertEqual(result['config_files'], 2)

    def test_attestation_order_and_optional_inline_config(self):
        def change(value, desc, statement, target, extra):
            del value['config']['data']
            extra['attestation_first'] = True
        result = self.scanner().scan_image_archive(io.BytesIO(attested_image(mutate=change)))
        self.assertEqual(result['images'], 1)

    def test_attestation_predicate_and_filesystem_credentials_are_never_skipped(self):
        secret = 'synthetic-attestation-secret-987654321'
        for params in ({'secret': secret}, {'layer_secret': secret}):
            error = self.refused(self.scanner([secret]).scan_image_archive,
                                 io.BytesIO(attested_image(**params)))
            self.assertEqual(error.reason_code, 'credential_detected')
        token = 'ghp_' + 'A' * 36
        error = self.refused(self.scanner().scan_image_archive,
                             io.BytesIO(attested_image(secret=token)))
        self.assertEqual(error.reason_code, 'credential_detected')

    def test_attestation_links_and_unknown_structures_fail_closed(self):
        def mutate(case):
            def change(value, desc, statement, target, extra):
                if case == 'missing_marker': desc['annotations'].clear()
                elif case == 'unknown_marker': desc['annotations']['vnd.docker.reference.type'] = 'unknown'
                elif case == 'wrong_target': desc['annotations']['vnd.docker.reference.digest'] = 'sha256:' + 'f' * 64
                elif case == 'wrong_subject': value['subject']['size'] += 1
                elif case == 'missing_subject': del value['subject']
                elif case == 'wrong_platform': desc['platform']['os'] = 'linux'
                elif case == 'unknown_artifact': value['artifactType'] = 'application/unknown'
                elif case == 'missing_artifact': del value['artifactType']
                elif case == 'empty_payloads': extra['layers'] = []
                elif case == 'unknown_payload': extra['payload'] = {'mediaType': 'application/unknown'}
                elif case == 'wrong_payload_size': extra['payload'] = {'size': 999999}
                elif case == 'wrong_empty_data': value['config']['data'] = 'WyJpZ25vcmVkIl0='
                elif case == 'wrong_empty_body': extra['empty_body'] = b'[]'
                elif case == 'nonempty_config':
                    body = b'{"unrecognized":true}'
                    value['config'].update(digest='sha256:' + hashlib.sha256(body).hexdigest(), size=len(body))
                    value['config'].pop('data')
                    extra['empty_body'] = body
                elif case == 'unknown_statement': statement['_type'] = 'https://in-toto.io/Statement/v999'
                elif case == 'wrong_statement_subject': statement['subject'][0]['digest']['sha256'] = 'f' * 64
                elif case == 'empty_statement_subject': statement['subject'] = []
                elif case == 'unknown_subject_digest': statement['subject'][0]['digest'] = {'sha512': 'f' * 128}
                elif case == 'invalid_predicate': statement['predicate'] = 'opaque text'
                elif case == 'invalid_predicate_type': statement['predicateType'] = 'not-a-uri'
                elif case == 'predicate_annotation_mismatch': extra['payload'] = {'annotations': {'in-toto.io/predicate-type': 'https://other.invalid'}}
                elif case == 'conflicting_alias': extra['conflicting_alias'] = True
                elif case == 'bad_platform_alias': extra['bad_platform_alias'] = True
                elif case == 'unreachable_subject': extra['unreachable_target'] = True
            return change
        cases = ('missing_marker', 'unknown_marker', 'wrong_target', 'wrong_subject',
                 'missing_subject', 'wrong_platform', 'unknown_artifact', 'missing_artifact',
                 'empty_payloads', 'unknown_payload', 'wrong_payload_size', 'wrong_empty_data',
                 'wrong_empty_body', 'nonempty_config', 'unknown_statement', 'wrong_statement_subject',
                 'empty_statement_subject', 'unknown_subject_digest', 'invalid_predicate',
                 'invalid_predicate_type', 'predicate_annotation_mismatch', 'conflicting_alias',
                 'bad_platform_alias', 'unreachable_subject')
        for case in cases:
            with self.subTest(case=case):
                self.refused(self.scanner().scan_image_archive,
                             io.BytesIO(attested_image(mutate=mutate(case))))

    def test_empty_oci_layer_is_accepted(self):
        result = self.scanner().scan_image_archive(io.BytesIO(oci_image(tar_bytes([]), 'none')))
        self.assertEqual(result['layers'], 1)
        self.assertEqual(result['layer_members'], 0)

    def test_long_pax_names_and_link_metadata_are_scanned(self):
        clean = tar_bytes([('nested/' + 'a' * 150, b'hello')])
        self.assertEqual(self.scanner().scan_image_archive(io.BytesIO(docker_image([clean])))['layers'], 1)
        dirty = tar_bytes([('a' * 120 + 'synthetic-secret-987654321', b'hello')])
        self.refused(self.scanner(['synthetic-secret-987654321']).scan_image_archive,
                     io.BytesIO(docker_image([dirty])))

    def test_nonzero_trailing_data_and_truncated_layer_refused(self):
        layer = tar_bytes([('file', b'hello')])
        for bad in (layer + b'bad trailer', layer[:1024]):
            self.refused(self.scanner().scan_image_archive, io.BytesIO(docker_image([bad])))
        image = docker_image([layer])
        self.refused(self.scanner().scan_image_archive, io.BytesIO(image + b'bad trailer'))

    def test_unreferenced_layer_and_wrong_diff_id_are_refused(self):
        layer = tar_bytes([('file', b'hello')])
        self.refused(self.scanner().scan_image_archive, io.BytesIO(docker_image([layer], config={
            'rootfs': {'type': 'layers', 'diff_ids': ['sha256:' + '0' * 64]}})))
        image = docker_image([layer])
        with tarfile.open(fileobj=io.BytesIO(image)) as old:
            entries = [(m.name, old.extractfile(m).read()) for m in old]
        entries.append(('unreferenced/layer.tar', layer))
        self.refused(self.scanner().scan_image_archive, io.BytesIO(tar_bytes(entries)))

    def test_limits_refuse_instead_of_silently_truncating(self):
        from unittest.mock import patch
        scanner = self.scanner()
        with patch('services.professor_activation_scan.MAX_ARCHIVE_BYTES', 100):
            error = self.refused(scanner.check_stream, io.BytesIO(b'a' * 101))
            self.assertEqual(error.reason_code, 'scan_limit_exceeded')
        with patch('services.professor_activation_scan.MAX_JSON_BYTES', 10):
            self.refused(scanner.scan_image_archive, io.BytesIO(docker_image([])))

    def test_pax_extension_metadata_has_aggregate_bound(self):
        from unittest.mock import patch
        layer = tar_bytes([('nested/' + str(i) + 'a' * 150, b'hello') for i in range(6)])
        with patch('services.professor_activation_scan.MAX_METADATA_BYTES', 700):
            error = self.refused(self.scanner().scan_image_archive, io.BytesIO(docker_image([layer])))
        self.assertEqual(error.reason_code, 'scan_limit_exceeded')

    def test_secret_variant_storage_has_aggregate_bound(self):
        from unittest.mock import patch
        from services.professor_activation_scan import SecretScanner
        with patch('services.professor_activation_scan.MAX_SECRET_VARIANT_BYTES', 100, create=True):
            error = self.refused(SecretScanner, ['synthetic-secret-987654321', 'another-synthetic-value-1234'])
        self.assertEqual(error.reason_code, 'scan_limit_exceeded')

    def test_stream_failure_is_sanitized_without_exception_context(self):
        class Broken:
            def read(self, size=-1):
                raise ValueError('synthetic-sensitive-error-text')
        for method in (self.scanner().check_stream, self.scanner().scan_image_archive):
            error = self.refused(method, Broken())
            self.assertIsNone(error.__context__)
            self.assertNotIn('synthetic-sensitive', repr(error))

    def test_json_duplicate_keys_and_unknown_layer_media_refused(self):
        self.refused(self.scanner().scan_image_archive,
                     io.BytesIO(tar_bytes([('manifest.json', b'{"key":1,"key":2}') ])))
        image = oci_image(tar_bytes([('file', b'hello')]))
        with tarfile.open(fileobj=io.BytesIO(image)) as old:
            entries = [(m.name, old.extractfile(m).read()) for m in old]
        # Rebuild hashes after changing declared layer type so a valid digest does
        # not hide the unsupported media declaration behind a mismatch refusal.
        for i, (name, body) in enumerate(entries):
            if b'"layers"' in body and b'mediaType' in body:
                manifest = json.loads(body)
                manifest['layers'][0]['mediaType'] = 'application/unsupported'
                new_body = json.dumps(manifest).encode()
                new_digest = hashlib.sha256(new_body).hexdigest()
                entries[i] = ('blobs/sha256/' + new_digest, new_body)
                for j, (index_name, index_body) in enumerate(entries):
                    if index_name == 'index.json':
                        index = json.loads(index_body)
                        index['manifests'][0].update(digest='sha256:' + new_digest, size=len(new_body))
                        entries[j] = (index_name, json.dumps(index).encode())
                break
        error = self.refused(self.scanner().scan_image_archive, io.BytesIO(tar_bytes(entries)))
        self.assertEqual(error.reason_code, 'archive_unsupported')


if __name__ == '__main__':
    unittest.main()
