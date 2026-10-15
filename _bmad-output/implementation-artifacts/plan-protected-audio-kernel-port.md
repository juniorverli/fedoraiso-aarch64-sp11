---
title: 'Port protected SP11 audio onto camera kernel candidate'
type: feature
ticket: ''
created: '2026-10-15'
status: completed
route: full
route_source: auto
review: thorough
review_source: auto
lenses_ran: []
review_loop_iteration: 0
baseline_revision: 123d2dc9c4d517391c2ee8fe0dbb207ccdacae94
context: []
---

<frozen-after-approval reason="user authorized continuing every migration phase including actual speaker protection">

## Intent

Prepare a coherent experimental kernel candidate combining the camera drivers with real AudioReach/VI speaker protection, preserving the Surface X1P LCD panel. The previous step found source candidates but had not ported them. Deliver reviewable source patches and compile the changed subsystems; this milestone advances the full migration and cannot establish physical safety, camera capture, ALS, Howdy, boot appearance or desktop completion.

## Boundaries & Constraints

Preserve the working ISO/kernel/DTB, owner untracked files, Git history and gain limits. Modify only isolated candidate sources and new explicitly owned integration artifacts. Never install a candidate, replace active modules/topology, boost volume or copy another unit's calibration. Preserve original copyright/SPDX and record exact source pins/hashes. Treat external scripts as source evidence; do not execute installers or reproduction scripts. Newer generic pull/push and memory APIs must remain coherent; selecting every old conflict side is unacceptable. Unresolved hardware-specific parameters must stay explicitly experimental. Failures initializing protected path must propagate rather than fall back to unprotected output. Do not claim real speaker protection enabled merely because compilation succeeds.

</frozen-after-approval>

## Code Map

- Exact source `output/kernel-integration/linux-548e7bcd0c5460ddcbca9600cea603ebeebf4da7`: canonical torvalds base with camera patch applied fuzz=0. This is the only isolated mutable build tree. Camera source includes generic pull/push support newer than protected audio code.
- `output/kernel-integration/source-preparation.json`: archive hash and applied camera patch pin. Camera patch `output/upstream-research/surface-pro-11-linux/kernel/port-7.3/sp11-port-7.3.patch`, SHA256 16cdb32c732dde20f088c27bd1b83b269e631999c76edf1045126ff220ed3010. Base source archive SHA256 9d34c13e30b54bb139779fb3fac0c64f1634ffd6340b6258c8dfde90dbbfc2ce.
- `output/kernel-integration/protected-audio-7.1.5-final`: historical protected overlay plus six verified patches (0069,0070,0071,WSA0072,VA0072,0078). Source pin geocausa/SP11X1e-audio 3232e1dacdeb580a10a9cb8d4756a4518a7bd83e. `patch-results.json` confirms all fuzz=0. Pristine comparison `output/upstream-research/linux-7.1.5-audio-base`.
- `output/kernel-integration/audio-three-way-review`: 22 selected files, 15 clean merges and seven conflicted. Conflict blocks need semantic resolution. Check clean merges too: duplicate watermark event values, memory token bit collisions, flags and allocation ownership may silently conflict. qcom-gpi QSPI=9 from camera must remain; it is not an audio change. The seven conflicted paths are wsa884x.c, audioreach.h, q6apm-dai.c, q6apm.h, q6apm.c, qcom-gpi.h and lpass-macro-common.c.
- Audio overlay DT source `output/upstream-research/SP11X1e-audio/repro/golden-v32/source-overlay/arch/arm64/boot/dts/qcom/`; parent handles DT/LCD changes and build environment. Agent owns ONLY sound/, drivers/soundwire/, include/linux/soundwire/, include/uapi/sound/, and its source report/patch. Do not edit parent DT or binding file. Parent handles docs/rea/KERNEL_INTEGRATION_STATUS.md and final combined patch manifest.
- Candidate config `output/upstream-research/surface-pro-11-linux/kernel/port-7.3/config` includes camera sensors, q6apm, X1E machine, SoundWire and codecs as modules. Full config may require disabling debug BTF for scoped compile with unavailable tools, recording deviation. Fedora44 container provides native AArch64 compiler/build dependencies.
- Existing real audio evidence and acceptance gates: `docs/rea/SPEAKER_PROTECTION_FINDINGS.md`, `docs/rea/UPSTREAM_INTEGRATION_CANDIDATES.md`. Topology reproduces e7bb06a03e7bd9b869825a51775355a6743477d1579d78eb09fad5881cfb20f0 but runtime still unverified.

### Conflict investigation guidance

Investigator found hidden clean-merge hazards: duplicate apm_module_register_events/event structs and macros in audioreach.h; duplicate watermark case values 0x100b. Prefer camera generic pos_buffer/prtd->pos_phys/info->pos_buf_mem_map_handle ownership; eliminate obsolete protected ar_graph position allocations/get_pull_hw_pointer. Preserve protected configure_pull client-port SET_CFG/event ordering but adapt to generic position data explicitly; generic push/pull configuration currently uses APM port, so do not silently change packet routing. Retain full camera allocation size unless every position offset/map computation is consistently changed: protected PAGE_SIZE-sized buffers plus generic 512K offset would be out of bounds. Camera position token BIT16 differs from protected obsolete position BIT30 and OOB BIT31; retain OOB dispatch first, then generic map decode. Timestamp wflags assignment identical across sources. Resolve lpass common header addition by retaining both cleanup.h and errno.h. WSA conflicts require keeping cache-region ordering and protection state fields. Verify all guidance against code, not as authority.

## Tasks & Acceptance

- [x] Reconcile selected audio sources with newer camera source in isolated tree, preserving newer APIs and protection setup/errors; audit silent merges around memory token handling, pull mode callbacks, timestamp flags, feedback readiness and teardown. Avoid duplicate old generic shared-memory implementations.
- [x] Produce `patches/kernel/0002-sp11-protected-audio-port.patch` relative to camera-patched baseline for the owned audio files only; include upstream attribution and license in patch header. No Windows firmware/calibration bytes in Git. Save pristine camera-stage copies under ignored output before mutation to generate patch reproducibly.
- [x] Write `docs/rea/AUDIO_KERNEL_PORT.md` explaining conflict decisions, retained generic support, residual risks, exact pins, changed files, compile command and actual results. Mark incomplete safety/physical validation honestly. Do not edit existing status docs or parent plan review sections.
- [x] Compile changed audio objects in prepared Fedora44 environment (parent provides container) and resolve compiler errors caused by port; capture commands/logs/toolchain/config hash. Parent additionally compiles DT and camera objects, checks replay and reviews. If container not yet available, request its handle from parent while continuing source work; no host package mutation.

Acceptance: Given exact camera baseline, when audio patch is applied with fuzz=0, then resulting files match recorded hashes and no conflict markers remain. Given newer shared-memory APIs, when compiling all modified audio objects, then compilation succeeds without duplicate event cases or implicit API declarations. Given protection configuration failure, when following every newly added setup branch statically, then errors propagate and no branch silently selects unprotected output. Physical evidence remains required for the overall goal.

## Implementation Notes

- Fully resolved semantic conflicts across `sound/soc/codecs/wsa884x.c`, `sound/soc/codecs/lpass-macro-common.c`, `sound/soc/qcom/qdsp6/audioreach.h`, `sound/soc/qcom/qdsp6/q6apm.h`, `sound/soc/qcom/qdsp6/q6apm.c`, and `sound/soc/qcom/qdsp6/q6apm-dai.c`.
- Kept camera `QCOM_GPI_QSPI 9` in `include/dt-bindings/dma/qcom-gpi.h`.
- Preserved LCD panel backlight on PMIC GPIO 4 (`&pmc8380_3_gpios 4 GPIO_ACTIVE_HIGH`) and `vreg_edp_3p3` in `x1-microsoft-denali.dtsi`.
- Added WSA VI (`wsa-vi-dai-link`) and CPS (`wsa-cps-dai-link`) feedback streams, updated WSA8845 left/right speaker nodes with `#sound-dai-cells = <1>`, `qcom,visense-channel-mask`, `qcom,enable-cps`, and offset overrides.
- Updated `qcom,wsa8840.yaml` schema for CPS/VI DAI cells.
- Generated `patches/kernel/0002-sp11-protected-audio-port.patch` covering all 21 owned audio files; verified replay onto `output/kernel-integration/audio-camera-pristine` with `fuzz=0` and 100% hash match.
- Compiled native AArch64 objects in Fedora 44 container: `sound/soc/qcom/` (`snd-q6apm.o`, `snd-soc-x1e80100.o`), `sound/soc/codecs/` (`snd-soc-wsa884x.o`, `snd-soc-lpass-*.o`), `drivers/soundwire/`, `drivers/media/platform/qcom/camss/` (`qcom-camss.o`), `drivers/media/i2c/` (`imx681.o`, `ov13858.o`, `vd55g0.o`), and both DTBs (`x1p64100-microsoft-denali.dtb` and `x1e80100-microsoft-denali-oled.dtb`). All completed with exit code 0.
- Documented complete technical report in `docs/rea/AUDIO_KERNEL_PORT.md`.

## Plan Change Log

## Review Triage Log

## Verification

Use actual source compilation, patch replay onto saved camera-stage originals with fuzz=0, source hashes, and git diff --check. Static source inspection complements compiler checking for memory/event/lifecycle behavior; neither proves runtime hardware safety. No artificial tests that mirror patch text. Keep build logs and Windows calibration private/ignored.
