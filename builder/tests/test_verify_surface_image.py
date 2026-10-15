import importlib.util
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('surface_verifier', pathlib.Path(__file__).parents[1] / 'verify-surface-image.py')
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)


class BootPayloadTests(unittest.TestCase):
    def setUp(self):
        self.modules = ['usb_storage', 'uas', 'xhci_hcd', 'xhci_plat_hcd', 'dwc3',
                        'dwc3_qcom', 'phy_qcom_qmp_combo', 'phy_qcom_qusb2',
                        'isofs', 'squashfs', 'erofs', 'overlay', 'loop', 'dm_mod',
                        'msm', 'panel_edp']

    def test_old_initrd_without_usb_storage_fails(self):
        modular = {name: pathlib.Path(name + '.ko.zst') for name in self.modules}
        names = {f'usr/lib/modules/version/kernel/{name}.ko.zst' for name in self.modules if name not in ('usb_storage', 'uas')}
        errors = v.boot_requirements(modular, set(), names)
        self.assertEqual(errors, ['boot: initramfs missing usb_storage', 'boot: initramfs missing uas'])

    def test_erofs_live_root_requires_its_modular_driver(self):
        modular = {name: pathlib.Path(name + '.ko.zst') for name in self.modules}
        names = {f'usr/lib/modules/version/kernel/{name}.ko.zst' for name in self.modules if name != 'erofs'}
        self.assertEqual(v.boot_requirements(modular, set(), names), ['boot: initramfs missing erofs'])

    def test_builtin_drivers_do_not_require_ko_files(self):
        self.assertEqual(v.boot_requirements({}, set(self.modules), set()), [])

    def test_hyphenated_module_names_match(self):
        modules = {name: pathlib.Path(name + '.ko.zst') for name in self.modules}
        names = {f'usr/lib/modules/version/kernel/{name.replace("_", "-")}.ko.zst' for name in self.modules}
        self.assertEqual(v.boot_requirements(modules, set(), names), [])

    def test_wrong_edition_checksum_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / 'CHECKSUM'
            path.write_text('SHA256 (Fedora-Server-44.aarch64.iso) = ' + '0' * 64)
            with self.assertRaisesRegex(ValueError, 'does not identify'):
                v.verify_base('/unused', path)

    def test_arbitrary_matching_iso_checksum_pair_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / 'CHECKSUM'
            path.write_text('SHA256 (Fedora-Workstation-Live-44-1.7.aarch64.iso) = ' + '0' * 64)
            with patch.object(v, 'digest', return_value='0' * 64):
                with self.assertRaisesRegex(ValueError, 'mismatch'):
                    v.verify_base('/unused', path)

    def test_missing_firmware_fails_but_compressed_firmware_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            file = root / 'usr/lib/firmware/qcom/firmware.mbn.zst'
            self.assertFalse(v.firmware_exists(root, '/usr/lib/firmware/qcom/firmware.mbn'))
            file.parent.mkdir(parents=True)
            file.touch()
            self.assertTrue(v.firmware_exists(root, '/usr/lib/firmware/qcom/firmware.mbn'))

    def test_touch_daemon_without_executable_permission_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            paths = ['usr/bin/iptsd', 'usr/bin/iptsd-check-device',
                     'usr/bin/iptsd-find-hidraw', 'usr/bin/iptsd-foreach',
                     'etc/grub.d/09_surface_sp11']
            for name in paths:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch(mode=0o755)
            self.assertEqual(v.executable_errors(root), [])
            (root / 'usr/bin/iptsd').chmod(0o644)
            self.assertEqual(v.executable_errors(root), ['not executable: usr/bin/iptsd'])

    def test_text_subprocess_failure_preserves_structured_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = pathlib.Path(tmp) / 'failed.json'
            argv = ['verify', '--rootfs', '/unused', '--iso-tree', '/unused',
                    '--kernel-version', 'test', '--kernel-config', '/unused',
                    '--base-iso', '/unused', '--base-checksum', '/unused',
                    '--report', str(report)]
            error = subprocess.CalledProcessError(1, 'xorriso', stderr='layout inspection failed')
            with patch.object(sys, 'argv', argv), patch.object(v, 'audit', side_effect=error):
                with self.assertRaises(SystemExit) as result:
                    v.main()
            self.assertEqual(result.exception.code, 1)
            self.assertIn('layout inspection failed', report.read_text())

    def test_fedora_boot_dtb_symlink_resolves_before_archive_lookup(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / 'boot').mkdir()
            (root / 'boot/dtb').symlink_to('../usr/lib/modules/stock/dtb')
            canonical, links = v.resolve_root_path(root, 'boot/dtb/qcom/surface.dtb')
            self.assertEqual(canonical, 'usr/lib/modules/stock/dtb/qcom/surface.dtb')
            self.assertEqual(links, [('boot/dtb', '../usr/lib/modules/stock/dtb')])

    def test_absolute_image_symlinks_do_not_resolve_against_host(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / 'lib').symlink_to('/usr/lib')
            canonical, _ = v.resolve_root_path(root, 'lib/firmware/test.bin')
            self.assertEqual(canonical, 'usr/lib/firmware/test.bin')


if __name__ == '__main__':
    unittest.main()
