Name:           iptsd
Version:        3.1.0
Release:        1%{?dist}
Summary:        Intel / Microsoft Precise Touch & Stylus Daemon
License:        GPL-2.0-only
URL:            https://github.com/linux-surface/iptsd

BuildRequires:  meson, ninja-build, gcc, gcc-c++, git
BuildRequires:  systemd-devel, hidapi-devel

Requires:       systemd

%description
iptsd is a userspace daemon for devices using the Intel Precise Touch & Stylus (IPTS)
interface or Microsoft G6 / Surface Touch digitizers over SPI/HID. It processes raw touch data
and emits multi-touch and stylus events via uinput.

%prep
# Unpack source archive
if [ ! -d iptsd-%{version} ]; then
    git clone --depth 1 --branch v%{version} https://github.com/linux-surface/iptsd.git iptsd-%{version} || git clone --depth 1 https://github.com/linux-surface/iptsd.git iptsd-%{version}
fi
cd iptsd-%{version}

%build
cd iptsd-%{version}
meson setup build -Ddebug_tools=[] --prefix=/usr --buildtype=release
ninja -C build

%install
cd iptsd-%{version}
DESTDIR=%{buildroot} ninja -C build install

mkdir -p %{buildroot}%{_unitdir}
mkdir -p %{buildroot}%{_udevrulesdir}
mkdir -p %{buildroot}%{_datadir}/iptsd/
mkdir -p %{buildroot}%{_sysconfdir}/iptsd

install -m 0644 etc/systemd/iptsd@.service.in %{buildroot}%{_unitdir}/iptsd@.service
sed -i 's|@bindir@|%{_bindir}|g' %{buildroot}%{_unitdir}/iptsd@.service

install -m 0644 etc/udev/50-iptsd.rules.in %{buildroot}%{_udevrulesdir}/50-iptsd.rules
sed -i 's|@bindir@|%{_bindir}|g' %{buildroot}%{_udevrulesdir}/50-iptsd.rules

install -m 0644 %{_sourcedir}/surface-pro-11.conf %{buildroot}%{_datadir}/iptsd/surface-pro-11.conf
install -m 0644 %{_sourcedir}/surface-pro-11.conf %{buildroot}%{_sysconfdir}/iptsd/iptsd.conf

%post
%systemd_post iptsd@.service

%preun
%systemd_preun iptsd@.service

%postun
%systemd_postun_with_restart iptsd@.service

%files
%{_bindir}/iptsd
%{_bindir}/iptsd-find-hidraw
%{_bindir}/iptsd-foreach
%{_bindir}/iptsd-check-device
%{_unitdir}/iptsd@.service
%{_udevrulesdir}/50-iptsd.rules
%dir %{_datadir}/iptsd
%{_datadir}/iptsd/*
%config(noreplace) %{_sysconfdir}/iptsd/iptsd.conf

%changelog
* Wed Oct 14 2026 Junior Mverli <juniormverli@surface> - 3.1.0-1
- Full native build for Surface Pro 11 on Fedora AArch64
