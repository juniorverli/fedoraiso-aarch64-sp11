import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('session', Path(__file__).resolve().parents[1] / 'scripts/collect-fedora-session.py')
session = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(session)


class SessionTests(unittest.TestCase):
    def test_guards_create_no_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'new'
            for uid, wsl, extra in ((0, False, []), (1000, True, [])):
                with self.subTest(uid=uid), patch.object(session.os, 'geteuid', return_value=uid), patch.object(session.helper, 'is_wsl', return_value=wsl), contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit):
                        session.main(['--output', str(output)] + extra)
                    self.assertFalse(output.exists())

    def test_sections_manifest_private_and_existing_output(self):
        for section in session.SECTIONS:
            with self.subTest(section=section), tempfile.TemporaryDirectory() as tmp, patch.object(session.os, 'geteuid', return_value=1000), patch.object(session.helper, 'run_command', return_value={'status': 'missing-command'}) as run:
                dest = Path(tmp) / 'bundle'
                session.collect(dest, False, section)
                self.assertEqual(stat.S_IMODE(dest.stat().st_mode), 0o700)
                self.assertEqual({p.stem for p in dest.glob('*.json')}, {section, 'metadata', 'manifest'})
                for call in run.call_args_list:
                    self.assertTrue(call.args[0] in session.commands_for(section).values() or call.args[0][0] in ('rpm', 'loginctl'))
                metadata = json.loads((dest / 'metadata.json').read_text())
                self.assertEqual(metadata['selected_section'], section)
                for name, digest in json.loads((dest / 'manifest.json').read_text())['files'].items():
                    self.assertEqual(hashlib.sha256((dest / name).read_bytes()).hexdigest(), digest)
                    self.assertEqual(stat.S_IMODE((dest / name).stat().st_mode), 0o600)
                self.assertIn('missing-command', (dest / 'summary.txt').read_text())
                before = {p: p.read_bytes() for p in dest.iterdir()}
                with self.assertRaises(FileExistsError):
                    session.collect(dest, False, section)
                self.assertEqual(before, {p: p.read_bytes() for p in dest.iterdir()})

    def test_wsl_smoke_all_and_session_selection(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(session.os, 'geteuid', return_value=1000), patch.object(session.helper, 'run_command', return_value={'status': 'ok'}), patch.dict(session.os.environ, {'XDG_SESSION_ID': '7'}, clear=True):
            dest = Path(tmp) / 'smoke'
            with self.assertRaises(ValueError):
                session.collect(dest, True)
            session.collect(dest, True, allow_wsl=True)
            self.assertIn('WSL tooling smoke only', (dest / 'summary.txt').read_text())
            self.assertEqual(set(p.stem for p in dest.glob('*.json')), {'audio', 'boot', 'desktop', 'metadata', 'manifest'})
            self.assertIn('session', session.commands_for('desktop'))
        self.assertNotIn('session', session.commands_for('desktop', {}))

    def test_command_allowlist_is_read_only(self):
        commands = [cmd for sec in session.SECTIONS for cmd in session.commands_for(sec, {'XDG_SESSION_ID': '7'}).values()]
        self.assertIn(['arecord', '-l'], commands)
        for cmd in commands:
            self.assertFalse(set(cmd) & {'set-volume', 'set-default', 'set-profile', 'restart', 'start', 'stop', 'play', 'record', 'set', 'sudo'})
            if cmd[0] in ('aplay', 'arecord'):
                self.assertEqual(cmd[1:], ['-l'])

    def test_required_audio_payloads_are_persisted_distinctly(self):
        required = {
            'wpctl-status': ['wpctl', 'status'],
            'cards': ['pactl', 'list', 'cards'], 'sinks': ['pactl', 'list', 'sinks'],
            'sources': ['pactl', 'list', 'sources'], 'alsa-playback-list': ['aplay', '-l'],
            'alsa-capture-list': ['arecord', '-l'], 'ucm-cards': ['alsaucm', 'listcards'],
            'default-sink-inspect': ['wpctl', 'inspect', '@DEFAULT_AUDIO_SINK@'],
            'default-source-inspect': ['wpctl', 'inspect', '@DEFAULT_AUDIO_SOURCE@'],
            'default-sink-get-volume': ['wpctl', 'get-volume', '@DEFAULT_AUDIO_SINK@'],
            'default-source-get-volume': ['wpctl', 'get-volume', '@DEFAULT_AUDIO_SOURCE@']}
        def result(argv):
            statuses = {'cards': 'permission-denied', 'sinks': 'timeout', 'sources': 'missing-command'}
            return {'status': statuses.get(argv[-1], 'ok'),
                    'stdout': 'payload:' + repr(argv), 'stderr': 'denied' if argv == ['pactl', 'list', 'cards'] else '',
                    'returncode': 1 if argv == ['pactl', 'list', 'cards'] else 0}
        with tempfile.TemporaryDirectory() as tmp, patch.object(session.os, 'geteuid', return_value=1000), patch.object(session.helper, 'run_command', side_effect=result):
            dest = Path(tmp) / 'bundle'
            session.collect(dest, False, 'audio')
            commands = json.loads((dest / 'audio.json').read_text())['commands']
            for key, argv in required.items():
                self.assertIn(key, commands)
                self.assertEqual(commands[key], result(argv))
            self.assertIn('audio-services', commands)
            self.assertIn('audio-journal', commands)

    def test_metadata_identity_session_versions_and_gap_summary(self):
        def read(path):
            if str(path) == '/etc/os-release':
                return {'status': 'permission-denied', 'error': 'OS denied'}
            if path.name == 'model':
                return {'status': 'ok', 'value': 'Surface', 'truncated': True}
            return {'status': 'absent'}
        def run(argv):
            if argv[0] == 'rpm':
                self.assertEqual(argv, ['rpm', '-q', 'pipewire', 'wireplumber', 'alsa-ucm', 'plymouth'])
                return {'status': 'failed', 'stdout': 'pipewire-1.4\npackage alsa-ucm is not installed', 'returncode': 1}
            return {'status': 'ok', 'stdout': 'probe evidence'}
        for section in session.SECTIONS:
            with self.subTest(section=section), tempfile.TemporaryDirectory() as tmp, patch.object(session.os, 'geteuid', return_value=1000), patch.object(session.helper, 'read_attribute', side_effect=read), patch.object(session.helper, 'run_command', side_effect=run), patch.dict(session.os.environ, {}, clear=True):
                dest = Path(tmp) / 'bundle'
                session.collect(dest, False, section)
                metadata = json.loads((dest / 'metadata.json').read_text())
                self.assertEqual(metadata['user_context']['effective_uid'], 1000)
                self.assertFalse(metadata['user_context']['dbus_session_address_present'])
                self.assertEqual(metadata['identity']['dt_model']['value'], 'Surface')
                self.assertIn('package alsa-ucm', metadata['commands']['package-versions']['stdout'])
                summary = (dest / 'summary.txt').read_text()
                for gap in ('metadata/os_release: permission-denied', 'metadata/dt_model: ok, truncated',
                            'metadata/dmi_product: absent', 'metadata/package-versions: failed',
                            'XDG_SESSION_ID missing', 'DBUS_SESSION_BUS_ADDRESS missing'):
                    self.assertIn(gap, summary)
        with tempfile.TemporaryDirectory() as tmp, patch.object(session.os, 'geteuid', return_value=1000), patch.object(session.helper, 'run_command', return_value={'status': 'permission-denied', 'stderr': 'session denied'}), patch.dict(session.os.environ, {'XDG_SESSION_ID': '7'}, clear=True):
            dest = Path(tmp) / 'bundle'
            session.collect(dest, False, 'boot')
            metadata = json.loads((dest / 'metadata.json').read_text())
            self.assertEqual(metadata['user_context']['session_environment']['XDG_SESSION_ID'], '7')
            self.assertEqual(metadata['commands']['session-context']['stderr'], 'session denied')
            self.assertIn('metadata/session-context: permission-denied', (dest / 'summary.txt').read_text())

    def test_real_failure_statuses_and_timeout(self):
        run = session.helper.run_command
        self.assertEqual(run(['/nonexistent-session-collector-command'])['status'], 'missing-command')
        self.assertEqual(run([sys.executable, '-c', 'import sys; sys.exit(9)'])['returncode'], 9)
        self.assertEqual(run([sys.executable, '-c', 'import sys; print("Permission denied", file=sys.stderr); sys.exit(1)'])['status'], 'permission-denied')
        with patch.object(session.helper, 'TIMEOUT', 0.02):
            self.assertEqual(run([sys.executable, '-c', 'import time; time.sleep(2)'])['status'], 'timeout')
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'not-executable'
            path.write_text('test')
            self.assertEqual(run([str(path)])['status'], 'permission-denied')
            self.assertEqual(session.artifact_hash(Path(tmp) / 'absent')['status'], 'absent')
        with patch.object(Path, 'open', side_effect=PermissionError('denied')):
            self.assertEqual(session.artifact_hash(Path('/denied'))['status'], 'permission-denied')


if __name__ == '__main__':
    unittest.main()
