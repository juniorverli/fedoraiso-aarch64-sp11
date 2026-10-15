# fedoraiso-aarch64-sp11

**Fedora Workstation 44 AArch64 Remix for Microsoft Surface Pro 11th Edition (Snapdragon X Plus `X1P64100` / PixelSense Flow LCD)**

This repository provides an automated build system, device tree, kernel patches, firmware packaging, and configuration to create an installation and live image of Fedora Workstation 44 (AArch64) optimized for the Microsoft Surface Pro 11 LCD edition.

---

## 1. Hardware Specifications & Target Platform

- **Device SKU:** Microsoft Surface Pro 11th Edition (13-inch LCD, Model 2076 / Denali)
- **SoC:** Qualcomm Snapdragon X Plus (`X1P-64-100` @ 3.40 GHz, 10 Oryon CPU cores)
- **Display:** 13" PixelSense Flow LCD (2880 x 1920 @ 120Hz via eDP)
- **Backlight Control:** PWM / Enable strictly routed through PMIC GPIO 4 (`&pmc8380_3_gpios 4`)
- **GPU:** Qualcomm Adreno X1-45 (Mesa `freedreno` OpenGL 4.6 + `turnip` Vulkan 1.3)
- **Audio:** Qualcomm AudioReach (`q6apm`), SoundWire bus, 2x WSA8845 smart amplifiers with active VI/CPS feedback protection, Dual Studio Mics
- **Touch & Pen:** PixelSense Digitizer (`MSHW0484`) over QSPI 1-4-4 mode via native `iptsd`
- **Keyboard / SAM:** Surface Serial Hub (`SSH` over `&uart2`), Precision Touchpad (`libinput`), `SW_TABLET_MODE`
- **Cameras:** Qualcomm Spectra CAMSS with Sony IMX681 (front 1440p), OmniVision OV13858 (rear 10MP), and ST VD55G0 (NIR Windows Hello)
- **Wireless:** Qualcomm FastConnect 7800 (`WCN7850` Wi-Fi 7 + Bluetooth 5.4)
- **AI / NPU:** Qualcomm Hexagon NPU (CDSP / HTP - 45 TOPS) via `/dev/fastrpc-cdsp`

---

## 2. Implementation Status Matrix

| Subsystem | Status | Details & Implementation |
|---|:---:|---|
| **Display & Backlight** | **Working** | Native eDP at 2880x1920@120Hz; backlight enable on PMIC GPIO 4. |
| **Graphics & 3D** | **Working** | Mesa Freedreno OpenGL 4.6 + Turnip Vulkan 1.3 with ZAP shader firmware. |
| **Keyboard & Touchpad** | **Working** | Type Cover / Flex attached via Surface Serial Hub (`surface_kbd` / `surface_aggregator`). |
| **Touchscreen & Pen** | **Working** | Native AArch64 `iptsd` daemon with Surface Pro 11 calibration presets (28.76 x 19.17 cm). |
| **Wi-Fi 7 & Bluetooth 5.4** | **Working** | WCN7850 calibrated via `board-2.bin` and MAC fixup daemon (`sp11-mac-fixup`). |
| **Hardware Speaker Protection** | **Integrated** | WSA8845 VI & CPS feedback streams, AudioReach DSP graphs, and `fullio-v19c-rebuilt.tplg.bin`. |
| **Cameras & Sensors** | **Experimental** | CAMSS and sensor drivers compiled into candidate kernel `7.2.0-sp11-exp`. Pipeline 3A in progress. |
| **Dual Bootloader** | **Ready** | Dual-entry GRUB configuration with safe default (`surface-sp11`) and candidate (`surface-sp11-exp`). |
| **Silent Boot / Plymouth** | **Documented** | Automatic live-diagnostic argument filter in GRUB generator; silent boot instructions in `docs/SILENT_BOOT.md`. |

---

## 3. Repository Architecture

```text
fedoraiso-aarch64-sp11/
├── bin/
│   └── iptsd                         # Native AArch64 IPTSD touchscreen daemon
├── boot/
│   ├── grub/
│   │   ├── 09_surface_sp11           # Dynamic GRUB configuration generator (dual-entry)
│   │   └── grub.cfg                  # Standalone live media GRUB configuration
│   └── loader/                       # Systemd-boot configuration entries
├── builder/
│   ├── build-fedora-image.sh         # Entrypoint script for ISO generation in Fedora 44 container
│   ├── install-surface-support.sh    # Installs kernel, modules, firmware, and daemons into rootfs
│   ├── remix-fedora-workstation.sh   # Main remastering engine (EROFS extraction, injection, ISO packing)
│   ├── surface-hardware.json         # Hardware subsystem dependency manifest
│   └── verify-surface-image.py       # 79-point automated validation audit script
├── configs/
│   ├── alsa/ucm2/                    # ALSA UCM2 audio profiles for Surface Pro 11
│   ├── environment.d/                # Wayland environment and Mesa driver variables
│   ├── gnome/                        # Dconf defaults and 120Hz display configuration
│   ├── iptsd/                        # IPTSD screen dimensions and systemd service
│   ├── libinput/                     # Touchpad palm rejection quirks
│   ├── modprobe.d/                   # Retimer and USB4 driver options
│   └── udev/                         # Hardware rules and FastRPC permissions
├── docs/
│   ├── rea/                          # Reverse engineering architecture and kernel port reports
│   │   ├── AUDIO_KERNEL_PORT.md      # Detailed report on WSA8845 speaker protection integration
│   │   └── KERNEL_INTEGRATION_STATUS.md # Current status of kernel compilation and packaging
│   ├── AUDIO_DIAGNOSTICS.md          # Audio debugging and telemetry runbook
│   ├── CAMERA_REVERSE_ENGINEERING_STRATEGY.md # Spectra ISP reverse engineering roadmap
│   └── SILENT_BOOT.md                # Guide for clean, flicker-free boot and shutdown
├── dracut/
│   └── sp11.conf                     # Dracut initramfs driver inclusion configuration
├── dts/
│   ├── blobs/                        # Precompiled Device Tree Blobs (x1p64100-microsoft-denali.dtb)
│   ├── x1-microsoft-denali.dtsi      # Surface Pro 11 base Device Tree Source
│   └── x1p64100-microsoft-denali.dts # LCD-specific Device Tree Source with GPIO 4 backlight
├── firmware/
│   ├── ath12k-bdencoder              # Qualcomm Wi-Fi board-file encoder utility
│   └── blobs/                        # Machine calibration blobs and AudioReach topologies
├── patches/
│   └── kernel/
│       ├── 0002-sp11-protected-audio-port.patch    # AudioReach & WSA8845 hardware protection port
│       └── 0003-sp11-denali-dts-protected-audio.patch # VI/CPS feedback Device Tree additions
├── power/
│   ├── 95-sp11-power.rules           # S2idle power policy and SAM permissions
│   └── sp11-power.conf               # Systemd sleep configuration
├── rpm/
│   └── sources/sp11-mac-fixup/       # Factory Bluetooth MAC address restore service
├── scripts/
│   └── collect-fedora-session.py     # Diagnostic and hardware telemetry collector
└── tests/
    ├── test_camera_resources.py      # Unit tests for camera resource decoder
    ├── test_fedora_session.py        # Unit tests for session diagnostic collector
    └── test_installed_boot.py        # Unit tests for GRUB generator and argument filtering
```

---

## 4. Building the Distribution ISO

To build the bootable Fedora 44 Workstation Remix ISO, run on an AArch64 host with Docker installed:

```bash
./builder/build-fedora-image.sh
```

The build pipeline performs the following steps:
1. Downloads and cryptographically verifies the official Fedora Workstation 44 AArch64 live base ISO using Fedora's release GPG key.
2. Extracts the official EROFS live root filesystem preserving permissions and SELinux contexts.
3. Installs the Surface Pro 11 kernel, device trees, firmware, and user daemons.
4. Generates bootloader configurations with dual-kernel fallback.
5. Repacks the live filesystem with `mkfs.erofs` and masters the UEFI hybrid ISO with `xorriso`.
6. Executes [`verify-surface-image.py`](file:///home/juniormverli/repositories/surface/builder/verify-surface-image.py) to audit 79 platform constraints before publishing the ISO.

Published artifacts in `output/`:
- `fedora-44-workstation-surface-pro-11-lcd.iso`
- `fedora-44-workstation-surface-pro-11-lcd.iso.sha256`
- `workstation44-evidence/` (Verification report and layout diagnostics)

---

## 5. Booting & Dual-Kernel Selection

When booted on the Surface Pro 11, GRUB offers two configurations:

1. **Fedora Workstation 44 — Surface Pro 11 LCD (Default):**
   - Kernel: `7.2.8-arch1-3-sp11`
   - Validated baseline with LCD display, graphics acceleration, Wi-Fi 7, keyboard, and touchscreen.
2. **Fedora Workstation 44 — Surface Pro 11 LCD (Experimental: Cameras + Speaker Protection):**
   - Kernel: `7.2.0-sp11-exp`
   - Includes experimental Qualcomm Spectra CAMSS drivers, Sony IMX681, OV13858, VD55G0, and WSA8845 VI/CPS speaker protection feedback telemetry.

---

## 6. License & Attribution

- Linux kernel drivers and patches are licensed under GPL-2.0.
- Surface Aggregator Module and IPTS drivers: GPL-2.0 (linux-surface community).
- Fedora packaging and integration scripts: BSD-3-Clause / MIT.
- All patches retain original community author attribution.
