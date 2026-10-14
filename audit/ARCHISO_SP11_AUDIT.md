# Surface Pro 11 (AArch64) Subsystem Audit: Arch Linux to Fedora Translation

This document provides a technical audit of `dwhinham/archiso-aarch64-sp11` and `dwhinham/archlinux-repo`, detailing the translation path to **Fedora AArch64 (GNOME Minimal on Wayland)** for the **Microsoft Surface Pro 11 LCD SKU (Snapdragon X Plus X1P-64-100 / Purwa / Hamoa 10-core)**.

---

## 1. Upstream & Archiso Repository Audit

### A. Kernel & Device Tree (`linux-sp11` / `linux-sp11-dtbs`)
- **Archlinux Package:** `linux-sp11` (based on `bschnei/linux` aarch64 branch + `dwhinham/linux-sp11`)
- **Key Kernel Commits & Patches:**
  1. `arm64: dts: qcom: x1-denali: Add PWM backlight for LCD` — Enables backlight on the LCD variant using PMIC LPG / PWM generator.
  2. `arm64: dts: qcom: x1-denali: Mux the eDP HPD pin` — Connects display hot-plug detection for eDP.
  3. `arm64: dts: qcom: x1-denali: Add the touch digitizer` — Adds SPI-HID touch digitizer child node under QSPI.
  4. `HID: spi-hid: Add the device compatible to the SPI id table` & `HID: spi-hid: Use a single full duplex transfer` — Fixes SPI-HID protocol for high polling rates.
  5. `dmaengine: qcom: gpi: Add QSPI protocol support` & `spi: geni-qcom: Add QSPI 1-4-4 support` — Enables 4-lane QSPI data transfers for the touch digitizer.
  6. `firmware: arm_scmi: Always create devices for standard protocols` — SCMI module autoloading fixes.
  7. Kernel cmdline flags:
     ```text
     clk_ignore_unused pd_ignore_unused arm64.nopauth systemd.mask=tpm2.target
     ```
     - `clk_ignore_unused` & `pd_ignore_unused`: Prevents power-management subsystem from turning off unassigned clocks/power domains during early boot.
     - `arm64.nopauth`: Disables ARMv8.3 Pointer Authentication to prevent firmware/hypervisor trap issues.
     - `systemd.mask=tpm2.target`: Bypasses Pluton TPM CRB driver timeout during early boot until upstream patches stabilize.

### B. Wireless Subsystem (`sp11-ath12k-board` & `sp11-mac-fixup`)
- **Wi-Fi 7 (WCN7850 / FastConnect 7800):**
  - Driver: `ath12k` over PCIe (`17cb:1107`).
  - Problem: Device reports `qmi-board-id=255` (unprogrammed in OTP), which fails exact board-2.bin lookup.
  - Workaround: Extract `bus=pci,vendor=17cb,device=1107,subsystem-vendor=17cb,subsystem-device=3378,qmi-chip-id=2,qmi-board-id=255` from `board-2.bin` using Qualcomm's `ath12k-bdencoder` script and install it as `/usr/lib/firmware/ath12k/WCN7850/hw2.0/board.bin`.
- **Bluetooth 5.4 (`btqca`):**
  - Driver: `btqca` / `hci_uart` on QCA UART interface (`/dev/ttyMSM*`).
  - Workaround: `sp11-mac-fixup` service waits for controller initialization and assigns the factory public Bluetooth MAC address using `btmgmt public-addr <MAC>`.

### C. Audio Subsystem (`sp11-audioreach-topology` & `alsa-ucm-conf-sp11`)
- **Audio Architecture:** Qualcomm AudioReach (`q6apm`).
- **Topology:** Built from `linux-msm/audioreach-topology` target `topology_X1E80100-Microsoft-Surface-Pro-11`, installed to `/usr/lib/firmware/qcom/x1e80100/X1E80100-Microsoft-Surface-Pro-11-tplg.bin`.
- **ALSA UCM:** `alsa-project/alsa-ucm-conf#847` patch provides the UCM profile for the Surface Pro 11 sound card (`X1E80100-Microsoft-Surface-Pro-11`).
- **Limitation:** Volume is artificially scaled down to 40% to protect the speakers because the Qualcomm WSA smart amplifier hardware protection loop is not fully enabled in upstream kernel.

### D. Touchscreen & Stylus (`iptsd`)
- **Hardware:** Surface Touch G6 digitizer (`MSHW0484`) over QSPI (`spi-geni-qcom`).
- **Userspace Daemon:** `iptsd` handles raw touch frames from `/dev/hidraw*` and emits standard Linux multitouch & MPP 2.6 pen events.

### E. Surface Type Cover / Flex (`surface_sam`)
- **Bus:** Surface Serial Hub (`SSH`) over `geni_se_qup` UART (`/dev/ttyMSM0` / ACPI `_SB.SSH0`).
- **Drivers:** `surface_aggregator`, `surface_aggregator_registry`, `surface_hid`, `surface_kbd`.
- **Tablet Mode:** `SW_TABLET_MODE` switch triggered when folding back the keyboard.

---

## 2. Fedora AArch64 Translation Strategy

| Component | Arch Linux Implementation | Fedora AArch64 Implementation |
|-----------|---------------------------|--------------------------------|
| **Initramfs** | `mkinitcpio` with custom hooks | **Dracut** (`/etc/dracut.conf.d/sp11.conf`) with `hostonly="no"` |
| **Packaging** | `PKGBUILD` / `pacman` | **RPM `.spec`** / `dnf` |
| **Image Tool** | `mkarchiso` | **`mkosi` / containerized DNF rootfs generator** |
| **Desktop** | Bare console / Archiso CLI | **GNOME Minimal Wayland** (`gnome-shell`, `mutter`, `gdm`, `ptyxis`) |
| **Display Server** | X11 / Wayland optional | **Pure Wayland Session** |
| **Audio Routing** | ALSA + raw UCM | **PipeWire + WirePlumber + ALSA UCM2** |
