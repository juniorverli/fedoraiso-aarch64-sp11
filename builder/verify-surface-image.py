#!/usr/bin/env python3
"""Audit the shipped Surface payload; does not assert physical hardware works."""
import argparse
import gzip
import hashlib
import json
import lzma
import pathlib
import re
import struct
import subprocess
import tempfile


def run(*args, **kwargs):
    return subprocess.run(args, check=True, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, **kwargs).stdout


def digest(path):
    with open(path, 'rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def verify_base(iso, checksum):
    text = pathlib.Path(checksum).read_text()
    name = 'Fedora-Workstation-Live-44-1.7.aarch64.iso'
    match = re.search(r'SHA256 \(' + re.escape(name) + r'\) = ([a-f0-9]{64})', text)
    if not match:
        raise ValueError('Checksum does not identify official Fedora Workstation 44 AArch64')
    # Pin the independently published Fedora44 artifact as well as the checksum
    # filename; arbitrary ISO/checksum pairs must not pass this identity gate.
    expected = '162ba3c552a2d241c7c63ec26777af0255ee1b5a135adc0be986ceed999933ef'
    if match[1] != expected or digest(iso) != expected:
        raise ValueError('Official Fedora Workstation 44 ISO checksum mismatch')
    return expected


def extract_kernel_config(path):
    raw = pathlib.Path(path).read_bytes()
    if raw[:2] == b'MZ' and raw[4:8] == b'zimg':
        offset, length = struct.unpack_from('<II', raw, 8)
        payload = raw[offset:offset + length]
        compression = raw[24:28]
        if compression == b'zstd':
            raw = run('zstd', '-q', '-d', '-c', input=payload)
        elif payload[:2] == b'\x1f\x8b':
            raw = gzip.decompress(payload)
        elif payload[:6] == b'\xfd7zXZ\x00':
            raw = lzma.decompress(payload)
        else:
            raise ValueError('Unsupported EFI zboot payload compression')
    marker = raw.find(b'IKCFG_ST')
    if marker < 0:
        raise ValueError('Actual kernel image has no embedded configuration')
    # A gzip member is followed by IKCFG_ED and the rest of the kernel.
    import zlib
    return zlib.decompress(raw[marker + 8:], 31).decode()


def normalize(name):
    return name.replace('-', '_')


def module_inventory(root, version):
    directory = root / 'usr/lib/modules' / version
    modular = {normalize(p.name.split('.ko')[0]): p for p in directory.rglob('*.ko*')}
    builtin = {normalize(pathlib.PurePosixPath(line).name.removesuffix('.ko'))
               for line in (directory / 'modules.builtin').read_text().splitlines()}
    return modular, builtin


def firmware_exists(root, path):
    return any((root / (path.lstrip('/') + suffix)).is_file()
               for suffix in ('', '.xz', '.zst'))


def executable_errors(root):
    paths = ['usr/bin/iptsd', 'usr/bin/iptsd-check-device',
             'usr/bin/iptsd-find-hidraw', 'usr/bin/iptsd-foreach',
             'etc/grub.d/09_surface_sp11']
    return ['not executable: ' + path for path in paths
            if not (root / path).is_file() or not (root / path).stat().st_mode & 0o111]


def boot_requirements(modular, builtin, initrd_names):
    errors = []
    required = ['usb_storage', 'uas', 'xhci_hcd', 'xhci_plat_hcd', 'dwc3',
                'dwc3_qcom', 'phy_qcom_qmp_combo', 'phy_qcom_qusb2',
                'isofs', 'squashfs', 'erofs', 'overlay', 'loop', 'dm_mod',
                'simpledrm', 'msm', 'panel_edp']
    for module in required:
        if module in builtin:
            continue
        if module not in modular:
            errors.append(f'boot: no kernel support for {module}')
        elif not any(normalize(pathlib.PurePosixPath(name).name.split('.ko')[0]) == module
                     for name in initrd_names if '.ko' in name):
            errors.append(f'boot: initramfs missing {module}')
    return errors


def resolve_root_path(root, name):
    """Resolve image symlinks inside the target root, including absolute links."""
    from collections import deque
    pending = deque(pathlib.PurePosixPath(name).parts)
    resolved, links = [], []
    while pending:
        part = pending.popleft()
        if part in ('/', '.'):
            continue
        if part == '..':
            if not resolved:
                raise ValueError('Image symlink escapes root: ' + name)
            resolved.pop()
            continue
        candidate = root.joinpath(*resolved, part)
        if candidate.is_symlink():
            target = str(candidate.readlink())
            links.append(('/'.join([*resolved, part]), target))
            if len(links) > 40:
                raise ValueError('Image symlink cycle: ' + name)
            if target.startswith('/'):
                resolved = []
            pending.extendleft(reversed(pathlib.PurePosixPath(target).parts))
        else:
            resolved.append(part)
    return '/'.join(resolved), links


def verify_live_files(root, image, paths):
    """Compare selected files from the actual immutable live filesystem."""
    kind = run('blkid', '-s', 'TYPE', '-o', 'value', str(image)).decode().strip()
    if kind != 'erofs':
        raise ValueError('Unsupported live filesystem: ' + kind)
    errors, checked_links = [], set()
    import os
    with tempfile.TemporaryDirectory(prefix='surface-live-audit-') as directory:
        for index, name in enumerate(sorted(set(paths))):
            canonical, links = resolve_root_path(root, name)
            source = root / canonical
            if not source.is_file():
                errors.append('live root source missing: ' + name)
                continue
            dest = pathlib.Path(directory) / str(index)
            for link, target in links:
                if link not in checked_links:
                    actual = run('dump.erofs', '--cat', '--path=/' + link, str(image)).decode()
                    if actual != target:
                        errors.append('immutable live symlink differs: ' + link)
                    checked_links.add(link)
            # fsck.erofs --path does not follow intermediate symlinks itself.
            run('fsck.erofs', '--extract=' + str(dest), '--xattrs',
                '--path=/' + canonical, str(image))
            if not dest.is_file() or digest(dest) != digest(source):
                errors.append('immutable live filesystem differs: ' + name)
            elif dest.stat().st_mode & 0o7777 != source.stat().st_mode & 0o7777:
                errors.append('immutable live filesystem permissions differ: ' + name)
            if kind == 'erofs' and name in ('usr/bin/iptsd', 'etc/gdm/custom.conf'):
                try:
                    label = os.getxattr(dest, 'security.selinux')
                    if not label.startswith(b'system_u:object_r:'):
                        errors.append('invalid SELinux label: ' + name)
                except OSError:
                    errors.append('missing SELinux label in live filesystem: ' + name)
    return kind, errors


def read_release(path):
    return {key: value.strip('"\'') for key, value in
            (line.split('=', 1) for line in path.read_text().splitlines() if '=' in line)}


def audit(args):
    root = pathlib.Path(args.rootfs)
    tree = pathlib.Path(args.iso_tree)
    errors, checks = [], {}
    def check(label, condition, detail=''):
        checks[label] = bool(condition)
        if not condition:
            errors.append(label + (': ' + detail if detail else ''))
    checks['base_sha256'] = verify_base(args.base_iso, args.base_checksum)
    release = read_release(root / 'etc/os-release')
    check('Fedora44 Workstation', release.get('VERSION_ID') == '44' and
          release.get('VARIANT_ID') == 'workstation', repr(release))
    arch = run('file', str(root / 'usr/bin/gnome-shell')).decode()
    check('AArch64 userspace', 'aarch64' in arch.lower())
    session_names = [p.name for p in (root / 'usr/share/wayland-sessions').glob('*gnome*.desktop')]
    check('GNOME Wayland session', bool(session_names))
    gdm = (root / 'etc/gdm/custom.conf').read_text()
    check('GDM Wayland enabled', bool(re.search(r'^WaylandEnable\s*=\s*true\s*$', gdm, re.M)))
    check('GDM installed session selected', any(re.search(r'^DefaultSession\s*=\s*' + re.escape(n) + r'\s*$', gdm, re.M) for n in session_names))
    check('Mesa Freedreno OpenGL driver', (root / 'usr/lib64/dri/msm_dri.so').is_file())
    turnip_icd = root / 'usr/share/vulkan/icd.d/freedreno_icd.aarch64.json'
    check('Mesa Turnip Vulkan driver', turnip_icd.is_file() and
          (root / 'usr/lib64/libvulkan_freedreno.so').is_file() and
          'libvulkan_freedreno.so' in turnip_icd.read_text())
    for binary in ['usr/bin/gnome-shell', 'usr/libexec/pipewire', 'usr/bin/wireplumber']:
        # PipeWire's daemon is /usr/bin/pipewire in the official Workstation.
        candidates = [binary, 'usr/bin/pipewire'] if binary.endswith('/pipewire') else [binary]
        check(binary, any((root / name).is_file() for name in candidates))
    check('Anaconda installer', (root / 'usr/bin/anaconda').is_file() or (root / 'usr/sbin/anaconda').is_file())
    check('graphical default target', (root / 'etc/systemd/system/default.target').is_symlink() and
          (root / 'etc/systemd/system/default.target').readlink().name == 'graphical.target')
    manifest = json.loads((root / 'usr/share/surface-pro-11/hardware.json').read_text())
    permissions = executable_errors(root)
    errors.extend(permissions)
    checks['executable hardware helpers and installed boot generator'] = not permissions
    modular, builtin = module_inventory(root, args.kernel_version)
    for module in ('msm', 'usb_storage', 'uas', 'spi_hid', 'ath12k', 'btqca',
                   'snd_soc_x1e80100', 'qcom_q6v5_pas', 'erofs'):
        if module in modular:
            abi = run('modinfo', '-F', 'vermagic', str(modular[module])).decode().split()
            check('module ABI:' + module, bool(abi) and abi[0] == args.kernel_version)
    for subsystem, entry in manifest['subsystems'].items():
        missing = []
        for module in entry.get('modules', []):
            if normalize(module) not in modular and normalize(module) not in builtin:
                missing.append('module ' + module)
        for path in entry.get('required_files', []):
            if not firmware_exists(root, path):
                missing.append(path)
        for pattern in entry.get('required_globs', []):
            if not list(root.glob(pattern.lstrip('/'))):
                missing.append(pattern)
        check('hardware:' + subsystem, not missing, ', '.join(missing))
    kernel = tree / 'vmlinuz-sp11'
    config = pathlib.Path(args.kernel_config).read_text()
    check('configuration belongs to shipped kernel', extract_kernel_config(kernel) == config)
    check('firmware early console support', 'CONFIG_EFI_EARLYCON=y' in config)
    initrd = tree / 'initramfs-sp11.img'
    listing = run('lsinitrd', str(initrd)).decode(errors='replace')
    # cpio -tv output is an evidence list; take path tokens without dates/sizes.
    names = {token for line in listing.splitlines() for token in line.split()
             if token.startswith(('usr/', 'etc/', 'lib/', 'var/'))}
    errors.extend(boot_requirements(modular, builtin, names))
    checks['initramfs_boot_modules'] = not boot_requirements(modular, builtin, names)
    check('initramfs correct kernel', bool(re.search(re.escape(args.kernel_version) + r'/kernel/', listing)))
    dtb = tree / 'dtb/qcom/x1p64100-microsoft-denali.dtb'
    dt = run('dtc', '-I', 'dtb', '-O', 'dts', str(dtb)).decode()
    check('LCD device tree', 'microsoft,denali-lcd' in dt)
    firmware = set()
    for assignment in re.findall(r'firmware-name\s*=\s*([^;]+);', dt):
        firmware.update(s for s in re.findall(r'"([^"]+)"', assignment))
    for name in sorted(firmware):
        check('DT firmware:' + name, firmware_exists(root, 'usr/lib/firmware/' + name))
        check('early firmware:' + name, any('usr/lib/firmware/' + name + suffix in names
              for suffix in ('', '.xz', '.zst')))
    for path in manifest['subsystems']['graphics'].get('required_files', []):
        if path.startswith('/usr/lib/firmware/'):
            check('early GPU firmware:' + path, any(path.lstrip('/') + suffix in names
                  for suffix in ('', '.xz', '.zst')))
    grub = (tree / 'EFI/BOOT/grub.cfg').read_text()
    check('GRUB finds kernel filesystem', 'search --no-floppy --file --set=root /vmlinuz-sp11' in grub)
    check('live root uses ISO label', 'root=live:CDLABEL=FEDORA_SP11' in grub)
    check('firmware console diagnostics', 'earlycon=efifb' in grub and 'keep_bootcon' in grub)
    check('GPU-independent diagnostic mode', 'nomodeset' in grub and 'systemd.unit=multi-user.target' in grub)
    check('no stale Fedora41 boot entry', 'Fedora Linux 41' not in grub)
    for target in ['display-manager.service', 'bluetooth.service', 'NetworkManager.service']:
        links = list((root / 'etc/systemd/system').rglob(target))
        check('enabled service:' + target, any(p.is_symlink() and str(p.readlink()) != '/dev/null' for p in links))
    live_paths = ['usr/lib/os-release', 'usr/share/surface-pro-11/hardware.json',
                  'usr/share/surface-pro-11/build-audit.json', 'etc/gdm/custom.conf',
                  'usr/bin/iptsd', 'usr/bin/iptsd-check-device',
                  'usr/bin/iptsd-find-hidraw', 'usr/bin/iptsd-foreach',
                  'etc/grub.d/09_surface_sp11',
                  'usr/lib64/libvulkan_freedreno.so',
                  'usr/share/vulkan/icd.d/freedreno_icd.aarch64.json',
                  'usr/lib/modules/' + args.kernel_version + '/modules.builtin',
                  'boot/vmlinuz-sp11', 'boot/initramfs-sp11.img',
                  'boot/dtb-sp11/qcom/x1p64100-microsoft-denali.dtb']
    for subsystem in manifest['subsystems'].values():
        for module in subsystem.get('modules', []):
            if normalize(module) in modular:
                live_paths.append(str(modular[normalize(module)].relative_to(root)))
        for path in subsystem.get('required_files', []):
            for suffix in ('', '.xz', '.zst'):
                target = path.lstrip('/') + suffix
                if (root / target).is_file():
                    live_paths.append(target)
                    break
    kind, live_errors = verify_live_files(root, tree / 'LiveOS/squashfs.img', live_paths)
    errors.extend(live_errors)
    checks['immutable live payload'] = not live_errors
    checks['live filesystem format'] = kind
    duplicate_paths = ['vmlinuz-sp11', 'initramfs-sp11.img', 'dtb/qcom/x1p64100-microsoft-denali.dtb',
                       'EFI/BOOT/BOOTAA64.EFI', 'EFI/BOOT/grub.cfg']
    with tempfile.TemporaryDirectory(prefix='surface-verify-') as directory:
        tmp = pathlib.Path(directory)
        esp = tree / 'images/efiboot.img'
        for path in duplicate_paths:
            dest = tmp / 'fat-file'
            run('mcopy', '-i', str(esp), '::/' + path, str(dest))
            check('EFI duplicate:' + path, digest(dest) == digest(tree / path))
            dest.unlink()
        if args.iso:
            result = subprocess.run(['xorriso', '-indev', str(args.iso), '-report_el_torito', 'plain',
                                     '-report_system_area', 'plain'], capture_output=True, text=True, check=True)
            report = result.stdout + result.stderr
            check('hybrid UEFI GPT', 'UEFI' in report and 'GPT' in report and 'EFI boot partition' in report)
            for index, path in enumerate(duplicate_paths + ['images/efiboot.img', 'LiveOS/squashfs.img']):
                dest = tmp / ('iso-file-' + str(index))
                run('xorriso', '-osirrox', 'on', '-indev', str(args.iso), '-extract', '/' + path, str(dest))
                check('ISO payload:' + path, digest(dest) == digest(tree / path))
    evidence = {'status': 'failed' if errors else 'passed', 'base': release,
                'kernel': args.kernel_version, 'physical_validation': 'pending',
                'checks': checks, 'errors': errors, 'subsystems': manifest['subsystems'],
                'iso_sha256': digest(args.iso) if args.iso else None}
    path = pathlib.Path(args.report)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(evidence, indent=2) + '\n')
    print(json.dumps({'status': evidence['status'], 'checks': len(checks), 'errors': errors,
                      'report': str(path)}, indent=2))
    return 1 if errors else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--extract-kernel-config')
    parser.add_argument('--output-config')
    for key in ['rootfs', 'iso-tree', 'kernel-version', 'kernel-config', 'base-iso', 'base-checksum', 'iso', 'report']:
        parser.add_argument('--' + key)
    args = parser.parse_args()
    if args.extract_kernel_config:
        pathlib.Path(args.output_config).write_text(extract_kernel_config(args.extract_kernel_config))
        return 0
    missing = [name for name in ['rootfs', 'iso_tree', 'kernel_version', 'kernel_config', 'base_iso', 'base_checksum', 'report'] if not getattr(args, name)]
    if missing:
        parser.error('required: ' + ', '.join(missing))
    try:
        return audit(args)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        detail = str(error)
        if isinstance(error, subprocess.CalledProcessError):
            stderr = error.stderr or ''
            detail += '\n' + (stderr.decode(errors='replace') if isinstance(stderr, bytes) else stderr)[-4000:]
        if args.report:
            path = pathlib.Path(args.report)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({'status': 'failed', 'physical_validation': 'pending',
                                        'errors': [detail]}, indent=2) + '\n')
        parser.exit(1, f'Surface image validation failed: {detail}\n')


if __name__ == '__main__':
    raise SystemExit(main())
