# Phase 1: cameras, IR and ambient light

Status: repository foundation and read-only collection tooling prepared. Fedora
runs on the owner's Surface; this development workspace is WSL. Hardware capture
and binding validation remain Fedora work. The static manifest
`builder/surface-hardware.json` describes shipped modules and firmware, not proof
of physical components. Legacy Portuguese notes are leads: their raw REA records
are unavailable here, so their sensor names, IDs, register sequences, clocks,
voltages and wiring remain unverified. IMX681, OV13858 and VD55G0 are candidate
labels, not established identities. Do not enable `dts/camera-sp11.dtsi`.

REA MCP is not connected here. Local CLI investigation, when available, is
recorded separately in [initial static findings](INITIAL_STATIC_FINDINGS.md);
CLI observations do not validate the legacy notes or physical wiring. The
[official REA documentation](https://github.com/morluto/rea) describes its CLI and
agent workflows (accessed 2026-10-15). Record the installed tool version and exact
commands alongside every new analysis. Collector metadata includes the collector
script SHA256; external tool versions are explicitly unknown/not collected. To
record them manually on Fedora, save the installed package versions (for example,
`rpm -q pciutils usbutils kmod v4l-utils`) and the Python version
(`python3 --version`) in the private capture notes and sanitized ledger. The
collector saves exact argv but does not run extra version probes. Never substitute invented evidence IDs
for retained source artifacts.

## Collect on Fedora

Clone or copy this checkout onto the Surface, open a terminal at its repository
root, and run the commands below. Python 3 is required; optional Fedora tools
improve inventory. Installation is a manual host preparation step:

```bash
sudo dnf install python3 pciutils usbutils kmod v4l-utils
python3 scripts/collect-camera-sensor-evidence.py
```

Fedora 44's [v4l-utils package file list](https://packages.fedoraproject.org/pkgs/v4l-utils/v4l-utils/fedora-44.html)
includes `media-ctl` and `v4l2-ctl` (checked 2026-10-15).

The default creates a unique private directory in
`research/camera-sensors/raw/`. For an explicit destination:

```bash
python3 scripts/collect-camera-sensor-evidence.py --output research/camera-sensors/raw/fedora-first-boot
```

If transferring only the collector, copy `scripts/collect-camera-sensor-evidence.py`
to the Fedora host and supply an explicit new destination (the default layout
otherwise assumes the script lives under the repository's `scripts/` directory):

```bash
python3 /path/to/collect-camera-sensor-evidence.py --output "$HOME/surface-private-evidence/first-capture"
```

This external directory is outside repository ignore protection: keep it private.

A reused destination is refused. Start without root; restricted `dmesg` or
unavailable binaries are recorded as gaps. If kernel logs are needed, the owner
can run the same read-only collector with `sudo python3` into a different private
destination. Do not run commands that scan I2C addresses, start camera streams,
change controls, power/GPIO states, firmware, kernel, or PAM during Phase 1.
Only media topology queries are performed. IIO collection lists channel names
without reading live measurements. Selected sysfs attributes omit serial-number
fields, but logs can contain personal identifiers. Captures are private and are
not automatically anonymized; prepare a reviewed report before sharing.

On WSL the default invocation refuses collection. A tooling smoke check is:

```bash
python3 scripts/collect-camera-sensor-evidence.py --allow-wsl
```

Its metadata and summary explicitly label WSL. It cannot establish Surface
hardware presence or absence. Every capture records UTC, OS, running kernel,
architecture, readable DT/DMI identity and firmware revision. Add the actual
kernel source commit/package release, loaded DTB hash and firmware artifact
versions/hashes to the ledger: a BIOS version or remoteproc firmware filename
alone is insufficient provenance. Use `manifest.json` to verify the SHA256 of
each payload; the manifest excludes itself.

## Analysis brief and target matrix

Retain original files locally in `private/`, compute full SHA256 before analysis,
and record origin (owner device, DriverStore directory, INF package version,
firmware version and acquisition date). Match INF hardware IDs to reproducible
Fedora bindings or independently preserved ACPI/DT sources before assigning a
sensor identity. Static strings alone establish presence of a string, not a
runtime route. Do not execute Windows binaries. Capture exact REA tool/version,
commands, offsets, decompiler uncertainty and retained output.

| Candidate target from legacy notes | Question | Required independent evidence |
| --- | --- | --- |
| Camera INF packages and sensor binaries | Which sensor and board variant? | Full hashes, INF match lines, hardware binding correlation |
| `qccammipicsi8380.sys` | CSI/CCI resources and controller relationship? | Resource parsing with offsets and callers; compare live graph |
| `qccamplatform8380.sys` | Clock, regulator, reset and sequencing? | Board-specific tables and call paths, units and provenance |
| `qccamisp8380.sys`, candidate `CAMERA_ICP.mbn` | ISP interface and firmware dependency? | Imports/messages/resource evidence, full hashes, no assumed protocol |
| `qccamflash8380.sys` | Flash vs privacy indicator responsibilities? | Separate resource ownership evidence; no LED writes |
| `qcSensors.dll`, sensor INFs and firmware service manifests | ALS via HID, IIO or DSP? | Matching bindings, channel names, remoteproc/service evidence |

Use [the evidence template](../../research/camera-sensors/reports/evidence-template.md)
for every conclusion:

| Full source SHA256 | Source / revision | Offset or line | Observation | Inference | Confidence / contradiction / next check |
| --- | --- | --- | --- | --- | --- |
| pending | pending | pending | directly observed only | explicitly provisional | pending |

## Driver roadmap and acceptance gates

1. **Enumerate:** collect Fedora inventory and reconcile DT/ACPI, modules, bus
   devices and media nodes. Gate: retained hashes, actual kernel/firmware revision,
   device identity and explicit inaccessible/missing-command gaps. An absent sysfs
   path does not establish absent physical hardware.
2. **Identify bus and binding:** correlate identifiers and driver symlinks with
   live source and INF evidence. Gate: confirmed sensor identity and transport;
   keep USB/UVC, I2C/CCI, HID and DSP alternatives open until evidence resolves them.
3. **Resolve platform resources:** clocks, regulators, power domains, reset,
   IOMMU, CCI and CSI lane mapping. Gate every wiring or power change on retained
   board-specific evidence and independent corroboration. Draft patches only
   after this gate; guessed DTS values are not test inputs.
4. **Sensor/ISP/media graph:** compare the running kernel implementation and
   bindings with established hardware, then develop narrowly scoped drivers and
   graph links. Gate: reviewed resource evidence and a coherent media graph.
   `/dev/video*` can be video codec nodes (for example Iris); its existence alone
   does not prove a camera. Phase 1 performs no streaming validation.
5. **libcamera:** after kernel graph and controlled capture validation,
   assess pipeline support, formats and sensor-specific tuning. Gate: repeatable
   camera output and correct provenance, rather than a speculative config file.
6. **IR exposure and Howdy:** establish IR hardware, independent usable device,
   illumination ownership and privacy behavior first. Gate: separately reviewed
   biometric capture and authentication plan. Do not install or alter PAM here.
   [Howdy's official project](https://github.com/boltgolt/howdy) describes IR based
   authentication; it does not supply missing kernel camera support (accessed
   2026-10-15).

Run ALS investigation alongside camera work: enumerate HID sensor bindings and
IIO light-channel availability, then inspect DSP/remoteproc and service evidence
if the direct route is absent. Gate: a demonstrated ALS transport and driver
binding before proposing sensor-proxy integration; package presence does not
prove sensor availability.

The [kernel CAMSS documentation](https://docs.kernel.org/admin-guide/media/qcom_camss.html)
explains V4L2 subdevices, CSIPHY/CSID and media controller graphs (accessed
2026-10-15). Its historical supported-platform list is not a complete current
Snapdragon X support survey. Assess the exact running kernel source and pending
patches before making upstream support claims.

## BMAD investigation work items

These are local investigation items, not claims of published or completed formal
tickets. The authored implementation plan tracks this foundation separately.

| Item | Deliverable | Acceptance gate |
| --- | --- | --- |
| Fedora baseline | Private capture and sanitized inventory report | Device/kernel/firmware provenance, hashes and explicit gaps |
| Candidate identity | INF/binary/live binding evidence ledger | Independent corroboration; contradictions retained |
| Camera resource map | Clock/regulator/IOMMU/CCI/CSI analysis | No unverified wiring promoted into active DTS |
| ALS route | HID vs IIO vs DSP decision with sources | Proven binding and channel availability |
| Driver delta | Kernel and userspace gap report | Exact source revision and patch references |
| Next implementation slice | Reviewable scoped plan | Resource evidence and a hardware validation plan |

Deferred backlog: audio validation and polish, splash, theming, and subsequent
camera capture/IR authentication work after their prerequisite gates.
