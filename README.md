# Fedora AArch64 for Microsoft Surface Pro 11 (LCD Variant)
### Qualcomm Snapdragon X Plus (`X1P64100` / Purwa 10-core Oryon CPU)
**Desktop Environment:** Minimal GNOME on Pure Wayland (Zero Bloatware)

Developed strictly under the **BMAD (Breakthrough Method of Agile AI-Driven Development)** methodology, porting and completing the implementation from `dwhinham/archiso-aarch64-sp11`, upstream `linux-surface` / `linux-msm`, and reverse engineering closed-source hardware blocks directly from the Surface Pro 11 Windows 11 ARM64 subsystem.

---

## 1. Verified Target Hardware Specifications
- **Device SKU:** Microsoft Surface Pro 11th Edition (13-inch LCD)
- **SoC:** Qualcomm Snapdragon X Plus (`X1P-64-100` @ 3.40 GHz, 10 Oryon CPU cores)
- **Display:** 13" PixelSense Flow LCD (2880 x 1920 @ 120Hz via eDP)
- **GPU:** Qualcomm Adreno X1-45 (Mesa `freedreno` OpenGL 4.6 + `turnip` Vulkan 1.3)
- **Wireless:** Qualcomm FastConnect 7800 (`WCN7850` Wi-Fi 7 + Bluetooth 5.4)
- **Audio:** Qualcomm AudioReach (`q6apm`), SoundWire bus, 2x WSA8845 smart speakers, Dual Studio Mics
- **Touch & Pen:** PixelSense Digitizer (`MSHW0484`) over QSPI 1-4-4 mode (`spi-geni-qcom` + `iptsd`)
- **Keyboard / SAM:** Surface Serial Hub (`SSH` over `&uart2`), Precision Touchpad (`libinput`), `SW_TABLET_MODE`
- **Cameras:** Front Sony IMX681 (`MSHW0490`), Rear OmniVision OV13858 (`MSHW0491`), Aux IR STMicroelectronics VD55G0 (`MSHW0492`)
- **AI / NPU:** Qualcomm Hexagon NPU (CDSP / HTP - 45 TOPS) via `/dev/fastrpc-cdsp`

---

## 2. Completed BMAD Sprints Roadmap

| Sprint | Subsystem & Focus | Key Deliverables & Git Commit | Status |
|--------|-------------------|-------------------------------|:------:|
| **Sprint 1** | Repo Audit & Image Pipeline | `ARCHISO_SP11_AUDIT.md`, `x1p64100-microsoft-denali.dts`, `dracut/sp11.conf`, Fedora 41 container builder (`8f726f8`) | **DONE** |
| **Sprint 2** | Kernel RPM, USB4 & S2Idle | `kernel-sp11.spec`, `boot/loader/`, `configs/modprobe.d/sp11-usb4.conf`, `power/95-sp11-power.rules` (`e8c6e9e`) | **DONE** |
| **Sprint 3** | Firmware & Wi-Fi 7 / BT 5.4 | `ath12k-bdencoder` board extraction, `output/firmware/ath12k/.../board.bin`, `sp11-mac-fixup` service (`adcb7bf`) | **DONE** |
| **Sprint 4** | Type Cover & Touch / Stylus | `configs/iptsd/surface-pro-11.conf`, `iptsd.spec`, `99-surface-sp11.quirks` for Precision Touchpad (`2e71dde`) | **DONE** |
| **Sprint 5** | GNOME Minimal on Wayland | `10-surface-wayland.conf`, `00-surface-sp11` dconf profile, 120Hz `monitors.xml` template (`04ccaef`) | **DONE** |
| **Sprint 6** | AudioReach & Dual Studio Mics | `X1E80100-Microsoft-Surface-Pro-11-tplg.bin`, `MICROSOFT-Surface-Pro-11.conf`, PipeWire studio mic filter chain (`e40d2e2`) | **DONE** |
| **Sprint 7** | Sensor Hub, Rotation & NPU | Qualcomm `sensor_pd`/`audio_pd`/`cdsp` JSNs, `61-surface-sp11-sensor.hwdb`, `99-fastrpc.rules` (`4f8bc9b`) | **DONE** |
| **Sprint 8** | CAMSS Cameras, IR & LEDs | `dts/camera-sp11.dtsi` (IMX681/OV13858/VD55G0), `configs/libcamera/qcom-camss.yaml`, privacy LED rules (`90b9dbe`) | **DONE** |

---

## 3. Directory Layout
```text
surface/
├── audit/
│   └── ARCHISO_SP11_AUDIT.md        # Complete analysis of archiso-aarch64-sp11 and translation path
├── boot/
│   └── loader/
│       ├── loader.conf              # Systemd-boot default config
│       └── entries/fedora-sp11.conf # SP11 LCD boot entry with clk/pd/pauth/tpm2 cmdline flags
├── builder/
│   ├── build-fedora-image.sh        # Reproducible Fedora AArch64 containerized image generator
│   └── package-list.txt             # Minimal GNOME Wayland package list (zero bloat)
├── configs/
│   ├── alsa/ucm2/                   # ALSA UCM2 profiles for Surface Pro 11 stereo speakers & studio mics
│   ├── environment.d/               # Wayland environment variables (Mesa Freedreno/Turnip tuning)
│   ├── gnome/                       # Dconf system profile and 2880x1920 @ 120Hz monitors.xml
│   ├── iptsd/                       # Touchscreen & Slim Pen 2 hardware preset (MSHW0484)
│   ├── libcamera/                   # Libcamera pipeline config for Spectra 695 CAMSS
│   ├── libinput/                    # Precision Touchpad and Tablet mode switch quirks
│   ├── modprobe.d/                  # USB4 / Type-C DisplayPort Alt-Mode retimer options
│   ├── pipewire/                    # AudioReach latency & Studio Mic echo-cancellation filter chain
│   ├── qcom/                        # Qualcomm Service Registry domain JSONs (sensor_pd, audio_pd, cdsp)
│   └── udev/                        # Accelerometer mount matrix, FastRPC NPU permissions & privacy LEDs
├── dracut/
│   └── sp11.conf                    # Early KMS, display, NVMe and Surface SAM initramfs modules
├── dts/
│   ├── camera-sp11.dtsi             # CAMSS CSI-2 sensor subnodes (IMX681, OV13858, VD55G0)
│   ├── x1-microsoft-denali.dtsi     # Core Denali base device tree
│   └── x1p64100-microsoft-denali.dts# LCD variant device tree with PMIC PWM backlight
├── firmware/
│   ├── ath12k-bdencoder             # Qualcomm board extraction utility
│   └── extract-firmware.sh          # Automated DriverStore firmware extractor
├── output/
│   └── firmware/                    # Extracted and compiled binaries:
│       ├── ath12k/WCN7850/hw2.0/board.bin
│       └── qcom/x1e80100/X1E80100-Microsoft-Surface-Pro-11-tplg.bin
├── power/
│   ├── 95-sp11-power.rules          # S2Idle enforcement & SAM platform profile permissions
│   └── sp11-power.conf              # Systemd logind tablet suspend rules
└── rpm/
    ├── sources/sp11-mac-fixup/      # Factory MAC address fixup service & udev rules
    └── specs/                       # RPM spec files for kernel-sp11, iptsd, ath12k-board, mac-fixup
```

---

## 4. Building the Fedora Image

Run the builder script from the repository root:
```bash
./builder/build-fedora-image.sh
```
This executes within a native `fedora:41` container on AArch64:
1. Extracts proprietary firmware from the local Windows `DriverStore` (or mirror).
2. Generates the `ath12k` calibration `board.bin` using `ath12k-bdencoder`.
3. Stages the AudioReach topology binary `X1E80100-Microsoft-Surface-Pro-11-tplg.bin`.
4. Bootstraps the minimal Fedora AArch64 package set.
5. Deploys the Dracut early-boot initramfs configuration, systemd-boot entries, ALSA UCM, PipeWire filter chains, sensor mount matrices, and pure Wayland GNOME session.
