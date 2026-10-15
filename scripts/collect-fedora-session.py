#!/usr/bin/env python3
"""Collect bounded, read-only Fedora desktop evidence as the desktop login user."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import os
from pathlib import Path
import platform
import pwd

_helper_spec = importlib.util.spec_from_file_location('camera_evidence', Path(__file__).with_name('collect-camera-sensor-evidence.py'))
helper = importlib.util.module_from_spec(_helper_spec)
_helper_spec.loader.exec_module(helper)
REPO = Path(__file__).resolve().parents[1]
SECTIONS = ('audio', 'boot', 'desktop')
ARTIFACTS = ('/boot/vmlinuz-sp11', '/boot/initramfs-sp11.img',
             '/boot/dtb-sp11/qcom/x1p64100-microsoft-denali.dtb')


def commands_for(section, environ=None):
    env = os.environ if environ is None else environ
    commands = {}
    if section == 'audio':
        commands = {'wpctl-status': ['wpctl', 'status'], 'cards': ['pactl', 'list', 'cards'],
                    'sinks': ['pactl', 'list', 'sinks'], 'sources': ['pactl', 'list', 'sources'],
                    'alsa-playback-list': ['aplay', '-l'], 'alsa-capture-list': ['arecord', '-l'],
                    'ucm-cards': ['alsaucm', 'listcards'],
                    'audio-services': ['systemctl', '--user', '--no-pager', 'status', 'pipewire.service', 'pipewire-pulse.service', 'wireplumber.service'],
                    'audio-journal': ['journalctl', '--user', '-b', '-n', '150', '--no-pager', '-u', 'pipewire.service', '-u', 'pipewire-pulse.service', '-u', 'wireplumber.service']}
        for kind in ('SINK', 'SOURCE'):
            for operation in ('inspect', 'get-volume'):
                commands[f'default-{kind.lower()}-{operation}'] = ['wpctl', operation, f'@DEFAULT_AUDIO_{kind}@']
    elif section == 'boot':
        commands = {'plymouth-theme': ['plymouth-set-default-theme'],
                    'boot-services': ['systemctl', '--no-pager', 'status', 'plymouth-start.service', 'plymouth-quit.service', 'display-manager.service'],
                    'boot-journal': ['journalctl', '-b', '-n', '150', '--no-pager', '-u', 'plymouth-start.service', '-u', 'plymouth-quit.service', '-u', 'display-manager.service'],
                    'kernel-journal': ['journalctl', '-k', '-b', '-n', '150', '--no-pager']}
    elif section == 'desktop':
        commands = {'gnome-version': ['gnome-shell', '--version'], 'extensions': ['gnome-extensions', 'list'],
                    'xwayland-process': ['pgrep', '-x', 'Xwayland'], 'x11-clients': ['xlsclients', '-l']}
        for schema, keys in {'org.gnome.desktop.interface': ('color-scheme', 'gtk-theme', 'icon-theme', 'font-name'),
                             'org.gnome.settings-daemon.plugins.power': ('sleep-inactive-ac-type', 'sleep-inactive-battery-type')}.items():
            for key in keys:
                commands[f'{schema}-{key}'] = ['gsettings', 'get', schema, key]
        if env.get('XDG_SESSION_ID'):
            commands['session'] = ['loginctl', 'show-session', env['XDG_SESSION_ID'], '-p', 'Type', '-p', 'Desktop', '-p', 'Class', '-p', 'Remote', '-p', 'State']
    else:
        raise ValueError(f'Unknown section: {section}')
    return commands


def artifact_hash(path):
    try:
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(block)
        return {'status': 'ok', 'sha256': digest.hexdigest()}
    except FileNotFoundError:
        return {'status': 'absent'}
    except PermissionError as exc:
        return {'status': 'permission-denied', 'error': str(exc)}
    except OSError as exc:
        return {'status': 'error', 'error': str(exc)}


def collect(destination, wsl, section='all', allow_wsl=False):
    # Do not inspect root's PipeWire/session even when invoked as a library.
    if os.geteuid() == 0:
        raise PermissionError('Run as the normal desktop login user; root session probes are not desktop evidence.')
    if wsl and not allow_wsl:
        raise ValueError('WSL requires explicit --allow-wsl; evidence is smoke only.')
    destination.mkdir(mode=0o700, parents=True, exist_ok=False)
    destination.chmod(0o700)
    # Payload files are private even if the caller has a permissive umask.
    previous_umask = os.umask(0o077)
    try:
        metadata = {'created_utc': helper.utc(), 'kernel_release': platform.release(),
                    'kernel_version': platform.version(), 'architecture': platform.machine(),
                    'os_release': helper.read_attribute(Path('/etc/os-release')), 'wsl': wsl,
                    'collector_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    'helper_sha256': hashlib.sha256(Path(helper.__file__).read_bytes()).hexdigest(),
                    'selected_section': section, 'privacy': 'Private raw logs; manually review before sharing.',
                    'evidence_scope': 'WSL tooling smoke only; NOT physical Fedora evidence' if wsl else 'Desktop login user inventory; confirm physical host identity'}
        metadata['identity'] = {name: helper.read_attribute(Path(path)) for name, path in {
            'dt_model': '/sys/firmware/devicetree/base/model',
            'dt_compatible': '/sys/firmware/devicetree/base/compatible',
            'dmi_product': '/sys/class/dmi/id/product_name',
            'dmi_vendor': '/sys/class/dmi/id/sys_vendor'}.items()}
        metadata['user_context'] = {'effective_uid': os.geteuid(), 'effective_gid': os.getegid(),
                                    'effective_user': pwd.getpwuid(os.geteuid()).pw_name,
                                    'session_environment': {key: os.environ.get(key) for key in (
                                        'XDG_SESSION_ID', 'XDG_SESSION_TYPE', 'XDG_CURRENT_DESKTOP',
                                        'XDG_RUNTIME_DIR', 'WAYLAND_DISPLAY', 'DISPLAY')},
                                    'dbus_session_address_present': bool(os.environ.get('DBUS_SESSION_BUS_ADDRESS'))}
        common_commands = {'package-versions': ['rpm', '-q', 'pipewire', 'wireplumber', 'alsa-ucm', 'plymouth']}
        if os.environ.get('XDG_SESSION_ID'):
            common_commands['session-context'] = ['loginctl', 'show-session', os.environ['XDG_SESSION_ID'],
                                                   '-p', 'User', '-p', 'Name', '-p', 'Type', '-p', 'Desktop', '-p', 'State']
        metadata['commands'] = {key: helper.run_command(argv) for key, argv in common_commands.items()}
        metadata['context_warnings'] = []
        for key in ('XDG_SESSION_ID', 'XDG_SESSION_TYPE', 'XDG_RUNTIME_DIR'):
            if not os.environ.get(key):
                metadata['context_warnings'].append(f'{key} missing; desktop session context incomplete')
        if not metadata['user_context']['dbus_session_address_present']:
            metadata['context_warnings'].append('DBUS_SESSION_BUS_ADDRESS missing; desktop D-Bus access not established')
        helper.write_json(destination / 'metadata.json', metadata)
        selected = SECTIONS if section == 'all' else (section,)
        summary = [metadata['evidence_scope'], 'Failures do not establish missing hardware.']
        for key, value in {'os_release': metadata['os_release'], **metadata['identity'], **metadata['commands']}.items():
            flags = ', truncated' if any(value.get(k) for k in ('truncated', 'stdout_truncated', 'stderr_truncated')) else ''
            summary.append(f"metadata/{key}: {value['status']}{flags}")
        summary.extend('context warning: ' + warning for warning in metadata['context_warnings'])
        for name in selected:
            results = {'commands': {key: helper.run_command(argv) for key, argv in commands_for(name).items()}}
            if name == 'boot':
                results['attributes'] = {path: helper.read_attribute(Path(path)) for path in ('/proc/cmdline', '/sys/firmware/acpi/bgrt/status', '/sys/firmware/acpi/bgrt/type')}
                results['artifacts'] = {path: artifact_hash(Path(path)) for path in ARTIFACTS}
            if name == 'desktop':
                results['session_environment'] = {key: os.environ.get(key) for key in ('XDG_SESSION_TYPE', 'XDG_SESSION_ID', 'XDG_CURRENT_DESKTOP', 'XDG_SESSION_DESKTOP', 'WAYLAND_DISPLAY', 'DISPLAY')}
                results['interpretation'] = 'Xwayland presence does not prove an app uses X11. Empty xlsclients is not exhaustive verification. pgrep exit 1 means no match. Missing XDG_SESSION_ID prevents loginctl session probe.'
                if not os.environ.get('XDG_SESSION_ID'):
                    summary.append('desktop/session: skipped; XDG_SESSION_ID missing')
            helper.write_json(destination / f'{name}.json', results)
            summary.append(f'[{name}]')
            for group in ('commands', 'attributes', 'artifacts'):
                for key, value in results.get(group, {}).items():
                    flags = ', truncated' if any(value.get(k) for k in ('truncated', 'stdout_truncated', 'stderr_truncated')) else ''
                    summary.append(f"{key}: {value['status']}{flags}")
        summary.append('No playback, recording, mixer writes, service restarts or configuration changes performed.')
        (destination / 'summary.txt').write_text('\n'.join(summary) + '\n', encoding='utf-8')
        helper.write_json(destination / 'manifest.json', {'algorithm': 'sha256', 'files': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(destination.iterdir()) if p.is_file()}})
    finally:
        os.umask(previous_umask)
    return destination


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--section', choices=('all',) + SECTIONS, default='all')
    parser.add_argument('--output', type=Path, help='new private directory; existing paths are refused')
    parser.add_argument('--allow-wsl', action='store_true', help='explicitly label WSL tooling smoke evidence')
    args = parser.parse_args(argv)
    if os.geteuid() == 0:
        parser.error('Run as the normal desktop login user, without sudo; root PipeWire is not desktop evidence.')
    wsl = helper.is_wsl()
    if wsl and not args.allow_wsl:
        parser.error('WSL is not Fedora desktop evidence; use --allow-wsl only for a labelled tooling smoke check.')
    output = args.output or REPO / 'research/camera-sensors/raw' / ('session-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ') + '-' + os.urandom(3).hex())
    try:
        collect(output, wsl, args.section, allow_wsl=args.allow_wsl)
    except FileExistsError:
        parser.error(f'Refusing existing output: {output}')
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(f'Private evidence: {output}; read summary.txt and manifest.json. ' + ('WSL SMOKE ONLY.' if wsl else 'Confirm physical host identity.'))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
