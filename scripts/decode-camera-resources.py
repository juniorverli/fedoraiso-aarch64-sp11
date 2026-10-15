#!/usr/bin/env python3
"""Decode explicit AeoB resource files as data, preserving byte provenance.

Offsets are absolute file offsets. Arguments occupy 4 + max(4, DataLength)
bytes; no alignment is added. Vendor tuple meanings are deliberately unknown.
Limits: 1 MiB/file, depth 32, 10000 nodes/file; batch 16 MiB, 50000 nodes,
128 files. Integer value is a JSON number: JavaScript loses precision above
2**53 - 1; use value_decimal or value_hex for exact interchange.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import struct
import tempfile
import sys

MAX_BYTES = 1024 * 1024
MAX_DEPTH = 32
MAX_NODES = 10000
MAX_BATCH_BYTES = 16 * 1024 * 1024
MAX_BATCH_NODES = 50000
MAX_BATCH_FILES = 128
SCHEMA_VERSION = 1


class DecodeError(ValueError):
    """Malformed or out-of-bounds resource data."""


def fail(offset, message):
    raise DecodeError(f'offset 0x{offset:x}: {message}')


def decode(data, path, *, node_budget=MAX_BATCH_NODES):
    """Validate a complete resource and return its lossless structural record."""
    if len(data) > MAX_BYTES:
        fail(0, f'input exceeds {MAX_BYTES}-byte limit')
    if len(data) < 12:
        fail(0, 'header requires 12 bytes')
    signature, length, count = struct.unpack_from('<4sII', data)
    if signature != b'AeoB':
        fail(0, 'bad signature (expected AeoB)')
    if length != len(data):
        fail(4, f'declared length {length} differs from file length {len(data)}')
    node_count = 0

    def sequence(start, end, depth, expected=None):
        nonlocal node_count
        nodes = []
        offset = start
        while offset < end and (expected is None or len(nodes) < expected):
            if depth > MAX_DEPTH:
                fail(offset, f'nesting exceeds depth limit {MAX_DEPTH}')
            node_count += 1
            if node_count > node_budget:
                fail(offset, 'batch node limit exceeded')
            if node_count > MAX_NODES:
                fail(offset, f'node count exceeds limit {MAX_NODES}')
            if end - offset < 8:
                fail(offset, 'short argument: minimum storage is 8 bytes')
            argument_type, size = struct.unpack_from('<HH', data, offset)
            data_offset = offset + 4
            storage_length = 4 + max(4, size)
            next_offset = offset + storage_length
            if next_offset > end:
                fail(offset, f'argument storage ends at 0x{next_offset:x}, beyond span end 0x{end:x}')
            payload = data[data_offset:data_offset + size]
            node = {
                'type': argument_type,
                'header_offset': offset,
                'header_length': 4,
                'header_raw_hex': data[offset:data_offset].hex(),
                'data_offset': data_offset,
                'data_length': size,
                'storage_length': storage_length,
                'padding_offset': data_offset + size,
                'padding_hex': data[data_offset + size:next_offset].hex(),
            }
            if argument_type == 3:
                node['kind'] = 'package'
                node['children'] = sequence(data_offset, data_offset + size, depth + 1)
            else:
                node['raw_hex'] = payload.hex()
                if argument_type == 0:
                    if size not in (4, 8):
                        fail(offset, f'integer data length {size} must be 4 or 8')
                    node['kind'] = 'integer'
                    node['value'] = int.from_bytes(payload, 'little')
                    node['value_decimal'] = str(node['value'])
                    node['value_hex'] = hex(node['value'])
                    if size == 8:
                        node['warnings'] = ['8-byte integer is wider than the documented V1 ULONG form']
                elif argument_type == 1:
                    node['kind'] = 'string'
                    if not payload or payload[-1] != 0:
                        fail(data_offset, 'string requires final NUL')
                    try:
                        node['value'] = payload[:-1].decode('ascii')
                    except UnicodeDecodeError as error:
                        fail(data_offset + error.start, 'string contains non-ASCII byte')
                    node['trailing_nul_count'] = len(payload) - len(payload.rstrip(b'\0'))
                elif argument_type == 2:
                    node['kind'] = 'buffer'
                else:
                    node['kind'] = 'unknown'
                    node['warnings'] = [f'unknown argument type {argument_type}; retained opaquely']
            nodes.append(node)
            offset = next_offset
        if expected is not None and len(nodes) != expected:
            fail(offset, f'argument count {expected} exceeds parsed count {len(nodes)}')
        if offset != end:
            fail(offset, 'residual bytes after declared argument count')
        return nodes

    arguments = sequence(12, len(data), 1, count)
    return {
        'path': os.fspath(path),
        'filename': Path(path).name,
        'sha256': hashlib.sha256(data).hexdigest(),
        'byte_length': len(data),
        'node_count': node_count,
        'header': {
            'offset': 0, 'length': 12, 'raw_hex': data[:12].hex(),
            'signature': signature.decode('ascii'),
            'declared_length': length, 'argument_count': count,
        },
        'arguments': arguments,
    }


def read_regular(path):
    """Reject special inputs before opening; nonblocking open also guards FIFO races."""
    if not stat.S_ISREG(path.stat().st_mode):
        raise OSError('input must be a regular file')
    descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise OSError('input must be a regular file')
        source = os.fdopen(descriptor, 'rb')
    except BaseException:
        os.close(descriptor)
        raise
    with source:
        return source.read(MAX_BYTES + 1)


def publish(output, serialized):
    """Publish only a completed private file, atomically refusing destination reuse."""
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', newline='\n',
                                         prefix='.camera-resources-', dir=output.parent,
                                         delete=False) as destination:
            temporary = Path(destination.name)
            destination.write(serialized)
        os.link(temporary, output)
    finally:
        if temporary is not None:
            temporary.unlink()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inputs', nargs='+', type=Path, help='explicit resource file paths')
    parser.add_argument('--output', type=Path, help='new JSON file; defaults to stdout')
    args = parser.parse_args(argv)
    try:
        # lexists also refuses dangling symlinks; exclusive creation closes races.
        if args.output is not None and os.path.lexists(args.output):
            raise OSError(f'refusing existing output: {args.output}')
        if len(args.inputs) > MAX_BATCH_FILES:
            raise DecodeError(f'batch file count exceeds limit {MAX_BATCH_FILES}')
        documents = []
        batch_bytes = 0
        batch_nodes = 0
        for path in args.inputs:
            try:
                data = read_regular(path)
                batch_bytes += len(data)
                if batch_bytes > MAX_BATCH_BYTES:
                    raise DecodeError(f'batch byte count exceeds limit {MAX_BATCH_BYTES}')
                document = decode(data, path, node_budget=MAX_BATCH_NODES - batch_nodes)
                batch_nodes += document['node_count']
                documents.append(document)
            except (OSError, DecodeError) as error:
                raise DecodeError(f'{path}: {error}') from error
        result = {
            'schema_version': SCHEMA_VERSION,
            'parser_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'documents': documents,
        }
        serialized = json.dumps(result, indent=2, ensure_ascii=True) + '\n'
        if args.output is None:
            sys.stdout.write(serialized)
        else:
            publish(args.output, serialized)
    except (OSError, DecodeError) as error:
        print(f'decode-camera-resources: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
