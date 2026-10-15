"""Exercise the launcher's process boundary; no camera hardware is emulated."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

LAUNCHER = Path(__file__).resolve().parents[1] / 'scripts/run-camera-candidate.sh'


class LauncherTests(unittest.TestCase):
    def test_relocated_prefix_overrides_inherited_paths_and_requires_ipa(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            prefix = root / 'relocated camera'
            for name in ['lib64/libcamera.so.0.7', 'lib64/libcamera-base.so.0.7',
                         'lib64/libcamera/ipa/ipa_soft_simple.so',
                         'share/libcamera/ipa/simple/imx681.yaml']:
                item = prefix / name
                item.parent.mkdir(parents=True, exist_ok=True)
                item.write_text('test prerequisite')
            proxy = prefix / 'libexec/libcamera/soft_ipa_proxy'
            proxy.parent.mkdir(parents=True)
            proxy.write_text('#!/bin/sh\nexit 0\n')
            proxy.chmod(0o755)
            cam = prefix / 'bin/cam'
            cam.parent.mkdir()
            # Observe the actual exec boundary, including exact arguments.
            cam.write_text('#!/usr/bin/python3\nimport os,sys,json\n'
                           'print(json.dumps({"args":sys.argv[1:],"env":dict(os.environ)}))\n')
            cam.chmod(0o755)
            tools = root / 'tools'
            tools.mkdir()
            uname = tools / 'uname'
            uname.write_text('#!/bin/sh\necho test-fedora-kernel\n')
            uname.chmod(0o755)
            env = dict(os.environ, SURFACE_CAMERA_PREFIX=str(prefix),
                       PATH=f'{tools}:{os.environ["PATH"]}', LD_LIBRARY_PATH='/inherited/lib',
                       LIBCAMERA_IPA_CONFIG_PATH='/wrong/config',
                       LIBCAMERA_IPA_MODULE_PATH='/wrong/module', LIBCAMERA_IPA_PROXY_PATH='/wrong/proxy')
            def run(*args):
                return subprocess.run(['bash', str(LAUNCHER), *args], env=env,
                                      capture_output=True, text=True, timeout=5)
            result = run()
            self.assertEqual(result.returncode, 0, result.stderr)
            observed = json.loads(result.stdout)
            self.assertEqual(observed['args'], ['--list'])
            for key, suffix in [('LIBCAMERA_IPA_CONFIG_PATH', 'share/libcamera/ipa'),
                                ('LIBCAMERA_IPA_MODULE_PATH', 'lib64/libcamera/ipa'),
                                ('LIBCAMERA_IPA_PROXY_PATH', 'libexec/libcamera')]:
                self.assertEqual(observed['env'][key], str(prefix / suffix))
            self.assertEqual(observed['env']['LD_LIBRARY_PATH'].split(':')[0], str(prefix / 'lib64'))
            result = run('--camera', 'ID with spaces', '--file=/private/frame-#.bin')
            self.assertEqual(json.loads(result.stdout)['args'],
                             ['--camera', 'ID with spaces', '--file=/private/frame-#.bin'])
            proxy.unlink()
            result = run()
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout, '')
            # WSL must refuse even an otherwise valid candidate.
            uname.write_text('#!/bin/sh\necho 6.6-microsoft-WSL2\n')
            result = run()
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Fedora físico', result.stderr)


if __name__ == '__main__':
    unittest.main()
