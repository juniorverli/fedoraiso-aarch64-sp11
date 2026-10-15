"""Exercise installed GRUB generation with real Fedora helpers and fixture probes.

Run inside the Fedora build container, where grub-mkconfig_lib is installed:
    python3 -m unittest discover -s tests -p test_installed_boot.py -v
"""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "boot/grub/09_surface_sp11"
LIBRARY = Path(os.environ.get("GRUB_MKCONFIG_LIB", "/usr/share/grub/grub-mkconfig_lib"))


@unittest.skipUnless(LIBRARY.is_file(), "requires installed Fedora grub-mkconfig_lib")
class InstalledBootTests(unittest.TestCase):
    def generate(self, filesystem="ext4", separate_boot=False, fsroot="/", cmdline=""):
        with tempfile.TemporaryDirectory(prefix="surface-boot-") as directory:
            scratch = Path(directory)
            boot = scratch / "boot"
            for filename in ("vmlinuz-sp11", "initramfs-sp11.img", "dtb-sp11/qcom/x1p64100-microsoft-denali.dtb"):
                path = boot / filename
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("fixture artifact")
            bins = scratch / "bin"
            bins.mkdir()
            probes = {
                "grub2-probe": '''#!/usr/bin/python3
import os, sys
args = sys.argv[1:]
target = next(arg.split('=', 1)[1] for arg in args if arg.startswith('--target='))
separate = os.environ['TEST_SEPARATE'] == 'yes'
if target == 'device': print('/dev/testboot' if separate else '/dev/testroot')
elif target == 'fs_uuid': print('BOOT-UUID' if separate and '/dev/testboot' in args else 'ROOT-UUID')
elif target == 'partmap': print('gpt')
elif target == 'fs': print('ext2' if separate else os.environ['TEST_FS'])
elif target in ('abstraction', 'hints_string', 'compatibility_hint'): pass
else: raise SystemExit('unexpected probe: ' + repr(args))
''',
                "grub2-mkrelpath": '''#!/usr/bin/python3
import os, pathlib, sys
name = pathlib.Path(sys.argv[-1]).relative_to(os.environ['SURFACE_BOOT_DIR'])
prefix = '' if os.environ['TEST_SEPARATE'] == 'yes' else ('/@root/boot' if os.environ['TEST_FS'] == 'btrfs' else '/boot')
print(prefix + '/' + str(name))
''',
                "findmnt": '''#!/usr/bin/python3
import os, sys
print(os.environ['TEST_FSROOT'] if 'FSROOT' in sys.argv else os.environ['TEST_FS'])
''',
            }
            for filename, body in probes.items():
                path = bins / filename
                path.write_text(body)
                path.chmod(0o755)
            env = dict(os.environ, PATH=str(bins) + os.pathsep + os.environ["PATH"],
                       pkgdatadir=str(LIBRARY.parent), grub_probe=str(bins / "grub2-probe"),
                       grub_mkrelpath=str(bins / "grub2-mkrelpath"), SURFACE_BOOT_DIR=str(boot),
                       TEST_FS=filesystem, TEST_SEPARATE="yes" if separate_boot else "no",
                       TEST_FSROOT=fsroot, GRUB_CMDLINE_LINUX=cmdline)
            return subprocess.run(["bash", str(SCRIPT)], env=env, text=True,
                                  capture_output=True, check=True).stdout

    def test_ext4_root_contains_complete_custom_boot(self):
        output = self.generate(cmdline="rd.luks.uuid=luks-123 console=tty0")
        self.assertIn("--fs-uuid --set=root ROOT-UUID", output)
        self.assertIn('if [ "${boot_once}" != "true" ]; then', output)
        self.assertIn("set default='surface-sp11'", output)

        self.assertIn("linux '/boot/vmlinuz-sp11' 'root=UUID=ROOT-UUID'", output)
        self.assertIn("devicetree '/boot/dtb-sp11/qcom/x1p64100-microsoft-denali.dtb'", output)
        self.assertIn("initrd '/boot/initramfs-sp11.img'", output)
        self.assertIn("'rd.luks.uuid=luks-123'", output)
        for flag in ("clk_ignore_unused", "pd_ignore_unused", "arm64.nopauth", "systemd.mask=tpm2.target"):
            self.assertIn("'" + flag + "'", output)

    def test_separate_boot_uses_boot_uuid_and_relative_paths(self):
        output = self.generate(separate_boot=True)
        self.assertIn("--fs-uuid --set=root BOOT-UUID", output)
        self.assertIn("linux '/vmlinuz-sp11' 'root=UUID=ROOT-UUID'", output)
        self.assertIn("devicetree '/dtb-sp11/qcom/x1p64100-microsoft-denali.dtb'", output)
        self.assertIn("initrd '/initramfs-sp11.img'", output)

    def test_btrfs_merges_subvolume_and_existing_rootflags(self):
        output = self.generate(filesystem="btrfs", fsroot="/@root", cmdline="rootflags=compress=zstd:1 rd.luks.uuid=abc")
        self.assertIn("'rootflags=compress=zstd:1,subvol=@root'", output)
        self.assertIn("linux '/@root/boot/vmlinuz-sp11'", output)
        self.assertIn("'rd.luks.uuid=abc'", output)
        self.assertEqual(output.count("'rootflags="), 1)

    def test_explicit_btrfs_subvolume_preserved_live_args_removed(self):
        output = self.generate(filesystem="btrfs", fsroot="/@root", cmdline="root=live:CDLABEL=FEDORA_SP11 rd.live.image inst.stage2=hd:LABEL=OLD rootflags=subvolid=256,compress=zstd ro")
        self.assertIn("'rootflags=subvolid=256,compress=zstd'", output)
        self.assertIn("'ro'", output)
        self.assertNotIn("CDLABEL", output)
        self.assertNotIn("rd.live", output)
        self.assertNotIn("inst.stage2", output)

    def test_live_root_does_not_generate_installed_entry(self):
        self.assertEqual(self.generate(filesystem="overlay"), "")


if __name__ == "__main__":
    unittest.main()
