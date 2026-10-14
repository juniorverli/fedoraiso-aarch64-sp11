Name:           iptsd
Version:        3.1.0
Release:        1%{?dist}
Summary:        Intel / Microsoft Precise Touch & Stylus Daemon
License:        GPL-2.0-only
URL:            https://github.com/linux-surface/iptsd

BuildRequires:  meson, ninja-build, gcc-c++, git
BuildRequires:  systemd-devel, hidapi-devel, cairo-devel
BuildRequires:  libx11-devel, libxext-devel, libxfixes-devel, libxi-devel
BuildRequires:  libxrandr-devel, libxcursor-devel, cairomm-devel

Requires:       systemd

%description
iptsd is a userspace daemon for devices using the Intel Precise Touch & Stylus (IPTS)
interface or Microsoft G6 / Surface Touch digitizers over SPI/HID. It processes raw touch data
and emits multi-touch and stylus events via uinput.

%prep
# Git clone or unpack v3.1.0

%build
# meson setup build
# meson compile -C build

%install
mkdir -p %{buildroot}%{_bindir}
mkdir -p %{buildroot}%{_unitdir}
mkdir -p %{buildroot}%{_udevrulesdir}
mkdir -p %{buildroot}%{_datadir}/iptsd/presets
mkdir -p %{buildroot}%{_sysconfdir}/iptsd

install -m 0644 %{_sourcedir}/surface-pro-11.conf %{buildroot}%{_datadir}/iptsd/presets/surface-pro-11.conf

%post
%systemd_post iptsd.service

%preun
%systemd_preun iptsd.service

%postun
%systemd_postun_with_restart iptsd.service

%files
%{_bindir}/iptsd
%{_unitdir}/iptsd.service
%{_udevrulesdir}/50-iptsd.rules
%dir %{_datadir}/iptsd
%{_datadir}/iptsd/presets/*
%config(noreplace) %{_sysconfdir}/iptsd.conf

%changelog
* Wed Oct 14 2026 Junior Mverli <juniormverli@surface> - 3.1.0-1
- Initial packaging for Surface Pro 11 on Fedora AArch64
