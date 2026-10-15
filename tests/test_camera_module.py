import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import struct
import tempfile
import unittest
from unittest.mock import patch
import zlib

SPEC = importlib.util.spec_from_file_location('camera_module', Path(__file__).resolve().parents[1] / 'scripts/decode-camera-module.py')
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def fixture(payloads=None):
    payloads = payloads if payloads is not None else [struct.pack('<10I', 1, 2, 0x136, 1, 3, 2, 1, 0, 1, 4),
                struct.pack('<H', 0xa0), struct.pack('<I', 0x13),
                struct.pack('<I', 25), struct.pack('<III', 8, 1, 2)]
    names = ['regSetting', 'slaveAddr', 'registerData', 'delayUs', 'powerSetting']
    header = bytearray(204)
    header[:28] = b'QTI Chromatix Header'.ljust(28, b'\0')
    struct.pack_into('<II', header, 32, 3, 1)
    struct.pack_into('<II', header, 160, 168, 3)
    symbols = bytearray()
    offset = 0
    for ident, (name, payload) in enumerate(zip(names, payloads), 1):
        symbols += struct.pack('<I32s5I', ident, name.encode(), 0, 0, 0xffffffff, offset, len(payload))
        offset += len(payload)
    struct.pack_into('<III', header, 168, 0, len(header), len(symbols))
    struct.pack_into('<III', header, 180, 1, len(header) + len(symbols), offset)
    struct.pack_into('<III', header, 192, 2, len(header) + len(symbols) + offset, 4)
    data = header + symbols + b''.join(payloads) + b'END!'
    struct.pack_into('<I', data, 28, len(data))
    return with_crc(data)


def with_crc(data):
    return bytes(data) + struct.pack('<I', zlib.crc32(data))


def mutate(data, offset, value):
    raw = bytearray(data[:-4])
    struct.pack_into('<I', raw, offset, value)
    return with_crc(raw)


class ModuleTests(unittest.TestCase):
    def test_register_reference_values_and_byte_provenance(self):
        data = fixture()
        result = module.decode(data)
        row = result['register_sets'][0]['rows'][0]
        self.assertEqual((row['register'], row['data'], row['slave_address'], row['delay_raw']),
                         (0x136, [0x13], [0xa0], [25]))
        self.assertEqual(result['power_sets'][0]['rows'], [[8, 1, 2]])
        self.assertEqual(result['source_sha256'], hashlib.sha256(data).hexdigest())
        for symbol in result['symbols']:
            payload = data[symbol['file_offset']:symbol['file_offset'] + symbol['bytes']]
            self.assertEqual(payload.hex(), symbol['payload_hex'])
            self.assertEqual(hashlib.sha256(payload).hexdigest(), symbol['sha256'])
        self.assertEqual(row['file_offset'], result['sections'][1]['offset'])

    def test_corruption_and_size_rejected(self):
        good = fixture()
        cases = [good[:-1], good + b'x', b'not a module',
                 good[:300] + bytes([good[300] ^ 1]) + good[301:],
                 mutate(good, 32, 4)]
        for data in cases:
            with self.subTest(length=len(data)), self.assertRaises(module.FormatError):
                module.decode(data)
        with patch.object(module, 'MAX_BYTES', len(good) - 1):
            with self.assertRaises(module.FormatError):
                module.decode(good)

    def test_sections_symbols_and_reference_bounds(self):
        good = fixture()
        data_start = struct.unpack_from('<I', good, 184)[0]
        cases = [mutate(good, 160, 0), mutate(good, 164, 100),
                 mutate(good, 184, 204),  # data overlaps symbol table
                 mutate(good, 180, 0),  # duplicate section ID
                 mutate(good, 176, 1),  # partial symbol
                 mutate(good, 204 + 48, 0xffffffff),  # payload offset
                 mutate(good, 204 + 56, 1)]  # duplicate symbol ID
        for i, data in enumerate(cases):
            with self.subTest(case=i), self.assertRaises(module.FormatError):
                module.decode(data)
        with patch.object(module, 'MAX_PAYLOAD_TOTAL', 1):
            with self.assertRaises(module.FormatError):
                module.decode(good)
        with patch.object(module, 'MAX_SYMBOLS', 1):
            with self.assertRaises(module.FormatError):
                module.decode(good)

    def test_unknown_candidate_preserves_validated_raw_container(self):
        good = fixture()
        start = struct.unpack_from('<I', good, 184)[0]
        for changed in [mutate(good, start + 16, 9999),
                        mutate(good, start + 12, 2), mutate(good, start, 9)]:
            report = module.decode(changed)
            self.assertEqual(report['register_sets'][0]['rows'][0]['status'], 'interpretation-error')
            symbol = report['symbols'][0]
            self.assertEqual(bytes.fromhex(symbol['payload_hex']), changed[start:start + 40])
        report = module.decode(fixture([b'unknown-reg', b'', b'', b'', b'unknown-power']))
        self.assertEqual(report['register_sets'][0]['status'], 'unsupported-record-size')
        self.assertEqual(report['power_sets'][0]['status'], 'unsupported-record-size')
        self.assertEqual(bytes.fromhex(report['symbols'][0]['payload_hex']), b'unknown-reg')
        self.assertEqual(bytes.fromhex(report['symbols'][4]['payload_hex']), b'unknown-power')

    def test_optional_fields_shared_references_and_expansion_budget(self):
        row = struct.pack('<10I', 0, 2, 0x136, 2, 3, 2, 1, 0, 0, 4)
        data = fixture([row * 3, b'', struct.pack('<II', 3, 4), b'', b''])
        report = module.decode(data)
        rows = report['register_sets'][0]['rows']
        self.assertEqual([r['data'] for r in rows], [[3, 4]] * 3)
        self.assertEqual(rows[0]['slave_address'], [])
        self.assertEqual(rows[0]['delay_raw'], [])
        self.assertEqual(rows[1]['file_offset'] - rows[0]['file_offset'], 40)
        with patch.object(module, 'MAX_EXPANDED_BYTES', 8):
            report = module.decode(data)
        rows = report['register_sets'][0]['rows']
        self.assertEqual(rows[0]['data'], [3, 4])
        self.assertIn('budget', rows[1]['error'])
        self.assertIn('budget', rows[2]['error'])

    def test_private_output_no_overwrite_or_partial_on_bad_input(self):
        with tempfile.TemporaryDirectory() as folder:
            source, output = Path(folder) / 'module.bin', Path(folder) / 'report.json'
            source.write_bytes(fixture())
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(module.main([str(source), '--output', str(output)]), 0)
            before = output.read_bytes()
            self.assertTrue(json.loads(before)['crc32_verified'])
            self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                module.main([str(source), '--output', str(output)])
            self.assertEqual(output.read_bytes(), before)
            source.write_bytes(b'corrupt')
            absent = Path(folder) / 'absent'
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                module.main([str(source), '--output', str(absent)])
            self.assertFalse(absent.exists())

    def test_read_refuses_fifo_symlink_directory_and_oversized_file(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            fifo = root / 'fifo'
            os.mkfifo(fifo)
            with self.assertRaises(module.FormatError):
                module.bounded_read(fifo)
            regular = root / 'module'
            regular.write_bytes(fixture())
            link = root / 'link'
            link.symlink_to(regular)
            with self.assertRaises(OSError):
                module.bounded_read(link)
            with self.assertRaises((OSError, module.FormatError)):
                module.bounded_read(root)
            with patch.object(module, 'MAX_BYTES', 1), self.assertRaises(module.FormatError):
                module.bounded_read(regular)


if __name__ == '__main__':
    unittest.main()
