# Camera resources: decoded package evidence

Status: offline package analysis. No new Fedora capture is present; the available captures remain labelled WSL smoke checks. Windows host IDs now correlate with the selected variants; Linux bindings and electrical behavior remain unconfirmed. Collected 2026-10-15 from the same local DriverStore source described in [initial findings](INITIAL_STATIC_FINDINGS.md).

## Container identification

The `AeoB` bytes and 12-byte header match the little-endian representation of the Windows ACPI method-output buffer signature. Microsoft documents its signature/length/count and typed arguments. ReactOS publishes compatible signature, type and argument-stride definitions. The selected files consume exactly their declared lengths and counts using this layout. This identifies a serialized method-output container, not executable AML.

- [Microsoft output-buffer layout](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/acpiioct/ns-acpiioct-_acpi_eval_output_buffer_v1)
- [Microsoft typed argument layout](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/acpiioct/ns-acpiioct-_acpi_method_argument_v1)
- [ReactOS signature and stride definitions](https://doxygen.reactos.org/d9/d81/acpiioct_8h_source.html) (snapshot identifies `3812a95`; lines 11, 30–34, 153–161).

Sources checked 2026-10-15. Advancing by `4 + max(4, DataLength)` preserves unaligned records. Eight-byte integer payloads occur in these files; the decoder preserves all eight bytes and warns that this is wider than the V1 documented ULONG member. This does not establish support for a different ACPI wire-layout version. Vendor tuple meanings remain separate from this container structure.

## Sources and selected board variants

All paths are under the local `DriverStore/FileRepository`. These packages support several variants. The matching extension INF entries associate SONY/0681 + MSHW0490, OVTI/D858 + MSHW0491 and SMO/55F0 + MSHW0492 with the files below; the exact INF hashes and line numbers are in [initial findings](INITIAL_STATIC_FINDINGS.md). DriverVer is `04/25/2025,1.0.4258.7908`. Package presence does not prove selection on this board.

| File | Bytes | SHA256 |
|---|---|---|
| `SCFG_FRONT_MSHW0490.bin` | 133 | `e6e3d828a1e4f5bc94c545848a091c20be399a4b22c938ed4a3df072dd033d99` |
| `CAMF_RES_MSHW0490.bin` | 1843 | `379a03154511922428ea27f56de625f579f39ca483fb97398953278b6b5f2851` |
| `SCFG_REAR_MSHW0491.bin` | 135 | `fa1d4b79ac3305ed822aae7fb2d1676d28eb130cb651b2b7f84d208aab64652a` |
| `CAMS_RES_MSHW0491.bin` | 2293 | `2d356bbfaf07ced1e5c03014a5c496b12107f5dc489c4333052565d5a5a5dcc2` |
| `SCFG_AUX_MSHW0492.bin` | 151 | `1c848ac4ddbe12948cae4affee421e3a457cac61f98dacb30043841bf0bd1bff` |
| `CAMI_RES_MSHW0492.bin` | 2187 | `fb058d3c966f4b48412d48c2de7f58b861103a8aa06f0bb8c1d198e12431d908` |

Each source lives in `surfacecamfrontsensor_extension8380.inf_arm64_5a4c66ce4812274e`, `surfacecamrearsensor_extension8380.inf_arm64_9e667d808f1a7021`, or `surfacecamauxsensor_extension8380.inf_arm64_84ddd55dc933cac9`, according to front/rear/aux. Native Windows PnP observations below correlate current host IDs with the selected variants. Original installation date and correspondence with the currently booted Fedora system remain unknown.

## Windows host correlation

Read-only native Windows queries through WSL identify the host as `Microsoft Corporation` / `Microsoft Surface Pro, 11th Edition` / `ARM64-based PC`. `Get-PnpDevice -PresentOnly` reports the following devices with status `OK`; this is Windows enumeration, not proof of Linux bindings or a camera capture test.

| Present device | First hardware ID | Driver matching ID | Active INF / version |
|---|---|---|---|
| Surface Camera Rear | `ACPI\VEN_OVTI&DEV_D858&SUBSYS_MSHW0491&REV_0000` | `ACPI\OVTID858` | `oem296.inf` / `1.0.4258.7908` |
| Qualcomm(R) All-Ways Aware(TM) Sensor Platform Device - Keyboard | `ACPI\VEN_MSHW&DEV_048B&SUBSYS_MSHW0487` | `ACPI\MSHW0488` | `oem126.inf` / `6982.1.0.0` |
| Surface Camera Front | `ACPI\VEN_SONY&DEV_0681&SUBSYS_MSHW0490&REV_0000` | `ACPI\SONY0681` | `oem295.inf` / `1.0.4258.7908` |
| Qualcomm(R) All-Ways Aware(TM) Sensor Platform Device - Display | `ACPI\VEN_MSHW&DEV_048A&SUBSYS_MSHW0487` | `ACPI\MSHW0488` | `oem126.inf` / `6982.1.0.0` |
| Surface IR Camera Front | `ACPI\VEN_SMO&DEV_55F0&SUBSYS_MSHW0492&REV_0000` | `ACPI\SMO55F0` | `oem293.inf` / `1.0.4258.7908` |

The front/rear/IR subsystem IDs match the MSHW0490/0491/0492 package variants selected for analysis. Windows reports `QCOM0C25` ISP, `QCOM0C98` MIPI CSI and `QCOM0C32` platform devices as present as well. Matching device IDs for the display/keyboard sensor platforms resolve through compatible ID `ACPI\MSHW0488`, explaining why the base `qcSensors.inf` did not list MSHW048A/048B directly.

`C:\Windows\INF\oem126.inf` has SHA256 `5a4ca78ece80732d552ae47e23158e6b77f70edc6387b712f591dc230ac59c82`, exactly matching the analyzed `qcSensors.inf`. Its UMDF service references `qcSensors.dll`; this ties the active Windows sensor-platform package to the earlier FastRPC/QMI string leads. It does not establish which logical sensor provides ALS, nor a Linux transport.

Retained private native-query envelopes (acquired 2026-10-15):

- `output/phase1-camera-resources/windows-present-devices.json`: SHA256 `1f792bd9a35ddcfc8fe20fc7ea11469c2d08cab81b8930ff3cdf98348164e383`
- `output/phase1-camera-resources/windows-driver-properties.json`: SHA256 `f7604354e1ec6cdf41669e7bc30b4a8030fcb2325152b280c7439e35fd187886`
- `output/phase1-camera-resources/windows-driver-matches.json`: SHA256 `4843a5c90e9adf99884ad06f2d5717f5eb1b98128eae648121610495c4b45035`

Native PowerShell reproduction for driver mapping (no serial/instance IDs are emitted):

```powershell
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
@(Get-PnpDevice -PresentOnly | Where-Object { $_.Class -eq 'Camera' -or $_.FriendlyName -like '*All-Ways Aware*' } | ForEach-Object {
  $properties = @{}
  foreach ($key in @('DEVPKEY_Device_DriverInfPath','DEVPKEY_Device_DriverVersion','DEVPKEY_Device_Service','DEVPKEY_Device_HardwareIds','DEVPKEY_Device_CompatibleIds','DEVPKEY_Device_MatchingDeviceId')) {
    $properties[$key] = (Get-PnpDeviceProperty -InstanceId $_.InstanceId -KeyName $key -ErrorAction SilentlyContinue).Data
  }
  [PSCustomObject]@{ Name=$_.FriendlyName; Properties=$properties }
}) | ConvertTo-Json -Depth 6
```

For host identity, use `Get-CimInstance Win32_ComputerSystem | Select-Object Manufacturer, Model, SystemType`. For presence/status, use `Get-PnpDevice -PresentOnly | Where-Object { $_.Class -in @('Camera','Sensor') } | Select-Object Class, FriendlyName, Status`. PowerShell version was not recorded; these are observations from the retained query outputs.

## SCFG observations

Offsets below are absolute argument-header offsets; payload begins four bytes later. Integers are reported without assigned vendor meaning.

| File | Argument offsets and observed values |
|---|---|
| `SCFG_FRONT_MSHW0490.bin` | `0x10`: `com.surface.sensormodule.ffc_imx681.bin`; `0x3c`: `com.surface.tuned.ffc_imx681.bin`; `0x61`: `1376288`; `0x6d`: `184483844`; `0x79`: `0` |
| `SCFG_REAR_MSHW0491.bin` | `0x10`: `com.surface.sensormodule.rfc_ov13858.bin`; `0x3d`: `com.surface.tuned.rfc_ov13858.bin`; `0x63`: `1376288`; `0x6f`: `3629461515`; `0x7b`: `0` |
| `SCFG_AUX_MSHW0492.bin` | `0x10`: `com.surface.sensormodule.aux_vd55g0_MSHW0492.bin`; `0x45`: `com.surface.tuned.aux_vd55g0_MSHW0492.bin`; `0x73`: `1376448`; `0x7f`: `809959424`; `0x8b`: `0` |

The module and tuning filenames are references in data, not Linux driver filenames. The trailing SCFG integers need consumer-code analysis before being assigned meanings such as sensor position, dimensions or transport.

## Resource observations and draft contradictions

The outer `DEVICE` package names `\_SB.CAMF`, `\_SB.CAMS`, `\_SB.CAMI`. Each contains serialized `DSTATE` packages with numeric labels 0 and 3. The following are selected entries inside the package labelled 0. Values retain serialized order. The table does not prove the driver executes every entry in this order.

| Resource | Type-tag header | Argument-header offsets and raw tuple values |
|---|---|---|
| `CAMF_RES_MSHW0490.bin` | `TLMMGPIO` at `0x1fd` | `0x20e`: `237`; `0x21a`: `0`; `0x226`: `0`; `0x232`: `1`; `0x23e`: `0`; `0x24a`: `0` |
| `CAMF_RES_MSHW0490.bin` | `CLOCK` at `0x25a` | `0x268`: `cam_cc_mclk4_clk`; `0x27d`: `8`; `0x289`: `19200000`; `0x295`: `3` |
| `CAMF_RES_MSHW0490.bin` | `PMICVREGVOTE` at `0x2a5` | `0x2ba`: `PPP_RESOURCE_ID_LDO3_M`; `0x2d5`: `1`; `0x2e1`: `1800000`; `0x2ed`: `1`; `0x2f9`: `7`; `0x305`: `0` |
| `CAMF_RES_MSHW0490.bin` | `PMICVREGVOTE` at `0x315` | `0x32a`: `PPP_RESOURCE_ID_LDO7_B`; `0x345`: `1`; `0x351`: `2800000`; `0x35d`: `1`; `0x369`: `7`; `0x375`: `0` |
| `CAMF_RES_MSHW0490.bin` | `TLMMGPIO` at `0x3a3` | `0x3b4`: `237`; `0x3c0`: `1`; `0x3cc`: `0`; `0x3d8`: `1`; `0x3e4`: `0`; `0x3f0`: `0` |
| `CAMS_RES_MSHW0491.bin` | `TLMMGPIO` at `0x1fd` | `0x20e`: `110`; `0x21a`: `0`; `0x226`: `0`; `0x232`: `1`; `0x23e`: `0`; `0x24a`: `0` |
| `CAMS_RES_MSHW0491.bin` | `PMICVREGVOTE` at `0x25a` | `0x26f`: `PPP_RESOURCE_ID_LDO6_M`; `0x28a`: `1`; `0x296`: `1800000`; `0x2a2`: `1`; `0x2ae`: `7`; `0x2ba`: `0` |
| `CAMS_RES_MSHW0491.bin` | `PMICVREGVOTE` at `0x2ca` | `0x2df`: `PPP_RESOURCE_ID_LDO1_M`; `0x2fa`: `1`; `0x306`: `1200000`; `0x312`: `1`; `0x31e`: `7`; `0x32a`: `0` |
| `CAMS_RES_MSHW0491.bin` | `PMICVREGVOTE` at `0x33a` | `0x34f`: `PPP_RESOURCE_ID_LDO5_M`; `0x36a`: `1`; `0x376`: `2800000`; `0x382`: `1`; `0x38e`: `7`; `0x39a`: `0` |
| `CAMS_RES_MSHW0491.bin` | `PMICVREGVOTE` at `0x3c8` | `0x3dd`: `PPP_RESOURCE_ID_LDO16_B`; `0x3f9`: `1`; `0x405`: `2900000`; `0x411`: `1`; `0x41d`: `7`; `0x429`: `0` |
| `CAMS_RES_MSHW0491.bin` | `CLOCK` at `0x439` | `0x447`: `cam_cc_mclk1_clk`; `0x45c`: `8`; `0x468`: `19200000`; `0x474`: `3` |
| `CAMS_RES_MSHW0491.bin` | `TLMMGPIO` at `0x484` | `0x495`: `110`; `0x4a1`: `1`; `0x4ad`: `0`; `0x4b9`: `1`; `0x4c5`: `0`; `0x4d1`: `0` |
| `CAMI_RES_MSHW0492.bin` | `TLMMGPIO` at `0x1fd` | `0x20e`: `109`; `0x21a`: `0`; `0x226`: `0`; `0x232`: `1`; `0x23e`: `0`; `0x24a`: `0` |
| `CAMI_RES_MSHW0492.bin` | `CLOCK` at `0x278` | `0x286`: `cam_cc_mclk0_clk`; `0x29b`: `8`; `0x2a7`: `19200000`; `0x2b3`: `3` |
| `CAMI_RES_MSHW0492.bin` | `PMICVREGVOTE` at `0x2e1` | `0x2f6`: `PPP_RESOURCE_ID_LDO4_M`; `0x311`: `1`; `0x31d`: `1800000`; `0x329`: `1`; `0x335`: `7`; `0x341`: `0` |
| `CAMI_RES_MSHW0492.bin` | `PMICVREGVOTE` at `0x351` | `0x366`: `PPP_RESOURCE_ID_LDO2_M`; `0x381`: `1`; `0x38d`: `1150000`; `0x399`: `1`; `0x3a5`: `7`; `0x3b1`: `0` |
| `CAMI_RES_MSHW0492.bin` | `PMICVREGVOTE` at `0x3df` | `0x3f4`: `PPP_RESOURCE_ID_LDO7_M`; `0x40f`: `1`; `0x41b`: `2800000`; `0x427`: `1`; `0x433`: `7`; `0x43f`: `0` |
| `CAMI_RES_MSHW0492.bin` | `TLMMGPIO` at `0x46d` | `0x47e`: `109`; `0x48a`: `1`; `0x496`: `0`; `0x4a2`: `1`; `0x4ae`: `0`; `0x4ba`: `0` |

| Candidate role | Parsed first TLMMGPIO integer | Parsed MCLK label / numeric value | Old inactive DTS hypothesis |
|---|---|---|---|
| Front / MSHW0490 | 237 (`0xed`) | `cam_cc_mclk4_clk` / 19200000 | GPIO110 / MCLK index0 / 24000000 |
| Rear / MSHW0491 | 110 (`0x6e`) | `cam_cc_mclk1_clk` / 19200000 | GPIO111 / MCLK index1 / 24000000 |
| Aux IR / MSHW0492 | 109 (`0x6d`) | `cam_cc_mclk0_clk` / 19200000 | GPIO112 / MCLK index2 / 24000000 |

Inference: the old draft is inconsistent with these selected Windows package descriptors. Numeric clock value 19200000 is consistent with 19.2MHz if the consumer expects Hz; the unit and flag fields still need verification. The first TLMMGPIO integer is a candidate pin identifier, not a proven Linux GPIO offset or reset line. PMIC tuple values resemble rail votes, but units, mapping and ownership have not been established. Delay entries likewise have unverified units.

Do not replace DTS constants from this table. Required corroboration: actual board variant, matching ACPI/DT resources, driver consumers of each tuple, regulator/clock provider mappings, and Linux pin numbering. Keep `dts/camera-sp11.dtsi` inactive. No active DTB or ISO was changed.

## Complete ordered DSTATE inventory

This compact inventory includes every direct resource entry in both serialized states. Offsets identify the resource package header; tuple values are in stored order. Units, flags and execution order remain unverified. Detailed leaf offsets are recoverable from the decoder output.

### CAMF_RES_MSHW0490.bin

State label `0`; package header `0x6e`:

- `0x89` `NPARESOURCE`: `[1, "/arc/client/rail_mmcx", 64]`
- `0xd3` `CLOCK`: `["gcc_camera_xo_clk", 1]`
- `0x107` `CLOCK`: `["gcc_camera_ahb_clk", 1]`
- `0x13c` `CLOCK`: `["cam_cc_gdsc_clk", 1]`
- `0x16e` `FOOTSWITCH`: `["cam_cc_titan_top_gdsc", 1]`
- `0x1ab` `CLOCK`: `["cam_cc_cpas_ahb_clk", 8, 80000000, 3]`
- `0x1f9` `TLMMGPIO`: `[237, 0, 0, 1, 0, 0]`
- `0x256` `CLOCK`: `["cam_cc_mclk4_clk", 8, 19200000, 3]`
- `0x2a1` `PMICVREGVOTE`: `["PPP_RESOURCE_ID_LDO3_M", 1, 1800000, 1, 7, 0]`
- `0x311` `PMICVREGVOTE`: `["PPP_RESOURCE_ID_LDO7_B", 1, 2800000, 1, 7, 0]`
- `0x381` `DELAY`: `[1]`
- `0x39f` `TLMMGPIO`: `[237, 1, 0, 1, 0, 0]`
- `0x3fc` `DELAY`: `[10]`

State label `3`; package header `0x41a`:

- `0x435` `TLMMGPIO`: `[237, 0, 0, 1, 0, 0]`
- `0x492` `DELAY`: `[1]`
- `0x4b0` `CLOCK`: `["cam_cc_mclk4_clk", 12, 0, 3]`
- `0x4fb` `PMICVREGVOTE`: `["PPP_RESOURCE_ID_LDO7_B", 1, 0, 0, 7, 0]`
- `0x56b` `PMICVREGVOTE`: `["PPP_RESOURCE_ID_LDO3_M", 1, 0, 0, 7, 0]`
- `0x5db` `CLOCK`: `["cam_cc_cpas_ahb_clk", 2]`
- `0x611` `FOOTSWITCH`: `["cam_cc_titan_top_gdsc", 2]`
- `0x64e` `CLOCK`: `["cam_cc_gdsc_clk", 2]`
- `0x680` `CLOCK`: `["gcc_camera_ahb_clk", 2]`
- `0x6b5` `CLOCK`: `["gcc_camera_xo_clk", 2]`
- `0x6e9` `NPARESOURCE`: `[1, "/arc/client/rail_mmcx", 0]`

### CAMS_RES_MSHW0491.bin

State label `0`; package header `0x6e`:

- `0x89` `NPARESOURCE`: `[1, "/arc/client/rail_mmcx", 64]`
- `0xd3` `CLOCK`: `["gcc_camera_xo_clk", 1]`
- `0x107` `CLOCK`: `["gcc_camera_ahb_clk", 1]`
- `0x13c` `CLOCK`: `["cam_cc_gdsc_clk", 1]`
- `0x16e` `FOOTSWITCH`: `["cam_cc_titan_top_gdsc", 1]`
- `0x1ab` `CLOCK`: `["cam_cc_cpas_ahb_clk", 8, 80000000, 3]`
- `0x1f9` `TLMMGPIO`: `[110, 0, 0, 1, 0, 0]`
- `0x256` `PMICVREGVOTE`: `["PPP_RESOURCE_ID_LDO6_M", 1, 1800000, 1, 7, 0]`
- `0x2c6` `PMICVREGVOTE`: `["PPP_RESOURCE_ID_LDO1_M", 1, 1200000, 1, 7, 0]`
- `0x336` `PMICVREGVOTE`: `["PPP_RESOURCE_ID_LDO5_M", 1, 2800000, 1, 7, 0]`
- `0x3a6` `DELAY`: `[1]`
- `0x3c4` `PMICVREGVOTE`: `["PPP_RESOURCE_ID_LDO16_B", 1, 2900000, 1, 7, 0]`
- `0x435` `CLOCK`: `["cam_cc_mclk1_clk", 8, 19200000, 3]`
- `0x480` `TLMMGPIO`: `[110, 1, 0, 1, 0, 0]`
- `0x4dd` `DELAY`: `[10]`

State label `3`; package header `0x4fb`:

- `0x516` `TLMMGPIO`: `[110, 0, 0, 1, 0, 0]`
- `0x573` `DELAY`: `[1]`
- `0x591` `CLOCK`: `["cam_cc_mclk1_clk", 12, 0, 3]`
- `0x5dc` `PMICVREGVOTE`: `["PPP_RESOURCE_ID_LDO16_B", 1, 0, 0, 7, 0]`
- `0x64d` `PMICVREGVOTE`: `["PPP_RESOURCE_ID_LDO5_M", 1, 0, 0, 7, 0]`
- `0x6bd` `PMICVREGVOTE`: `["PPP_RESOURCE_ID_LDO1_M", 1, 0, 0, 7, 0]`
- `0x72d` `PMICVREGVOTE`: `["PPP_RESOURCE_ID_LDO6_M", 1, 0, 0, 7, 0]`
- `0x79d` `CLOCK`: `["cam_cc_cpas_ahb_clk", 2]`
- `0x7d3` `FOOTSWITCH`: `["cam_cc_titan_top_gdsc", 2]`
- `0x810` `CLOCK`: `["cam_cc_gdsc_clk", 2]`
- `0x842` `CLOCK`: `["gcc_camera_ahb_clk", 2]`
- `0x877` `CLOCK`: `["gcc_camera_xo_clk", 2]`
- `0x8ab` `NPARESOURCE`: `[1, "/arc/client/rail_mmcx", 0]`

### CAMI_RES_MSHW0492.bin

State label `0`; package header `0x6e`:

- `0x89` `NPARESOURCE`: `[1, "/arc/client/rail_mmcx", 64]`
- `0xd3` `CLOCK`: `["gcc_camera_xo_clk", 1]`
- `0x107` `CLOCK`: `["gcc_camera_ahb_clk", 1]`
- `0x13c` `CLOCK`: `["cam_cc_gdsc_clk", 1]`
- `0x16e` `FOOTSWITCH`: `["cam_cc_titan_top_gdsc", 1]`
- `0x1ab` `CLOCK`: `["cam_cc_cpas_ahb_clk", 8, 80000000, 3]`
- `0x1f9` `TLMMGPIO`: `[109, 0, 0, 1, 0, 0]`
- `0x256` `DELAY`: `[1]`
- `0x274` `CLOCK`: `["cam_cc_mclk0_clk", 8, 19200000, 3]`
- `0x2bf` `DELAY`: `[2]`
- `0x2dd` `PMICVREGVOTE`: `["PPP_RESOURCE_ID_LDO4_M", 1, 1800000, 1, 7, 0]`
- `0x34d` `PMICVREGVOTE`: `["PPP_RESOURCE_ID_LDO2_M", 1, 1150000, 1, 7, 0]`
- `0x3bd` `DELAY`: `[1]`
- `0x3db` `PMICVREGVOTE`: `["PPP_RESOURCE_ID_LDO7_M", 1, 2800000, 1, 7, 0]`
- `0x44b` `DELAY`: `[1]`
- `0x469` `TLMMGPIO`: `[109, 1, 0, 1, 0, 0]`
- `0x4c6` `DELAY`: `[1]`

State label `3`; package header `0x4e4`:

- `0x4ff` `TLMMGPIO`: `[109, 0, 0, 1, 0, 0]`
- `0x55c` `DELAY`: `[5]`
- `0x57a` `PMICVREGVOTE`: `["PPP_RESOURCE_ID_LDO7_M", 1, 0, 0, 7, 0]`
- `0x5ea` `DELAY`: `[1]`
- `0x608` `PMICVREGVOTE`: `["PPP_RESOURCE_ID_LDO2_M", 1, 0, 0, 7, 0]`
- `0x678` `PMICVREGVOTE`: `["PPP_RESOURCE_ID_LDO4_M", 1, 0, 0, 7, 0]`
- `0x6e8` `CLOCK`: `["cam_cc_mclk0_clk", 12, 0, 3]`
- `0x733` `CLOCK`: `["cam_cc_cpas_ahb_clk", 2]`
- `0x769` `FOOTSWITCH`: `["cam_cc_titan_top_gdsc", 2]`
- `0x7a6` `CLOCK`: `["cam_cc_gdsc_clk", 2]`
- `0x7d8` `CLOCK`: `["gcc_camera_ahb_clk", 2]`
- `0x80d` `CLOCK`: `["gcc_camera_xo_clk", 2]`
- `0x841` `NPARESOURCE`: `[1, "/arc/client/rail_mmcx", 0]`

## Sensor-module data triage

The SCFG-referenced module files begin with ASCII `QTI Chromatix Header` and include `Parameter Parser V3.4.0 (2106301010)` at file offset `0x28`. GNU `file` reports them as data. This prefix is an observation, not a decoded Qualcomm schema. No sensor register table has been recovered from these bytes.

| Module | Bytes | SHA256 |
|---|---|---|
| `com.surface.sensormodule.ffc_imx681.bin` | 212272 | `f7dd81be64153fd3f0da8e6288ee1b9906b7bf51b773a98496934d76dc96a45c` |
| `com.surface.sensormodule.rfc_ov13858.bin` | 148262 | `f8f60e79b77bd3d5896cb04167ee428455e1a241f1ff9e50abee6b4dacfe6b14` |
| `com.surface.sensormodule.aux_vd55g0_MSHW0492.bin` | 136411 | `e574db7eb28231d3fa4f5eee5c1861919125d8ec7a753fc7a0708606e1f1a794` |

## REA platform-driver inspection

REA 6.5.0 CLI captured GNU AArch64 objdump disassembly of
`qccamplatform8380.sys` (SHA256 `836714ec41f92f45af363d7bf3c9b9cfc2cccdbd19a1c57f355b471068648049`).
Evidence ID: `ev_a99dcc3712512c266fdd6934ec4e5018c7b68214d68c379bab346f826d079eb7`. Provider exit was 0,
completion was complete, output was not truncated and before/after artifact
hashes matched. The raw envelope is ignored at
`output/phase1-camera-resources/platform-disassembly.json`.

```bash
mkdir -p output/phase1-camera-resources
REA_OBJDUMP_COMMAND=/usr/bin/aarch64-linux-gnu-objdump \
  npx --yes rea-agents@6.5.0 inspect-with-objdump \
  /mnt/c/Windows/System32/DriverStore/FileRepository/qccamplatform8380.inf_arm64_16d44e9aca3becfb/qccamplatform8380.sys \
  disassemble --format json > output/phase1-camera-resources/platform-disassembly.json
```

This retains assembly for subsequent consumer tracing; no function call graph,
GPIO flag meanings, or complete power sequence was established from it in this
step. The structural resource decoder is independent Python analysis, not REA
decompilation. REA's [objdump contract](https://github.com/morluto/rea/blob/main/docs/reverse-engineering-tools.md)
describes its raw-output and digest limitations (checked 2026-10-15).

## Reproduce and next checks

Generating decoder SHA256: `56c50e4577cff2dbcb8e5b777b038cd7ac72cc40818a7e91aa0c20ab151d0187`. The reviewed decoder reprocessed all six sources, matched the independent 595-node byte walk and reconstructed every source byte exactly.

Integer `value_decimal` and `value_hex` strings preserve exact values across JSON consumers; the numeric `value` field can round above 2^53−1 in JavaScript. Generated JSON should remain private.


The standard-library decoder is `scripts/decode-camera-resources.py` (1MiB and 10000 nodes per input, depth32; batches capped at 16MiB, 50000 nodes and 128 files). It validates bounded input, argument/package extents and counts, preserves source/parser hashes and byte offsets, and never executes an input. Unknown types stay opaque; malformed inputs fail. Full decoded JSON belongs under ignored output or private research paths. Existing output files are refused.

From the repository root under WSL:

```bash
mkdir -p output/phase1-camera-resources
python3 scripts/decode-camera-resources.py \
  /mnt/c/Windows/System32/DriverStore/FileRepository/surfacecamfrontsensor_extension8380.inf_arm64_5a4c66ce4812274e/SCFG_FRONT_MSHW0490.bin \
  /mnt/c/Windows/System32/DriverStore/FileRepository/surfacecamfrontsensor_extension8380.inf_arm64_5a4c66ce4812274e/CAMF_RES_MSHW0490.bin \
  /mnt/c/Windows/System32/DriverStore/FileRepository/surfacecamrearsensor_extension8380.inf_arm64_9e667d808f1a7021/SCFG_REAR_MSHW0491.bin \
  /mnt/c/Windows/System32/DriverStore/FileRepository/surfacecamrearsensor_extension8380.inf_arm64_9e667d808f1a7021/CAMS_RES_MSHW0491.bin \
  /mnt/c/Windows/System32/DriverStore/FileRepository/surfacecamauxsensor_extension8380.inf_arm64_84ddd55dc933cac9/SCFG_AUX_MSHW0492.bin \
  /mnt/c/Windows/System32/DriverStore/FileRepository/surfacecamauxsensor_extension8380.inf_arm64_84ddd55dc933cac9/CAMI_RES_MSHW0492.bin \
  --output output/phase1-camera-resources/selected-resources.json
```

1. Match a physical Fedora capture to board and kernel/DT revision; DT boot need not expose Windows ACPI nodes.
2. Trace the platform driver consumers of `TLMMGPIO`, `CLOCK`, `PMICVREGVOTE` and `DELAY`, preserving call-site addresses and flag meanings.
3. Identify the sensor-module parameter format before extracting register tables or CSI/CCI settings; the ASCII header alone is insufficient.
4. Correlate the resulting resource map with Linux providers and camera/ISP support. Camera output still requires a coherent kernel media graph and userspace pipeline.
5. ALS remains a parallel live-enumeration task: these camera descriptors do not establish its HID/IIO/DSP transport.
