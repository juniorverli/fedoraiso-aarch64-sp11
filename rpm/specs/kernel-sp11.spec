# Spec file for Microsoft Surface Pro 11 Kernel (AArch64)
# Targets Qualcomm Snapdragon X Plus (X1P64100) and X Elite (X1E80100)

%define kversion 6.15.0
%define pkgrelease 1.sp11.fc41
%define git_commit 616a9f22113e7dc96e558b4426424ea1d7511092

Name:           kernel-sp11
Version:        %{kversion}
Release:        %{pkgrelease}%{?dist}
Summary:        Linux Kernel tailored for Microsoft Surface Pro 11 (Qualcomm Snapdragon X)
License:        GPL-2.0-only
URL:            https://github.com/dwhinham/linux-sp11
ExclusiveArch:  aarch64

Requires:       kernel-sp11-core = %{version}-%{release}
Requires:       kernel-sp11-modules = %{version}-%{release}
Requires:       kernel-sp11-dtbs = %{version}-%{release}

BuildRequires:  bash, bc, binutils, bison, flex, gcc, git
BuildRequires:  diffutils, elfutils-libelf-devel, openssl-devel
BuildRequires:  perl-interpreter, perl-devel, python3-devel
BuildRequires:  systemd-boot, dracut, kmod, tar, xz, zstd, dtc

%description
The Linux kernel with upstream Qualcomm and Microsoft Surface Aggregator Module (SAM)
patches for the Microsoft Surface Pro 11 (13-inch LCD and OLED variants).

%package core
Summary:        Core kernel image for Microsoft Surface Pro 11
Requires:       dracut
Requires:       systemd >= 250

%description core
The core kernel binary (vmlinuz) and symbol map for Microsoft Surface Pro 11.

%package modules
Summary:        Kernel modules for Microsoft Surface Pro 11
Requires:       kmod

%description modules
Kernel modules for Microsoft Surface Pro 11 peripherals, including Surface Serial Hub,
Adreno GPU, Qualcomm AudioReach, FastConnect Wi-Fi 7, and Type-C Alt-Mode.

%package dtbs
Summary:        Device Tree Blobs for Microsoft Surface Pro 11
BuildArch:      noarch

%description dtbs
Precompiled Device Tree Blobs (DTB) including x1p64100-microsoft-denali.dtb for the LCD model
and x1e80100-microsoft-denali-oled.dtb for the OLED model.

%prep
if [ ! -d linux-sp11 ]; then
    git clone --depth 1 https://github.com/dwhinham/linux-sp11.git linux-sp11
fi

%build
cd linux-sp11
make ARCH=arm64 defconfig
# Enable essential Surface SAM and Qualcomm modules
./scripts/config --enable CONFIG_SURFACE_PLATFORMS
./scripts/config --module CONFIG_SURFACE_AGGREGATOR
./scripts/config --module CONFIG_SURFACE_AGGREGATOR_REGISTRY
./scripts/config --module CONFIG_SURFACE_AGGREGATOR_TABLET_SWITCH
./scripts/config --module CONFIG_SURFACE_HID
./scripts/config --module CONFIG_SURFACE_KBD
./scripts/config --module CONFIG_BATTERY_SURFACE
./scripts/config --module CONFIG_CHARGER_SURFACE
./scripts/config --module CONFIG_SURFACE_PLATFORM_PROFILE
./scripts/config --module CONFIG_DRM_MSM
./scripts/config --module CONFIG_ATH12K
./scripts/config --enable CONFIG_ATH12K_AHB
./scripts/config --module CONFIG_SPI_GENI_QCOM
./scripts/config --module CONFIG_HID_SPI_HID
./scripts/config --module CONFIG_SOUNDWIRE_QCOM
./scripts/config --module CONFIG_SND_SOC_QCOM_COMMON

make -j$(nproc) ARCH=arm64 Image.gz modules dtbs

%install
cd linux-sp11
mkdir -p %{buildroot}/boot/dtb/qcom
mkdir -p %{buildroot}/lib/modules/%{kversion}-sp11

install -m 0755 arch/arm64/boot/Image.gz %{buildroot}/boot/vmlinuz-sp11
install -m 0644 System.map %{buildroot}/boot/System.map-%{kversion}-sp11
install -m 0644 .config %{buildroot}/boot/config-%{kversion}-sp11

# Install device tree blobs
install -m 0644 arch/arm64/boot/dts/qcom/x1p64100-microsoft-denali.dtb %{buildroot}/boot/dtb/qcom/
install -m 0644 arch/arm64/boot/dts/qcom/x1e80100-microsoft-denali-oled.dtb %{buildroot}/boot/dtb/qcom/ || true

# Install kernel modules
make ARCH=arm64 INSTALL_MOD_PATH=%{buildroot} modules_install

%post core
if [ -x /usr/bin/dracut ]; then
    /usr/bin/dracut -f /boot/initramfs-sp11.img %{kversion}-sp11
fi

%files
# Meta-package

%files core
/boot/vmlinuz-sp11
/boot/System.map-%{kversion}-sp11
/boot/config-%{kversion}-sp11

%files modules
/lib/modules/%{kversion}-sp11/*

%files dtbs
/boot/dtb/qcom/x1p64100-microsoft-denali.dtb
/boot/dtb/qcom/x1e80100-microsoft-denali-oled.dtb

%changelog
* Wed Oct 14 2026 Junior Mverli <juniormverli@surface> - 6.15.0-1.sp11.fc41
- Full build and packaging logic for Surface Pro 11 kernel RPM
