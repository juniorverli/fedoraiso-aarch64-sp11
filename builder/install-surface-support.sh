#!/usr/bin/env bash
# Apply Surface support to an extracted official Fedora Workstation 44 rootfs.
# Usage: install-surface-support.sh ROOTFS [KERNEL_SOURCE_ROOTFS]
set -euo pipefail
ROOTFS=$(realpath "${1:?usage: $0 ROOTFS [KERNEL_SOURCE_ROOTFS]}")
REPO=$(cd "$(dirname "$0")/.." && pwd)
KERNEL_SOURCE=$(realpath "${2:-$REPO/output/rootfs}")
KERNEL_VERSION=${KERNEL_VERSION:-7.2.8-arch1-3-sp11}
[[ $EUID == 0 && $ROOTFS != / && $ROOTFS != "$KERNEL_SOURCE" ]] || { echo 'Run as root with a separate extracted Workstation rootfs.' >&2; exit 1; }
grep -Eq '^VERSION_ID="?44"?$' "$ROOTFS/etc/os-release"
grep -Eq '^VARIANT_ID="?workstation"?$' "$ROOTFS/etc/os-release"
[[ -s $KERNEL_SOURCE/usr/lib/modules/$KERNEL_VERSION/vmlinuz ]]
install -d "$ROOTFS/usr/lib/modules/$KERNEL_VERSION" "$ROOTFS/usr/lib/firmware"
rsync -a --delete "$KERNEL_SOURCE/usr/lib/modules/$KERNEL_VERSION/" "$ROOTFS/usr/lib/modules/$KERNEL_VERSION/"
# Official Fedora supplies generic QCA, ath12k and GPU firmware. Add only the
# extracted machine firmware and calibration; do not import the old OS config.
for source in "$REPO/output/firmware" "$REPO/firmware/blobs"; do
    [[ ! -d $source ]] || rsync -a "$source/" "$ROOTFS/usr/lib/firmware/"
done
install -d "$ROOTFS/usr/lib/firmware/qcom/x1e80100/microsoft/Denali"
install -m 0644 "$REPO"/configs/qcom/*.jsn "$ROOTFS/usr/lib/firmware/qcom/x1e80100/microsoft/Denali/"

install -d "$ROOTFS/usr/bin" "$ROOTFS/etc/udev/rules.d" "$ROOTFS/etc/systemd/system"
for binary in iptsd iptsd-check-device iptsd-find-hidraw iptsd-foreach; do
    install -m 0755 "$REPO/output/iptsd-pkg/usr/bin/$binary" "$ROOTFS/usr/bin/"
done
install -m 0644 "$REPO/configs/iptsd/50-iptsd.rules" "$ROOTFS/etc/udev/rules.d/"
install -m 0644 "$REPO/configs/iptsd/iptsd@.service" "$ROOTFS/etc/systemd/system/"
# IPTSD dimensions are centimetres, not millimetres. Keep algorithm defaults
# until the digitizer has been calibrated on the physical LCD device.
cat > "$ROOTFS/etc/iptsd.conf" <<'CONF'
[Config]
Width = 28.76
Height = 19.17

[Touchscreen]
DisableOnPalm = true
DisableOnStylus = true
CONF
install -m 0755 "$REPO/rpm/sources/sp11-mac-fixup/sp11-mac-fixup" "$ROOTFS/usr/bin/"
install -m 0644 "$REPO/rpm/sources/sp11-mac-fixup/90-sp11-mac.rules" "$ROOTFS/etc/udev/rules.d/"
install -m 0644 "$REPO/rpm/sources/sp11-mac-fixup/sp11-bt-mac@.service" "$ROOTFS/etc/systemd/system/"
# These addresses were recovered for the owner's device, not a generic fleet.
[[ -e $ROOTFS/etc/sp11-mac.conf ]] || install -m 0600 "$REPO/rpm/sources/sp11-mac-fixup/sp11-mac.conf" "$ROOTFS/etc/sp11-mac.conf"

# Isolated Surface camera candidate stack and launcher commands
install -d "$ROOTFS/opt/surface-camera" "$ROOTFS/usr/local/bin" "$ROOTFS/etc/profile.d"
if [[ -d $REPO/output/libcamera-integration/stage/opt/surface-camera ]]; then
    rsync -a "$REPO/output/libcamera-integration/stage/opt/surface-camera/" "$ROOTFS/opt/surface-camera/"
elif [[ -f $REPO/output/surface-camera-userspace-f44-aarch64.tar.gz ]]; then
    tar --no-same-owner -xzf "$REPO/output/surface-camera-userspace-f44-aarch64.tar.gz" -C "$ROOTFS/"
fi

install -m 0755 "$REPO/scripts/run-camera-candidate.sh" "$ROOTFS/usr/local/bin/surface-cam"
install -m 0755 "$REPO/scripts/surface-camera-test.sh" "$ROOTFS/usr/local/bin/surface-camera-test"
install -m 0755 "$REPO/scripts/surface-camera-preview.sh" "$ROOTFS/usr/local/bin/surface-camera-preview"
[[ ! -f $REPO/scripts/collect-camera-sensor-evidence.py ]] || install -m 0755 "$REPO/scripts/collect-camera-sensor-evidence.py" "$ROOTFS/usr/local/bin/surface-camera-evidence"

for cmd in surface-cam surface-camera-test surface-camera-preview surface-camera-evidence; do
    if [[ -x $ROOTFS/usr/local/bin/$cmd ]]; then
        ln -sf "/usr/local/bin/$cmd" "$ROOTFS/usr/bin/$cmd"
    fi
done

cat > "$ROOTFS/etc/profile.d/surface-camera.sh" <<'CONF'
# Surface Pro 11 isolated camera environment
if [[ -d /opt/surface-camera/lib64/gstreamer-1.0 ]]; then
    export GST_PLUGIN_PATH="/opt/surface-camera/lib64/gstreamer-1.0${GST_PLUGIN_PATH:+:$GST_PLUGIN_PATH}"
fi
CONF
chmod 0644 "$ROOTFS/etc/profile.d/surface-camera.sh"

# Prefer the distribution's UCM, including its dispatcher. If it predates SP11,
# add the exact profile supplied by the reviewed upstream patch in this repo.
python3 - "$ROOTFS" "$REPO" <<'PY'
import pathlib, re, sys
root, repo = map(pathlib.Path, sys.argv[1:])
ucm = root / 'usr/share/alsa/ucm2/Qualcomm/x1e80100'
dispatcher = ucm / 'x1e80100.conf'
text = dispatcher.read_text()
if 'MICROSOFT-Surface-Pro-11.conf' not in text:
    patch = (repo / 'rpm/sources/alsa-ucm-conf-sp11/847.patch').read_text()
    for name in ('MICROSOFT-Surface-Pro-11.conf', 'Surface11-HiFi.conf'):
        match = re.search(r'\+\+\+ b/ucm2/Qualcomm/x1e80100/' + re.escape(name) + r'\n(.*?)(?=\ndiff --git|\n-- \n)', patch, re.S)
        if not match:
            raise SystemExit(f'Cannot read UCM patch: {name}')
        content = '\n'.join(line[1:] for line in match[1].splitlines() if line.startswith('+')) + '\n'
        (ucm / name).write_text(content)
    text += '''\n# Surface Pro 11: upstream alsa-ucm-conf patch 847.
If.SURFACEPro11 {
    Condition {
        Type RegexMatch
        String "${var:DMI_info}"
        Regex "Microsoft Corporation.*Surface.*Microsoft Surface Pro( with 5G)?, 11th Edition"
    }
    True.Include.sp11.File "/Qualcomm/x1e80100/MICROSOFT-Surface-Pro-11.conf"
}
'''
    dispatcher.write_text(text)
# Catch missing includes before producing an ISO; no sound card is available
# here to validate runtime ALSA controls or microphone channel routing.
for name in ('MICROSOFT-Surface-Pro-11.conf', 'Surface11-HiFi.conf'):
    for include in re.findall(r'File\s+"(/[^"]+)"', (ucm / name).read_text()):
        if not (root / 'usr/share/alsa/ucm2' / include.lstrip('/')).is_file():
            raise SystemExit(f'Missing UCM include: {include}')
PY

# GNOME's installed Wayland desktop name is authoritative. GDM configuration
# is changed in place so the official live autologin remains intact.
python3 - "$ROOTFS" <<'PY'
import configparser, pathlib, sys
root = pathlib.Path(sys.argv[1])
sessions = root / 'usr/share/wayland-sessions'
choices = [name for name in ('gnome.desktop', 'gnome-wayland.desktop') if (sessions / name).is_file()]
if not choices:
    raise SystemExit('Official GNOME Wayland session is missing')
path = root / 'etc/gdm/custom.conf'
config = configparser.ConfigParser(interpolation=None, strict=False)
config.optionxform = str
config.read(path)
if not config.has_section('daemon'):
    config.add_section('daemon')
config.set('daemon', 'WaylandEnable', 'true')
config.set('daemon', 'DefaultSession', choices[0])
with path.open('w') as out:
    config.write(out)
(root / 'usr/share/surface-pro-11').mkdir(parents=True, exist_ok=True)
(root / 'usr/share/surface-pro-11/wayland-session').write_text(choices[0] + '\n')
PY
# Workstation already supplies PipeWire/WirePlumber, UPower, power profiles,
# libinput and sensor proxy. Keep distro power, audio and monitor settings.
systemctl --root "$ROOTFS" enable bluetooth.service NetworkManager.service gdm.service
# The supplied kernel includes the in-kernel Qualcomm PD mapper. Do not
# start a competing userspace pd-mapper; Fedora otherwise retains its units.
if [[ -f $ROOTFS/usr/lib/systemd/system/pd-mapper.service ]]; then
    systemctl --root "$ROOTFS" mask pd-mapper.service
fi
# Runtime linkage/architecture smoke checks without opening hardware devices.
chroot "$ROOTFS" /usr/bin/iptsd --help >/dev/null
chroot "$ROOTFS" /usr/bin/iptsd-check-device --help >/dev/null
install -d "$ROOTFS/etc/grub.d"
install -m 0755 "$REPO/boot/grub/09_surface_sp11" "$ROOTFS/etc/grub.d/09_surface_sp11"
depmod -b "$ROOTFS" "$KERNEL_VERSION"
install -m 0644 "$REPO/builder/surface-hardware.json" "$ROOTFS/usr/share/surface-pro-11/hardware.json"
# A presence audit distinguishes shipped support from physical validation.
python3 - "$ROOTFS" "$KERNEL_VERSION" <<'PY'
import glob, json, pathlib, sys
root = pathlib.Path(sys.argv[1]); version = sys.argv[2]
manifest = json.loads((root / 'usr/share/surface-pro-11/hardware.json').read_text())
modules = root / 'usr/lib/modules' / version
available = {p.name.split('.ko')[0].replace('-', '_') for p in modules.rglob('*.ko*')}
available.update(pathlib.PurePosixPath(line).name.removesuffix('.ko').replace('-', '_') for line in (modules / 'modules.builtin').read_text().splitlines())
errors = []
for subsystem, entry in manifest['subsystems'].items():
    for module in entry.get('modules', []):
        if module.replace('-', '_') not in available:
            errors.append(f'{subsystem}: missing module {module}')
    for file in entry.get('required_files', []):
        if not any((root / (file.lstrip('/') + suffix)).is_file() for suffix in ('', '.xz', '.zst')):
            errors.append(f'{subsystem}: missing file {file}')
    for pattern in entry.get('required_globs', []):
        if not glob.glob(str(root / pattern.lstrip('/'))):
            errors.append(f'{subsystem}: missing {pattern}')
if errors:
    raise SystemExit('\n'.join(errors))
report = {'kernel': version, 'presence_audit': 'passed', 'physical_validation': 'pending', 'subsystems': list(manifest['subsystems'])}
(root / 'usr/share/surface-pro-11/build-audit.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
PY
