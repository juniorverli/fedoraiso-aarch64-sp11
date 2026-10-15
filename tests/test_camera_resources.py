"""Synthetic, hardware-independent checks of resource decoding and CLI safety."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/decode-camera-resources.py'
SPEC = importlib.util.spec_from_file_location('camera_resources', SCRIPT)
decoder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(decoder)


def arg(kind, data=b'', padding=None):
    needed = max(4, len(data)) - len(data)
    if padding is None:
        padding = b'\0' * needed
    assert len(padding) == needed
    return struct.pack('<HH', kind, len(data)) + data + padding


def resource(*arguments):
    body = b''.join(arguments)
    return struct.pack('<4sII', b'AeoB', 12 + len(body), len(arguments)) + body


class DecodeTests(unittest.TestCase):
    def decode(self, data):
        return decoder.decode(data, 'synthetic/resource.bin')

    def reject(self, data, pattern):
        with self.assertRaisesRegex(decoder.DecodeError, pattern):
            self.decode(data)

    def test_nested_mixed_unaligned_and_byte_provenance(self):
        children = (arg(1, b'abcd\0') + arg(0, struct.pack('<Q', 0xFEDCBA9876543210))
                    + arg(2, b'\x7f', b'\xa1\xa2\xa3') + arg(2, b'', b'\xf1\xf2\xf3\xf4'))
        data = resource(arg(3, children), arg(0, struct.pack('<I', 0x87654321)))
        doc = self.decode(data)
        self.assertEqual(doc['sha256'], hashlib.sha256(data).hexdigest())
        self.assertEqual(doc['filename'], 'resource.bin')
        self.assertEqual(doc['path'], 'synthetic/resource.bin')
        self.assertEqual(doc['header']['raw_hex'], data[:12].hex())
        package, integer = doc['arguments']
        self.assertNotIn('raw_hex', package)
        self.assertEqual((package['header_offset'], package['data_offset'], package['data_length'], package['storage_length']), (12, 16, 37, 41))
        string, wide, short, empty = package['children']
        self.assertEqual((string['header_offset'], string['data_offset'], string['value'], string['trailing_nul_count']), (16, 20, 'abcd', 1))
        self.assertEqual((wide['header_offset'], wide['data_offset'], wide['data_length'], wide['value']), (25, 29, 8, 0xFEDCBA9876543210))
        self.assertIn('wider', wide['warnings'][0])
        self.assertEqual(wide['value_decimal'], '18364758544493064720')
        self.assertEqual(wide['value_hex'], '0xfedcba9876543210')
        self.assertEqual((short['header_offset'], short['raw_hex'], short['padding_offset'], short['padding_hex']), (37, '7f', 42, 'a1a2a3'))
        self.assertEqual((empty['header_offset'], empty['raw_hex'], empty['padding_hex']), (45, '', 'f1f2f3f4'))
        self.assertEqual((integer['header_offset'], integer['value']), (53, 0x87654321))
        self.assertEqual(integer['value_decimal'], '2271560481')
        self.assertEqual(integer['value_hex'], '0x87654321')
        # Every input byte has exactly one owner, including package/header padding.
        rebuilt = bytearray.fromhex(doc['header']['raw_hex'])
        def walk(node):
            rebuilt.extend(bytes.fromhex(node['header_raw_hex']))
            if node['kind'] == 'package':
                for child in node['children']:
                    walk(child)
            else:
                rebuilt.extend(bytes.fromhex(node['raw_hex']))
            rebuilt.extend(bytes.fromhex(node['padding_hex']))
        for node in doc['arguments']:
            walk(node)
        self.assertEqual(bytes(rebuilt), data)

    def test_empty_package_unknown_and_trailing_nuls(self):
        doc = self.decode(resource(arg(3, b'', b'abcd'), arg(77, b'', b'WXYZ'), arg(1, b'a\0\0')))
        package, unknown, string = doc['arguments']
        self.assertEqual(package['children'], [])
        self.assertEqual(package['padding_hex'], '61626364')
        self.assertEqual((unknown['kind'], unknown['type'], unknown['raw_hex']), ('unknown', 77, ''))
        self.assertNotIn('children', unknown)
        self.assertTrue(unknown['warnings'])
        self.assertEqual((string['value'], string['trailing_nul_count']), ('a\0', 2))
        opaque = self.decode(resource(arg(99, arg(0, b'abcd'))))['arguments'][0]
        self.assertEqual(opaque['raw_hex'], arg(0, b'abcd').hex())
        self.assertNotIn('children', opaque)

    def test_header_validation(self):
        for size in (0, 1, 11):
            with self.subTest(size=size):
                self.reject(b'X' * size, 'offset 0x0: header')
        self.reject(b'Bad!' + resource()[4:], 'offset 0x0: bad signature')
        self.reject(struct.pack('<4sII', b'AeoB', 13, 0), 'offset 0x4: declared length')
        self.reject(struct.pack('<4sII', b'AeoB', 12, 1), 'offset 0xc: argument count')
        self.reject(struct.pack('<4sII', b'AeoB', 20, 0) + arg(2), 'offset 0xc: residual')
        data = resource(arg(2))
        self.reject(data[:8] + struct.pack('<I', 2) + data[12:], 'argument count')

    def test_argument_spans_and_nested_residual(self):
        self.reject(resource(b'\0' * 7), 'offset 0xc: short argument')
        self.reject(resource(struct.pack('<HH', 2, 8) + b'1234'), 'offset 0xc: argument storage')
        self.reject(resource(arg(3, b'1234')), 'offset 0x10: short argument')
        self.reject(resource(arg(3, arg(2) + b'X')), 'offset 0x18: short argument')
        self.reject(resource(arg(3, struct.pack('<HH', 2, 9) + b'1234')), 'offset 0x10: argument storage')

    def test_integer_and_string_validation(self):
        for size in (0, 1, 2, 3, 5, 7, 9):
            with self.subTest(size=size):
                self.reject(resource(arg(0, b'x' * size)), 'offset 0xc: integer data length')
        for payload in (b'', b'abc'):
            self.reject(resource(arg(1, payload)), 'offset 0x10: string requires final NUL')
        self.reject(resource(arg(1, b'a\xff\0')), 'offset 0x11: string contains non-ASCII')

    def test_byte_depth_and_node_limits(self):
        self.reject(b'X' * (decoder.MAX_BYTES + 1), 'exceeds.*byte limit')
        nested = arg(2)
        for _ in range(decoder.MAX_DEPTH - 1):
            nested = arg(3, nested)
        self.decode(resource(nested))
        self.reject(resource(arg(3, nested)), 'nesting exceeds depth limit 32')
        self.decode(resource(*([arg(2)] * decoder.MAX_NODES)))
        self.reject(resource(*([arg(2)] * (decoder.MAX_NODES + 1))), 'node count exceeds limit 10000')


class CLITests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True, text=True)

    def test_stdout_deterministic_and_new_file(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'source'
            output = Path(directory) / 'out.json'
            source.write_bytes(resource(arg(0, struct.pack('<I', 123))))
            first = self.run_cli(source)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(first.stdout, self.run_cli(source).stdout)
            doc = json.loads(first.stdout)
            self.assertEqual(doc['schema_version'], 1)
            self.assertEqual(doc['parser_sha256'], hashlib.sha256(SCRIPT.read_bytes()).hexdigest())
            self.assertEqual(doc['documents'][0]['arguments'][0]['value'], 123)
            written = self.run_cli(source, '--output', output)
            self.assertEqual(written.returncode, 0, written.stderr)
            self.assertEqual(written.stdout, '')
            self.assertEqual(output.read_text(), first.stdout)

    def test_valid_batch_preserves_input_order(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = [Path(directory) / name for name in ('second', 'first')]
            for value, path in enumerate(paths):
                path.write_bytes(resource(arg(0, struct.pack('<I', value))))
            result = self.run_cli(*paths)
            self.assertEqual(result.returncode, 0, result.stderr)
            documents = json.loads(result.stdout)['documents']
            self.assertEqual([doc['path'] for doc in documents], list(map(str, paths)))
            self.assertEqual([doc['arguments'][0]['value'] for doc in documents], [0, 1])

    def test_batch_invalid_or_missing_input_publishes_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid, invalid, output = root / 'valid', root / 'invalid', root / 'out'
            valid.write_bytes(resource())
            invalid.write_bytes(b'invalid')
            before = valid.read_bytes(), invalid.read_bytes()
            for bad in (invalid, root / 'missing'):
                for suffix in ((), ('--output', output)):
                    result = self.run_cli(valid, bad, *suffix)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(str(bad), result.stderr)
                    self.assertEqual(result.stdout, '')
                    self.assertFalse(output.exists())
            self.assertEqual(before, (valid.read_bytes(), invalid.read_bytes()))

    def test_existing_output_and_aliases_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root / 'source', root / 'out'
            source.write_bytes(resource())
            output.write_bytes(b'keep me')
            symlink, dangling, hardlink = root / 'symlink', root / 'dangling', root / 'hardlink'
            symlink.symlink_to(source)
            dangling.symlink_to(root / 'absent')
            os.link(source, hardlink)
            before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in (source, output, symlink, hardlink)}
            for target in (output, source, root / '.' / 'source', symlink, dangling, hardlink):
                result = self.run_cli(source, '--output', target)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('refusing existing output', result.stderr)
            for path, digest in before.items():
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest)
            self.assertTrue(dangling.is_symlink())
            self.assertFalse((root / 'absent').exists())

    def test_no_implicit_directories_and_filesystem_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source'
            source.write_bytes(resource())
            output = root / 'not-created' / 'out'
            result = self.run_cli(source, '--output', output)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(output.parent.exists())
            result = self.run_cli(root)
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn('Traceback', result.stderr)

    def test_input_read_is_capped(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'oversize'
            source.write_bytes(b'X' * (decoder.MAX_BYTES + 10))
            result = self.run_cli(source)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('byte limit', result.stderr)
        # A real regular input is opened; spy on the actual source read size.
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'source'
            source.write_bytes(resource())
            requested = []
            real_fdopen = os.fdopen
            class ReadSpy:
                def __init__(self, stream):
                    self.stream = stream
                def __enter__(self):
                    return self
                def __exit__(self, *args):
                    self.stream.close()
                def read(self, size):
                    requested.append(size)
                    return self.stream.read(size)
            with patch.object(decoder.os, 'fdopen', side_effect=lambda *a: ReadSpy(real_fdopen(*a))), patch('sys.stdout'):
                self.assertEqual(decoder.main([str(source)]), 0)
            self.assertEqual(requested, [decoder.MAX_BYTES + 1])

    def test_fifo_and_device_rejected_before_open(self):
        with tempfile.TemporaryDirectory() as directory:
            fifo = Path(directory) / 'fifo'
            os.mkfifo(fifo)
            result = subprocess.run([sys.executable, str(SCRIPT), str(fifo)],
                                    capture_output=True, text=True, timeout=2)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('regular file', result.stderr)
            for path in (fifo, Path('/dev/null')):
                with patch.object(decoder.os, 'open', side_effect=AssertionError('must not open')):
                    with self.assertRaisesRegex(OSError, 'regular file'):
                        decoder.read_regular(path)

    def test_failed_write_or_publish_cleans_temporary_and_allows_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root / 'source', root / 'out'
            source.write_bytes(resource())
            original = source.read_bytes()
            real_temporary = tempfile.NamedTemporaryFile
            def fail_write(*args, **kwargs):
                stream = real_temporary(*args, **kwargs)
                actual_write = stream.write
                def partial_write(text):
                    actual_write(text[:10])
                    raise OSError('injected write failure')
                stream.write = partial_write
                return stream
            for injected in (
                patch.object(decoder.tempfile, 'NamedTemporaryFile', side_effect=fail_write),
                patch.object(decoder.os, 'link', side_effect=OSError('injected publication failure')),
            ):
                with injected, patch('sys.stderr'):
                    self.assertEqual(decoder.main([str(source), '--output', str(output)]), 1)
                self.assertFalse(output.exists())
                self.assertEqual(list(root.iterdir()), [source])
                self.assertEqual(source.read_bytes(), original)
            self.assertEqual(decoder.main([str(source), '--output', str(output)]), 0)
            self.assertEqual(json.loads(output.read_text())['documents'][0]['sha256'], hashlib.sha256(original).hexdigest())

    def test_destination_created_during_publication_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root / 'source', root / 'out'
            source.write_bytes(resource())
            real_link = os.link
            def racing_link(temporary, destination):
                destination.write_bytes(b'concurrent owner')
                return real_link(temporary, destination)
            with patch.object(decoder.os, 'link', side_effect=racing_link), patch('sys.stderr'):
                self.assertEqual(decoder.main([str(source), '--output', str(output)]), 1)
            self.assertEqual(output.read_bytes(), b'concurrent owner')
            self.assertEqual(set(root.iterdir()), {source, output})

    def test_batch_limits_fail_before_publication(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root / 'source', root / 'out'
            source.write_bytes(resource(arg(2)))
            for constant, limit, message in (
                ('MAX_BATCH_BYTES', len(source.read_bytes()), 'batch byte count'),
                ('MAX_BATCH_NODES', 1, 'batch node limit'),
                ('MAX_BATCH_FILES', 1, 'batch file count'),
            ):
                with self.subTest(constant=constant), patch.object(decoder, constant, limit), patch('sys.stderr') as errors, patch('sys.stdout') as stdout:
                    self.assertEqual(decoder.main([str(source), str(source), '--output', str(output)]), 1)
                    self.assertIn(message, errors.write.call_args_list[0].args[0])
                    stdout.write.assert_not_called()
                self.assertFalse(output.exists())
                self.assertEqual(list(root.iterdir()), [source])
            # Exactly the low aggregate limits remains valid.
            with patch.object(decoder, 'MAX_BATCH_BYTES', 2 * source.stat().st_size), patch.object(decoder, 'MAX_BATCH_NODES', 2), patch.object(decoder, 'MAX_BATCH_FILES', 2):
                self.assertEqual(decoder.main([str(source), str(source), '--output', str(output)]), 0)



if __name__ == '__main__':
    unittest.main()
