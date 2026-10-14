# Fedora AArch64 for Microsoft Surface Pro 11 (LCD Variant)
### Qualcomm Snapdragon X Plus (`X1P64100` / Purwa 10-core Oryon CPU)
**Desktop Environment:** Minimal GNOME on Pure Wayland (Zero Bloatware)

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
| **4. Teclado Type Cover** | **Configurado** | Configurado | • `dracut/sp11.conf` com drivers `surface_sam`, `surface_hid`, `surface_kbd`<br>• `configs/libinput/99-surface-sp11.quirks`<br>• Postura `SW_TABLET_MODE` | Funcionalidade docked mapeada via UART; modo sem fio Bluetooth do Flex Keyboard requer pareamento dedicado. |
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
│   ├── build-fedora-image.sh         # Pipeline de build automatizado do RootFS e imagem .raw
│   └── package-list.txt              # Lista enxuta de pacotes Fedora GNOME Wayland
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

## 4. Instruções de Execução

Para compilar o rootfs completo do Fedora e gerar a imagem particionada `.raw`:
```bash
cd /home/juniormverli/repositories/surface
./builder/build-fedora-image.sh
```
O script usará o container Docker `fedora:41`, compilará os binários pendentes, montará a árvore de arquivos, formatará as partições GPT (ESP + RootFS) e produzirá `output/fedora-surface-pro-11-lcd.raw`.
