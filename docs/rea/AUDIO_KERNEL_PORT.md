# Port do áudio protegido SP11 no kernel candidato com câmera

Data: 2026-10-15  
Status: **Compilado e verificado estruturalmente em árvore isolada (experimental)**  
Aviso de Segurança: **A compilação com sucesso não comprova segurança física nem autoriza elevação de volume.**

---

## 1. Contexto e Objetivos

Este documento descreve o port e a reconciliação do subsistema de áudio com proteção ativa de alto-falantes proveniente do repositório [geocausa/SP11X1e-audio](https://github.com/geocausa/SP11X1e-audio) (base 7.1.5) sobre a base do kernel com suporte a câmeras [turbineBMW/surface-pro-11-linux](https://github.com/turbineBMW/surface-pro-11-linux) (base mainline `548e7bcd0c5460ddcbca9600cea603ebeebf4da7`).

O trabalho reconciliou os conflitos semânticos e textuais entre as duas árvores, preservou as novas APIs de memória compartilhada e push/pull do kernel mais novo, garantiu a integridade do backlight LCD no GPIO 4 do PMIC no Device Tree do Microsoft Surface Pro 11 (Denali) e adicionou as vias de telemetria VI (Voltage/Current) e CPS (Capacitive Sensing) para ambos os amplificadores inteligentes WSA8845.

---

## 2. Identificação Exata de Fontes e Hashes

| Componente | Origem / Commit / Arquivo | SHA256 |
|---|---|---|
| **Base Kernel** | `torvalds/linux` commit `548e7bcd0c5460ddcbca9600cea603ebeebf4da7` | `9d34c13e30b54bb139779fb3fac0c64f1634ffd6340b6258c8dfde90dbbfc2ce` (tarball) |
| **Patch Câmera** | `turbineBMW/surface-pro-11-linux` (`sp11-port-7.3.patch`) | `16cdb32c732dde20f088c27bd1b83b269e631999c76edf1045126ff220ed3010` |
| **Áudio Protegido** | `geocausa/SP11X1e-audio` commit `3232e1dacdeb580a10a9cb8d4756a4518a7bd83e` | `3232e1dacdeb580a10a9cb8d4756a4518a7bd83e` |
| **Patch de Áudio Gerado** | `patches/kernel/0002-sp11-protected-audio-port.patch` | Replay verificado com `fuzz=0` nos 21 arquivos |
| **Configuração Kernel** | `surface-pro-11-linux/kernel/port-7.3/config` | `7798b8bebf2d286c0dfea770d357ceea7ff3b6e55c14bcb70cf5dfad6dc2d011` |
| **Topologia Recompilada** | `X1E80100-Microsoft-Surface-Pro-11-FullIO-v19c0.conf` | `e7bb06a03e7bd9b869825a51775355a6743477d1579d78eb09fad5881cfb20f0` |

---

## 3. Decisões de Resolução de Conflitos

### 3.1 Gerenciamento de Memória e Buffer de Posição (`q6apm-dai.c` e `q6apm.c`)
- **Problema detectado:** A base protegida antiga alocava buffers de posição específicos via `ar_graph` com deslocamentos obsoletos e utilizava `q6apm_get_pull_hw_pointer()`. A base nova de câmera introduziu um mecanismo genérico de push/pull com buffer fixo de 512 KB (`BUFFER_BYTES_MAX`) e buffer de posição de 4 KB anexado (`POS_BUFFER_BYTES`), mapeado via `q6apm_map_pos_buffer()`.
- **Decisão:** Manteve-se a infraestrutura de memória genérica do kernel mais novo (`pos_buffer`, `prtd->pos_phys`, `info->pos_buf_mem_map_handle`). A rotina `q6apm_graph_configure_pull()` foi adaptada para utilizar explicitamente o buffer de posição mapeado genericamente, eliminando alocações redundantes e impedindo estouro de buffer (out-of-bounds) que ocorreria caso se combinasse buffer de página simples com offset de 512 KB.

### 3.2 Despacho de Eventos e Identificadores Duplicados (`audioreach.h` e `q6apm.h`)
- **Problema detectado:** Risco de colisão no identificador numérico `0x100b`, presente tanto como `APM_CLIENT_EVENT_WATERMARK_EVENT` (upstream/câmera) quanto `APM_CLIENT_EVENT_PULL_WATERMARK` (SP11X1e-audio).
- **Decisão:** Padronizou-se o uso de `APM_CLIENT_EVENT_WATERMARK_EVENT` (0x100b). Foram preservadas as definições necessárias de `APM_CLIENT_EVENT_SOFT_PAUSE_COMPLETE` (0x100c) e `APM_CLIENT_EVENT_SOFT_RESUME_COMPLETE` (0x100d). No callback `graph_callback`, declarou-se e utilizou-se `client_event` de forma unificada.

### 3.3 Tratamento de Tokens de Mapeamento (`q6apm.c`)
- **Problema detectado:** A árvore de áudio protegido utilizava `Q6APM_OOB_MAP_TOKEN` (`BIT(31)`) e `Q6APM_POSITION_MAP_TOKEN` (`BIT(30)`), enquanto a árvore nova utiliza `APM_MMAP_TOKEN_MAP_TYPE_POS_BUF` (`BIT(16)`).
- **Decisão:** O despacho de unmap e map foi estruturado priorizando o token OOB (`hdr->token & Q6APM_OOB_MAP_TOKEN`), e em seguida direcionando o token genérico com `APM_MMAP_TOKEN_MAP_TYPE_POS_BUF` para o `pos_buf_mem_map_handle` da estrutura `graph_info`.

### 3.4 Ciclo de Vida do WSA884x (`wsa884x.c`)
- **Problema detectado:** Conflito nos hooks DAPM `SND_SOC_DAPM_POST_PMU` e `SND_SOC_DAPM_PRE_PMD` entre o locking scoped upstream e a máquina de estados de recuperação/observação de saúde dos transdutores (`wsa884x->pa_health_work`).
- **Decisão:** Preservou-se o locking com `sp_lock` protegendo o estado `pa_on`, os contadores de recuperação e a sincronização `cancel_delayed_work_sync(&wsa884x->pa_health_work)` no desligamento (PMD). Mantido `#sound-dai-cells = <1>` para suportar os 3 DAIs: Playback (0), VI feedback (1) e CPS feedback (2).

### 3.5 Inclusões de Cabeçalhos e Bindings (`lpass-macro-common.c` e `qcom-gpi.h`)
- **`lpass-macro-common.c`:** Mantidas ambas as inclusões: `<linux/cleanup.h>` (da base de câmera) e `<linux/errno.h>` (da base de áudio).
- **`qcom-gpi.h`:** Mantido `#define QCOM_GPI_QSPI 9` exigido pelo controlador SPI/câmera.

---

## 4. Integração no Device Tree (`x1-microsoft-denali.dtsi`)

A integração conciliou os requisitos de proteção com a preservação do display LCD:

1. **Preservação do Display e Backlight:**
   - O painel LCD mantém sua alimentação e controle no conector eDP:
     ```dts
     &mdss_dp3 {
         compatible = "qcom,x1e80100-dp";
         status = "okay";
         aux-bus {
             panel: panel {
                 compatible = "edp-panel";
                 enable-gpios = <&pmc8380_3_gpios 4 GPIO_ACTIVE_HIGH>;
                 power-supply = <&vreg_edp_3p3>;
                 pinctrl-0 = <&edp_bl_en>;
                 pinctrl-names = "default";
             };
         };
     };
     ```
   - O pino `pmc8380_3_gpios 4` (`edp_bl_en`) foi integralmente mantido sem alterações.

2. **Caminhos de Feedback e Proteção dos Alto-Falantes:**
   - Atualizado o DAI link principal (`wsa-dai-link`) para apontar para o DAI 0 dos dois amplificadores:
     `sound-dai = <&left_spkr 0>, <&right_spkr 0>, <&swr0 0>, <&lpass_wsamacro 0>;`
   - Adicionado `wsa-vi-dai-link` (link de proteção VI, 8 kHz, 2 canais, S32_LE via `WSA_CODEC_DMA_TX_0`):
     `sound-dai = <&left_spkr 1>, <&right_spkr 1>, <&swr0 9>, <&lpass_wsamacro 2>;`
   - Adicionado `wsa-cps-dai-link` (link de proteção CPS, 24 kHz via `WSA_CODEC_DMA_TX_1`):
     `sound-dai = <&left_spkr 2>, <&right_spkr 2>, <&swr0 10>, <&lpass_wsamacro 4>;`
   - Configurados `left_spkr` e `right_spkr` em `&swr0` com `#sound-dai-cells = <1>`, `qcom,visense-channel-mask = <3>`, `qcom,enable-cps`, e `qcom,cps-offset1` (<0> e <25>).
   - Atualizado `&lpass_vamacro` com `qcom,dmic-sample-rate = <4800000>` para coincidir com o divisor DIV4 do Windows no clock de 19.2 MHz do DMIC.
   - Atualizado o schema de binding `Documentation/devicetree/bindings/sound/qcom,wsa8840.yaml`.

---

## 5. Auditoria de Falhas e Propagação de Erros

A árvore foi inspecionada estaticamente para garantir que nenhuma falha no subsistema de proteção resulte em bypass silencioso para áudio desprotegido:
- Se `q6apm_map_oob_buffer()` falhar: o grafo é imediatamente abortado e fechado (`goto close_graph`), retornando código de erro.
- Se `audioreach_send_protected_graph_calibration()` falhar: o buffer OOB é desfeito (`q6apm_unmap_oob_buffer`) e o grafo é fechado.
- Se `q6apm_graph_configure_pull()` falhar (ex.: parâmetros de sample rate, canais ou formato incompatíveis): o erro é propagado para o driver ALSA DAI (`q6apm-dai.c`), abortando a inicialização do fluxo.
- Em `x1e80100.c`: se a alocação de SoundWire para VI ou CPS falhar, o estado de prontidão é explicitamente desativado (`q6apm_sp11_set_vi_ready(false)`, `q6apm_sp11_set_cps_ready(false)`).

---

## 6. Resultados da Compilação

Ambiente: Container Docker `fedora:44` nativo AArch64 com GCC 16.2.1, pahole v1.32.

### 6.1 Subsistemas Compilados
- `drivers/soundwire/`: compilação concluída com sucesso (código de saída 0).
- `sound/soc/codecs/`: compilação concluída com sucesso (código de saída 0), gerando `snd-soc-wsa884x.o`, `snd-soc-lpass-wsa-macro.o`, `snd-soc-lpass-va-macro.o`, `snd-soc-lpass-tx-macro.o`, `snd-soc-lpass-macro-common.o`.
- `sound/soc/qcom/`: compilação concluída com sucesso (código de saída 0), gerando `snd-q6apm.o` e `snd-soc-x1e80100.o`.
- `drivers/media/platform/qcom/camss/` e `drivers/media/i2c/`: compilação concluída com sucesso (código de saída 0), gerando `qcom-camss.o`, `imx681.o`, `ov13858.o`, `vd55g0.o`.
- `arch/arm64/boot/dts/qcom/`: compilação de DTBs concluída com sucesso (código de saída 0), gerando `x1p64100-microsoft-denali.dtb` (LCD) e `x1e80100-microsoft-denali-oled.dtb`.

### 6.2 Reprodutibilidade do Patch
- O arquivo `patches/kernel/0002-sp11-protected-audio-port.patch` foi testado aplicando-se sobre uma árvore limpa de `output/kernel-integration/audio-camera-pristine/` com o comando:
  ```sh
  patch -p1 --fuzz=0 --batch -i patches/kernel/0002-sp11-protected-audio-port.patch
  ```
- Resultado: Exit code 0, 21 arquivos modificados, hashes SHA256 100% idênticos aos da árvore de integração.
- `git diff --check` executado sem erros de formatação ou whitespace.

---

## 7. Riscos Residuais e Limites de Validação Física

> [!IMPORTANT]
> **Validação em Hardware Real Pendente:**
> 1. A compilação sem erros dos módulos e do Device Tree valida a coerência da ABI e da sintaxe, mas **não valida o comportamento físico nem a segurança térmica/mecânica dos transdutores**.
> 2. Os parâmetros individuais de calibração R0/T0 variam por unidade fabril. O ACDB `REV_0D` confere com o da máquina investigada, mas a telemetria do DSP em tempo de execução precisa ser monitorada em hardware real antes de qualquer teste com volume ampliado.
> 3. Os limites conservadores de ganho em software (PipeWire/ALSA UCM) devem ser mantidos estritamente ativos até que a instrumentação física comprove a atuação efetiva do algoritmo de atenuação por excursão/aquecimento.
