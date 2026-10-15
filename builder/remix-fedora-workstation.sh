#!/bin/bash
# SPDX-License-Identifier: BSD-3-Clause
# Preserve the official Workstation live filesystem and installer, adding Surface support.
set -euo pipefail
WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="$WORKSPACE_DIR/output"
CACHE="$OUTPUT_DIR/cache"
BASE_NAME=Fedora-Workstation-Live-44-1.7.aarch64.iso
BASE_ISO="${FEDORA_BASE_ISO:-$CACHE/$BASE_NAME}"
CHECKSUM="${FEDORA_CHECKSUM_FILE:-$CACHE/Fedora-Workstation-44-1.7-aarch64-CHECKSUM}"
BASE_URL=https://download.fedoraproject.org/pub/fedora/linux/releases/44/Workstation/aarch64/iso
ROOTFS="$OUTPUT_DIR/workstation44-rootfs"
KERNEL_SOURCE="${SURFACE_KERNEL_SOURCE:-$OUTPUT_DIR/rootfs}"
ISO_OUTPUT="${SURFACE_ISO_OUTPUT:-$OUTPUT_DIR/fedora-44-workstation-surface-pro-11-lcd.iso}"
PUBLISHED_EVIDENCE="$OUTPUT_DIR/workstation44-evidence"
[[ $(id -u) == 0 && $(uname -m) == aarch64 ]] || { echo 'Build requires root in native AArch64 Fedora 44.' >&2; exit 1; }
source /etc/os-release
[[ $ID == fedora && $VERSION_ID == 44 ]] || { echo 'Build environment must be Fedora 44.' >&2; exit 1; }
dnf install -y curl gnupg2 fedora-gpg-keys xorriso squashfs-tools erofs-utils e2fsprogs dosfstools mtools rsync dracut dracut-live kmod python3 file dtc grub2-efi-aa64-modules grub2-tools grub2-tools-extra policycoreutils
mkdir -p "$CACHE"
if [[ -n ${SURFACE_RESUME_BUILD:-} ]]; then
    BUILD=$(realpath "$SURFACE_RESUME_BUILD")
    [[ $BUILD == "$OUTPUT_DIR"/.workstation44-build.* && -d $BUILD/iso ]] || {
        echo 'Resume requires an existing extracted ISO under output/.workstation44-build.*' >&2; exit 1;
    }
else
    BUILD=$(mktemp -d "$OUTPUT_DIR/.workstation44-build.XXXXXX")
fi
EVIDENCE="$BUILD/evidence"
mkdir -p "$EVIDENCE"
# Download to temporary names; incomplete transfers can never become base inputs.
if [[ ! -f $BASE_ISO ]]; then
    curl --fail --location --retry 5 "$BASE_URL/$BASE_NAME" -o "$BASE_ISO.downloading"
    mv "$BASE_ISO.downloading" "$BASE_ISO"
fi
if [[ ! -f $CHECKSUM ]]; then
    curl --fail --location --retry 5 "$BASE_URL/Fedora-Workstation-44-1.7-aarch64-CHECKSUM" -o "$CHECKSUM.downloading"
    mv "$CHECKSUM.downloading" "$CHECKSUM"
fi
# Authenticate the published CHECKSUM with Fedora's packaged release key.
GNUPGHOME=$(mktemp -d)
export GNUPGHOME
chmod 700 "$GNUPGHOME"
trap 'rm -rf "$GNUPGHOME"' EXIT
gpg --batch --import /etc/pki/rpm-gpg/RPM-GPG-KEY-fedora-44-primary
gpg --batch --verify "$CHECKSUM" 2> "$EVIDENCE/base-signature.txt"
python3 - "$BASE_ISO" "$CHECKSUM" "$EVIDENCE/base.json" <<'PY'
import hashlib, json, pathlib, re, sys
iso, checksum, report = map(pathlib.Path, sys.argv[1:])
name = 'Fedora-Workstation-Live-44-1.7.aarch64.iso'
matches = re.findall(r'^SHA256 \(' + re.escape(name) + r'\) = ([0-9a-f]{64})$', checksum.read_text(), re.M)
if len(matches) != 1:
    raise SystemExit('Signed checksum lacks the exact Fedora 44 Workstation AArch64 base')
with iso.open('rb') as f:
    actual = hashlib.file_digest(f, 'sha256').hexdigest()
if actual != matches[0]:
    raise SystemExit('Official base SHA256 mismatch; refusing build')
report.write_text(json.dumps({'base_iso': str(iso), 'sha256': actual, 'checksum': str(checksum), 'signature_verified': True}, indent=2) + '\n')
PY
BASE_SHA256=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["sha256"])' "$EVIDENCE/base.json")
if [[ -n ${SURFACE_RESUME_BUILD:-} ]]; then
    [[ -f $BUILD/iso-extraction.complete && $(cat "$BUILD/iso-extraction.complete") == "$BASE_SHA256" ]] || {
        echo 'Resume requires a complete ISO extraction bound to this verified base SHA256' >&2; exit 1;
    }
fi
ISO_TREE="$BUILD/iso"
SQUASH="$BUILD/squash"
MOUNT="$BUILD/mount"
mkdir -p "$ISO_TREE" "$MOUNT"
# Keep recovery information and all remaining build output alongside the artifacts.
printf '%s\n' "$BUILD" > "$EVIDENCE/current-build.txt"
exec > >(tee -a "$BUILD/build.log") 2>&1
cleanup() {
    local status=$?
    trap - EXIT
    mountpoint -q "$ROOTFS/proc" && umount "$ROOTFS/proc" || :
    mountpoint -q "$ROOTFS/sys" && umount -R "$ROOTFS/sys" || :
    mountpoint -q "$ROOTFS/dev" && umount -R "$ROOTFS/dev" || :
    mountpoint -q "$MOUNT" && umount "$MOUNT" || :
    rm -rf "$GNUPGHOME"
    printf '%s\n' "$status" > "$BUILD/exit-status"
    if (( status != 0 )); then
        echo "Build failed (exit $status); retained workspace: $BUILD" >&2
        echo "Build log: $BUILD/build.log; target root: $ROOTFS" >&2
    fi
    exit "$status"
}
trap cleanup EXIT
if [[ -z ${SURFACE_RESUME_BUILD:-} ]]; then
    xorriso -osirrox on -indev "$BASE_ISO" -extract / "$ISO_TREE"
    printf '%s\n' "$BASE_SHA256" > "$BUILD/iso-extraction.complete"
fi
chmod -R u+w "$ISO_TREE"
LIVE_FS_TYPE=$(blkid -p -s TYPE -o value "$ISO_TREE/LiveOS/squashfs.img")
[[ $LIVE_FS_TYPE == erofs ]] || { echo 'Pinned Fedora 44 base must contain EROFS' >&2; exit 1; }
printf '%s\n' "$LIVE_FS_TYPE" > "$BUILD/live-filesystem-type"
if [[ -n ${SURFACE_RESUME_BUILD:-} && -f $BUILD/live-extraction.complete &&
      $(cat "$BUILD/live-extraction.complete") == "$LIVE_FS_TYPE" && -d $SQUASH ]]; then
    echo "Reusing completed $LIVE_FS_TYPE extraction: $SQUASH"
else
    [[ ! -e $SQUASH ]] || mv "$SQUASH" "$BUILD/squash.previous.$(date +%s)"
    fsck.erofs --extract="$SQUASH" --preserve --xattrs "$ISO_TREE/LiveOS/squashfs.img"
    printf '%s\n' "$LIVE_FS_TYPE" > "$BUILD/live-extraction.complete"
fi
# The verified Fedora 44 Workstation 1.7 EROFS contains the live root directly.
[[ -f $SQUASH/usr/lib/os-release && ! -f $SQUASH/LiveOS/rootfs.img ]] || {
    echo 'Pinned Fedora 44 base must contain a direct EROFS root' >&2; exit 1;
}
if [[ -n ${SURFACE_REUSE_ROOTFS:-} && -d $ROOTFS ]]; then
    echo "Reusing prepared rootfs: $ROOTFS"
else
    if [[ -e $ROOTFS ]]; then
        mv "$ROOTFS" "$OUTPUT_DIR/workstation44-rootfs.previous.$(date +%s)"
    fi
    mkdir -p "$ROOTFS"
    rsync -aHAX --numeric-ids "$SQUASH/" "$ROOTFS/"
fi
python3 - "$ROOTFS" <<'PY'
import pathlib, shlex, sys
root = pathlib.Path(sys.argv[1])
p = root / 'usr/lib/os-release'
data = dict(line.split('=', 1) for line in p.read_text().splitlines() if '=' in line)
data = {k: shlex.split(v)[0] if shlex.split(v) else '' for k,v in data.items()}
if not (data.get('ID') == 'fedora' and data.get('VERSION_ID') == '44' and data.get('VARIANT_ID') == 'workstation'):
    raise SystemExit('Base live root is not Fedora 44 Workstation')
if not list((root / 'usr/share/wayland-sessions').glob('*gnome*.desktop')) or not any((root / p).exists() for p in ('usr/bin/anaconda', 'usr/sbin/anaconda')):
    raise SystemExit('Official GNOME Wayland session or Anaconda is absent')
PY
KVER="${SURFACE_KERNEL_VERSION:-7.2.0-sp11-exp}"
[[ -s $KERNEL_SOURCE/usr/lib/modules/$KVER/vmlinuz ]] || { echo "Missing source kernel: $KVER" >&2; exit 1; }
KERNEL_VERSION="$KVER" bash "$WORKSPACE_DIR/builder/install-surface-support.sh" "$ROOTFS" "$KERNEL_SOURCE"
install -Dm644 "$ROOTFS/usr/lib/modules/$KVER/vmlinuz" "$ROOTFS/boot/vmlinuz-sp11"
install -Dm644 "$WORKSPACE_DIR/dts/blobs/x1p64100-microsoft-denali.dtb" "$ROOTFS/boot/dtb-sp11/qcom/x1p64100-microsoft-denali.dtb"
[[ -d $ROOTFS/usr/lib/modules/$KVER ]] || { echo "Missing integrated modules for $KVER" >&2; exit 1; }
install -Dm644 "$WORKSPACE_DIR/dracut/sp11.conf" "$ROOTFS/etc/dracut.conf.d/sp11.conf"
# DTB-selected remoteproc firmware is not fully described by module metadata.
# Explicitly include the Surface payload, while retaining generic Fedora firmware.
python3 - "$ROOTFS" "$WORKSPACE_DIR/builder/surface-hardware.json" <<'PY_FW'
import json, pathlib, sys
root = pathlib.Path(sys.argv[1])
paths = []
for directory in ('usr/lib/firmware/qcom/x1e80100', 'usr/lib/firmware/ath12k/WCN7850'):
    paths.extend('/' + str(p.relative_to(root)) for p in (root / directory).rglob('*') if p.is_file())
# Some GPU firmware lives directly under qcom/, outside the machine subtree.
def required_files(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if key == 'required_files':
                yield from child
            else:
                yield from required_files(child)
    elif isinstance(value, list):
        for child in value:
            yield from required_files(child)
for name in required_files(json.loads(pathlib.Path(sys.argv[2]).read_text())):
    if isinstance(name, str) and name.startswith('/usr/lib/firmware/'):
        for suffix in ('', '.xz', '.zst'):
            if (root / (name.lstrip('/') + suffix)).is_file():
                paths.append(name + suffix)
                break
paths = sorted(set(paths))
if any(' ' in p or '\n' in p or '"' in p or '$' in p or '`' in p for p in paths):
    raise SystemExit('Unsupported whitespace or shell characters in firmware path')
(root / 'etc/dracut.conf.d/sp11-firmware.conf').write_text('install_items+=" ' + ' '.join(paths) + ' "\n')
PY_FW
# Extract the configuration embedded in the actual installed custom kernel.
python3 "$WORKSPACE_DIR/builder/verify-surface-image.py" \
    --extract-kernel-config "$ROOTFS/usr/lib/modules/$KVER/vmlinuz" \
    --output-config "$EVIDENCE/kernel.config"
install -m644 "$EVIDENCE/kernel.config" "$ROOTFS/boot/config-$KVER"
mkdir -p "$ROOTFS/proc" "$ROOTFS/sys" "$ROOTFS/dev"
mount -t proc proc "$ROOTFS/proc"
mount --rbind /sys "$ROOTFS/sys"
mount --make-rslave "$ROOTFS/sys"
mount --rbind /dev "$ROOTFS/dev"
mount --make-rslave "$ROOTFS/dev"
chroot "$ROOTFS" depmod -a "$KVER"
# Always rebuild after firmware, modules and all configuration have been installed.
chroot "$ROOTFS" dracut --force --no-hostonly --kver "$KVER" /boot/initramfs-sp11.img
chroot "$ROOTFS" lsinitrd /boot/initramfs-sp11.img > "$EVIDENCE/initramfs.txt"
umount "$ROOTFS/proc"
umount -R "$ROOTFS/sys"
umount -R "$ROOTFS/dev"
install -m644 "$ROOTFS/usr/lib/modules/$KVER/vmlinuz" "$ISO_TREE/vmlinuz-sp11"
install -m644 "$ROOTFS/boot/initramfs-sp11.img" "$ISO_TREE/initramfs-sp11.img"
install -Dm644 "$WORKSPACE_DIR/dts/blobs/x1p64100-microsoft-denali.dtb" "$ISO_TREE/dtb/qcom/x1p64100-microsoft-denali.dtb"
install -Dm644 "$WORKSPACE_DIR/boot/grub/grub.cfg" "$ISO_TREE/EFI/BOOT/grub.cfg"
install -Dm644 "$WORKSPACE_DIR/boot/grub/grub.cfg" "$ISO_TREE/boot/grub/grub.cfg"
install -Dm644 "$WORKSPACE_DIR/boot/loader/entries/fedora-sp11.conf" "$ISO_TREE/loader/entries/fedora-sp11.conf"
install -Dm644 "$WORKSPACE_DIR/boot/loader/loader.conf" "$ISO_TREE/loader/loader.conf"
cat > "$BUILD/early.cfg" <<'GRUB'
search --no-floppy --file --set=root /vmlinuz-sp11
configfile ($root)/EFI/BOOT/grub.cfg
GRUB
# FAT is case insensitive; discard Fedora's lowercase fallback before replacing it.
find "$ISO_TREE/EFI/BOOT" -maxdepth 1 -type f -iname 'bootaa64.efi' -delete
grub2-mkstandalone -O arm64-efi -o "$ISO_TREE/EFI/BOOT/BOOTAA64.EFI" \
    --locales='' --fonts='' \
    --modules='part_gpt part_msdos fat ext2 iso9660 search search_fs_file normal configfile echo test linux fdt all_video reboot halt' \
    "boot/grub/grub.cfg=$BUILD/early.cfg"
# The custom loader is unsigned: remove the official shim fallback to avoid suggesting trust.
rm -f "$ISO_TREE/EFI/BOOT/grubaa64.efi"
mkdir -p "$ISO_TREE/images"
ESP="$ISO_TREE/images/efiboot.img"
ESP_FILES=("$ISO_TREE/vmlinuz-sp11" "$ISO_TREE/initramfs-sp11.img" "$ISO_TREE/dtb" "$ISO_TREE/EFI" "$ISO_TREE/loader")
ESP_MB=$(( ($(du -cm "${ESP_FILES[@]}" | tail -n1 | cut -f1) + 64 + 31) / 32 * 32 ))
rm -f "$ESP"
truncate -s "${ESP_MB}M" "$ESP"
mkfs.vfat -F32 -n SP11_EFI "$ESP"
mmd -i "$ESP" ::EFI ::EFI/BOOT ::boot ::boot/grub ::loader ::loader/entries ::dtb ::dtb/qcom
for dir in EFI/BOOT boot/grub loader/entries dtb/qcom; do
    mcopy -i "$ESP" "$ISO_TREE/$dir/"* "::$dir/"
done
mcopy -i "$ESP" "$ISO_TREE/loader/loader.conf" ::loader/
mcopy -i "$ESP" "$ISO_TREE/vmlinuz-sp11" "$ISO_TREE/initramfs-sp11.img" ::/
# Apply the real Workstation policy to copied and generated Surface files.
# Container host policy is unrelated; never disable enforcement in the target.
FILE_CONTEXTS="$ROOTFS/etc/selinux/targeted/contexts/files/file_contexts"
[[ -s $FILE_CONTEXTS ]] || { echo 'Fedora targeted SELinux file contexts missing' >&2; exit 1; }
setfiles -F -r "$ROOTFS" "$FILE_CONTEXTS" "$ROOTFS" > "$EVIDENCE/selinux-labeling.txt" 2>&1
# A modified ISO tree is no longer eligible for extraction resume.
rm -f "$BUILD/iso-extraction.complete"
# Retain the exact official live filesystem format.
rm -f "$ISO_TREE/LiveOS/squashfs.img"
mkfs.erofs -zlz4hc --preserve-mtime --file-contexts="$FILE_CONTEXTS" --mount-point=/ "$ISO_TREE/LiveOS/squashfs.img" "$ROOTFS"
[[ $(blkid -p -s TYPE -o value "$ISO_TREE/LiveOS/squashfs.img") == "$LIVE_FS_TYPE" ]] || {
    echo 'Repacked live filesystem type differs from the official base' >&2; exit 1;
}
python3 "$WORKSPACE_DIR/builder/verify-surface-image.py" \
    --rootfs "$ROOTFS" --iso-tree "$ISO_TREE" --kernel-version "$KVER" \
    --kernel-config "$EVIDENCE/kernel.config" --base-iso "$BASE_ISO" \
    --base-checksum "$CHECKSUM" --report "$EVIDENCE/pre-master-verification.json"
CANDIDATE="$BUILD/candidate.iso"
xorriso -as mkisofs -iso-level 3 -R -J -V FEDORA_SP11 \
    -A 'Fedora 44 Workstation Surface remix' -e images/efiboot.img \
    -no-emul-boot -efi-boot-part --efi-boot-image -o "$CANDIDATE" "$ISO_TREE"
python3 "$WORKSPACE_DIR/builder/verify-surface-image.py" \
    --rootfs "$ROOTFS" --iso-tree "$ISO_TREE" --kernel-version "$KVER" \
    --kernel-config "$EVIDENCE/kernel.config" --base-iso "$BASE_ISO" \
    --base-checksum "$CHECKSUM" --iso "$CANDIDATE" --report "$EVIDENCE/verification.json"
xorriso -indev "$CANDIDATE" -report_el_torito plain -report_system_area plain > "$EVIDENCE/iso-layout.txt" 2>&1
# Prepare the ISO, checksum and hash-bound evidence before replacing published files.
ISO_SHA256=$(sha256sum "$CANDIDATE" | cut -d' ' -f1)
python3 - "$EVIDENCE/publication.json" "$ISO_OUTPUT" "$ISO_SHA256" <<'PY_PUBLISH'
import json, pathlib, sys
pathlib.Path(sys.argv[1]).write_text(json.dumps({'iso': sys.argv[2], 'sha256': sys.argv[3]}, indent=2) + '\n')
PY_PUBLISH
mkdir -p "$(dirname "$ISO_OUTPUT")"
PUBLISH_STAGE=$(mktemp -d "$(dirname "$ISO_OUTPUT")/.surface-publication.XXXXXX")
cp --reflink=auto "$CANDIDATE" "$PUBLISH_STAGE/image.iso"
[[ $(sha256sum "$PUBLISH_STAGE/image.iso" | cut -d' ' -f1) == "$ISO_SHA256" ]] || {
    echo 'Staged ISO checksum mismatch' >&2; exit 1;
}
printf '%s  %s\n' "$ISO_SHA256" "$(basename "$ISO_OUTPUT")" > "$PUBLISH_STAGE/image.iso.sha256"
EVIDENCE_STAGE=$(mktemp -d "$OUTPUT_DIR/.surface-evidence.XXXXXX")
cp -a "$EVIDENCE/." "$EVIDENCE_STAGE/"
BACKUP_SUFFIX="previous.$(date +%Y%m%d-%H%M%S).$$"
[[ ! -e $ISO_OUTPUT ]] || cp --reflink=auto --preserve=all "$ISO_OUTPUT" "$ISO_OUTPUT.$BACKUP_SUFFIX"
[[ ! -e $ISO_OUTPUT.sha256 ]] || cp --preserve=all "$ISO_OUTPUT.sha256" "$ISO_OUTPUT.sha256.$BACKUP_SUFFIX"
# Remove old associations before replacing the ISO, so failure cannot pair a new
# image with an old checksum or report. Every rename below stays on one filesystem.
[[ ! -e $PUBLISHED_EVIDENCE ]] || mv "$PUBLISHED_EVIDENCE" "$PUBLISHED_EVIDENCE.$BACKUP_SUFFIX"
rm -f "$ISO_OUTPUT.sha256"
mv -f "$PUBLISH_STAGE/image.iso" "$ISO_OUTPUT"
mv -f "$PUBLISH_STAGE/image.iso.sha256" "$ISO_OUTPUT.sha256"
mv "$EVIDENCE_STAGE" "$PUBLISHED_EVIDENCE"
rmdir "$PUBLISH_STAGE"
echo "Validated ISO: $ISO_OUTPUT"
echo "Integration evidence: $PUBLISHED_EVIDENCE"
echo "Retained build workspace: $BUILD"
