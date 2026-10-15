#!/usr/bin/env python3
"""Inspect QTI Chromatix V3 sensor modules without executing or programming them.

The container layout is recovered from local Windows files. Register/power
interpretations are candidate schemas, explicitly separate from byte evidence.
Outputs may contain private calibration and belong in ignored raw directories.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import struct
import tempfile
import zlib

MAX_BYTES = 16 * 1024 * 1024
MAX_SYMBOLS = 65536
MAX_PAYLOAD_TOTAL = 4 * 1024 * 1024
MAX_EXPANDED_BYTES = 4 * 1024 * 1024
SYMBOL = struct.Struct('<I32s5I')
SECTION = struct.Struct('<III')


class FormatError(ValueError):
    pass


def bounded_read(path):
    flags = os.O_RDONLY | os.O_NONBLOCK | getattr(os, 'O_NOFOLLOW', 0)
    descriptor = os.open(path, flags)
    with os.fdopen(descriptor, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_BYTES:
            raise FormatError('Input must be a bounded regular file')
        data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise FormatError('Input grew beyond the byte limit')
    return data


def span(data, offset, size, limit=None):
    end = len(data) if limit is None else limit
    if offset < 0 or size < 0 or offset > end or size > end - offset:
        raise FormatError(f'Out-of-bounds range: {offset:#x}+{size:#x}')
    return data[offset:offset + size]


def decode(data):
    if len(data) > MAX_BYTES:
        raise FormatError('Input exceeds byte limit')
    if len(data) < 172 or data[:28] != b'QTI Chromatix Header'.ljust(28, b'\0'):
        raise FormatError('Not a supported Chromatix container')
    declared, = struct.unpack_from('<I', data, 28)
    if declared != len(data) - 4:
        raise FormatError('Declared size does not match file minus CRC')
    crc, = struct.unpack_from('<I', data, declared)
    if zlib.crc32(data[:declared]) != crc:
        raise FormatError('CRC32 mismatch')
    version = struct.unpack_from('<II', data, 32)
    if version != (3, 1):
        raise FormatError(f'Unsupported header version fields: {version}')
    table, count = struct.unpack_from('<II', data, 160)
    if table < 168 or not 2 <= count <= 16:
        raise FormatError('Invalid section table')
    span(data, table, count * SECTION.size, declared)
    sections = {}
    ranges = [(0, table + count * SECTION.size)]
    for i in range(count):
        ident, offset, size = SECTION.unpack_from(data, table + i * SECTION.size)
        if ident in sections:
            raise FormatError('Duplicate section identifier')
        payload = span(data, offset, size, declared)
        ranges.append((offset, offset + size))
        sections[ident] = {'id': ident, 'offset': offset, 'bytes': size,
                           'sha256': hashlib.sha256(payload).hexdigest()}
    ordered = sorted(ranges)
    if any(left[1] > right[0] for left, right in zip(ordered, ordered[1:])):
        raise FormatError('Overlapping sections or header')
    if not {0, 1} <= sections.keys():
        raise FormatError('Missing symbol or data section')
    symbols_section, values = sections[0], sections[1]
    if symbols_section['bytes'] % SYMBOL.size:
        raise FormatError('Partial symbol record')
    symbol_count = symbols_section['bytes'] // SYMBOL.size
    if symbol_count > MAX_SYMBOLS:
        raise FormatError('Symbol count exceeds limit')
    symbols = []
    by_id = {}
    payload_total = 0
    for i in range(symbol_count):
        address = symbols_section['offset'] + i * SYMBOL.size
        ident, raw_name, field0, field1, field2, offset, size = SYMBOL.unpack_from(data, address)
        try:
            name = raw_name.split(b'\0', 1)[0].decode('ascii')
        except UnicodeDecodeError as exc:
            raise FormatError('Non-ASCII symbol name') from exc
        if not name or any(ord(c) < 32 or ord(c) > 126 for c in name):
            raise FormatError('Invalid symbol name')
        if ident in by_id:
            raise FormatError('Duplicate symbol identifier')
        if offset > values['bytes'] or size > values['bytes'] - offset:
            raise FormatError('Symbol payload escapes data section')
        payload_total += size
        if payload_total > MAX_PAYLOAD_TOTAL:
            raise FormatError('Aggregate symbol payload exceeds limit')
        absolute = values['offset'] + offset
        payload = span(data, absolute, size, declared)
        entry = {'id': ident, 'name': name, 'descriptor_offset': address,
                 'unknown_fields': [field0, field1, field2],
                 'data_offset': offset, 'file_offset': absolute, 'bytes': size,
                 'payload_hex': payload.hex(), 'sha256': hashlib.sha256(payload).hexdigest()}
        symbols.append(entry)
        by_id[ident] = entry

    expanded_bytes = 0

    def referenced_words(ident, name, count=None, width=4):
        nonlocal expanded_bytes
        entry = by_id.get(ident)
        if entry is None or entry['name'] != name or entry['bytes'] % width:
            raise FormatError(f'Invalid {name} reference {ident}')
        length = entry['bytes'] // width
        if count is not None and length != count:
            raise FormatError(f'{name} count mismatch')
        if entry['bytes'] > MAX_EXPANDED_BYTES - expanded_bytes:
            raise FormatError('Expanded reference budget exceeded')
        expanded_bytes += entry['bytes']
        return list(struct.unpack('<' + ('H' if width == 2 else 'I') * length, bytes.fromhex(entry['payload_hex'])))

    register_sets, power_sets = [], []
    for entry in symbols:
        raw = bytes.fromhex(entry['payload_hex'])
        if entry['name'] == 'powerSetting':
            result = {'symbol_id': entry['id'], 'file_offset': entry['file_offset']}
            if len(raw) % 12:
                result['status'] = 'unsupported-record-size'
            else:
                result.update(status='candidate-triples', rows=[list(row) for row in struct.iter_unpack('<III', raw)])
            power_sets.append(result)
        if entry['name'] != 'regSetting':
            continue
        result = {'symbol_id': entry['id'], 'file_offset': entry['file_offset']}
        if not raw or len(raw) % 40:
            result['status'] = 'unsupported-record-size'
            register_sets.append(result)
            continue
        rows = []
        for i, row in enumerate(struct.iter_unpack('<10I', raw)):
            present, slave_id, register, number, data_id, address_type, data_type, operation, delay_present, delay_id = row
            try:
                if present not in (0, 1) or delay_present not in (0, 1):
                    raise FormatError('Invalid optional-field marker in register candidate')
                slave = referenced_words(slave_id, 'slaveAddr', present, width=2)
                words = referenced_words(data_id, 'registerData', number)
                delay = referenced_words(delay_id, 'delayUs', delay_present)
            except FormatError as exc:
                # The container is validated. A speculative record schema must
                # not discard its raw evidence when an interpretation fails.
                rows.append({'file_offset': entry['file_offset'] + i * 40,
                             'raw_words': list(row), 'status': 'interpretation-error',
                             'error': str(exc)})
                continue
            rows.append({'file_offset': entry['file_offset'] + i * 40,
                         'raw_words': list(row), 'register': register, 'data': words,
                         'slave_address': slave, 'delay_raw': delay,
                         'address_type_raw': address_type, 'data_type_raw': data_type,
                         'operation_raw': operation,
                         'references': [slave_id, data_id, delay_id]})
        result.update(status='candidate-40-byte-register-records', rows=rows)
        register_sets.append(result)
    return {'schema_version': 1,
            'decoder_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'format': 'QTI Chromatix V3 sensor module, recovered container layout',
            'source_sha256': hashlib.sha256(data).hexdigest(), 'source_bytes': len(data),
            'version_fields': list(version), 'crc32': f'{crc:08x}', 'crc32_verified': True,
            'sections': list(sections.values()), 'symbols': symbols,
            'register_sets': register_sets, 'power_sets': power_sets,
            'interpretation': 'Raw schema candidates only. Power enums, delay units and operation enums require driver correlation; no hardware programming or safety validation.'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--output', type=Path, required=True, help='new private JSON file; refuses overwrite')
    args = parser.parse_args(argv)
    try:
        report = decode(bounded_read(args.input))
        report['source_path'] = str(args.input)
        serialized = json.dumps(report, indent=2) + '\n'
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8',
                                             dir=args.output.parent, delete=False,
                                             prefix='.camera-module-') as stream:
                temporary = Path(stream.name)
                stream.write(serialized)
            # Atomic publication without replacing an existing file or symlink.
            os.link(temporary, args.output)
        finally:
            if temporary is not None:
                temporary.unlink()
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(f'Private report: {args.output}; {len(report["symbols"])} symbols, CRC verified. Candidate interpretations only.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
