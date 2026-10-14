#!/bin/bash
# SPDX-License-Identifier: BSD-3-Clause
# Fedora AArch64 Image Builder for Microsoft Surface Pro 11 (LCD)
# Operates natively on AArch64 within Fedora container environment.

set -euo pipefail

WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="${WORKSPACE_DIR}/output"
ROOTFS_DIR="${OUTPUT_DIR}/rootfs"
IMAGE_FILE="${OUTPUT_DIR}/fedora-surface-pro-11-lcd.raw"
IMAGE_SIZE_GB=8

echo "=========================================================="
echo " Fedora AArch64 Minimal Builder for Surface Pro 11 (LCD) "
echo " Workspace: ${WORKSPACE_DIR}"
echo " Image:     ${IMAGE_FILE} (${IMAGE_SIZE_GB} GB)"
echo "=========================================================="

mkdir -p "${OUTPUT_DIR}"

DRIVERSTORE_MOUNT=""
if [ -d "/mnt/c/Windows/System32/DriverStore/FileRepository" ]; then
    DRIVERSTORE_MOUNT="-v /mnt/c/Windows/System32/DriverStore/FileRepository:/mnt/driverstore:ro"
fi

docker run --rm --privileged \
    -v "${WORKSPACE_DIR}:/workspace" \
    ${DRIVERSTORE_MOUNT} \
    fedora:41 bash -c "
set -euo pipefail

echo '[*] Installing build dependencies in builder container...'
dnf install -y -q dnf dnf-plugins-core dtc dracut dosfstools e2fsprogs parted util-linux rsync git gcc gcc-c++ make cmake m4 alsa-topology-utils meson ninja-build

echo '[*] Step 1: Extracting hardware firmware & Wi-Fi calibration...'
bash /workspace/firmware/extract-firmware.sh /workspace/output/firmware

echo '[*] Step 2: Compiling Device Tree for Surface Pro 11 (LCD)...'
mkdir -p /workspace/output/dtb/qcom
if [ ! -f /workspace/output/dtb/qcom/x1p64100-microsoft-denali.dtb ]; then
    echo '[+] Cloning kernel DTS tree to compile DTB...'
    git clone --depth 1 https://github.com/dwhinham/linux-sp11.git /tmp/linux-sp11
    cp /workspace/dts/x1p64100-microsoft-denali.dts /tmp/linux-sp11/arch/arm64/boot/dts/qcom/
    cp /workspace/dts/x1-microsoft-denali.dtsi /tmp/linux-sp11/arch/arm64/boot/dts/qcom/
    (
        cd /tmp/linux-sp11
        make ARCH=arm64 defconfig >/dev/null 2>&1
        make ARCH=arm64 qcom/x1p64100-microsoft-denali.dtb
        cp -v arch/arm64/boot/dts/qcom/x1p64100-microsoft-denali.dtb /workspace/output/dtb/qcom/
    )
fi

echo '[*] Step 3: Compiling iptsd Touch & Stylus daemon...'
mkdir -p /workspace/output/bin
if [ ! -f /workspace/output/bin/iptsd ]; then
    echo '[+] Building native iptsd binary...'
    git clone --depth 1 https://github.com/linux-surface/iptsd.git /tmp/iptsd
    (
        cd /tmp/iptsd
        meson setup build -Ddebug_tools=[] --prefix=/usr --buildtype=release
        ninja -C build
        cp -v build/src/iptsd /workspace/output/bin/
        cp -v build/src/iptsd-* /workspace/output/bin/ || true
    )
fi

echo '[*] Step 4: Compiling AudioReach topology binary...'
if [ ! -f /workspace/output/firmware/qcom/x1e80100/X1E80100-Microsoft-Surface-Pro-11-tplg.bin ]; then
    echo '[+] Building X1E80100-Microsoft-Surface-Pro-11-tplg.bin...'
    git clone --depth 1 https://github.com/linux-msm/audioreach-topology.git /tmp/audioreach
    (
        cd /tmp/audioreach
        cmake -B build -S .
        cmake --build build --target topology_X1E80100-Microsoft-Surface-Pro-11
        mkdir -p /workspace/output/firmware/qcom/x1e80100
        cp -v build/qcom/x1e80100/X1E80100-Microsoft-Surface-Pro-11-tplg.bin /workspace/output/firmware/qcom/x1e80100/
    )
fi

echo '[*] Step 5: Bootstrapping RootFS via DNF...'
rm -rf /workspace/output/rootfs
mkdir -p /workspace/output/rootfs
PKGS=\$(grep -v '^#' /workspace/builder/package-list.txt | grep -v '^$' | tr '\n' ' ')

dnf --installroot=/workspace/output/rootfs \
    --releasever=41 \
    --setopt=install_weak_deps=False \
    --nodocs \
    -y install \$PKGS

echo '[*] Step 6: Installing Custom Surface Pro 11 Configurations into RootFS...'
# Dracut
mkdir -p /workspace/output/rootfs/etc/dracut.conf.d/
cp -v /workspace/dracut/sp11.conf /workspace/output/rootfs/etc/dracut.conf.d/

# Firmware
mkdir -p /workspace/output/rootfs/usr/lib/firmware/
cp -rv /workspace/output/firmware/* /workspace/output/rootfs/usr/lib/firmware/

# Power & S2Idle
mkdir -p /workspace/output/rootfs/etc/systemd/logind.conf.d/ /workspace/output/rootfs/etc/udev/rules.d/
cp -v /workspace/power/sp11-power.conf /workspace/output/rootfs/etc/systemd/logind.conf.d/
cp -v /workspace/power/95-sp11-power.rules /workspace/output/rootfs/etc/udev/rules.d/

# Modprobe
mkdir -p /workspace/output/rootfs/etc/modprobe.d/
cp -v /workspace/configs/modprobe.d/sp11-usb4.conf /workspace/output/rootfs/etc/modprobe.d/

# Wi-Fi 7 & BT MAC fixup
mkdir -p /workspace/output/rootfs/usr/bin/ /workspace/output/rootfs/etc/systemd/system/
cp -v /workspace/rpm/sources/sp11-mac-fixup/sp11-mac-fixup /workspace/output/rootfs/usr/bin/
chmod 0755 /workspace/output/rootfs/usr/bin/sp11-mac-fixup
cp -v /workspace/rpm/sources/sp11-mac-fixup/sp11-mac.conf /workspace/output/rootfs/etc/
cp -v /workspace/rpm/sources/sp11-mac-fixup/90-sp11-mac.rules /workspace/output/rootfs/etc/udev/rules.d/
cp -v /workspace/rpm/sources/sp11-mac-fixup/sp11-bt-mac@.service /workspace/output/rootfs/etc/systemd/system/

# iptsd Daemon & Presets
cp -v /workspace/output/bin/iptsd* /workspace/output/rootfs/usr/bin/
chmod 0755 /workspace/output/rootfs/usr/bin/iptsd*
mkdir -p /workspace/output/rootfs/etc/iptsd/ /workspace/output/rootfs/usr/share/iptsd/
cp -v /workspace/configs/iptsd/surface-pro-11.conf /workspace/output/rootfs/etc/iptsd/iptsd.conf
cp -v /workspace/configs/iptsd/surface-pro-11.conf /workspace/output/rootfs/usr/share/iptsd/
cp -v /workspace/configs/iptsd/50-iptsd.rules /workspace/output/rootfs/etc/udev/rules.d/
cp -v /workspace/configs/iptsd/iptsd@.service /workspace/output/rootfs/etc/systemd/system/

# Touchpad Quirks
mkdir -p /workspace/output/rootfs/etc/libinput/
cp -v /workspace/configs/libinput/99-surface-sp11.quirks /workspace/output/rootfs/etc/libinput/

# GNOME Wayland & 120Hz Display
mkdir -p /workspace/output/rootfs/etc/environment.d/ /workspace/output/rootfs/etc/dconf/db/local.d/ /workspace/output/rootfs/etc/dconf/profile/
cp -v /workspace/configs/environment.d/10-surface-wayland.conf /workspace/output/rootfs/etc/environment.d/
cp -v /workspace/configs/gnome/00-surface-sp11 /workspace/output/rootfs/etc/dconf/db/local.d/
echo -e 'user-db:user\nsystem-db:local' > /workspace/output/rootfs/etc/dconf/profile/user
chroot /workspace/output/rootfs dconf update || true

mkdir -p /workspace/output/rootfs/var/lib/gdm/.config/ /workspace/output/rootfs/etc/skel/.config/
cp -v /workspace/configs/gnome/monitors.xml /workspace/output/rootfs/var/lib/gdm/.config/monitors.xml
cp -v /workspace/configs/gnome/monitors.xml /workspace/output/rootfs/etc/skel/.config/monitors.xml

# GDM Pure Wayland
mkdir -p /workspace/output/rootfs/etc/gdm/
cat << 'EOF_GDM' > /workspace/output/rootfs/etc/gdm/custom.conf
[daemon]
WaylandEnable=true
DefaultSession=gnome-wayland.desktop
EOF_GDM

# AudioReach ALSA UCM & PipeWire
mkdir -p /workspace/output/rootfs/usr/share/alsa/ucm2/Qualcomm/x1e80100/
cp -v /workspace/configs/alsa/ucm2/Qualcomm/x1e80100/*.conf /workspace/output/rootfs/usr/share/alsa/ucm2/Qualcomm/x1e80100/
mkdir -p /workspace/output/rootfs/etc/pipewire/pipewire.conf.d/
cp -v /workspace/configs/pipewire/pipewire.conf.d/10-surface-sp11-audio.conf /workspace/output/rootfs/etc/pipewire/pipewire.conf.d/

# Sensors & NPU
mkdir -p /workspace/output/rootfs/usr/share/qcom/ /workspace/output/rootfs/etc/udev/hwdb.d/
cp -v /workspace/configs/qcom/*.jsn /workspace/output/rootfs/usr/share/qcom/
cp -v /workspace/configs/udev/61-surface-sp11-sensor.hwdb /workspace/output/rootfs/etc/udev/hwdb.d/
cp -v /workspace/configs/udev/99-fastrpc.rules /workspace/output/rootfs/etc/udev/rules.d/
chroot /workspace/output/rootfs systemd-hwdb update || true

# User and service configuration
chroot /workspace/output/rootfs useradd -m -G wheel -s /bin/bash surface || true
echo 'surface:surface' | chroot /workspace/output/rootfs chpasswd
echo '%wheel ALL=(ALL) NOPASSWD: ALL' > /workspace/output/rootfs/etc/sudoers.d/wheel-nopasswd
chroot /workspace/output/rootfs systemctl enable NetworkManager.service gdm.service iio-sensor-proxy.service

echo '[*] Step 7: Generating Partitioned Bootable Disk Image (${IMAGE_FILE})...'
rm -f \"${IMAGE_FILE}\"
truncate -s ${IMAGE_SIZE_GB}G \"${IMAGE_FILE}\"

parted -s \"${IMAGE_FILE}\" mklabel gpt
parted -s \"${IMAGE_FILE}\" mkpart ESP fat32 1MiB 513MiB
parted -s \"${IMAGE_FILE}\" set 1 esp on
parted -s \"${IMAGE_FILE}\" mkpart fedora-root ext4 513MiB 100%

LOOP_DEV=\$(losetup -Pf --show \"${IMAGE_FILE}\")
echo \"[+] Bound image to loop device: \${LOOP_DEV}\"

mkfs.vfat -F 32 -n EFI \"\${LOOP_DEV}p1\"
mkfs.ext4 -F -L fedora-root \"\${LOOP_DEV}p2\"

MOUNT_DIR=\$(mktemp -d)
mount \"\${LOOP_DEV}p2\" \"\${MOUNT_DIR}\"
mkdir -p \"\${MOUNT_DIR}/boot/efi\"
mount \"\${LOOP_DEV}p1\" \"\${MOUNT_DIR}/boot/efi\"

echo '[+] Syncing RootFS to image partition...'
rsync -aAX /workspace/output/rootfs/ \"\${MOUNT_DIR}/\"

# Setup fstab
ROOT_UUID=\$(blkid -s UUID -o value \"\${LOOP_DEV}p2\")
EFI_UUID=\$(blkid -s UUID -o value \"\${LOOP_DEV}p1\")

cat << EOF_FSTAB > \"\${MOUNT_DIR}/etc/fstab\"
UUID=\${ROOT_UUID}  /           ext4    defaults,noatime    0 1
UUID=\${EFI_UUID}   /boot/efi   vfat    umask=0077,shortname=winnt 0 2
EOF_FSTAB

# Install bootloader entries & DTB into EFI System Partition
mkdir -p \"\${MOUNT_DIR}/boot/efi/loader/entries\"
mkdir -p \"\${MOUNT_DIR}/boot/efi/dtb/qcom\"
cp -v /workspace/boot/loader/loader.conf \"\${MOUNT_DIR}/boot/efi/loader/\"
cp -v /workspace/boot/loader/entries/fedora-sp11.conf \"\${MOUNT_DIR}/boot/efi/loader/entries/\"
cp -v /workspace/output/dtb/qcom/x1p64100-microsoft-denali.dtb \"\${MOUNT_DIR}/boot/efi/dtb/qcom/\"

# Copy kernel image if present in rootfs
KERNEL_BIN=\$(find \"\${MOUNT_DIR}/boot\" -maxdepth 1 -name 'vmlinuz*' | head -n 1 || true)
if [ -n \"\${KERNEL_BIN}\" ]; then
    cp -v \"\${KERNEL_BIN}\" \"\${MOUNT_DIR}/boot/efi/vmlinuz-sp11\"
fi

echo '[+] Cleaning up loop mounts...'
umount \"\${MOUNT_DIR}/boot/efi\"
umount \"\${MOUNT_DIR}\"
rmdir \"\${MOUNT_DIR}\"
losetup -d \"\${LOOP_DEV}\"

echo '[✓] Disk image fedora-surface-pro-11-lcd.raw built successfully!'
"

echo "=========================================================="
echo " BUILD COMPLETE!"
echo " Artifacts created:"
ls -lh "${OUTPUT_DIR}/fedora-surface-pro-11-lcd.raw" || true
echo "=========================================================="
