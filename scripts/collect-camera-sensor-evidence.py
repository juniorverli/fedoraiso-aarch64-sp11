#!/usr/bin/env python3
"""Read-only, bounded camera/sensor inventory. Captures remain private."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import tempfile
import time

REPO = Path(__file__).resolve().parents[1]
MAX_BYTES = 256 * 1024
MAX_NODES = 512
TIMEOUT = 12
LOG_FILTER = re.compile(r'camera|camss|csiphy|csid|cci|i2c|sensor|iio|hid|remoteproc|fastrpc|adsp|cdsp|iris|video|firmware|iommu', re.I)


def utc():
    return datetime.now(timezone.utc).isoformat()


def read_attribute(path):
    """Never consume arbitrary large sysfs files, buffers or sensor samples."""
    try:
        with path.open('rb') as stream:
            data = stream.read(MAX_BYTES + 1)
        return {'status': 'ok', 'value': data[:MAX_BYTES].decode('utf-8', 'replace').replace('\0', '\n').strip(),
                'truncated': len(data) > MAX_BYTES}
    except FileNotFoundError:
        return {'status': 'absent'}
    except PermissionError as exc:
        return {'status': 'permission-denied', 'error': str(exc)}
    except OSError as exc:
        return {'status': 'error', 'error': str(exc)}


def run_command(argv, filter_lines=None):
    """Use disk spools so subprocess output cannot grow Python memory unbounded."""
    started = time.monotonic()
    result = {'argv': argv, 'started_utc': utc()}
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        try:
            proc = subprocess.run(argv, stdout=out, stderr=err, timeout=TIMEOUT, check=False,
                                  env=dict(os.environ, LC_ALL='C'))
            result.update(returncode=proc.returncode, status='ok' if proc.returncode == 0 else 'failed')
        except FileNotFoundError:
            result['status'] = 'missing-command'
        except PermissionError as exc:
            result.update(status='permission-denied', error=str(exc))
        except subprocess.TimeoutExpired:
            result['status'] = 'timeout'
        except OSError as exc:
            result.update(status='error', error=str(exc))
        out.seek(0)
        # Filter the kernel stream incrementally, retaining only bounded output.
        if filter_lines:
            chunks, size = [], 0
            for line in out:
                if filter_lines.search(line.decode('utf-8', 'replace')):
                    chunks.append(line[:max(0, MAX_BYTES - size)])
                    size += len(line)
                    if size > MAX_BYTES:
                        break
            stdout = b''.join(chunks)
            result['stdout_truncated'] = size > MAX_BYTES
        else:
            stdout = out.read(MAX_BYTES + 1)
            result['stdout_truncated'] = len(stdout) > MAX_BYTES
        err.seek(0)
        stderr = err.read(MAX_BYTES + 1)
        result['stdout'] = stdout[:MAX_BYTES].decode('utf-8', 'replace')
        result['stderr'] = stderr[:MAX_BYTES].decode('utf-8', 'replace')
        result['stderr_truncated'] = len(stderr) > MAX_BYTES
        if result['status'] == 'failed' and re.search(r'permission denied|operation not permitted|access denied', result['stderr'], re.I):
            result['status'] = 'permission-denied'
    result['duration_seconds'] = round(time.monotonic() - started, 3)
    return result


def inventory(root, attrs, channels=False):
    """List selected attributes and link destinations, never read measurement values."""
    try:
        # Cap traversal as well as output, including channel directory listings.
        with os.scandir(root) as entries:
            names = []
            for entry in entries:
                names.append(entry.name)
                if len(names) > MAX_NODES:
                    break
    except FileNotFoundError:
        return {'status': 'absent', 'nodes': []}
    except PermissionError as exc:
        return {'status': 'permission-denied', 'error': str(exc), 'nodes': []}
    except OSError as exc:
        return {'status': 'error', 'error': str(exc), 'nodes': []}
    nodes = []
    for name in sorted(names[:MAX_NODES]):
        node = root / name
        item = {'node': name, 'attributes': {attr: read_attribute(node / attr) for attr in attrs}}
        item['link_status'] = {}
        for link in ('driver', 'subsystem', 'of_node', 'firmware_node', 'device'):
            try:
                item[link] = os.readlink(node / link)
                item['link_status'][link] = {'status': 'ok'}
            except FileNotFoundError:
                item['link_status'][link] = {'status': 'absent'}
            except PermissionError as exc:
                item['link_status'][link] = {'status': 'permission-denied', 'error': str(exc)}
            except OSError as exc:
                item['link_status'][link] = {'status': 'error', 'error': str(exc)}
        if channels:
            try:
                with os.scandir(node) as entries:
                    available = []
                    scanned = 0
                    for entry in entries:
                        scanned += 1
                        if entry.name.startswith(('in_', 'out_')):
                            available.append(entry.name)
                        if scanned > MAX_NODES:
                            break
                item['channel_attributes_available'] = sorted(available)
                item['channels_truncated'] = scanned > MAX_NODES
            except OSError as exc:
                item['channel_listing_error'] = str(exc)
        nodes.append(item)
    return {'status': 'ok', 'nodes': nodes, 'truncated': len(names) > MAX_NODES}


def is_wsl():
    return 'microsoft' in platform.release().lower() or 'microsoft' in platform.version().lower() or bool(os.environ.get('WSL_INTEROP') or os.environ.get('WSL_DISTRO_NAME'))


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def collect(destination, wsl, sysroot=Path('/sys'), etcroot=Path('/etc'), devroot=Path('/dev')):
    # Atomic exclusive creation refuses all reused outputs, including symlinks.
    destination.mkdir(mode=0o700, parents=True, exist_ok=False)
    metadata = {'created_utc': utc(),
                'collector_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'external_tool_versions': 'unknown; not collected (record manually)', 'kernel_release': platform.release(),
                'kernel_version': platform.version(), 'architecture': platform.machine(),
                'wsl': wsl, 'evidence_scope': 'WSL tooling smoke check; NOT physical Surface evidence' if wsl else 'host inventory; confirm device identity before Surface attribution',
                'privacy': 'Private raw evidence. Not automatically anonymized.',
                'os_release': read_attribute(etcroot / 'os-release')}
    metadata['identity'] = {name: read_attribute(sysroot / path) for name, path in {
        'dt_model': 'firmware/devicetree/base/model', 'dt_compatible': 'firmware/devicetree/base/compatible',
        'dmi_product': 'class/dmi/id/product_name', 'dmi_vendor': 'class/dmi/id/sys_vendor',
        'firmware_version': 'class/dmi/id/bios_version', 'firmware_date': 'class/dmi/id/bios_date'}.items()}
    write_json(destination / 'metadata.json', metadata)
    commands = {name: run_command(argv, LOG_FILTER if name == 'kernel-log' else None) for name, argv in {
        'pci-tree': ['lspci', '-t'], 'pci-bindings': ['lspci', '-nnk'],
        'usb-tree': ['lsusb', '-t'], 'usb-devices': ['lsusb'],
        'modules': ['lsmod'], 'kernel-log': ['dmesg', '--color=never'],
        'v4l2-devices': ['v4l2-ctl', '--list-devices']}.items()}
    # Numeric media nodes only; topology readout does not stream or set links.
    media_nodes = inventory(sysroot / 'class/media', ['model', 'dev'])
    for node in media_nodes['nodes']:
        if re.fullmatch(r'media\d+', node['node']):
            commands[node['node'] + '-topology'] = run_command(['media-ctl', '-d', str(devroot / node['node']), '--print-topology'])
    write_json(destination / 'commands.json', commands)
    inventories = {'media': media_nodes}
    for bus in ('acpi', 'platform', 'i2c', 'spi', 'hid'):
        inventories[bus] = inventory(sysroot / 'bus' / bus / 'devices', ['name', 'modalias'])
    inventories['v4l2'] = inventory(sysroot / 'class/video4linux', ['name', 'dev', 'index'])
    inventories['iio'] = inventory(sysroot / 'bus/iio/devices', ['name'], channels=True)
    inventories['remoteproc'] = inventory(sysroot / 'class/remoteproc', ['name', 'state', 'firmware'])
    write_json(destination / 'sysfs.json', inventories)
    summary = [metadata['evidence_scope'], '', 'Command results (failure does not establish device absence):']
    for name, item in commands.items():
        flags = [field for field in ('stdout_truncated', 'stderr_truncated') if item.get(field)]
        summary.append(f"- {name}: {item['status']}" + ('; ' + ', '.join(flags) if flags else ''))
    summary.append('\nMetadata gaps:')
    for name, attr in {'os_release': metadata['os_release'], **metadata['identity']}.items():
        if attr['status'] != 'ok' or attr.get('truncated'):
            summary.append(f"- {name}: {attr['status']}" + ('; truncated' if attr.get('truncated') else ''))
    summary.append('\nSysfs results (absent means this path was not present; it does not prove absent hardware):')
    summary.extend(f"- {name}: {item['status']}, {len(item['nodes'])} nodes" + ('; truncated' if item.get('truncated') else '') for name, item in inventories.items())
    # Surface inaccessible attributes explicitly in the short gap summary.
    for name, inv in inventories.items():
        failures = sum(attr['status'] not in ('ok', 'absent') for node in inv['nodes'] for attr in node['attributes'].values())
        if failures:
            summary.append(f'- {name}: {failures} attribute read failures; see sysfs.json')
        for node in inv['nodes']:
            flags = []
            truncated_attrs = [key for key, attr in node['attributes'].items() if attr.get('truncated')]
            if truncated_attrs:
                flags.append('truncated attributes: ' + ', '.join(truncated_attrs))
            links = [f"{key}={status['status']}" for key, status in node.get('link_status', {}).items()
                     if status['status'] not in ('ok', 'absent')]
            if links:
                flags.append('inaccessible links: ' + ', '.join(links))
            if node.get('channels_truncated'):
                flags.append('channels truncated')
            if 'channel_listing_error' in node:
                flags.append('channel listing error: ' + node['channel_listing_error'])
            if flags:
                summary.append(f"- {name}/{node['node']}: " + '; '.join(flags))
    summary.append('\nNo streaming, samples, bus scanning, power changes or setting changes performed.\nPrivate raw logs require manual review before any sanitized handoff.')
    (destination / 'summary.txt').write_text('\n'.join(summary) + '\n', encoding='utf-8')
    # Manifest covers every payload; it cannot hash itself.
    manifest = {'algorithm': 'sha256', 'files': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(destination.iterdir()) if p.is_file()}}
    write_json(destination / 'manifest.json', manifest)
    return destination


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='new private destination; must not already exist')
    parser.add_argument('--allow-wsl', action='store_true', help='allow a clearly labelled WSL tooling smoke check')
    args = parser.parse_args(argv)
    wsl = is_wsl()
    if wsl and not args.allow_wsl:
        parser.error('WSL is not target hardware evidence. Run on Fedora, or use --allow-wsl for a tooling smoke check.')
    output = args.output or REPO / 'research/camera-sensors/raw' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ') + '-' + os.urandom(3).hex())
    try:
        collect(output, wsl)
    except FileExistsError:
        parser.error(f'refusing to overwrite existing destination: {output}')
    except OSError as exc:
        parser.error(f'cannot collect evidence: {exc}')
    print(f'Private inventory: {output}\nReview summary.txt and manifest.json; {"WSL smoke check only" if wsl else "confirm host identity"}.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
