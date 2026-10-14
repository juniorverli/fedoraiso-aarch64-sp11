Name:           sp11-mac-fixup
Version:        20261014
Release:        1%{?dist}
Summary:        Wi-Fi and Bluetooth MAC address fixup for Microsoft Surface Pro 11
License:        BSD-3-Clause
URL:            https://github.com/dwhinham/archlinux-repo
BuildArch:      noarch

Requires:       iproute
Requires:       bluez
Requires:       systemd

%description
Applies the factory Wi-Fi and Bluetooth addresses from /etc/sp11-mac.conf to the
Qualcomm WCN7850 wireless controller on the Microsoft Surface Pro 11.

%install
mkdir -p %{buildroot}%{_bindir}
mkdir -p %{buildroot}%{_sysconfdir}
mkdir -p %{buildroot}%{_udevrulesdir}
mkdir -p %{buildroot}%{_unitdir}

install -m 0755 %{_sourcedir}/sp11-mac-fixup %{buildroot}%{_bindir}/sp11-mac-fixup
install -m 0644 %{_sourcedir}/sp11-mac.conf %{buildroot}%{_sysconfdir}/sp11-mac.conf
install -m 0644 %{_sourcedir}/90-sp11-mac.rules %{buildroot}%{_udevrulesdir}/90-sp11-mac.rules
install -m 0644 %{_sourcedir}/sp11-bt-mac@.service %{buildroot}%{_unitdir}/sp11-bt-mac@.service

%files
%{_bindir}/sp11-mac-fixup
%config(noreplace) %{_sysconfdir}/sp11-mac.conf
%{_udevrulesdir}/90-sp11-mac.rules
%{_unitdir}/sp11-bt-mac@.service

%changelog
* Wed Oct 14 2026 Junior Mverli <juniormverli@surface> - 20261014-1
- Ported to Fedora AArch64
