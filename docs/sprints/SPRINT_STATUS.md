# BMAD Sprint Status: Fedora AArch64 for Surface Pro 11 LCD
**Project:** Fedora Linux 41 AArch64 on Microsoft Surface Pro 11 (Qualcomm Snapdragon X Plus `X1P64100` / Purwa 10-core Oryon CPU)
**Desktop Environment:** GNOME Minimal on Pure Wayland
**Methodology:** Breakthrough Method of Agile AI-Driven Development (BMAD)
**Last Updated:** 2026-10-14 (Sprint Consolidation & Verification Phase)

---

## 1. Subsystem Implementation & Validation Matrix

> [!IMPORTANT]
> Em conformidade estrita com a integridade técnica do BMAD, os estados de validação distinguem expressamente componentes compilados/integrados no sistema daqueles que exigem execução física no Surface Pro 11. **Nenhum componente é rotulado como 100% funcional sem validação em bare-metal.**

| # | Subsistema | Estado Atual | Evidências no Repositório / Artefatos | Requisitos para Validação Física (Bare-Metal) |
|---|---|:---:|---|---|
| **1** | **Compute & Energia** (Snapdragon X Plus 10c, CPUFreq, PMIC, S2Idle) | **Compilado & Integrado** | • Kernel `vmlinuz-sp11` (6.11/7.2-sp11)<br>• DTB `x1p64100-microsoft-denali.dtb` com nós Oryon e PM8550<br>• Regras `power/sp11-power.conf` e `power/95-sp11-power.rules` (s2idle) | • Medição de consumo de energia em suspensão S2Idle.<br>• Retomada via botão liga/desliga e abertura de tampa.<br>• Escalonamento de frequência sob carga multinúcleo. |
| **2** | **Display LCD** (13" 2880x1920 @ 120Hz via eDP) | **Compilado & Integrado** | • Nós eDP e backlight PWM PMK8550 / PMC8380 em `x1p64100-microsoft-denali.dtb`<br>• Módulo `phy-qcom-edp.ko.zst` no initramfs<br>• `monitors.xml` com modo 2880x1920@120Hz | • Inicialização KMS sem tela preta (flicker-free).<br>• Controle de brilho via `/sys/class/backlight`.<br>• Taxa de atualização a 120Hz confirmada no Mutter Wayland. |
| **3** | **Gráficos & Vídeo** (Adreno X1-45, Freedreno, Turnip, Iris VPU) | **Compilado & Integrado** | • Módulos `msm.ko.zst`, `gpucc-x1e80100.ko.zst` no initramfs<br>• Firmware Zap Shader `qcdxkmsuc8380.mbn`<br>• Pacotes Mesa 25 (`freedreno`, `turnip`) e GDM Wayland | • Renderização por hardware em `glxinfo` / `vulkaninfo`.<br>• Desempenho e estabilidade sob Wayland nativo.<br>• Decodificação acelerada de vídeo h.264/HEVC/AV1. |
| **4** | **Teclado Type Cover / Flex** (SSH UART, Touchpad, Fn-keys, Tablet Mode) | **Compilado & Integrado** | • Módulos `surface_aggregator`, `surface_hid`, `surface_kbd`<br>• Mapeamento de nós SAM e Target KIP (0x02)<br>• Quirks libinput `99-surface-sp11.quirks` | • Digitação no prompt de inicialização / LUKS.<br>• Detecção de conexão e desconexão física (attach/detach).<br>• Alternância de `SW_TABLET_MODE` ao dobrar o teclado.<br>• Retroiluminação das teclas e LED de Fn-Lock. |
| **5** | **Toque e Caneta Slim Pen 2** (PixelSense Digitizer, MPP 2.6, IPTFS) | **Compilado & Integrado** | • Binário nativo AArch64 `/usr/bin/iptsd` (853 KB)<br>• Serviço `iptsd@.service` e preset `surface-pro-11.conf`<br>• Regra udev `50-iptsd.rules` | • Rastreamento multitouch responsivo com rejeição de palma.<br>• Coleta de pressão, inclinação e botão da Slim Pen 2.<br>• Inicialização do transport QSPI sob o kernel de produção. |
| **6** | **Conectividade Wi-Fi 7 & Bluetooth 5.4** (FastConnect 7800 / WCN7850) | **Compilado & Integrado** | • Firmware de calibração `ath12k/WCN7850/hw2.0/board.bin` (88.872 B)<br>• Driver `ath12k` e `btqca` incluídos<br>• Script e serviço `sp11-mac-fixup` para MAC do SP11 | • Associação a redes 2.4GHz, 5GHz e 6GHz (Wi-Fi 7).<br>• Throughput de rádio e pareamento de periféricos Bluetooth.<br>• Fixação persistente do endereço MAC oficial do dispositivo. |
| **7** | **Portas Externas & Carga** (2x USB4 / TB4, Surface Connect, Type-C PD) | **Compilado & Integrado** | • Módulos `ucsi_glink.ko.zst`, `pmic_glink.ko.zst`, `typec_ucsi.ko.zst`<br>• Opções de retimer `sp11-usb4.conf`<br>• Mapeamento DTB de conectores USB Type-C | • Carregamento via USB-C PD e porta magnética Surface Connect.<br>• Negociação de conexões USB 3.2 / USB4.<br>• Limitação: DisplayPort Alt-Mode via dock USB4 em refinamento. |
| **8** | **Áudio & Microfones de Estúdio** (AudioReach, SoundWire, WSA8845, DMIC) | **Compilado & Integrado** | • Topologia `X1E80100-Microsoft-Surface-Pro-11-tplg.bin` (22.856 B)<br>• Perfis ALSA UCM2 (`MICROSOFT-Surface-Pro-11.conf`, `Surface11-HiFi.conf`)<br>• Configuração PipeWire / WirePlumber | • Reprodução de áudio estéreo nos 2 alto-falantes de 2W.<br>• Gravação de voz nítida pelo array duplo de microfones de estúdio.<br>• Validação da proteção acústica (speaker protection) em volume alto. |
| **9** | **Sensores & Aceleração NPU** (Acelerômetro SEE, Giroscópio, CDSP 45 TOPS) | **Compilado & Integrado** | • Firmwares `qccdsp8380.mbn`, `cdsp_dtb.mbn`, `battmgr.jsn`<br>• Sensor HWDB `61-surface-sp11-sensor.hwdb`<br>• Regras udev FastRPC `/dev/fastrpc-cdsp` | • Rotação automática da interface GNOME via `iio-sensor-proxy`.<br>• Ajuste de brilho dinâmico via sensor de luz ambiente (ALS).<br>• Execução de inferência via runtime FastRPC na NPU Hexagon. |
| **10** | **Câmeras, IR & LED de Privacidade** (Spectra ISP, MIPI CSI-2, Status LED) | **Bloqueado Upstream** | • Nós preliminares `camera-sp11.dtsi` (IMX681, OV13858, VD55G0)<br>• Firmwares Windows identificados (`qccamisp8380`, `CAMERA_ICP.mbn`)<br>• Script `surface-privacy-led.sh` (userspace) | • **Bloqueio Técnico:** Driver Qualcomm Spectra ISP / CAMSS para Snapdragon X não está concluído no Linux mainline.<br>• Streaming de vídeo e infravermelho desabilitados até implementação de driver ISP no kernel. |

---

## 2. Artefatos de Entrega Gerados

1. **Live ISO Inicializável UEFI AArch64:**
   - Caminho: `output/fedora-surface-pro-11-lcd.iso`
   - Formato: ISO-9660 Híbrida UEFI com partição FAT32 `images/efiboot.img`
   - Carregadores: `systemd-boot` (`BOOTAA64.EFI`) e `GRUB2`
   - Kernel e DTB: `vmlinuz-sp11` e `x1p64100-microsoft-denali.dtb` integrados

2. **Imagem de Disco Particionada (.raw):**
   - Caminho: `output/fedora-surface-pro-11-lcd.raw`
   - Formato: Tabela de Partição GPT (512MB ESP FAT32 + partição raiz ext4)
   - Pronta para gravação direta via `dd` / `balenaEtcher` em cartão NVMe ou pendrive USB.
