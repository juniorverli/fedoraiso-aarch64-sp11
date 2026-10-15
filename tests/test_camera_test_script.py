"""Exercise surface-camera-test CLI behavior without physical camera hardware."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/surface-camera-test.sh'


class CameraTestScriptTests(unittest.TestCase):
    def test_wsl_is_rejected_by_default(self):
        env = dict(os.environ)
        env.pop('SURFACE_CAMERA_IGNORE_WSL', None)
        # Mock uname returning WSL
        with tempfile.TemporaryDirectory() as folder:
            tools = Path(folder)
            uname = tools / 'uname'
            uname.write_text('#!/bin/sh\necho 6.6.87.2-microsoft-standard-WSL2\n')
            uname.chmod(0o755)
            env['PATH'] = f"{tools}:{env['PATH']}"
            res = subprocess.run(['bash', str(SCRIPT)], env=env, capture_output=True, text=True)
            self.assertNotEqual(res.returncode, 0)
            self.assertIn('WSL environment detected', res.stderr)

    def test_enumeration_mock_without_sensors(self):
        with tempfile.TemporaryDirectory() as folder:
            tools = Path(folder)
            uname = tools / 'uname'
            uname.write_text('#!/bin/sh\necho 7.2.0-sp11-exp\n')
            uname.chmod(0o755)
            cam = tools / 'surface-cam'
            cam.write_text('#!/bin/sh\necho "Available cameras:"\nexit 0\n')
            cam.chmod(0o755)
            env = dict(os.environ, PATH=f"{tools}:{os.environ['PATH']}",
                       SURFACE_CAMERA_IGNORE_WSL='1')
            res = subprocess.run(['bash', str(SCRIPT)], env=env, capture_output=True, text=True)
            self.assertEqual(res.returncode, 2)
            self.assertIn('No Surface cameras were enumerated', res.stdout)


if __name__ == '__main__':
    unittest.main()
