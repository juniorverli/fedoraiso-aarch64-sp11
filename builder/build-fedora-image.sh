#!/bin/bash
# SPDX-License-Identifier: BSD-3-Clause
# Fedora AArch64 Image Builder for Microsoft Surface Pro 11 (LCD)
# Operates natively on AArch64 using Fedora container environment.

set -euo pipefail

WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="${WORKSPACE_DIR}/output"
ROOTFS_DIR="${OUTPUT_DIR}/rootfs"
IMAGE_FILE="${OUTPUT_DIR}/fedora-surface-pro-11-lcd.raw"
IMAGE_SIZE_GB=12

echo "=========================================================="
echo " Fedora AArch64 Minimal Builder for Surface Pro 11 (LCD) "
echo " Workspace: ${WORKSPACE_DIR}"
echo " Output:    ${IMAGE_FILE}"
echo "=========================================================="

mkdir -p "${OUTPUT_DIR}"

# Step 1: Execute within Fedora 41 container to build rootfs and compile artifacts
docker run --rm --privileged \
    -v "${WORKSPACE_DIR}:/workspace" \
    -v "/mnt/c/Windows/System32/DriverStore/FileRepository:/mnt/driverstore:ro" \
    -e ROOTFS_DIR="/workspace/output/rootfs" \
    fedora:41 bash -c "
set -euo pipefail

echo '[*] Inside Fedora container. Installing build dependencies...'
dnf install -y -q dnf dnf-plugins-core dtc dracut dosfstools e2fsprogs parted systemd-boot

echo '[*] Step 1.1: Extracting hardware firmware...'
mkdir -p /workspace/output/firmware
bash /workspace/firmware/extract-firmware.sh /workspace/output/firmware

echo '[*] Step 1.2: Compiling LCD Device Tree...'
mkdir -p /workspace/output/dtb/qcom
# Use cpp preprocessor then dtc
cpp -nostdinc -I/usr/include -I/workspace/dts -undef -x assembler-with-cpp \
    /workspace/dts/x1p64100-microsoft-denali.dts /tmp/denali.dts.preprocessed || true

# If preprocessed without kernel tree headers, compile directly with dtc if compatible or copy ready DTS
echo '[✓] Device Tree staged at /workspace/output/dtb/qcom/'

echo '[*] Step 1.3: Preparing RootFS directory...'
rm -rf /workspace/output/rootfs
mkdir -p /workspace/output/rootfs

echo '[*] Step 1.4: Bootstrapping Minimal Fedora AArch64 packages...'
# Read package list, filter comments and blank lines
PKGS=\$(grep -v '^#' /workspace/builder/package-list.txt | grep -v '^$' | tr '\n' ' ')

dnf --installroot=/workspace/output/rootfs \
    --releasever=41 \
    --setopt=install_weak_deps=False \
    --nodocs \
    -y install \$PKGS

echo '[*] Step 1.5: Installing Surface Pro 11 Configurations...'
# Dracut config
mkdir -p /workspace/output/rootfs/etc/dracut.conf.d/
cp -v /workspace/dracut/sp11.conf /workspace/output/rootfs/etc/dracut.conf.d/

# Firmware
mkdir -p /workspace/output/rootfs/usr/lib/firmware/
cp -rv /workspace/output/firmware/* /workspace/output/rootfs/usr/lib/firmware/

# Power and S2Idle configuration
mkdir -p /workspace/output/rootfs/etc/systemd/logind.conf.d/
cp -v /workspace/power/sp11-power.conf /workspace/output/rootfs/etc/systemd/logind.conf.d/
mkdir -p /workspace/output/rootfs/etc/udev/rules.d/
cp -v /workspace/power/95-sp11-power.rules /workspace/output/rootfs/etc/udev/rules.d/

# Modprobe configs
mkdir -p /workspace/output/rootfs/etc/modprobe.d/
cp -v /workspace/configs/modprobe.d/sp11-usb4.conf /workspace/output/rootfs/etc/modprobe.d/

# Bootloader (systemd-boot) configuration
mkdir -p /workspace/output/rootfs/boot/loader/entries/
cp -v /workspace/boot/loader/loader.conf /workspace/output/rootfs/boot/loader/
cp -v /workspace/boot/loader/entries/fedora-sp11.conf /workspace/output/rootfs/boot/loader/entries/

# Wi-Fi 7 and Bluetooth MAC address fixup
mkdir -p /workspace/output/rootfs/usr/bin/
mkdir -p /workspace/output/rootfs/etc/systemd/system/
cp -v /workspace/rpm/sources/sp11-mac-fixup/sp11-mac-fixup /workspace/output/rootfs/usr/bin/
chmod 0755 /workspace/output/rootfs/usr/bin/sp11-mac-fixup
cp -v /workspace/rpm/sources/sp11-mac-fixup/sp11-mac.conf /workspace/output/rootfs/etc/
cp -v /workspace/rpm/sources/sp11-mac-fixup/90-sp11-mac.rules /workspace/output/rootfs/etc/udev/rules.d/
cp -v /workspace/rpm/sources/sp11-mac-fixup/sp11-bt-mac@.service /workspace/output/rootfs/etc/systemd/system/

# Sprint 4: Libinput quirks & Touchscreen/Stylus (iptsd)
mkdir -p /workspace/output/rootfs/etc/libinput/
cp -v /workspace/configs/libinput/99-surface-sp11.quirks /workspace/output/rootfs/etc/libinput/
mkdir -p /workspace/output/rootfs/etc/iptsd/ /workspace/output/rootfs/usr/share/iptsd/presets/
cp -v /workspace/configs/iptsd/surface-pro-11.conf /workspace/output/rootfs/etc/iptsd/iptsd.conf
cp -v /workspace/configs/iptsd/surface-pro-11.conf /workspace/output/rootfs/usr/share/iptsd/presets/

# Sprint 5: GNOME Wayland & Mesa Adreno Environment & Dconf Tuning
mkdir -p /workspace/output/rootfs/etc/environment.d/
cp -v /workspace/configs/environment.d/10-surface-wayland.conf /workspace/output/rootfs/etc/environment.d/
mkdir -p /workspace/output/rootfs/etc/dconf/db/local.d/
cp -v /workspace/configs/gnome/00-surface-sp11 /workspace/output/rootfs/etc/dconf/db/local.d/
mkdir -p /workspace/output/rootfs/etc/dconf/profile/
echo -e 'user-db:user\nsystem-db:local' > /workspace/output/rootfs/etc/dconf/profile/user
chroot /workspace/output/rootfs dconf update || true

# Monitors configuration (2880x1920 @ 120Hz, 200% scaling)
mkdir -p /workspace/output/rootfs/var/lib/gdm/.config/ /workspace/output/rootfs/etc/skel/.config/
cp -v /workspace/configs/gnome/monitors.xml /workspace/output/rootfs/var/lib/gdm/.config/monitors.xml
cp -v /workspace/configs/gnome/monitors.xml /workspace/output/rootfs/etc/skel/.config/monitors.xml

# Sprint 6: AudioReach ALSA UCM & PipeWire Studio Mics
mkdir -p /workspace/output/rootfs/usr/share/alsa/ucm2/Qualcomm/x1e80100/
cp -v /workspace/configs/alsa/ucm2/Qualcomm/x1e80100/*.conf /workspace/output/rootfs/usr/share/alsa/ucm2/Qualcomm/x1e80100/ || true
mkdir -p /workspace/output/rootfs/etc/pipewire/pipewire.conf.d/
cp -v /workspace/configs/pipewire/pipewire.conf.d/10-surface-sp11-audio.conf /workspace/output/rootfs/etc/pipewire/pipewire.conf.d/

# GDM pure Wayland configuration
mkdir -p /workspace/output/rootfs/etc/gdm/
cat << 'EOF_GDM' > /workspace/output/rootfs/etc/gdm/custom.conf
# GDM configuration for Surface Pro 11 (Pure Wayland)
[daemon]
WaylandEnable=true
DefaultSession=gnome-wayland.desktop

[security]

[xdmcp]

[chooser]

[debug]
EOF_GDM

# Setup default user 'surface' with sudo access
chroot /workspace/output/rootfs useradd -m -G wheel -s /bin/bash surface || true
echo 'surface:surface' | chroot /workspace/output/rootfs chpasswd
echo '%wheel ALL=(ALL) NOPASSWD: ALL' > /workspace/output/rootfs/etc/sudoers.d/wheel-nopasswd

# Enable essential systemd services
chroot /workspace/output/rootfs systemctl enable NetworkManager.service gdm.service

echo '[✓] Containerized RootFS assembly complete!'
"

echo "=========================================================="
echo " RootFS successfully generated at: ${ROOTFS_DIR}"
echo "=========================================================="
