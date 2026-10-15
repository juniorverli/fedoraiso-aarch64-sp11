# Phase 1: initial static findings

Collected 2026-10-15 from the locally mounted Windows DriverStore under WSL. This is package evidence, not enumeration of the running Fedora installation. No driver was executed, sensor powered, or image captured.

## REA inspection performed

REA CLI `rea-agents@6.5.0` with `/usr/bin/aarch64-linux-gnu-objdump`; five `file_headers` inspections succeeded (exit 0, complete output, unchanged before/after digest). Raw envelopes are local in ignored `output/phase1-rea-static/`. The MCP server is not connected in this session.

| Artifact | SHA-256 | REA evidence ID |
|---|---|---|
| `qccamisp8380.sys` | `64463b4d78894fdeee01ce87b51e3153662243e3fdf16f87596579b58617c21c` | `ev_f238cec95b6b66e834dba73234fd118405c013bb642ac73f2eb99faa3e266003` |
| `qcSensors.dll` | `7bb1e9571bd5838b32ede7ae22810fb377b3bc1354dc0e2a4f8ec497aaaa9fbf` | `ev_7a8da67803f96236f58333e651ae4bcd8c62c3f652dc2b0970342171b68c83b2` |
| `qccamflash8380.sys` | `6bc1d698bc3b6da16974cd6f3ea89dc1ba6a8ea102eebe1a5d41129b4eb9ba2b` | `ev_eddf368ea10f49f1947ca1f74cdc88897066c3816080d80091e40df0c36bbcc0` |
| `qccammipicsi8380.sys` | `033f5b1431ad4c76a12ac3b7f0a5be42e460a03bcff40d249511b3034786d407` | `ev_8f3b4e035ee52b5ea1b56d4d33ab69e40c453cca781eef7f077a013130e91be2` |
| `qccamplatform8380.sys` | `836714ec41f92f45af363d7bf3c9b9cfc2cccdbd19a1c57f355b471068648049` | `ev_5dda6b1727b452f05134913d1a3de48c91bb06ea7f17c6bb062bab972b306a9a` |

The raw objdump output identifies each artifact as `pei-aarch64-little`. REA subject format/architecture metadata remained unknown; the observation comes from `raw_result.stdout`. Objdump warned that it ignored `IMAGE_SCN_MEM_NOT_PAGED` section flags on several drivers. Header inspection does not establish device presence, power sequences, firmware protocol, or code behavior.

Reproduce for each local artifact:

```bash
REA_OBJDUMP_COMMAND=/usr/bin/aarch64-linux-gnu-objdump \
  npx --yes rea-agents@6.5.0 inspect-with-objdump \
  /absolute/path/to/driver.sys file_headers --format json
```

## INF observations

Paths below are relative to `C:\Windows\System32\DriverStore\FileRepository`. Line numbers refer to decoded original files. A package may support several board variants; an INF match is a candidate until matched to a present device.

| Source | SHA-256 | Observation / location |
|---|---|---|
| `qccamisp8380.inf_arm64_068a5d125dcec104/qccamisp8380.inf` | `ec3855d887b6095e2774db5805287d6b0e772124c81916ff474fa49e59248d15` | Line 43 maps `ACPI\QCOM0C25`; lines 52–53 copy `CAMERA_ICP_AAAAAA.elf` and `CAMERA_ICP.mbn`; lines 83–84 describe Spectra 695. |
| `surfacecamfrontsensor_extension8380.inf_arm64_5a4c66ce4812274e/surfacecamfrontsensor_extension8380.inf` | `383b0d61d8ca099599ebc6e7cfc1628fb0bc74034a4d66b66c35fae9f0899c27` | Line 97 maps SONY/0681 + MSHW0490; lines 65–71 select IMX681-named module/tuning and SCFG/CAMF resource files. Other entries select OV02C10 variants. |
| `surfacecamrearsensor_extension8380.inf_arm64_9e667d808f1a7021/surfacecamrearsensor_extension8380.inf` | `4bb1e0590bfcb32eb6195547b91cdc0725d6c733bf36d08324b8dab2c73dcb03` | Line 69 maps OVTI/D858 + MSHW0491; lines 46–52 select OV13858-named module/tuning and SCFG/CAMS resources. |
| `surfacecamauxsensor_extension8380.inf_arm64_84ddd55dc933cac9/surfacecamauxsensor_extension8380.inf` | `bf2f917d1859adf21b68de9b86e5f37a710b940eb049d88ab8f59bb23d7d4725` | Line 83 maps SMO/55F0 + MSHW0492; lines 59–65 select VD55G0-named module/tuning and SCFG/CAMI resources. Other entries select different board IDs. |
| `qcsensors.inf_arm64_08abad6c5f3b94d9/qcSensors.inf` | `5a4ca78ece80732d552ae47e23158e6b77f70edc6387b712f591dc230ac59c82` | Lines 40–44 list MSHW0464/0488/0544/0568 and QCOM0CE7. Line 84 registers several sensor types including color; ambient_light appears in a commented generic list on line 85. Neither proves this machine exposes ALS through this package. |

These package observations support investigating the legacy IMX681 / OV13858 / VD55G0 leads. They do **not** confirm the installed board variant or any GPIO, supply voltage, I2C address, clock rate, or CSI lane count in `dts/camera-sp11.dtsi`.

## Sensor transport leads

`qcSensors.dll` (digest above) contains these ASCII strings at file offsets, found by a separate literal byte search, not REA decompilation:

| Offset | String |
|---|---|
| `0x1ad427` | `createstaticpd:sensorspd` |
| `0x1acc0c` | `IOCTL_FASTRPC_GET_INTERFACE_VERSION` |
| `0x1ad6ee` | `IOCTL_FASTRPC_GET_MAPPING` |
| `0x1adbc0` | `FATAL: could not find sensors QMI service due to timeout` |

Inference: the package includes code paths referring to FastRPC, a sensors protection domain and QMI. No call graph was traced. This does not exclude a separate HID or ACPI ALS route; live binding and IIO enumeration decide that investigation branch.

## Resource-file header triage

The three MSHW0490/0491/0492 SCFG files and front CAMF resource file begin with bytes `41 65 6f 42` (ASCII `AeoB`), not an ACPI `DSDT`/`SSDT` table signature. Do not feed them to an AML disassembler on the assumption that the INF comment “Asl binary” establishes their format. A decoder for this container still needs to be identified.

Follow-up: [resource decoding](CAMERA_RESOURCE_FINDINGS.md) now identifies the
serialized Windows ACPI method-output layout and provides a tested structural
decoder. The observation above records the initial triage stage; electrical
semantics and live device correlation remain unresolved.

| Resource | Bytes | SHA-256 |
|---|---|---|
| `SCFG_FRONT_MSHW0490.bin` | 133 | `e6e3d828a1e4f5bc94c545848a091c20be399a4b22c938ed4a3df072dd033d99` |
| `SCFG_REAR_MSHW0491.bin` | 135 | `fa1d4b79ac3305ed822aae7fb2d1676d28eb130cb651b2b7f84d208aab64652a` |
| `SCFG_AUX_MSHW0492.bin` | 151 | `1c848ac4ddbe12948cae4affee421e3a457cac61f98dacb30043841bf0bd1bff` |
| `CAMF_RES_MSHW0490.bin` | 1843 | `379a03154511922428ea27f56de625f579f39ca483fb97398953278b6b5f2851` |

## Next analysis targets

1. Collect Fedora inventory and match its DT/ACPI IDs to these package variants. DT boot may not enumerate the same ACPI devices as Windows.
2. Use the [resource decoder and findings](CAMERA_RESOURCE_FINDINGS.md) to inspect matching SCFG and CAM*_RES files with offsets; correlate vendor tuples with their driver consumers and DT providers. Filenames and decoded values alone do not establish electrical semantics.
3. Trace the platform/sensor driver functions using a configured Ghidra/Hopper provider to recover resource use and power sequencing. Header and string evidence is insufficient for driver implementation.
4. Compare the live kernel revision, media graph and binding failures with a pinned upstream source revision. Do not infer global upstream support status from generic CAMSS module availability.

The current ISP hash differs from the shortened hash in the older strategy note. Preserve revisions independently; that older observation is not evidence for these bytes.

## Acquisition and reproduction details

Source: the Windows volume mounted at `/mnt/c` in this WSL workspace; acquisition
date 2026-10-15. The original driver installation date and correspondence between
this Windows volume and the currently booted Fedora device are **unknown** until
correlated with device evidence. Follow-up [Windows host correlation](CAMERA_RESOURCE_FINDINGS.md#windows-host-correlation) now confirms the selected camera IDs on this Windows host and the active sensor-platform INF; Fedora correlation remains pending. Presence in DriverStore does not prove a package
is active. No device serial number is retained in this report.

Observed INF `DriverVer` values (Windows date notation):

| Package | DriverVer |
|---|---|
| ISP, MIPI CSI, platform, flash | `03/06/2025,1.0.4258.7900` |
| Front, rear, auxiliary sensor extensions | `04/25/2025,1.0.4258.7908` |
| Qualcomm sensor collection | `08/27/2024,6982.1.0.0` |

Tools observed: Python 3.12.3, REA 6.5.0, GNU objdump (GNU Binutils for Ubuntu)
2.42. REA's envelope did not populate its provider version field; the version
above comes from a separate `aarch64-linux-gnu-objdump --version` probe.

The following standard-library command reproduces INF decoding/line numbers,
literal byte offsets and the selected resource headers/hashes. Run from the
repository root under WSL; output is saved in ignored `output/`. Full INF text
remains local. Set `driverstore` to the actual acquisition source when different.

```bash
mkdir -p output/phase1-rea-static
/usr/bin/python3 - <<'PY' > output/phase1-rea-static/reproduction.txt
from pathlib import Path
import hashlib
driverstore = Path('/mnt/c/Windows/System32/DriverStore/FileRepository')
patterns = ('qccamisp8380*/qccamisp8380.inf',
            'qccammipicsi8380*/qccammipicsi8380.inf',
            'qccamplatform8380*/qccamplatform8380.inf',
            'qccamflash8380*/qccamflash8380.inf',
            'surfacecam*sensor*/*.inf', 'qcsensors*/qcSensors.inf')
for pattern in patterns:
    for path in sorted(driverstore.glob(pattern)):
        data = path.read_bytes()
        text = (data.decode('utf-16') if data.startswith((b'\xff\xfe', b'\xfe\xff'))
                else data.decode('utf-8-sig'))
        print(path.relative_to(driverstore), hashlib.sha256(data).hexdigest())
        for number, line in enumerate(text.splitlines(), 1):
            print(f'{number}: {line}')
for path in driverstore.glob('qcsensors*/qcSensors.dll'):
    data = path.read_bytes()
    for text in ('createstaticpd:sensorspd', 'IOCTL_FASTRPC_GET_INTERFACE_VERSION',
                 'IOCTL_FASTRPC_GET_MAPPING',
                 'FATAL: could not find sensors QMI service due to timeout'):
        offset = data.find(text.encode('ascii'))
        print(path.name, text, hex(offset) if offset >= 0 else 'not found')
for pattern in ('surfacecamfrontsensor_extension8380*/SCFG_FRONT_MSHW0490.bin',
                'surfacecamrearsensor_extension8380*/SCFG_REAR_MSHW0491.bin',
                'surfacecamauxsensor_extension8380*/SCFG_AUX_MSHW0492.bin',
                'surfacecamfrontsensor_extension8380*/CAMF_RES_MSHW0490.bin'):
    for path in driverstore.glob(pattern):
        data = path.read_bytes()
        print(path.name, len(data), hashlib.sha256(data).hexdigest(), data[:36].hex())
PY
```

## Method references

- [REA CLI and evidence](https://github.com/morluto/rea/blob/main/docs/cli.md)
- [REA GNU objdump integration and limits](https://github.com/morluto/rea/blob/main/docs/reverse-engineering-tools.md)

References checked 2026-10-15. Raw envelopes and source-index hashes are retained locally; only this reviewed metadata summary is intended for Git.
