# Fedora AArch64 for Microsoft Surface Pro 11 (LCD Variant)
### Qualcomm Snapdragon X Plus (`X1P64100` / Purwa 10-core Oryon CPU)
**Base:** official Fedora Workstation 44 AArch64 live ISO, GNOME on Wayland, with the original live session and Anaconda installer.

The builder verifies Fedora's signed CHECKSUM and the ISO SHA256, then adds the existing Surface kernel, LCD DTB, firmware and configuration. It does not bootstrap a replacement desktop from a package list. Static integration evidence does not demonstrate that the display or peripherals work on physical hardware. Cameras remain unsupported; the NPU mapping is experimental.

Porting implementation from `dwhinham/archiso-aarch64-sp11`, upstream `linux-surface` / `linux-msm`, and hardware parameter reverse engineering from the Surface Pro 11 Windows 11 ARM64 subsystem.

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

## 2. Real Implementation & Validation Status Matrix

| Subsystem | Status de Implementação | Nível de Validação | Evidência / Artefatos Produzidos | Limitações Upstream / Próximos Passos |
|:---|:---:|:---:|:---|:---|
| **1. Compute e Energia** | **Configurado / Empacotado** | Estático / Configurado | • `rpm/specs/kernel-sp11.spec` com regras ativas de compilação<br>• `power/sp11-power.conf`<br>• `power/95-sp11-power.rules` (s2idle) | Suspensão/retomada s2idle e `power_profile` dependem do boot em bare-metal com o kernel compilado. |
| **2. Display LCD** | **Compilado / Gerado** | Compilado | • `dts/blobs/x1p64100-microsoft-denali.dtb` (205 KB, compilado com `dtc`)<br>• PWM backlight via PMK8550 e PMC8380 GPIO 4/10 | Controle de backlight em painel LCD precisa de teste físico; OLED usa controle DPCD. |
| **3. Gráficos & Vídeo** | **Configurado** | Configurado | • `configs/environment.d/10-surface-wayland.conf`<br>• Shaders Zap extraídos (`qcdxkmsuc8380.mbn`)<br>• `configs/gnome/00-surface-sp11` | Aceleração 3D Freedreno e Vulkan Turnip requerem execução ativa do servidor Wayland. |
| **4. Teclado Type Cover** | **Configurado** | Configurado | • `dracut/sp11.conf` com drivers `surface_aggregator`, `surface_hid`, `surface_kbd`<br>• `configs/libinput/99-surface-sp11.quirks`<br>• Postura `SW_TABLET_MODE` | Funcionalidade docked mapeada via UART; modo sem fio Bluetooth do Flex Keyboard requer pareamento dedicado. |
| **5. Toque e Caneta** | **Compilado / Empacotado** | Compilado | • Daemon `bin/iptsd` compilado nativamente (834 KB)<br>• `configs/iptsd/surface-pro-11.conf` (dimensões 287.6x191.7 mm)<br>• `configs/iptsd/iptsd@.service` & `50-iptsd.rules` | Necessita de teste de latência e inking com Surface Slim Pen 2 no hardware físico. |
| **6. Wi-Fi e Bluetooth** | **Compilado / Configurado** | Extraído / Configurado | • `firmware/blobs/ath12k/WCN7850/hw2.0/board.bin` (88.872 bytes gerado via `ath12k-bdencoder`)<br>• `rpm/sources/sp11-mac-fixup/sp11-mac.conf` com MACs físicos (`e8:a7:2f:79:a5:c3/c4`) | Requer boot com driver `ath12k` e `btqca` para validar throughput Wi-Fi 7 e pareamento BLE. |
| **7. Portas e Carga** | **Configurado** | Configurado | • `configs/modprobe.d/sp11-usb4.conf`<br>• Configuração GLINK e PS8830 retimers | Limitação upstream: saída externa de display em dock USB4/Surface Dock 2 ainda não opera em X1. |
| **8. Áudio & Microfones** | **Compilado / Configurado** | Compilado | • `firmware/blobs/qcom/x1e80100/X1E80100-Microsoft-Surface-Pro-11-tplg.bin` (23 KB compilado com `alsatplg`)<br>• UCM2 HiFi profiles<br>• PipeWire filter-chain | Volume do alto-falante permanece conservador para proteção acústica enquanto o DSP de proteção não for validado. |
| **9. Sensores e NPU** | **Configurado / Extraído** | Extraído / Configurado | • JSONs de domínio Qualcomm (`adsps.jsn`, `cdspr.jsn`, `battmgr.jsn`) em `configs/qcom/`<br>• `configs/udev/61-surface-sp11-sensor.hwdb`<br>• `configs/udev/99-fastrpc.rules` | Rotação automática e inferência via FastRPC `/dev/fastrpc-cdsp` requerem teste em sessão ativa. |
| **10. Câmeras, IR e LEDs** | **Pesquisa / Parcial** | Engenharia Reversa | • `dts/camera-sp11.dtsi` mapeando IMX681, OV13858 e VD55G0<br>• `configs/libcamera/qcom-camss.yaml`<br>• `scripts/surface-privacy-led.sh` (via SAM) | **Limitação Upstream:** Sem driver CAMSS Spectra 695 funcional no kernel upstream. Câmeras não transmitem vídeo atualmente. |

---

## 3. Estrutura do Repositório

```text
surface/
├── bin/
│   └── iptsd                         # Binário compilado do daemon IPTSD (AArch64)
├── boot/
│   └── loader/
│       ├── loader.conf               # Configuração padrão do systemd-boot
│       └── entries/fedora-sp11.conf  # Entrada de boot com parâmetros clk/pd/pauth/tpm2
├── builder/
│   ├── build-fedora-image.sh         # Remix do ISO oficial Fedora Workstation 44
│   └── package-list.txt              # Lista legada; não define o remix Workstation 44
├── configs/
│   ├── alsa/ucm2/                    # Perfis ALSA UCM2 para Surface Pro 11
│   ├── environment.d/                # Variáveis de ambiente Wayland / Mesa Freedreno
│   ├── gnome/                        # Perfil Dconf e modelo monitors.xml (120 Hz)
│   ├── iptsd/                        # Preset de hardware, serviço systemd e regras udev
│   ├── libcamera/                    # Mapeamento conceitual libcamera para Spectra 695
│   ├── libinput/                     # Quirks de rejeição de palma do Touchpad e tablet mode
│   ├── modprobe.d/                   # Opções de retimers USB4 / DP Alt-Mode
│   ├── pipewire/                     # Latência AudioReach e cancelamento de eco para Studio Mics
│   ├── qcom/                         # JSONs de registro de serviços Qualcomm (sensor_pd, cdsp, audio)
│   └── udev/                         # Matriz de montagem de acelerômetro e permissões FastRPC
├── dracut/
│   └── sp11.conf                     # Módulos initramfs (KMS, eDP, NVMe, SAM)
├── dts/
│   ├── blobs/
│   │   └── x1p64100-microsoft-denali.dtb # DTB compilado via dtc (205 KB)
│   ├── camera-sp11.dtsi              # Overlay de pesquisa das câmeras (IMX681, OV13858, VD55G0)
│   ├── x1-microsoft-denali.dtsi      # DTS base do Surface Pro 11
│   └── x1p64100-microsoft-denali.dts # DTS da variante LCD com backlight PWM
├── firmware/
│   ├── ath12k-bdencoder              # Utilitário Qualcomm para extração de calibração Wi-Fi
│   ├── blobs/                        # Calibração e topologia compiladas:
│   │   ├── ath12k/WCN7850/hw2.0/board.bin
│   │   └── qcom/x1e80100/X1E80100-Microsoft-Surface-Pro-11-tplg.bin
│   └── extract-firmware.sh           # Extrator de firmwares do DriverStore
├── power/
│   ├── 95-sp11-power.rules           # Forçamento de s2idle e permissões de perfil SAM
│   └── sp11-power.conf               # Configurações de suspensão no systemd-logind
├── rpm/
│   ├── sources/sp11-mac-fixup/       # Serviço e regras de fixação dos MACs físicos de fábrica
│   └── specs/                        # Specs RPM (kernel-sp11, iptsd, ath12k-board, mac-fixup)
└── scripts/
    └── surface-privacy-led.sh        # Controle do LED de privacidade via SAM
```

---

## 4. Build the Fedora Workstation 44 remix

Run on a native AArch64 host with Docker and enough space for the official ISO, extracted Workstation root, compressed filesystem and final ISO (allow at least 35 GB free):

```bash
./builder/build-fedora-image.sh
```

The privileged `fedora:44` container verifies the official Fedora Workstation 44 AArch64 ISO and signed checksum using Fedora's packaged signing key. Existing cached inputs live in `output/cache/`. The build requires the already compiled custom kernel and modules in `output/rootfs/`, the LCD DTB in `dts/blobs/`, the four executables `iptsd`, `iptsd-check-device`, `iptsd-find-hidraw` and `iptsd-foreach` in `output/iptsd-pkg/usr/bin/` and extracted device firmware in `output/firmware/`. Missing requirements stop validation. The previous Fedora 41 ISO and raw image remain historical artifacts.

Optional absolute container paths can be supplied through `FEDORA_BASE_ISO`, `FEDORA_CHECKSUM_FILE`, `SURFACE_KERNEL_SOURCE`, `SURFACE_KERNEL_VERSION`, `SURFACE_ISO_OUTPUT` and `SURFACE_RESUME_BUILD`. Files under this repository are available under `/workspace` inside the container. To run in an existing native Fedora 44 container, use `bash builder/build-fedora-image.sh --inside-container`.

The live image named `LiveOS/squashfs.img` is detected by its filesystem signature. The pinned Fedora 44 Workstation 1.7 base uses a direct EROFS root; extraction preserves ownership, permissions and extended attributes, and repacking retains EROFS. Any other filesystem or nested root layout is rejected.

For an interrupted extraction or subsequent build, `SURFACE_RESUME_BUILD=/workspace/output/.workstation44-build.XXXXXX` reuses that extracted ISO tree after verifying the official base again and matching its SHA256 to a successful full ISO extraction marker. Incomplete or unrelated trees are rejected. A completed live extraction is reused only when `live-extraction.complete` records its filesystem type; partial extractions are preserved under a different name and repeated. The build log, current build path and exit status are retained. Evidence stays in the individual build directory until a validated ISO is published; published evidence records its ISO hash. Resume expects an extracted tree from the same verified base, before live-image repacking; use a fresh build after a repacking failure.

The pipeline extracts the original Workstation live root, adds the Surface support payload, rebuilds initramfs inside that root, then creates and checks the UEFI ISO and its ESP. It retains the official live session and installer configuration. Kernel, initramfs, DTB and GRUB configuration are duplicated in the ESP for firmware boot and in the ISO filesystem for live media access. The ESP size grows with the payload.

Outputs are published only after validation:

- `output/fedora-44-workstation-surface-pro-11-lcd.iso`
- `output/fedora-44-workstation-surface-pro-11-lcd.iso.sha256`
- `output/workstation44-evidence/` containing base signature and checksum evidence, matching kernel configuration, initramfs listing, verifier reports and ISO boot layout.
- `output/workstation44-rootfs/`, retained for inspection. A previous target root is renamed before a rebuild.

The generated GRUB EFI loader is unsigned and requires Secure Boot to be disabled. The default entry starts GNOME Wayland with verbose boot messages. The diagnostics entry uses the firmware framebuffer, disables GPU modesetting and starts a text session so boot failures can be observed. Physical validation follows [the hardware test runbook](docs/HARDWARE_TEST_RUNBOOK.md). Neither static verification nor a successful ISO build proves physical display, USB, touch, sound or suspend behavior.

The Anaconda files are retained from the official base. Installing to an internal disk and subsequently booting the Surface kernel requires separate physical validation; successful live-media validation does not establish installation success. Device firmware is retained locally and must not be published externally.
