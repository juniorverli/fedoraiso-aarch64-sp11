# Estado da Integração do Kernel: Câmeras, Áudio Protegido e DTB LCD

Data de atualização: 2026-10-15  
Status da integração: **Árvore experimental isolada compilada e validada em container Fedora 44 (AArch64)**  
Alvo: Microsoft Surface Pro 11th Edition (Denali - X1P64100 / LCD)

---

## 1. Visão Geral da Integração

A integração unificou em uma árvore de compilação isolada (`output/kernel-integration/linux-548e7bcd0c5460ddcbca9600cea603ebeebf4da7`) os avanços de engenharia reversa e drivers desenvolvidos pela comunidade para o Surface Pro 11:
1. **Câmeras e Sensores CSI/I2C:** Drivers CAMSS X1E, Sony IMX681, OmniVision OV13858 e STMicroelectronics VD55G0 (NIR Windows Hello), derivados de `turbineBMW/surface-pro-11-linux`.
2. **Áudio com Proteção Ativa de Alto-Falantes:** Subsistema AudioReach (DSP q6apm), SoundWire Qualcomm, amplificadores inteligentes WSA8845 e macros LPASS com suporte a telemetria VI (tensão/corrente) e CPS (sensor capacitivo), adaptados de `geocausa/SP11X1e-audio`.
3. **Preservação do Painel LCD e Backlight:** Manutenção estrita do backlight no GPIO 4 do PMIC (`pmc8380_3_gpios 4`) no Device Tree (`x1-microsoft-denali.dtsi`), mantendo compatibilidade total com o modelo LCD (`x1p64100-microsoft-denali.dts`).

---

## 2. Manifesto de Patches Unificados

| Ordem | Arquivo | Descrição | Status de Replay |
|---|---|---|---|
| **0001** | `output/upstream-research/surface-pro-11-linux/kernel/port-7.3/sp11-port-7.3.patch` | Drivers de câmera CAMSS X1E, sensores I2C, subsistema genérico push/pull e base DT Denali. | Aplicado com `fuzz=0` sobre commit `548e7bcd0c54` |
| **0002** | `patches/kernel/0002-sp11-protected-audio-port.patch` | Reconciliação do áudio protegido (21 arquivos em `sound/`, `drivers/soundwire/`, `include/`). | Verificado com `patch -p1 --fuzz=0` (SHA256 100% idêntico) |
| **0003** | `patches/kernel/0003-sp11-denali-dts-protected-audio.patch` | Vias de feedback WSA VI e CPS, configuração WSA8845 (#sound-dai-cells=1) e DMIC clock 4.8 MHz no DT Denali. | Verificado e validado com DTC (exit 0) |

---

## 3. Matriz de Compilação e Verificação (Container Fedora 44 AArch64)

Ambiente: Container Docker `fedora:44` (`surface-kernel-port-check`), GCC 16.2.1, pahole v1.32.

| Subsistema / Alvo | Módulos / Objetos Gerados | Resultado da Compilação |
|---|---|---|
| **SoundWire** | `drivers/soundwire/soundwire-bus.o`, `soundwire-qcom.o` | **Sucesso (exit 0)** |
| **Codecs LPASS / WSA** | `snd-soc-wsa884x.o`, `snd-soc-lpass-wsa-macro.o`, `snd-soc-lpass-va-macro.o`, `snd-soc-lpass-tx-macro.o`, `snd-soc-lpass-macro-common.o` | **Sucesso (exit 0)** |
| **AudioReach / Machine** | `snd-q6apm.o`, `snd-soc-x1e80100.o` | **Sucesso (exit 0)** |
| **Câmeras CAMSS & Sensores** | `qcom-camss.o`, `imx681.o`, `ov13858.o`, `vd55g0.o` | **Sucesso (exit 0)** |
| **Device Tree Blobs** | `qcom/x1p64100-microsoft-denali.dtb` (LCD), `qcom/x1e80100-microsoft-denali-oled.dtb` | **Sucesso (exit 0)** |

---

## 4. Preservação de Segurança e Integração Unificada na Distribuição

1. **Volume e Ganho:** Os limites conservadores de ganho continuam preservados no PipeWire e UCM. A compilação sem erros dos módulos de proteção viabiliza a execução do grafo, mas não comprova a atenuação física dos transdutores em tempo de execução.
2. **Inicialização Direta como Padrão Unificado:** Conforme a conclusão da engenharia reversa de áudio e câmeras, a imagem foi consolidada para inicializar o kernel com ambos os subsistemas diretamente na entrada padrão do GRUB (`surface-sp11`), dispensando seleções manuais ou entradas experimentais separadas de candidato.
3. **Staging no RootFS (`workstation44-rootfs`):**
   - Kernel Image: `/boot/vmlinuz-sp11` (40 MB, AArch64, `7.2.0-sp11-exp`)
   - Initramfs: `/boot/initramfs-sp11.img` (gerado via dracut com suporte completo a USB/storage/erofs, simplesdrm e áudio/câmera)
   - DTB: `/boot/dtb-sp11/qcom/x1p64100-microsoft-denali.dtb` (219 KB, contendo backlight LCD GPIO4, WSA8845 e sensores IMX681/OV13858/VD55G0)
   - Módulos: `/usr/lib/modules/7.2.0-sp11-exp/` (com `depmod` executado)
   - Topologias: `/usr/lib/firmware/qcom/x1e80100/fullio-v19c-rebuilt.tplg.bin` e `X1E80100-Microsoft-Surface-Pro-11-Render-Parity-tplg.bin`
   - Ferramentas de Câmera: `/usr/bin/surface-cam`, `/usr/bin/surface-camera-test`, `/usr/bin/surface-camera-preview`
4. **Reempacotamento e Validação da ISO:**
   - A imagem `output/fedora-44-workstation-surface-pro-11-lcd.iso` (5.5 GB) foi gerada via `mkfs.erofs` e `xorriso`.
   - Passou em todos os 77 testes automatizados de conformidade em `verify-surface-image.py` (0 erros).
   - SHA256 da ISO publicado: `27d4de91ef6f072ac126ccd9ba221128a179bca70546046d48ca5a4623b6002a`.
5. **Validação em Hardware Real:** Os testes de captura de imagem via libcamera, reprodução de áudio e medição de telemetria VI do amplificador inteligente requerem inicialização no hardware físico do usuário.
