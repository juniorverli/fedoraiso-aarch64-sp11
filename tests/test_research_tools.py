"""Hardware independent tests for investigation setup and partial evidence."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
INIT = ROOT / 'scripts/init-repository.sh'
spec = importlib.util.spec_from_file_location('collector', ROOT / 'scripts/collect-camera-sensor-evidence.py')
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)


class BootstrapTests(unittest.TestCase):
    def git(self, target, *args):
        return subprocess.check_output(['git', '-C', str(target), *args], text=True).strip()

    def run_init(self, target, cwd=None):
        return subprocess.run(['bash', str(INIT), str(target)], cwd=cwd, capture_output=True, text=True)

    def test_existing_preserves_head_branch_index_remotes_and_files(self):
        with tempfile.TemporaryDirectory(prefix='surface existing ') as directory:
            target = Path(directory)
            self.git(target, 'init', '-b', 'master')
            self.git(target, 'config', 'user.email', 'test@example.invalid')
            self.git(target, 'config', 'user.name', 'Test')
            (target / 'tracked').write_text('initial')
            self.git(target, 'add', 'tracked')
            self.git(target, 'commit', '-m', 'baseline')
            (target / 'tracked').write_text('staged')
            self.git(target, 'add', 'tracked')
            self.git(target, 'remote', 'add', 'origin', 'https://example.invalid/owner/repo')
            (target / '.gitignore').write_text('owner rule\n/research/camera-sensors/raw/\n/research/camera-sensors/private/\n')
            before = [self.git(target, *args) for args in [('rev-parse', 'HEAD'), ('branch', '--show-current'), ('diff', '--cached'), ('remote', '-v')]]
            index = (target / '.git/index').read_bytes()
            for _ in range(2):
                result = self.run_init(target, target)
                self.assertEqual(result.returncode, 0, result.stderr)
            after = [self.git(target, *args) for args in [('rev-parse', 'HEAD'), ('branch', '--show-current'), ('diff', '--cached'), ('remote', '-v')]]
            self.assertEqual(before, after)
            self.assertEqual(index, (target / '.git/index').read_bytes())
            self.assertEqual((target / '.gitignore').read_text(), 'owner rule\n/research/camera-sensors/raw/\n/research/camera-sensors/private/\n')
            self.assertTrue((target / 'research/camera-sensors/raw').is_dir())

    def test_fresh_with_spaces_repeated_no_commit_or_remote(self):
        with tempfile.TemporaryDirectory(prefix='surface fresh ') as directory:
            target = Path(directory) / 'new investigation'
            for _ in range(2):
                result = self.run_init(target, Path(directory))
                self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(self.git(target, 'branch', '--show-current'), 'main')
            self.assertEqual(self.git(target, 'remote'), '')
            self.assertEqual(self.git(target, 'ls-files'), '')
            self.assertEqual((target / '.gitignore').read_bytes(), (ROOT / '.gitignore').read_bytes())
            self.assertTrue((target / 'README.md').is_file())
            self.assertNotEqual(subprocess.run(['git', '-C', str(target), 'rev-parse', '--verify', 'HEAD'], capture_output=True).returncode, 0)

    def test_missing_protection_fails_and_preserves_ignore_and_index(self):
        for existing_repo in (False, True):
            with self.subTest(existing_repo=existing_repo), tempfile.TemporaryDirectory() as directory:
                target = Path(directory)
                if existing_repo:
                    self.git(target, 'init', '-b', 'master')
                    (target / 'staged').write_text('preserve')
                    self.git(target, 'add', 'staged')
                ignore = target / '.gitignore'
                ignore.write_text('owner rule\n/research/camera-sensors/raw/\n')
                index = target / '.git/index'
                before_index = index.read_bytes() if index.exists() else None
                result = self.run_init(target)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('Missing ignore protection for research/camera-sensors/private/', result.stderr)
                self.assertEqual(ignore.read_text(), 'owner rule\n/research/camera-sensors/raw/\n')
                self.assertEqual(index.read_bytes() if index.exists() else None, before_index)
                self.assertFalse((target / 'research').exists())

    def test_fresh_preserves_protective_ignore(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            content = 'owner rule\n/research/camera-sensors/raw/\n/research/camera-sensors/private/\n'
            (target / '.gitignore').write_text(content)
            result = self.run_init(target)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((target / '.gitignore').read_text(), content)

    def test_nested_target_refused_before_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.git(root, 'init', '-b', 'main')
            nested = root / 'not created' / 'child'
            result = self.run_init(nested)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Refusing nested', result.stderr)
            self.assertFalse((root / 'not created').exists())


class CollectorTests(unittest.TestCase):
    def test_actual_wsl_detector_controlled_inputs(self):
        cases = [
            ('6.12.0', 'Linux generic', {}, False),
            ('6.6.0-Microsoft-WSL2', 'Linux generic', {}, True),
            ('6.12.0', 'Microsoft kernel', {}, True),
            ('6.12.0', 'Linux generic', {'WSL_INTEROP': '/run/WSL/1_interop'}, True),
            ('6.12.0', 'Linux generic', {'WSL_DISTRO_NAME': 'Ubuntu'}, True),
        ]
        for release, version, env, expected in cases:
            with self.subTest(release=release, version=version, env=env), patch.dict(os.environ, env, clear=True), patch.object(collector.platform, 'release', return_value=release), patch.object(collector.platform, 'version', return_value=version):
                self.assertEqual(collector.is_wsl(), expected)

    def test_link_absence_permission_and_error_are_distinct(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'node').mkdir()
            def fake(path):
                if path.name == 'driver':
                    raise PermissionError('restricted driver')
                if path.name == 'firmware_node':
                    raise OSError('unreadable firmware link')
                raise FileNotFoundError()
            with patch.object(collector.os, 'readlink', side_effect=fake):
                node = collector.inventory(root, [])['nodes'][0]
            self.assertEqual(node['link_status']['driver']['status'], 'permission-denied')
            self.assertIn('restricted driver', node['link_status']['driver']['error'])
            self.assertEqual(node['link_status']['firmware_node']['status'], 'error')
            self.assertEqual(node['link_status']['device']['status'], 'absent')

    def test_summary_exposes_truncation_and_inaccessible_data(self):
        node = {'node': 'node0', 'attributes': {'name': {'status': 'ok', 'truncated': True},
                 'modalias': {'status': 'permission-denied'}},
                'link_status': {'driver': {'status': 'permission-denied'}, 'firmware_node': {'status': 'error'}},
                'channels_truncated': True, 'channel_listing_error': 'restricted channels'}
        def attribute(path):
            if path.name == 'model':
                return {'status': 'permission-denied'}
            return {'status': 'absent'}
        with tempfile.TemporaryDirectory() as directory, patch.object(collector, 'read_attribute', side_effect=attribute), patch.object(collector, 'inventory', return_value={'status': 'ok', 'nodes': [node], 'truncated': True}), patch.object(collector, 'run_command', return_value={'status': 'ok', 'stdout_truncated': True, 'stderr_truncated': True}):
            output = Path(directory) / 'capture'
            collector.collect(output, False)
            summary = (output / 'summary.txt').read_text()
            for expected in ('stdout_truncated', 'stderr_truncated', 'dt_model: permission-denied',
                             'dt_compatible: absent', 'truncated attributes: name', 'attribute read failures',
                             'inaccessible links: driver=permission-denied, firmware_node=error',
                             'channels truncated', 'channel listing error: restricted channels'):
                self.assertIn(expected, summary)
            metadata = json.loads((output / 'metadata.json').read_text())
            self.assertEqual(metadata['collector_sha256'], hashlib.sha256(Path(collector.__file__).read_bytes()).hexdigest())
            self.assertIn('unknown; not collected', metadata['external_tool_versions'])

    def test_wsl_refusal_and_explicit_smoke_label(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(collector, 'is_wsl', return_value=True):
            output = Path(directory) / 'capture'
            with self.assertRaises(SystemExit) as error:
                collector.main(['--output', str(output)])
            self.assertEqual(error.exception.code, 2)
            self.assertFalse(output.exists())
            with patch.object(collector, 'run_command', return_value={'status': 'missing-command'}), patch.object(collector, 'inventory', return_value={'status': 'absent', 'nodes': []}):
                self.assertEqual(collector.main(['--allow-wsl', '--output', str(output)]), 0)
            metadata = json.loads((output / 'metadata.json').read_text())
            self.assertTrue(metadata['wsl'])
            self.assertIn('NOT physical Surface evidence', metadata['evidence_scope'])
            self.assertIn('WSL tooling smoke', (output / 'summary.txt').read_text())

    def test_missing_command(self):
        with patch.object(subprocess, 'run', side_effect=FileNotFoundError):
            self.assertEqual(collector.run_command(['missing'])['status'], 'missing-command')

    def test_timeout(self):
        with patch.object(subprocess, 'run', side_effect=subprocess.TimeoutExpired(['slow'], 12)):
            result = collector.run_command(['slow'])
        self.assertEqual(result['status'], 'timeout')
        self.assertIn('duration_seconds', result)

    def test_permission_error(self):
        with patch.object(subprocess, 'run', side_effect=PermissionError('denied')):
            self.assertEqual(collector.run_command(['restricted'])['status'], 'permission-denied')

    def test_command_failure_permission_and_truncation(self):
        def fake(argv, **kwargs):
            self.assertNotIn('shell', kwargs)
            self.assertEqual(kwargs['timeout'], collector.TIMEOUT)
            kwargs['stdout'].write(b'x' * (collector.MAX_BYTES + 20))
            kwargs['stderr'].write(b'Operation not permitted')
            return subprocess.CompletedProcess(argv, 1)
        with patch.object(subprocess, 'run', side_effect=fake):
            result = collector.run_command(['restricted'])
        self.assertEqual(result['status'], 'permission-denied')
        self.assertEqual(result['returncode'], 1)
        self.assertTrue(result['stdout_truncated'])
        self.assertEqual(len(result['stdout']), collector.MAX_BYTES)

    def test_filtered_logs(self):
        def fake(argv, **kwargs):
            kwargs['stdout'].write(b'unrelated log\ncamss probing\nIIO registered\n')
            return subprocess.CompletedProcess(argv, 0)
        with patch.object(subprocess, 'run', side_effect=fake):
            result = collector.run_command(['dmesg'], collector.LOG_FILTER)
        self.assertEqual(result['stdout'], 'camss probing\nIIO registered\n')

    def test_attribute_permission_and_missing_separately(self):
        with patch.object(Path, 'open', side_effect=PermissionError('denied')):
            self.assertEqual(collector.read_attribute(Path('/fake'))['status'], 'permission-denied')
        with patch.object(Path, 'open', side_effect=FileNotFoundError):
            self.assertEqual(collector.read_attribute(Path('/fake'))['status'], 'absent')

    def test_partial_inventory_manifest_and_no_sample_reads(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sysroot = root / 'sys'
            sensor = sysroot / 'bus/iio/devices/iio:device0'
            sensor.mkdir(parents=True)
            (sensor / 'name').write_text('test-als')
            (sensor / 'in_illuminance_raw').write_text('MUST NOT BE CAPTURED')
            (sensor / 'serial').write_text('PRIVATE SERIAL')
            remote = sysroot / 'class/remoteproc/remoteproc0'
            remote.mkdir(parents=True)
            (remote / 'firmware').write_text('example.mbn')
            media = sysroot / 'class/media/media0'
            media.mkdir(parents=True)
            for bus in ('acpi', 'platform'):
                node = sysroot / 'bus' / bus / 'devices' / 'sensor0'
                node.mkdir(parents=True)
                (node / 'name').write_text(bus + '-sensor')
                (node / 'modalias').write_text(bus + ':test-id')
                (node / 'driver').symlink_to('../../drivers/test-driver')
                (node / 'firmware_node').symlink_to('../../../acpi/devices/SENSOR000:00')
            output = root / 'capture'
            commands = []
            def fake(argv, filter_lines=None):
                commands.append(argv)
                return {'status': 'missing-command', 'argv': argv}
            with patch.object(collector, 'run_command', side_effect=fake):
                collector.collect(output, False, sysroot=sysroot, etcroot=root / 'etc', devroot=root / 'dev')
            payload = (output / 'sysfs.json').read_text()
            self.assertIn('in_illuminance_raw', payload)
            self.assertNotIn('MUST NOT BE CAPTURED', payload)
            self.assertNotIn('PRIVATE SERIAL', payload)
            self.assertIn('example.mbn', payload)
            self.assertIn(['media-ctl', '-d', str(root / 'dev/media0'), '--print-topology'], commands)
            self.assertFalse(any('stream' in arg for command in commands for arg in command))
            summary = (output / 'summary.txt').read_text()
            self.assertIn('acpi: ok, 1 nodes', summary)
            sysfs = json.loads(payload)
            for bus in ('acpi', 'platform'):
                node = sysfs[bus]['nodes'][0]
                self.assertEqual(node['attributes']['name']['value'], bus + '-sensor')
                self.assertEqual(node['attributes']['modalias']['value'], bus + ':test-id')
                self.assertEqual(node['driver'], '../../drivers/test-driver')
                self.assertEqual(node['firmware_node'], '../../../acpi/devices/SENSOR000:00')
                self.assertEqual(node['link_status']['driver']['status'], 'ok')
            self.assertIn('missing-command', summary)
            manifest = json.loads((output / 'manifest.json').read_text())
            self.assertEqual(set(manifest['files']), {'metadata.json', 'commands.json', 'sysfs.json', 'summary.txt'})
            for name, digest in manifest['files'].items():
                self.assertEqual(hashlib.sha256((output / name).read_bytes()).hexdigest(), digest)
            self.assertEqual(output.stat().st_mode & 0o777, 0o700)

    def test_existing_destination_refuses_without_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            keep = output / 'keep'
            keep.write_bytes(b'prior evidence')
            with self.assertRaises(FileExistsError):
                collector.collect(output, False)
            self.assertEqual(list(output.iterdir()), [keep])
            self.assertEqual(keep.read_bytes(), b'prior evidence')


if __name__ == '__main__':
    unittest.main()
