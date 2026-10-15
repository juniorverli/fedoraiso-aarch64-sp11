---
title: 'Repository foundation for camera and sensor investigation'
type: feature
ticket: ''
created: '2026-10-15'
status: built
route: full
route_source: auto
review: thorough
review_source: auto
lenses_ran: [blind-hunter, edge-case-hunter, verification-gap, intent-alignment]
review_loop_iteration: 0
baseline_revision: 2d6e592a45cb32e9aba0096d300552b1c9e0db30
context: []
---

<frozen-after-approval reason="user authorized repository setup and Phase 1 kickoff">

## Intent

Create a reproducible investigation workspace for Surface Pro 11 cameras, IR and ambient light sensing. Fedora now runs on the user's device; this development workspace is WSL, so actual Linux hardware evidence must be collected on Fedora. Deliver the repository scaffolding, collection tooling and initial driver roadmap needed to begin REA analysis with BMAD tracking.

## Boundaries & Constraints

Preserve existing Git history, branch and build paths. Existing untracked BMAD files and Portuguese research documents belong to the user; read them as leads and leave them unstaged. Local proprietary binaries and raw hardware logs remain ignored. Never stage the whole repository, push, alter firmware/kernel/PAM, enable speculative camera DTS nodes, scan I2C addresses, capture images or change power/GPIO states. Keep audio, splash and theming as subsequent backlog items. Hardware IDs, clocks, voltages, lane maps and sensor names in legacy notes require independently reproducible evidence. No remote Git URL has been supplied; document placeholder commands, never invent one.

## I/O & Edge-Case Matrix

| Scenario | Input | Behavior |
|---|---|---|
| Existing repository | Initialization run repeatedly | Preserve HEAD, branch, index and remotes; create missing directories only |
| Fresh repository | Explicit target outside another repository | Initialize main and scaffold; never commit or push automatically |
| Nested target | Target inside a different repository | Refuse accidental nested project creation |
| WSL collection | Default invocation on WSL | Refuse as target evidence; explicit allow flag enables tooling smoke check with clear WSL label |
| Missing tools or permission | Optional binaries absent or kernel logs restricted | Save status per operation; complete partial inventory without fabricating absence |
| Output reuse | Existing destination | Refuse overwrite and leave prior evidence intact |

</frozen-after-approval>

## Code Map

- `.gitignore`: currently ignores output, RPMs and some extracted firmware. Extend without undoing existing curated blob exceptions.
- `README.md`: contains legacy confident camera names; add a current-investigation entry and qualify those camera assertions.
- `dts/camera-sp11.dtsi`: inactive speculative overlay with unproven GPIO/voltage/lane details. Add a clear research warning, keep inactive.
- `docs/CAMERA_REVERSE_ENGINEERING_STRATEGY.md`, `docs/REVERSE_ENGINEERING_REPORT.md`: untracked legacy notes; their missing raw REA references make conclusions provisional. Do not edit or commit these files.
- `builder/surface-hardware.json`: current shipped static module/firmware manifest, useful for comparing with live kernel, not physical proof.
- `tests/`: existing unittest style; use standard Python for new meaningful tool tests.
- `_bmad/config.toml`: local installation configuration, already present untracked. New plan documents BMAD build; do not vendor installed runtime.

## Tasks & Acceptance

**Implementation agent ownership:** all implementation below. Parent performs independent verification, review and final local commit afterwards. Do not spawn more agents or commit yourself.

- [x] `scripts/init-repository.sh`: idempotent bootstrap accepting optional target path; scaffolds docs/rea, research/camera-sensors/{reports,raw,private}, scripts, configs, tests and patches. Detect existing repository root vs nested target; preserve existing state and configure no remote. In a fresh target install project ignore template from this checkout and short layout README as needed. Quote paths, handle spaces and fail clearly.
- [x] `.gitignore`: add ISO/build caches, Python/venv, raw/private evidence, REA local sessions and credentials/editor temporary files. Avoid broad patterns that hide legitimate driver source, tests or reports. Ignore `_bmad/render/`, not authored plans.
- [x] `scripts/collect-camera-sensor-evidence.py`: standard-library-only command accepting `--output` and explicit `--allow-wsl`. Default output under repository research raw directory, fresh timestamp/unique destination. Use bounded commands without shell, capture return status/timeouts/missing/permission failures. Save metadata (UTC, OS release, kernel, architecture, WSL, DT model/compatible or DMI product), PCI/USB trees, loaded modules, filtered kernel logs, ACPI/platform/I2C/SPI/HID bindings/modaliases, media/V4L2 topology, IIO names/channel availability and remoteproc status. Read sysfs using bounded selected attributes, avoid serial numbers and biometric captures. Include manifest hashes and short summary distinguishing absent nodes from unsupported/inaccessible commands. Inventory never starts streaming or changes settings. Raw logs are private: do not claim automatic anonymization or ask user to share them publicly.
- [x] `docs/REPOSITORY_SETUP.md`: accurate layout, init and explicit selective add/commit examples, preservation of existing master, GitHub remote placeholder and push HEAD commands. Explain ignore rules do not scrub existing history.
- [x] `docs/rea/PHASE_1_CAMERA_SENSORS.md`: status, executable Fedora collection commands/dependencies, evidence ledger template (hash/source/offset or line/observation/inference/confidence), REA target matrix and analysis brief. Document REA isn't connected here and previously named sensors remain unverified. Driver roadmap: enumerate -> identify bus and binding -> platform clocks/regulators/IOMMU/CCI/CSI -> sensor/ISP/media graph -> libcamera -> IR exposure/Howdy; parallel ALS HID vs IIO vs DSP route. Gate every wiring change on evidence, distinguish video codec from camera nodes. Cite primary kernel CAMSS, Howdy and official morluto/rea docs with URLs and access date. Include BMAD investigation work items, acceptance gates and deferred polish backlog, no fabricated formal ticket state.
- [x] `research/camera-sensors/README.md`, `research/camera-sensors/reports/evidence-template.md`: provenance conventions and sanitized handoff template, record actual firmware/kernel revision per capture.
- [x] `README.md`, `dts/camera-sp11.dtsi`: concise links and qualify unverified camera claims without changing active build.
- [x] `tests/test_research_tools.py`: cover every matrix row using temporary repos and mocked commands/filesystem for collector. Test timeout/permission/missing separately, manifest hashes, and refusal to overwrite. No physical hardware tests claimed.

**Acceptance:** Given Fedora on the Surface, when collection completes, then its files identify the running kernel and readable hardware graph with explicit gaps. Given only WSL, when verifying tools here, then no result is represented as physical Surface evidence. Given a fresh or existing checkout, when setup runs twice, then the user can version reviewed artifacts without losing history or publishing raw captures.

## Implementation Notes

- Implemented idempotent bootstrap, private read-only collector, repository setup,
  Phase 1 roadmap and provenance templates. Updated README camera assertions and
  warned that the speculative camera DTS must remain inactive.
- Parent performed actual REA 6.5.0 CLI static header inspection and INF/string
  analysis, recorded in `docs/rea/INITIAL_STATIC_FINDINGS.md`; raw evidence stays
  ignored under `output/phase1-rea-static/`. No connected REA MCP or physical
  hardware validation is claimed.
- Added 12 hardware independent tests covering the scenario matrix, output
  integrity, command gaps and avoidance of IIO sample reads. Bootstrap and WSL
  smoke runs preserve existing repository state and label WSL explicitly.

## Plan Change Log

## Review Triage Log

Review pass 1: 10 medium, 2 low, 4 false; observations below include each lens finding before grouping. No high findings. Real medium findings received direct patches; no plan re-derivation required.

| Lens / finding | Verdict | Route and evidence |
|---|---|---|
| Blind: existing ignore gaps | medium | patch: existing arbitrary repository can omit exclusions; bootstrap now verifies protection and fails clearly, preserving owner rules. |
| Blind: spool and line bounds | low | rejected: output byte cap is applied after finite inventory commands with a 12s timeout. Theoretical excessive provider output remains possible; a streaming process manager is disproportionate to these fixed commands. |
| Blind: blocking sysfs reads | low | rejected: selected identity/name/state attributes have no per-read deadline; no stalled read observed. Isolating every sysfs read adds process management for an uncommon case; byte/node limits retained. |
| Blind: inaccessible links hidden | medium | patch: errors previously discarded; record link statuses and summarize inaccessible bindings. |
| Blind: summary hides gaps | medium | patch: expose output/attribute/channel truncation and identity failures. |
| Blind: collector/tool provenance | medium | patch: add collector digest, explicit unknown external versions and manual version recording instructions. |
| Blind: static reproduction missing | medium | patch: exact Python decoder/line/offset/header reproduction command added and executed successfully. |
| Blind: package/acquisition provenance | medium | patch: record observed DriverVer and explicitly unknown install date/device correlation. |
| Edges: existing ignore gaps | medium | patch: same root cause as blind ignore finding, verified missing-rule state. |
| Edges: link failures hidden | medium | patch: same root cause as blind binding finding, permission/error states retained. |
| Verification: actual WSL detector untested | medium | patch: input-controlled detector cases added; original mock bypassed actual detector. |
| Verification: bus identity/bindings untested | medium | patch: populated bus and symlink fixture assertions added; original tests lacked these observations. |
| Intent: physical surface vs fixtures | false | no defect: intent explicitly calls for preparation on WSL; Fedora capture remains pending in docs and final delivery. |
| Intent: static findings outside tests | false | no defect: raw envelopes were actually produced and inspected; added executable reproduction for non-REA findings. Unit tests do not establish hardware facts. |
| Intent: planning vs formal ticket hierarchy | false | no defect: BMAD build plan and work-item table track kickoff; no formal ticket hierarchy was requested or claimed. |
| Intent: skeletal fresh scaffold | false | no defect: separate-target bootstrap creates layout, as documented; full checkout contains tooling. Clarified clone/copy distinction. |

## Verification

Implementation checks completed: shell syntax; all 12 research-tool unittest
cases; actual WSL refusal (exit 2); explicitly allowed smoke capture in ignored
`research/camera-sensors/raw/implementation-wsl-smoke`; inspected gap summary and
manifest; `git diff --check`; confirmed raw/private/render paths ignored and
reports, collector source and Phase 1 plan visible. Fedora capture remains pending.
Parent performs independent verification, review and final selective local commit.

Planned/reproducible checks:

- `bash -n scripts/init-repository.sh`
- `/usr/bin/python3 -m unittest discover -s tests -p test_research_tools.py -v`
- Collector WSL refusal and explicit smoke run into ignored raw directory; inspect manifest and gap summary.
- `git diff --check`; verify raw/private dummy paths ignored and report/source paths visible.

Final verification: 17 research-tool tests pass after review fixes; bash syntax and diff checks pass. Parent repeated actual WSL smoke collection, verified every payload manifest digest and collector digest, and confirmed public/private ignore behavior. Reproduction snippet for static findings executed successfully. Four review lenses completed; no material findings remain open. Fedora physical capture remains the next investigation activity.
