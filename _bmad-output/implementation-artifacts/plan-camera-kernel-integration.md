---
title: 'Enable Surface front and rear cameras with Windows REA and CAMSS'
type: feature
created: '2026-10-15'
status: in-progress
route: full
route_source: auto
review: thorough
review_source: auto
lenses_ran: [blind, edge-case, verification-gap, intent]
review_loop_iteration: 0
baseline_revision: 123d2dc9c4d517391c2ee8fe0dbb207ccdacae94
context: []
---

<frozen-after-approval reason="user explicitly prioritizes front/rear camera functionality and all necessary Windows RAW reverse engineering">

## Intent

Deliver working front IMX681 and rear OV13858 camera pipelines on the user's Surface X1P/LCD Fedora installation, using REA on the actual Windows packages and BMAD implementation/review. Do not make arbitrary line-count limits or assume firmware reconstruction is mandatory. Follow evidence from physical resources through sensor setup, CSI/CAMSS, RAW capture and libcamera applications. Keep the full migration goal intact; prioritize cameras per latest instruction.

## Boundaries & Constraints

Preserve working ISO, installed boot files, original Windows binaries, private calibration and owner notes. Analyze copies/read-only originals. Record source hashes, offsets and uncertainties; string names alone do not prove behavior. Preserve source licenses. Never infer unknown regulator voltages/GPIO polarity from guesses. Physical capture remains the completion criterion, not successful compilation or device nodes. No webcam image or biometric capture without explicit test scope; requested front/rear camera tests are authorized. Raw frames stay private. IR illumination and PAM remain separate dependent work. No remote push.

</frozen-after-approval>

## Code Map

- `output/camera-rea-full/windows-camera-inventory.json`: 97 selected driver/extension files, 78079773 bytes. Front/rear module files use QTI Chromatix Header, Parameter Parser V3.4.0; section table at 0xa8, records 12 bytes; symbol records 56 bytes, format <I32s5I. Data offsets appear relative to section1. Validate assumptions exhaustively before decoding semantics.
- Native Windows front module SHA f7dd81be64153fd3f0da8e6288ee1b9906b7bf51b773a98496934d76dc96a45c; rear f8f60e79b77bd3d5896cb04167ee428455e1a241f1ff9e50abee6b4dacfe6b14. Module symbols include initSettings, resolutionData, regSetting, registerData, delayUs, powerSetting. Dump exact bounded data and references with original offsets; do not fabricate optional/default semantics.
- Existing `scripts/decode-camera-resources.py` handles ACPI AeoB format, a different container. Reuse private/exclusive bounded I/O practices, not its incompatible parser. Existing findings under docs/rea and private output/phase1-*.
- `output/kernel-integration/linux-camera-only-548e7bcd`: fresh camera-only source clone being prepared; restore 21 unfinished audio files from saved pristine camera copies. Preserve original audio worktree separately. Camera patch pin and exact source in source-preparation.json. No DT modifications yet because attempted parent edits failed before writes.
- Camera candidate source revision 15e590c3c3298dd75a0b79256efa815c15dc0897 (turbineBMW/surface-pro-11-linux); patch SHA 16cdb32c732dde20f088c27bd1b83b269e631999c76edf1045126ff220ed3010, canonical base 548e7bcd0c5460ddcbca9600cea603ebeebf4da7. Candidate adds IMX681, OV13858 mode, VD55G0 and X1E C-PHY support. Provenance report separates withdrawn history; preserve that boundary.
- `dts/x1p64100-microsoft-denali.dts` current LCD config; new camera common DTS already edp-panel and PMIC GPIO4. Retain HPD pinctrl only if applicable. Camera PM8010 parent supply mapping still marked unverified. Verify original ACPI resources and Windows parser behavior before changes.
- Native Windows API download works; Linux direct HTTPS currently TLS-timeouts. Official Ghidra12.1.4 release metadata output/ghidra-release-windows.json, archive digest ddac49f903da9d5bac833e5cc79395098b9c33cfd3279be5f31bd00387d2d4db. Download running; configure REA via per-command env without editing global client registrations. Ghidra needs matching AArch64 JDK. ObjDump REA already available.
- Container surface-kernel-port-check restarted after terminal exit255, Fedora44 gcc16.2.1/make4.4.1/bison/flex/bc/OpenSSL/libelf/dwarves installed. Mounted repository /workspace. Use independent build-camera-only O= directory, bounded jobs and saved build logs.

## Tasks & Acceptance

- [x] Windows package inventory and bounded Chromatix decoder `scripts/decode-camera-module.py`, meaningful synthetic malformed-container/limits/no-overwrite tests in `tests/test_camera_module.py`; analyze actual modules privately with exact byte provenance. Decode register/power semantics only where evidence establishes layout.
- [ ] Configure actual REA decompiler and inspect front/rear sensor drivers, platform/MIPI/ISP references as necessary; correlate field formats and power sequence with ACPI and candidate sources. Save evidence IDs/hashes and a public derived-fact report, never raw proprietary tables in Git.
- [x] Build camera-only kernel Image/modules/LCD DTB from fixed source/config, resolve build failures, stage complete candidate under ignored output with hashes/toolchain/config manifest. Preserve recoverable existing boot choice; deploy only after physical Fedora path is known.
- [ ] Verify Fedora libcamera version and prepare compatible front/rear userspace support and bounded RAW/application capture procedure; execute actual hardware capture when connection/capture evidence arrives. Record final per-camera frames, hashes, formats, cadence, privacy indicator, post-stream errors and lifecycle regressions.
- [x] `docs/rea/CAMERA_INTEGRATION_STATUS.md`: source decisions, actual REA/compile evidence and remaining physical requirements. Update overall status honestly, never mark hardware complete from static results.

Acceptance: Given original module files, when decoding, then every selected symbol payload remains within its section and retains source offsets/hashes. Given corrupt or huge input or existing destination, when invoked, then refuse without overwrite. Given exact kernel candidate, when building, then Image, camera modules and LCD DTB compile and manifests identify all pieces. Given Fedora physical hardware, when capturing front/rear, then changing correctly sized frames and working applications are demonstrated without driver errors; until then cameras remain unverified.

## Implementation Notes

No implementation subagent capacity: attempted coder returned explicit usage-limit error. Root implements directly as workflow permits when subagents unavailable. All current workflow prerequisites investigated; user has already authorized continuation and prioritization. Untracked owner notes preserved.

## Plan Change Log

## Review Triage Log

## Verification

Run targeted decoder tests, actual module bounds/provenance checks, REA evidence inspection, camera-only kernel build, module vermagic and DT inspection. Dynamic capture must run on Fedora physical system; WSL is not acceptable evidence.

Current-state correction: HEAD is now 14b9353 (full hash recorded in subsequent manifest); commits d8c46f9/dfac78d/4d3b658/14b9353 already integrated experimental camera/audio kernel, ISO and GRUB improvements after prior context. Those are existing user work, not this implementation. Original audio plan restored byte-for-byte to HEAD after detecting stale context. Keep those files unchanged. Do not claim their docs prove physical camera behavior. Fresh camera-source-clean tree avoids unfinished-source/build products and is compiling as independent baseline; existing experimental ISO remains untouched. Review diff must include only this camera slice's owned additions.

Implementation checkpoint (objective remains in progress):
- Full package inventory expanded from 97 filtered files to all 142 files in 20 camera packages, all hashed.
- Decoder implemented; all eight sensor modules pass CRC, limits and independent source-byte payload checks. Five targeted tests passed; reports regenerated with final decoder hash.
- Persistent REA/Ghidra session recovered all identified local non-thunk bodies from front133, rear166, CSI139, ISP494 and platform219: 1151 functions/88627 pseudocode lines. This is recovery coverage, not complete analyst understanding. Windows originals preserved.
- Actual front tables match ordered364+68 register/value pairs. Rear combined207 rows differ in 0x3813, retained for phase/crop investigation. C-PHY settle table bytes mapped by REA and independently checked; candidate2406Msym/s selects0x22, matching Linux observed table.
- Full camera-only Image/modules/LCD DTB build exit0; all3767 modules share exact vermagic. Ten stack-frame warnings in base code logged, none in new sensor/CAMSS code. Endpoint592800000 DT correction replayed fuzz0, compiled DT verified resets/clocks/lanes/backlight.
- libcamera0.7.0 source from maintainer fork tag b7854fd07d42168f099b5ce30d1702e0e0875bf5; GitHub reports tag GPG valid (not independently verified locally). Three IMX681 patches apply fuzz0 and compile. GStreamer/udev added and libcamerasrc plugin load verified. Optimized O2/GLES build being finalized before repackaging; no hardware proof from container.
- Physical Fedora uname/cam list or access requested asynchronously. Userspace integration and autofocus/per-unit calibration remain open. Rear module identifies DW9800, absent from candidate DT. Full intent and migration goal remain active; do not mark built or achieved from these artifacts.


### Review checkpoint 2026-10-15

All four independent reviewers returned before triage. Implementation subagent remained unavailable after its explicit usage-limit failure; root applied local corrections. No review finding changes the frozen intent.

| Finding | Evidence / severity | Category and disposition |
|---|---|---|
| Blind1 optional `--file` argument | cam getopt optional argument needs `=`; high, wrong command | patch: fixed RAW/PPM syntax; verified against cam help/source |
| Blind2 repeated reference expansion; Edge1 duplicate | serialized payload bound did not bound decoded repeated words; high | patch: aggregate expansion budget before unpack, bounded local errors and shared-reference regression |
| Blind3 missing PPM validation; Edge2 duplicate | FileSink does not propagate PPM errors; medium | patch: exactly three frames plus P6 header/dimensions/exact payload byte checks before hashes |
| Blind4 interpretation loses raw evidence | unconfirmed 40-byte schema errors rejected validated container; medium | patch: per-row interpretation-error, retain validated symbols; tests for invalid refs/counts/markers |
| Blind5 checksum artifact absent during review | delivery finalization had not run; low | patch: final bundles produced, full archive/manifest comparison and SHA256SUMS created |
| Blind6 missing candidate runtime prerequisites | system library fallback possible if candidate incomplete; medium | patch: validate both libraries, simple IPA and executable proxy before exec |
| Blind7 reproducibility gap | source/options/packaging recipe missing from tracked files; medium | patch: pinned recipe added, actual options/hashes/logs recorded |
| Blind8 optional/shared fixtures missing | only populated valid row covered; medium | patch: absent optional payloads, shared data and bounded repeated expansion fixture |
| Verification1 unsupported-size fallback untested | no test would detect rejecting validated unknown schemas; medium | patch: register/power fallback test checks retained payload bytes/status |
| Verification2 launcher process boundary untested | inherited wrong paths/extracted prefix not exercised; medium | patch: executable relocated-prefix test checks exports, arguments, missing proxy and WSL guard. Actual candidate ldd/plugin/helper checks pass. Tuning discovery during streaming remains an explicit physical requirement, not simulated hardware proof |
| Intent: physical/electrical/focus acceptance missing | no boot/capture evidence and unresolved electrical resource consumer/DW9800 integration | open requirements of the original goal; no intent violation and no completion claimed |

Verification after patches:
- 24 camera-focused unittests pass (7 new module, 1 launcher, 16 existing ACPI resource tests).
- Eight original modules re-decoded into private reviewed-modules-v2 with final decoder hash, source inventory hash identity and every symbol compared against original byte spans; zero interpretation errors.
- Optimized/stripped libcamera final cam, IPA and GStreamer plugin ldd have no missing dependencies; cam help and candidate plugin load exit0. Real C++ IMX681 factory/black-level/gain round trips pass.
- Full camera-only kernel build and endpoint DT rebuild exit0; 3767 consistent modules. Packaging verified every regular file hash and link against manifests, rejecting escaping paths/devices.
- Physical acceptance remains outstanding: kernel/DT identity, binding/media graph, changing RAW frames, processed output, cadence, privacy indicator, post-stream errors, lifecycle and focus/calibration. Plan intentionally stays in-progress because its acceptance has not been met.

Change log clarification: authoritative fresh kernel source is output/kernel-integration/camera-source-clean; the earlier partial copy mentioned in the initial Code Map is abandoned. Final optimized libcamera build, strip, GLES and repackaging completed. Windows originals, integrated ISO, user audio work and main boot choice were preserved.

Delivery checkpoint: both bundles plus SHA256SUMS and three guides copied to a new exclusive Windows Downloads/surface-camera-20261015-x1p1 folder; copied bytes re-hashed and identical. Local only, no push/publication. Kernel tar SHA256 0cb2096694d896bb7df9651a4efc58c1547018cafc949e29693f7de1dfbf8ae3; userspace tar SHA256 1e18ee8a9b1cdf778842e5e1267ff844ddb9af60675248d1dbc9d1f2cd822ab2.

Whitespace verification: staged diff check passes outside patch files. The outer diff reports intentional context-space-before-tab and git-mail signature/context blank whitespace inside the preserved patch files; these are not modified to avoid corrupting patches or changing source hashes. Kernel endpoint and all three imported patches were replayed with fuzz0. This exception is recorded rather than claiming an unqualified diff-check pass.
