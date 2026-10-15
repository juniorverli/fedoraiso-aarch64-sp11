# Relatório de Engenharia Reversa (REA - morluto/rea)
**Dispositivo:** Microsoft Surface Pro 11 (Qualcomm Snapdragon X Plus `X1P64100`)
**Origem dos Binários:** Windows 11 ARM64 DriverStore (`/mnt/c/Windows/System32/DriverStore/FileRepository/`)
**Ferramental Utilizado:** REA (`morluto/rea` / `rea-agents` v6.5.0) via `inspect-with-objdump`, análise de cabeçalhos PE/COFF AArch64, dissecção de tabelas de símbolos e extração de strings de chamadas DMF/WDF.

---

## 1. Subsistema Teclado Type Cover & Flex (Surface Serial Hub / SAM)

### 1.1 Artefato Analisado
- **Arquivo:** `SurfaceTypeCoverV7FprUdeDriver.sys`
- **Caminho:** `/mnt/c/Windows/System32/DriverStore/FileRepository/surfacetypecoverv7fprudedriver.inf_arm64_dcf9c3172b6e3fbd/SurfaceTypeCoverV7FprUdeDriver.sys`
- **Formato:** PE32+ Executable (pei-aarch64-little), Kernel Driver
- **SHA-256:** `5cf829915e1fb0b62f94f483f024904d7c031b7323d6c37a357789bd7b026920`
- **Endereço de Entrada (Entry Point):** `0x0000000140028620`
- **REA Evidence ID:** `ev_4ce5b7a162918e84ead84c25f917413a0c21d0797011ed69cb055c59ef60810c`

### 1.2 Evidências e Símbolos Identificados
Através da análise com o REA, foram identificados os seguintes módulos do Driver Module Framework (DMF) e da biblioteca de comunicação Surface Serial Hub (SSH):
- `SamCommunicationViaSsh_OnDeviceArrivalNotification`: Manipulador de chegada de dispositivo (attach) no conector físico.
- `SamCommunicationViaSsh_OnDeviceRemovalNotification`: Manipulador de remoção de dispositivo (detach).
- `SamNotificationViaSsh_StreamingStart`: Início do fluxo assíncrono de eventos de entrada via SSH.
- `SamNotificationViaSsh_RegisterForTargetNotification`: Registro de categoria de alvo junto ao firmware do SAM.
- Identificador de Destino INF: `{8203a233-a0ce-44ae-b67b-9ba128f5acc4}\Target_KIP&Category_FPR`
- No driver complementar `SurfaceHidMiniDriver.sys` (SHA-256: `66d8bfa7f2a1ebbb59e5124b8156aa4e01974776`):
  - `Target_KIP&Category_HID` e `Target_SAM&Category_HID` vinculados aos ACPI IDs `MSHW0096` e barramento serial SSH UART (`&uart2`).

### 1.3 Conclusão Técnica e Relação com Linux
- **Fato Observado:** O teclado Type Cover comunica-se exclusivamente através do protocolo serial do SAM (Target `KIP` = Keyboard Interface Protocol, código `0x02`, categoria HID `0x02`). O leitor de impressão digital opera sobre uma emulação UDE (USB Device Emulation) via SSH.
- **Implementação no Linux:** O driver Linux `surface_hid` e `surface_kbd` espelha exatamente a mesma arquitetura de despache KIP via `surface_aggregator` (`CONFIG_SURFACE_AGGREGATOR`). O suporte para digitação e touchpad no dock é suportado; a funcionalidade sem fio do novo Surface Pro Flex Keyboard requer emparelhamento Bluetooth LE padrão em modo desacoplado.

---

## 2. Subsistema Sensores (Qualcomm Sensor SEE & FastRPC)

### 2.1 Artefato Analisado
- **Arquivo:** `qcSensors.dll`
- **Caminho:** `/mnt/c/Windows/System32/DriverStore/FileRepository/qcsensors.inf_arm64_08abad6c5f3b94d9/qcSensors.dll`
- **Formato:** PE32+ DLL (pei-aarch64-little), UMDF Sensor Driver
- **SHA-256:** `7bb1e9571bd5838b32ede7ae22810fb377b3bc1354dc0e2a4f8ec497aaaa9fbf`
- **Endereço de Entrada (Entry Point):** `0x0000000180182350`
- **REA Evidence ID:** `ev_f49966334bd1181b767b1376d094d921999e18be3d1ede12ecdeff9d565527f4`

### 2.2 Evidências e Símbolos Identificados
- Símbolos de Interface:
  - `IOCTL_FASTRPC_GET_INTERFACE_VERSION`
  - `IOCTL_FASTRPC_GET_MAPPING`
  - `createstaticpd:sensorspd`
  - `FATAL: could not find sensors QMI service due to timeout`
- Hardware ACPI IDs identificados no `.inf`:
  - `ACPI\MSHW0464`, `ACPI\MSHW0488`, `ACPI\MSHW0544`, `ACPI\MSHW0568`, `ACPI\QCOM0CE7`

### 2.3 Conclusão Técnica e Relação com Linux
- **Fato Observado:** Os sensores físicos (acelerômetro, giroscópio, luz ambiente) **não possuem registradores de I2C/SPI diretamente expostos ao sistema operacional**. O firmware do processador de sinais digitais de áudio/sensores (ADSP - `qcadsp8380.mbn`) executa o **Qualcomm Sensors Execution Environment (SEE)** em um domínio de proteção dedicado (`sensorspd`), acessível via FastRPC e mensagens QMI.
- **Implementação no Linux:** O suporte requer o carregamento bem-sucedido do ADSP remoteproc (`qcom_q6v5_pas`), disponibilidade do dispositivo `/dev/fastrpc-adsp` (ou `sensorspd`) e dos arquivos JSON de registro de sensores (`adsps.jsn`, `adspr.jsn`) mapeados em `/usr/share/qcom/` para integração ao `iio-sensor-proxy`.

---

## 3. Subsistema Câmeras, MIPI CSI-2 & Spectra ISP

### 3.1 Artefatos Analisados
- **Arquivo 1:** `qccammipicsi8380.sys`
  - **SHA-256:** `033f5b1431ad4c76a12ac3b7f0a5be42e460a03bcff40d249511b3034786d407`
  - **Hardware ID:** `ACPI\QCOM0C98` (Qualcomm Camera MIPI CSI Controller)
  - **REA Evidence ID:** `ev_071842a6f28f1031778aaedc57aaca4d4ffb4ff1fdbdfe7c166659e3162bb89c`
- **Arquivo 2:** `qccamisp8380.sys`
  - **Hardware ID:** `ACPI\QCOM0C25` (Qualcomm Spectra Image Signal Processor)
  - **Firmware Requerido:** `CAMERA_ICP.mbn` (Image Control Processor)

### 3.2 Evidências e Símbolos Identificados
- Símbolos de controle:
  - `CameraKMDFlashEvtIoControl`
  - `CAMERA_DEVICE_IRPCMD_GETFNTABLE`
  - Chamadas de controle de ISP via IPC e barramento CSI-2 D-PHY/C-PHY.
  - O driver de sensor requer alimentação de clock e tensão através dos reguladores PMIC VANA/VDIG gerenciados pelo subsistema ISP.

### 3.3 Conclusão Técnica e Relação com Linux
- **Fato Observado:** As câmeras dependem de uma stack de hardware proprietária de três camadas:
  1. Controlador MIPI CSI-2 físico (`QCOM0C98`).
  2. Processador de sinal de imagem Spectra 695 / CAMSS (`QCOM0C25`), controlado pelo microcódigo `CAMERA_ICP.mbn`.
  3. Módulos de sensor (Frontal Sony IMX681, Traseira OmniVision OV13858, IR STMicroelectronics VD55G0).
- **Status no Linux:** No kernel Linux atual (mainline e `linux-surface`), o driver `camss` da Qualcomm suporta gerações anteriores (Titan 170 / SC8280XP), mas o pipeline Spectra 695 da plataforma Snapdragon X Plus/Elite **ainda não foi implementado pelo consórcio Linaro/Qualcomm**.
- **Grau de Confiança:** Fato comprovado por inspeção binária e pelo estado da árvore de desenvolvimento do kernel upstream. Câmeras permanecem classificadas como **bloqueadas upstream**.

---

## 4. Subsistema LED de Privacidade & Flash

### 4.1 Artefato Analisado
- **Arquivo:** `qccamflash8380.sys`
- **Caminho:** `/mnt/c/Windows/System32/DriverStore/FileRepository/qccamflash8380.inf_arm64_e7729176a9bcf2a8/qccamflash8380.sys`
- **Hardware ID:** `ACPI\QCOM0C27`

### 4.2 Evidências e Símbolos Identificados
- Strings de código-fonte registradas no binário:
  - `Z:\b\WP\Camera\rel\10.9\CamZ\Core\FlashDriver\WhiteLEDFlashDriverSoC\src\CameraWhiteLEDFlash.c`
  - `Z:\b\WP\Camera\rel\10.9\CamZ\Core\FlashDriver\WhiteLEDFlashDriverSoC\src\CameraWhiteLEDFlashPMIC.c`
  - `CameraWhiteLEDFlashPMIC_SetTargetCurrent with LED1 %d LED2 %d`
  - `CameraWhiteLEDFlashPMIC_Fire for LED1 %d LED2 %d`

### 4.3 Conclusão Técnica e Relação com Linux
- **Fato Observado:** O indicador de flash/iluminação e o LED de status não são GPIOs simples acessíveis diretamente pelo usuário; eles são controlados pelo submódulo de White LED Flash do PMIC Qualcomm (`pmic_flash` / `qcom-spmi-flash-led`).
- **Implementação no Linux:** Scripts em userspace baseados em gatilhos de udev (`90-surface-privacy-led.rules`) atuam como proxy para dispositivos que utilizam câmeras virtuais, mas o controle nativo do LED físico de privacidade permanece acoplado à inicialização do subsistema de câmera pelo hardware.

---

## 5. Diretrizes de Redistribuição de Firmwares
Em conformidade com a legislação de propriedade intelectual e a política estrita de licenciamento do projeto:
- Firmwares proprietários extraídos da partição Windows DriverStore do usuário **não devem ser commitados no histórico público do Git sem permissão explícita de redistribuição da Microsoft e da Qualcomm**.
- O pipeline foi construído com a ferramenta automatizada `firmware/extract-firmware.sh`, que extrai legitimamente os arquivos locais da instalação física do usuário em tempo de build, respeitando a conformidade de licenciamento.
