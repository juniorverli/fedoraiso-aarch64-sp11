#!/bin/bash
# SPDX-License-Identifier: BSD-3-Clause
# Fedora AArch64 Image & ISO Builder for Microsoft Surface Pro 11 (LCD)
# Operates natively on AArch64 within Fedora container environment.

set -euo pipefail

WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="${WORKSPACE_DIR}/output"
RAW_IMAGE="${OUTPUT_DIR}/fedora-surface-pro-11-lcd.raw"
ISO_IMAGE="${OUTPUT_DIR}/fedora-surface-pro-11-lcd.iso"
IMAGE_SIZE_GB=8

echo "=========================================================="
echo " Fedora AArch64 Image & ISO Builder for Surface Pro 11 (LCD)"
echo " Workspace: ${WORKSPACE_DIR}"
echo " RAW Image: ${RAW_IMAGE} (${IMAGE_SIZE_GB} GB)"
echo " Live ISO:  ${ISO_IMAGE}"
echo "=========================================================="

mkdir -p "${OUTPUT_DIR}"

DRIVERSTORE_MOUNT=""
if [ -d "/mnt/c/Windows/System32/DriverStore/FileRepository" ]; then
    DRIVERSTORE_MOUNT="-v /mnt/c/Windows/System32/DriverStore/FileRepository:/mnt/driverstore:ro"
fi

KERNEL_PKG_MOUNT=""
if [ -d "/tmp/kernel-sp11" ]; then
    KERNEL_PKG_MOUNT="-v /tmp/kernel-sp11:/pkg:ro"
fi

docker run --rm --privileged \
    -v "${WORKSPACE_DIR}:/workspace" \
    ${DRIVERSTORE_MOUNT} \
    ${KERNEL_PKG_MOUNT} \
    fedora:41 bash -c "
set -euo pipefail

RAW_IMAGE="/workspace/output/fedora-surface-pro-11-lcd.raw"
ISO_IMAGE="/workspace/output/fedora-surface-pro-11-lcd.iso"
IMAGE_SIZE_GB=8

echo '[*] Step 0: Installing build dependencies in container...'
dnf install -y -q dnf dnf-plugins-core dtc dracut dracut-live dosfstools e2fsprogs parted kpartx util-linux rsync git gcc gcc-c++ make cmake m4 alsa-topology-utils meson ninja-build xorriso squashfs-tools mtools zstd tar kmod systemd systemd-udev grub2-efi-aa64 grub2-efi-aa64-modules grub2-tools grub2-tools-extra bison flex

echo '[*] Step 1: Extracting hardware firmware & Wi-Fi calibration...'
mkdir -p /workspace/output/firmware
if [ -d /workspace/firmware/blobs ]; then
    cp -r /workspace/firmware/blobs/* /workspace/output/firmware/
fi
bash /workspace/firmware/extract-firmware.sh /workspace/output/firmware

echo '[*] Step 2: Preparing Device Tree for Surface Pro 11 (LCD)...'
mkdir -p /workspace/output/dtb/qcom /workspace/dts/blobs
echo '[+] Compiling Device Tree for Surface Pro 11 LCD (edp-panel with native GPIO4 enable)...'
if [ ! -d /tmp/linux-sp11 ]; then
    echo '[+] Cloning kernel DTS tree to compile DTB...'
    git clone --depth 1 https://github.com/dwhinham/linux-sp11.git /tmp/linux-sp11
fi
cp -v /workspace/dts/x1p64100-microsoft-denali.dts /tmp/linux-sp11/arch/arm64/boot/dts/qcom/
cp -v /workspace/dts/x1-microsoft-denali.dtsi /tmp/linux-sp11/arch/arm64/boot/dts/qcom/
(
    cd /tmp/linux-sp11
    make ARCH=arm64 defconfig >/dev/null 2>&1
    make ARCH=arm64 qcom/x1p64100-microsoft-denali.dtb
    cp -v arch/arm64/boot/dts/qcom/x1p64100-microsoft-denali.dtb /workspace/output/dtb/qcom/
    cp -v arch/arm64/boot/dts/qcom/x1p64100-microsoft-denali.dtb /workspace/dts/blobs/
)

echo '[*] Step 3: Preparing iptsd Touch & Stylus daemon...'
mkdir -p /workspace/output/bin
if [ ! -f /workspace/output/bin/iptsd ]; then
    echo '[+] Building native iptsd binary...'
    git clone --depth 1 https://github.com/linux-surface/iptsd.git /tmp/iptsd
    (
        cd /tmp/iptsd
        meson setup build -Ddebug_tools=[] --prefix=/usr --buildtype=release
        ninja -C build
        cp -v build/src/iptsd /workspace/output/bin/
    )
fi

echo '[*] Step 4: Preparing AudioReach topology binary...'
if [ ! -f /workspace/output/firmware/qcom/x1e80100/X1E80100-Microsoft-Surface-Pro-11-tplg.bin ]; then
    if [ -f /workspace/firmware/blobs/qcom/x1e80100/X1E80100-Microsoft-Surface-Pro-11-tplg.bin ]; then
        mkdir -p /workspace/output/firmware/qcom/x1e80100
        cp -v /workspace/firmware/blobs/qcom/x1e80100/X1E80100-Microsoft-Surface-Pro-11-tplg.bin /workspace/output/firmware/qcom/x1e80100/
    else
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
fi

echo '[*] Step 5: Preparing Kernel, Modules, and Initramfs...'
mkdir -p /workspace/output/boot /tmp/unpack_kernel
KVER=""
if [ -f /pkg/linux-sp11.pkg.tar.zst ]; then
    tar --zstd -xf /pkg/linux-sp11.pkg.tar.zst -C /tmp/unpack_kernel
    KVER=\$(ls /tmp/unpack_kernel/usr/lib/modules/ | head -n 1)
    echo \"Kernel version detected from package: \$KVER\"
    cp -r /tmp/unpack_kernel/usr/lib/modules/\$KVER /usr/lib/modules/
    depmod -a \$KVER
    cp /tmp/unpack_kernel/usr/lib/modules/\$KVER/vmlinuz /workspace/output/boot/vmlinuz-sp11
fi

if [ -z \"\$KVER\" ]; then
    if [ -d /workspace/output/rootfs/usr/lib/modules ]; then
        KVER=\$(ls /workspace/output/rootfs/usr/lib/modules | head -n 1)
        echo \"Reusing existing kernel version from rootfs: \$KVER\"
        if [ ! -d \"/usr/lib/modules/\$KVER\" ]; then
            cp -r /workspace/output/rootfs/usr/lib/modules/\$KVER /usr/lib/modules/
            depmod -a \$KVER
        fi
        if [ ! -f /workspace/output/boot/vmlinuz-sp11 ] && [ -f \"/workspace/output/rootfs/usr/lib/modules/\$KVER/vmlinuz\" ]; then
            cp -v \"/workspace/output/rootfs/usr/lib/modules/\$KVER/vmlinuz\" /workspace/output/boot/vmlinuz-sp11
        fi
    fi
fi

if [ ! -f /workspace/output/initramfs-sp11.img ]; then
    echo \"[+] Generating Dracut early-boot initramfs for kernel \${KVER}...\"
    cp /workspace/dracut/sp11.conf /etc/dracut.conf.d/
    dracut --force --no-hostonly --kver \"\${KVER}\" /workspace/output/initramfs-sp11.img
fi

echo '[*] Step 6: Bootstrapping RootFS via DNF...'
PKGS=\$(grep -v '^#' /workspace/builder/package-list.txt | grep -v '^$' | tr '\n' ' ')
if [ ! -f /workspace/output/rootfs/usr/bin/bash ]; then
    rm -rf /workspace/output/rootfs
    mkdir -p /workspace/output/rootfs
fi

dnf --installroot=/workspace/output/rootfs \
    --use-host-config \
    --releasever=41 \
    --setopt=install_weak_deps=False \
    --nodocs \
    -y install \$PKGS

echo '[*] Step 7: Installing Custom Surface Pro 11 Configurations into RootFS...'
# Kernel modules & depmod
if [ -n \"\${KVER}\" ] && [ -d \"/tmp/unpack_kernel/usr/lib/modules/\${KVER}\" ]; then
    mkdir -p /workspace/output/rootfs/usr/lib/modules/
    cp -r /tmp/unpack_kernel/usr/lib/modules/\${KVER} /workspace/output/rootfs/usr/lib/modules/
    depmod -a -b /workspace/output/rootfs \${KVER}
fi

# Kernel & Initramfs & DTB in /boot
mkdir -p /workspace/output/rootfs/boot/dtb/qcom/ /workspace/output/rootfs/boot/grub2/
cp -v /workspace/output/boot/vmlinuz-sp11 /workspace/output/rootfs/boot/
cp -v /workspace/output/initramfs-sp11.img /workspace/output/rootfs/boot/
cp -v /workspace/output/dtb/qcom/x1p64100-microsoft-denali.dtb /workspace/output/rootfs/boot/dtb/qcom/
cp -v /workspace/boot/grub/grub.cfg /workspace/output/rootfs/boot/grub2/grub.cfg

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
cp -v /workspace/output/bin/iptsd /workspace/output/rootfs/usr/bin/
chmod 0755 /workspace/output/rootfs/usr/bin/iptsd
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
chroot /workspace/output/rootfs dconf update

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
rm -f /workspace/output/rootfs/etc/udev/hwdb.bin
chroot /workspace/output/rootfs systemd-hwdb update

# Camera Privacy LED
cp -v /workspace/scripts/surface-privacy-led.sh /workspace/output/rootfs/usr/bin/surface-privacy-led.sh
chmod 0755 /workspace/output/rootfs/usr/bin/surface-privacy-led.sh
cp -v /workspace/configs/udev/90-surface-privacy-led.rules /workspace/output/rootfs/etc/udev/rules.d/

# User and service configuration
if ! chroot /workspace/output/rootfs id surface >/dev/null 2>&1; then
    chroot /workspace/output/rootfs useradd -m -G wheel -s /bin/bash surface
fi
echo 'surface:surface' | chroot /workspace/output/rootfs chpasswd
echo '%wheel ALL=(ALL) NOPASSWD: ALL' > /workspace/output/rootfs/etc/sudoers.d/wheel-nopasswd
chroot /workspace/output/rootfs systemctl enable NetworkManager.service gdm.service iio-sensor-proxy.service

echo '[*] Step 8: Generating Partitioned Bootable Disk Image (\${RAW_IMAGE})...'
rm -f \"\${RAW_IMAGE}\"
truncate -s \${IMAGE_SIZE_GB}G \"\${RAW_IMAGE}\"

parted -s \"\${RAW_IMAGE}\" mklabel gpt
parted -s \"\${RAW_IMAGE}\" mkpart ESP fat32 1MiB 513MiB
parted -s \"\${RAW_IMAGE}\" set 1 esp on
parted -s \"\${RAW_IMAGE}\" mkpart fedora-root ext4 513MiB 100%

LOOP_DEV=\$(losetup -Pf --show \"\${RAW_IMAGE}\")
LOOP_NAME=\$(basename \"\${LOOP_DEV}\")
echo \"[+] Bound image to loop device: \${LOOP_DEV}\"
kpartx -av \"\${LOOP_DEV}\"
sleep 1

ESP_DEV=\"/dev/mapper/\${LOOP_NAME}p1\"
ROOT_DEV=\"/dev/mapper/\${LOOP_NAME}p2\"

mkfs.vfat -F 32 -n EFI \"\${ESP_DEV}\"
mkfs.ext4 -F -L fedora-root \"\${ROOT_DEV}\"

MOUNT_DIR=\$(mktemp -d)
mount \"\${ROOT_DEV}\" \"\${MOUNT_DIR}\"
mkdir -p \"\${MOUNT_DIR}/boot/efi\"

echo '[+] Syncing RootFS to RAW image partition...'
rsync -aAX /workspace/output/rootfs/ \"\${MOUNT_DIR}/\"

ROOT_UUID=\$(blkid -s UUID -o value \"\${ROOT_DEV}\")
EFI_UUID=\$(blkid -s UUID -o value \"\${ESP_DEV}\")

cat << EOF_FSTAB > \"\${MOUNT_DIR}/etc/fstab\"
UUID=\${ROOT_UUID}  /           ext4    defaults,noatime    0 1
UUID=\${EFI_UUID}   /boot/efi   vfat    umask=0077,shortname=winnt 0 2
EOF_FSTAB

umount \"\${MOUNT_DIR}\"
rmdir \"\${MOUNT_DIR}\"

echo '[+] Building standalone GRUB2 AArch64 EFI bootloader (BOOTAA64.EFI)...'
cat << 'EOF_EARLY_RAW' > /tmp/early-raw.cfg
set prefix=(\$root)/EFI/BOOT
if [ -e (\$root)/EFI/BOOT/grub.cfg ]; then
    configfile (\$root)/EFI/BOOT/grub.cfg
elif [ -e (\$root)/boot/grub/grub.cfg ]; then
    configfile (\$root)/boot/grub/grub.cfg
elif [ -e (\$root)/grub.cfg ]; then
    configfile (\$root)/grub.cfg
fi
EOF_EARLY_RAW

grub2-mkstandalone \
    --format=arm64-efi \
    --output=/tmp/BOOTAA64.EFI \
    --locales=\"\" \
    --fonts=\"\" \
    --modules=\"part_gpt part_msdos fat ext2 iso9660 search search_fs_file search_fs_uuid search_label normal configfile echo test linux fdt all_video font gfxterm reboot halt\" \
    \"boot/grub/grub.cfg=/tmp/early-raw.cfg\"

echo '[+] Installing GRUB2, DTB, kernel and initramfs into ESP partition with mtools...'
mmd -i \"\${ESP_DEV}\" ::EFI ::EFI/BOOT ::loader ::loader/entries ::dtb ::dtb/qcom
mcopy -i \"\${ESP_DEV}\" /tmp/BOOTAA64.EFI ::EFI/BOOT/BOOTAA64.EFI
mcopy -i \"\${ESP_DEV}\" /workspace/boot/grub/grub.cfg ::EFI/BOOT/grub.cfg
mcopy -i \"\${ESP_DEV}\" /workspace/output/rootfs/usr/lib/systemd/boot/efi/systemd-bootaa64.efi ::EFI/BOOT/systemd-bootaa64.efi
mcopy -i \"\${ESP_DEV}\" /workspace/boot/loader/loader.conf ::loader/loader.conf
mcopy -i \"\${ESP_DEV}\" /workspace/boot/loader/entries/fedora-sp11.conf ::loader/entries/fedora-sp11.conf
mcopy -i \"\${ESP_DEV}\" /workspace/output/dtb/qcom/x1p64100-microsoft-denali.dtb ::dtb/qcom/x1p64100-microsoft-denali.dtb
mcopy -i \"\${ESP_DEV}\" /workspace/output/boot/vmlinuz-sp11 ::vmlinuz-sp11
mcopy -i \"\${ESP_DEV}\" /workspace/output/initramfs-sp11.img ::initramfs-sp11.img

kpartx -dv \"\${LOOP_DEV}\"
losetup -d \"\${LOOP_DEV}\"
echo '[✓] RAW disk image fedora-surface-pro-11-lcd.raw built successfully!'

echo '[*] Step 9: Generating UEFI Bootable Live ISO (\${ISO_IMAGE})...'
ISO_ROOT=/tmp/iso_root
rm -rf \"\${ISO_ROOT}\"
mkdir -p \"\${ISO_ROOT}/LiveOS\" \"\${ISO_ROOT}/images\" \"\${ISO_ROOT}/EFI/BOOT\" \"\${ISO_ROOT}/loader/entries\" \"\${ISO_ROOT}/dtb/qcom\"

echo '[+] Creating rootfs ext4 image for LiveOS...'
ROOTFS_IMG=/tmp/rootfs.img
rm -f \"\${ROOTFS_IMG}\"
ROOTFS_SIZE_MB=\$(du -sm /workspace/output/rootfs | awk '{print int(\$1 * 1.35 + 512)}')
echo \"Calculated rootfs image size: \${ROOTFS_SIZE_MB} MB\"
truncate -s \${ROOTFS_SIZE_MB}M \"\${ROOTFS_IMG}\"
mkfs.ext4 -F -L fedora-root \"\${ROOTFS_IMG}\"

MNT_LIVE=\$(mktemp -d)
mount -o loop \"\${ROOTFS_IMG}\" \"\${MNT_LIVE}\"
rsync -aAX /workspace/output/rootfs/ \"\${MNT_LIVE}/\"
umount \"\${MNT_LIVE}\"
rmdir \"\${MNT_LIVE}\"
e2fsck -fy \"\${ROOTFS_IMG}\" || [ \$? -le 2 ]
resize2fs -M \"\${ROOTFS_IMG}\"

echo '[+] Compressing LiveOS squashfs.img...'
SQUASH_SRC=/tmp/squash_src
rm -rf \"\${SQUASH_SRC}\"
mkdir -p \"\${SQUASH_SRC}/LiveOS\"
mv \"\${ROOTFS_IMG}\" \"\${SQUASH_SRC}/LiveOS/rootfs.img\"
mksquashfs \"\${SQUASH_SRC}\" \"\${ISO_ROOT}/LiveOS/squashfs.img\" -comp zstd -noappend

echo '[+] Setting up UEFI boot directory tree for Live ISO...'
mkdir -p \"\${ISO_ROOT}/EFI/BOOT\" \"\${ISO_ROOT}/boot/grub\" \"\${ISO_ROOT}/loader/entries\" \"\${ISO_ROOT}/dtb/qcom\"

cat << 'EOF_EARLY_ISO' > /tmp/early-iso.cfg
set prefix=(\$root)/EFI/BOOT
if [ -e (\$root)/EFI/BOOT/grub.cfg ]; then
    configfile (\$root)/EFI/BOOT/grub.cfg
elif [ -e (\$root)/boot/grub/grub.cfg ]; then
    configfile (\$root)/boot/grub/grub.cfg
elif [ -e (\$root)/grub.cfg ]; then
    configfile (\$root)/grub.cfg
fi
EOF_EARLY_ISO

grub2-mkstandalone \
    --format=arm64-efi \
    --output=\"\${ISO_ROOT}/EFI/BOOT/BOOTAA64.EFI\" \
    --locales=\"\" \
    --fonts=\"\" \
    --modules=\"part_gpt part_msdos fat ext2 iso9660 search search_fs_file search_fs_uuid search_label normal configfile echo test linux fdt all_video font gfxterm reboot halt\" \
    \"boot/grub/grub.cfg=/tmp/early-iso.cfg\"

cp -v /workspace/output/rootfs/usr/lib/systemd/boot/efi/systemd-bootaa64.efi \"\${ISO_ROOT}/EFI/BOOT/systemd-bootaa64.efi\"
cp -v /workspace/output/boot/vmlinuz-sp11 \"\${ISO_ROOT}/vmlinuz-sp11\"
cp -v /workspace/output/initramfs-sp11.img \"\${ISO_ROOT}/initramfs-sp11.img\"
cp -v /workspace/output/dtb/qcom/x1p64100-microsoft-denali.dtb \"\${ISO_ROOT}/dtb/qcom/\"

cat << 'EOF_LOADER' > \"\${ISO_ROOT}/loader/loader.conf\"
default fedora-sp11-live.conf
timeout 5
console-mode max
editor yes
EOF_LOADER

cat << 'EOF_ENTRY' > \"\${ISO_ROOT}/loader/entries/fedora-sp11-live.conf\"
title      Fedora Linux 41 Live (Microsoft Surface Pro 11 LCD)
linux      /vmlinuz-sp11
initrd     /initramfs-sp11.img
devicetree /dtb/qcom/x1p64100-microsoft-denali.dtb
options    root=live:CDLABEL=FEDORA_SP11 rd.live.image clk_ignore_unused pd_ignore_unused arm64.nopauth systemd.mask=tpm2.target console=tty0 earlycon
EOF_ENTRY

cat << 'EOF_GRUB' > \"\${ISO_ROOT}/EFI/BOOT/grub.cfg\"
set default=\"0\"
set timeout=5

# Load partition and filesystem modules
insmod part_gpt
insmod part_msdos
insmod fat
insmod iso9660

# Video and console output
insmod all_video
set gfxmode=auto
set gfxpayload=keep
terminal_output console

menuentry \"Fedora Linux 41 Live (Microsoft Surface Pro 11 LCD)\" --class fedora --class gnu-linux --class gnu --class os {
    echo \"Loading Device Tree: /dtb/qcom/x1p64100-microsoft-denali.dtb...\"
    devicetree /dtb/qcom/x1p64100-microsoft-denali.dtb
    echo \"Loading Linux Kernel: /vmlinuz-sp11...\"
    linux /vmlinuz-sp11 root=live:CDLABEL=FEDORA_SP11 rd.live.image clk_ignore_unused pd_ignore_unused arm64.nopauth systemd.mask=tpm2.target console=tty0 earlycon
    echo \"Loading Initial RAM Disk: /initramfs-sp11.img...\"
    initrd /initramfs-sp11.img
    echo \"Booting Surface Pro 11 Live...\"
}

menuentry \"Fedora Linux 41 Live (Safe Graphics / Nomodeset)\" --class fedora --class gnu-linux --class gnu --class os {
    echo \"Loading Device Tree: /dtb/qcom/x1p64100-microsoft-denali.dtb...\"
    devicetree /dtb/qcom/x1p64100-microsoft-denali.dtb
    echo \"Loading Linux Kernel in safe mode...\"
    linux /vmlinuz-sp11 root=live:CDLABEL=FEDORA_SP11 rd.live.image clk_ignore_unused pd_ignore_unused arm64.nopauth systemd.mask=tpm2.target nomodeset console=tty0 earlycon
    echo \"Loading Initial RAM Disk...\"
    initrd /initramfs-sp11.img
    echo \"Booting...\"
}

menuentry \"UEFI Firmware Settings\" --id 'uefi-firmware' {
    fwsetup
}

menuentry \"Reboot System\" --class reboot {
    reboot
}

menuentry \"Shutdown System\" --class shutdown {
    halt
}
EOF_GRUB
cp -v \"\${ISO_ROOT}/EFI/BOOT/grub.cfg\" \"\${ISO_ROOT}/boot/grub/grub.cfg\"

echo '[+] Creating FAT32 efiboot.img with mtools...'
EFIBOOT_IMG=\"\${ISO_ROOT}/images/efiboot.img\"
truncate -s 128M \"\${EFIBOOT_IMG}\"
mkfs.vfat -F 32 -n \"EFI\" \"\${EFIBOOT_IMG}\"

mmd -i \"\${EFIBOOT_IMG}\" ::EFI ::EFI/BOOT ::boot ::boot/grub ::loader ::loader/entries ::dtb ::dtb/qcom
mcopy -i \"\${EFIBOOT_IMG}\" \"\${ISO_ROOT}/EFI/BOOT/BOOTAA64.EFI\" ::EFI/BOOT/
mcopy -i \"\${EFIBOOT_IMG}\" \"\${ISO_ROOT}/EFI/BOOT/grub.cfg\" ::EFI/BOOT/
mcopy -i \"\${EFIBOOT_IMG}\" \"\${ISO_ROOT}/EFI/BOOT/grub.cfg\" ::boot/grub/
mcopy -i \"\${EFIBOOT_IMG}\" \"\${ISO_ROOT}/EFI/BOOT/systemd-bootaa64.efi\" ::EFI/BOOT/
mcopy -i \"\${EFIBOOT_IMG}\" \"\${ISO_ROOT}/loader/loader.conf\" ::loader/
mcopy -i \"\${EFIBOOT_IMG}\" \"\${ISO_ROOT}/loader/entries/fedora-sp11-live.conf\" ::loader/entries/
mcopy -i \"\${EFIBOOT_IMG}\" \"\${ISO_ROOT}/dtb/qcom/x1p64100-microsoft-denali.dtb\" ::dtb/qcom/
mcopy -i \"\${EFIBOOT_IMG}\" \"\${ISO_ROOT}/vmlinuz-sp11\" ::/
mcopy -i \"\${EFIBOOT_IMG}\" \"\${ISO_ROOT}/initramfs-sp11.img\" ::/

echo '[+] Mastering hybrid UEFI AArch64 ISO with xorriso...'
rm -f \"\${ISO_IMAGE}\"
xorriso -as mkisofs \
    -iso-level 3 \
    -R -J \
    -volid \"FEDORA_SP11\" \
    -appid \"Fedora-SP11-Live\" \
    -publisher \"Surface Linux Team\" \
    -preparer \"Antigravity\" \
    -e images/efiboot.img \
    -no-emul-boot \
    -efi-boot-part --efi-boot-image \
    -output \"\${ISO_IMAGE}\" \
    \"\${ISO_ROOT}\"

echo '[✓] Live ISO fedora-surface-pro-11-lcd.iso built successfully!'

echo '[*] Step 10: Validating Artifacts...'
echo '=== RAW IMAGE INSPECTION ==='
parted -s \"\${RAW_IMAGE}\" print
LOOP_RAW=\$(losetup -Pf --show \"\${RAW_IMAGE}\")
LOOP_RAW_NAME=\$(basename \"\${LOOP_RAW}\")
kpartx -av \"\${LOOP_RAW}\"
sleep 1

echo '[+] RAW ESP Partition Contents (inspected via mtools):'
mdir -i \"/dev/mapper/\${LOOP_RAW_NAME}p1\" -/ ::

MNT_VAL=\$(mktemp -d)
mount \"/dev/mapper/\${LOOP_RAW_NAME}p2\" \"\${MNT_VAL}\"
echo '[+] RAW Root Partition Key Components:'
ls -lh \"\${MNT_VAL}/usr/bin/iptsd\"
ls -lh \"\${MNT_VAL}/boot/vmlinuz-sp11\"
ls -lh \"\${MNT_VAL}/boot/initramfs-sp11.img\"
ls -lh \"\${MNT_VAL}/boot/dtb/qcom/x1p64100-microsoft-denali.dtb\"
ls -lh \"\${MNT_VAL}/usr/lib/firmware/ath12k/WCN7850/hw2.0/board.bin\"
ls -lh \"\${MNT_VAL}/usr/lib/firmware/qcom/x1e80100/X1E80100-Microsoft-Surface-Pro-11-tplg.bin\"
ls -lh \"\${MNT_VAL}/usr/lib/firmware/qcom/x1e80100/microsoft/Denali/qcadsp8380.mbn\"
ls -lh \"\${MNT_VAL}/usr/lib/modules/7.2.8-arch1-3-sp11/kernel/drivers/hid/surface-hid/surface_kbd.ko.zst\"
umount \"\${MNT_VAL}\"
rmdir \"\${MNT_VAL}\"
kpartx -dv \"\${LOOP_RAW}\"
losetup -d \"\${LOOP_RAW}\"

echo '=== ISO IMAGE INSPECTION ==='
xorriso -indev \"\${ISO_IMAGE}\" -report_system_area as_mkisofs
MNT_ISO=\$(mktemp -d)
mount -o loop \"\${ISO_IMAGE}\" \"\${MNT_ISO}\"
echo '[+] ISO Root Directory:'
ls -lR \"\${MNT_ISO}\"

echo '[+] efiboot.img Contents (inspected via mtools):'
mdir -i \"\${MNT_ISO}/images/efiboot.img\" -/ ::

echo '[+] Inspecting LiveOS squashfs.img:'
unsquashfs -l \"\${MNT_ISO}/LiveOS/squashfs.img\" | head -n 30

umount \"\${MNT_ISO}\"
rmdir \"\${MNT_ISO}\"

echo '=== CHECKSUMS & ARTIFACT DETAILS ==='
sha256sum \"\${RAW_IMAGE}\" \"\${ISO_IMAGE}\"
ls -lh \"\${RAW_IMAGE}\" \"\${ISO_IMAGE}\"
"

echo "=========================================================="
echo " BUILD AND VALIDATION COMPLETE!"
echo " Artifacts:"
ls -lh "${RAW_IMAGE}"
ls -lh "${ISO_IMAGE}"
sha256sum "${RAW_IMAGE}" "${ISO_IMAGE}"
echo "=========================================================="
