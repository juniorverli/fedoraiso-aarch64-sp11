Name:           sp11-ath12k-board
Version:        20261014
Release:        1%{?dist}
Summary:        ath12k board file for Microsoft Surface Pro 11 Wi-Fi (WCN7850)
License:        Redistributable
URL:            https://github.com/qualcomm
BuildArch:      noarch

Requires:       linux-firmware
BuildRequires:  python3
BuildRequires:  zstd

%description
Wi-Fi board file for the Surface Pro 11.
ath12k asks linux-firmware's board-2.bin for:
  bus=pci,vendor=17cb,device=1107,subsystem-vendor=17cb,subsystem-device=1107,qmi-chip-id=2,qmi-board-id=255
Since qmi-board-id=255 was unprogrammed in OTP, this package extracts the matching
calibration entry (subsystem-device=3378) and installs it as board.bin.

%prep

%build

%install
mkdir -p %{buildroot}/usr/lib/firmware/ath12k/WCN7850/hw2.0

%files
/usr/lib/firmware/ath12k/WCN7850/hw2.0/board.bin

%changelog
* Wed Oct 14 2026 Junior Mverli <juniormverli@surface> - 20261014-1
- Initial packaging for Fedora AArch64
