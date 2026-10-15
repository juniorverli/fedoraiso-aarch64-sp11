---
title: 'Fedora migration diagnostics and configuration guides'
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
baseline_revision: 84c3dcc27e0243ec4eea9a440c5d12ab2ba36521
context: []
---

<frozen-after-approval reason="user explicitly requests completing all migration phases">

## Intent

Advance all requested Fedora migration phases with actionable audio, silent boot and GNOME/Wayland diagnostics and configuration instructions, preserving the camera investigation and Git work already delivered. User specifically clarified that missing speaker protection needs real DSP/amplifier investigation, not volume boosting. Full goal stays active until physical requirements are verified; this implementation is the diagnostic/configuration deliverable, not a claim of hardware completion.

## Boundaries & Constraints

Preserve user-owned untracked notes, Git history, working ISO and kernel/DTB. No changes on the physically booted Fedora are possible until access/captures arrive. Do not mistake WSL or extracted rootfs for a live desktop. Keep collected data ignored/private and report missing tools/permissions. Do not change speaker gain, install arbitrary UCM/ACDB, activate speculative DTS, capture biometrics or modify PAM. No Git push or invented remote. User authorized every phase together; do not stop for another scope approval. Guidance must retain encryption/root flags, emergency access and rollback. OEM logo continuity and strict native Wayland require actual verification, not environment-variable assertions.

## I/O & Edge-Case Matrix

| State | Expected behavior |
|---|---|
| Fedora desktop user | Read-only private timestamped bundle with command statuses, hashes and section summaries |
| WSL default | Refuse; explicit smoke option labels every bundle as WSL only |
| Missing binaries or denied journal/sysfs | Complete partial evidence, preserve failure types |
| Existing output path | Refuse overwrite without changes |
| Section selection | Only selected read-only commands run; no recording, mixer writes, restart or playback |
| Root invocation | Explain user-session probes must run as login user; do not inspect root PipeWire as desktop evidence |

</frozen-after-approval>

## Code Map

- `scripts/collect-camera-sensor-evidence.py`: reusable standard-library run_command, is_wsl, read_attribute, write_json helpers; import by path or reuse thoughtfully, do not duplicate huge collector. Existing helper spools output and records timeout/missing/permission status.
- `boot/grub/09_surface_sp11`: installed custom menu entry generated from GRUB_CMDLINE_LINUX/DEFAULT, not managed by grubby/BLS; preserves UUID, encryption and Btrfs flags. Do not edit in this slice.
- `boot/grub/grub.cfg`: ISO explicitly uses earlycon/keep_bootcon/loglevel7/rd.plymouth=0/plymouth.enable=0. Guide must explain these conflict with silent boot; installer custom entry also inherits them if configured.
- `builder/install-surface-support.sh`: keeps official distribution audio/monitor defaults; the legacy PipeWire preset is not installed by remix builder.
- `configs/pipewire/pipewire.conf.d/10-surface-sp11-audio.conf`: legacy rate/latency/AEC preset, not speaker protection. Do not activate it or claim beamforming/protection from this file.
- `output/workstation44-rootfs/usr/share/plymouth/themes/bgrt/bgrt.plymouth`: actual Fedora44 theme uses two-step with UseFirmwareBackground=true for boot/shutdown/reboot; cannot promise firmware BGRT exists under DT boot.

## Tasks & Acceptance

Implementation agent owns session collector, tests and three guides below, plus notes here. Parent owns speaker-protection REA/upstream source audit and global status document. No commits or extra agents from implementer.

- [x] `scripts/collect-fedora-session.py`: Python standard-library collector with `--section all|audio|boot|desktop`, optional new `--output`, explicit `--allow-wsl`. Run as normal desktop user; refuse root. Default output ignored `research/camera-sensors/raw/session-<unique>`. Reuse helper statuses and command bounds. Metadata includes UTC, kernel, OS, WSL, collector hash and selected section. Audio: wpctl status/default sink/source inspect/get-volume, pactl card/sink/source data, aplay -l, arecord -l (listing only), alsaucm listcards, user audio services and bounded recent journals. Boot: /proc/cmdline, Plymouth default-theme query, boot service status/logs, BGRT sysfs status/existence, selected installed Surface artifact hashes if accessible; no private binary copies. Desktop: gnome-shell --version, loginctl show-session when XDG_SESSION_ID exists, selected XDG session variables, gsettings interface/power reads, gnome-extensions list, Xwayland process presence via pgrep and read-only xlsclients when available. Explain a running Xwayland process does not prove each app uses X11, and empty xlsclients isn't exhaustive verification. No full process environment scraping. Save manifest and concise gap summary; create output mode0700 exclusively. No implicit dependencies installed.
- [x] `tests/test_fedora_session.py`: meaningful temporary/mocked tests cover matrix, command selection without hardware mutation, manifest, WSL/root guards and capture of real status failures. Existing collectors remain functional.
- [x] `docs/AUDIO_DIAGNOSTICS.md` (Portuguese): Fedora checklist with commands, UCM/card/profile evidence, stereo mapping, sample rate/quantum and XRUN diagnostics, stock config comparison, reversible user PipeWire override example only if measured need, no rate inflation as fidelity claim. Speaker protection is DSP/VI/calibration work with separate parent report; do not lift cap or imply EQ/AEC protects drivers. Microphone reported working; avoid unnecessary changes. Explain rollback/backups and user-service restart effects. Cite primary WirePlumber/PipeWire/ALSA docs after verifying current instructions.
- [x] `docs/SILENT_BOOT.md` (Portuguese): exact installed-GRUB instructions and rollback; remove verbose/disable-Plymouth flags, add quiet splash loglevel=0 systemd.show_status=false rd.systemd.show_status=false udev.log_level=err rd.udev.log_level=err; preserve hardware/root/LUKS flags. Select available bgrt theme, rebuild correct pinned custom initramfs explicitly, regenerate /boot/grub2/grub.cfg; explain grubby won't update this custom entry and never overwrite EFI vendor stub. Show kernel/artifact verification, journal retention, manual diagnostics recovery and shutdown observations. BGRT/OEM logo may be absent on DT boot; give owner-supplied logo theme approach or explicitly mark exact seamless logo pending asset/physical display. Never promise every firmware/security/error prompt can be hidden. Preserve required password prompts. No auto deployment or ISO rebuild in this slice.
- [x] `docs/GNOME_MATERIAL3.md` (Portuguese): exact session and per-app Wayland checks using env/loginctl, GTK Inspector when enabled, Firefox about:support, Chromium Ozone app launches and WAYLAND_DEBUG per-target. Xwayland/app claims must be scoped; strict GDK_BACKEND=wayland / QT_QPA_PLATFORM=wayland are per-app options and cannot convert X11-only applications. Fedora44 ships GNOME50 (verify actual version). Provide staged native color/dark/icon/font/wallpaper steps and Material3 dynamic palette/theming route with backups/rollback and GTK3/GTK4/libadwaita/Flatpak limitations. Official extension registry currently Material You 5236 supports42–44, Open Bar6580 up to49, not50: don't disable compatibility checks or claim success from those. Verify current sources; state unsupported portions honestly. Material-inspired colors do not transform application layout into full Material3. Include usable specific steps for icons and dynamic palette tools with pinned/reviewable source and dependency requirements, not an unverified curl installer. No downloads/config mutations in product flow without explicit commands.

Acceptance: Given the user follows the guides on Fedora, when diagnosing, then evidence can identify their current card/profile, boot arguments and desktop protocols before modifications. Given this WSL workspace, when verifying, then only tooling/static guarantees are claimed. Given remaining hardware speaker protection, camera and OEM-logo constraints, when reporting status, then the full goal remains open.

## Implementation Notes

- Parent audited pinned external audio/camera sources, confirmed native Windows X1P REV_0D and exact ACDB match, recompiled protected topology on Fedora44 with published SHA256, and recorded findings plus full-phase status. Active hardware integration remains pending.

- Implemented a standard-library session collector reusing the existing camera collector's bounded subprocess/status/read/JSON helpers. Root and unapproved WSL invocations refuse before creating output; selected sections run only explicit read-only probes. New private bundles contain UTC/OS/kernel/hash metadata, status summaries and payload manifests.
- Added Portuguese audio, installed custom-GRUB/Plymouth and GNOME/Wayland/Material-inspired configuration guides. Speaker protection links the separate REA report and preserves current limits; native Wayland and OEM logo remain physically unverified. No hardware/configuration changes, ISO rebuild, arbitrary DSP/UCM deployment or Git operations performed.
- Verified primary PipeWire, WirePlumber, ALSA, GTK, Chromium, Fedora package and GNOME extension sources. Registry still lists Material You for 42–44 and Open Bar through 49. Matugen example pins 9f8c7fd583e44310a642772ff8f13b693949baf2 with locked build and isolated preview; it is guidance, not a claimed Fedora runtime success. Fedora quick-docs fetch was blocked by Anubis; boot details were checked against the repository generator, builder, local theme and upstream dracut manual.

## Plan Change Log

## Review Triage Log

All four independent lenses completed before triage. Blind quota: nine findings. Intent alignment confirmed the explicitly limited deliverable; overall physical completion remains pending.

| ID / lens | Verdict | Evidence and action |
|---|---|---|
| B1 blind | medium / patch | Backup failure does not stop boot edits; guard every backup operation. |
| B2 blind | medium / patch | Independent dracut/GRUB commands allow failure progression; guard and provide restoration. |
| B3 blind | medium / patch | Theme may be absent but bgrt is unconditionally selected; stop on unavailable theme before edits. |
| B4 blind | medium / patch | No machine identity in metadata; add bounded nonserial DT/DMI attributes. |
| B5 blind | medium / patch | Nonroot alone does not identify desktop session; record effective user and context, warn on missing session/D-Bus. |
| B6 blind | low / patch | OS metadata failure omitted from summary; summarize statuses and truncation. |
| B7 blind | low / patch | Installed audio/Plymouth versions missing; add read-only RPM queries. |
| B8 blind | medium / patch | Palette repeat execution overwrites previous files; refuse existing work directory. |
| B9 blind | medium / patch | Speaker protection completion gate lacks specified evidence; add measurement/acceptance engineering prerequisites below. |
| E1 edge | medium / patch (duplicate B1) | mkdir/cp may fail without stop; same guarded backup fix. |
| E2 edge | medium / patch (duplicate B2/B3) | Theme/dracut failures allow continuation; same stop/restore fixes. |
| E3 edge | medium / patch | Noclobber refusal followed by rollback can remove existing override; condition rollback on successful own creation. |
| V1 verification | medium / patch | Test compares command list with implementation itself; removing required wpctl-status still passes. Independently assert required keys and persisted distinct payload/status. |

No review finding deferred. Physical deployment, acoustic protection measurements, capture and boot/desktop observations are external acceptance gaps already declared in scope, not successful test outcomes.

## Verification

- `/usr/bin/python3 -m unittest discover -s tests -p test_fedora_session.py -v`
- Session collector real labelled WSL smoke as a normal user or verified root refusal; inspect selected-command list and manifest.
- `git diff --check`; inspect guide commands against actual custom GRUB generator and extracted Fedora Plymouth theme.

Implementation verification (2026-10-15):

- `/usr/bin/python3 -m unittest discover -s tests -p test_fedora_session.py -v`: 5/5 passed, including exclusive/private output, manifest, root/WSL, section allowlist, real missing/denied/nonzero/timeout subprocess failures.
- Full existing unittest suite: 43 tests, OK with 5 installed-GRUB tests skipped because Fedora grub-mkconfig_lib is unavailable on WSL. Existing camera/research collector tests passed.
- Real normal-user WSL smoke (`--section desktop` and `--section all`, explicit `--allow-wsl`) completed, labelled WSL-only, under ignored raw/session directories. Inspected command selections, missing/failed/absent statuses and verified every manifest digest. No physical Fedora conclusion drawn.
- `git diff --check` passed; boot commands inspected against `09_surface_sp11`, pinned module/kernel path in builder, dracut config and Fedora BGRT theme. Physical stereo/protection, boot transitions and per-app protocols remain pending access to Fedora.

Post-review verification:

- Seven targeted session tests passed after fixes; independent required-probe assertions now detect missing wpctl-status and preserve distinct statuses/payloads.
- Actual nonroot WSL all-section smoke in raw/session-reviewed-20261015 passed, labelled WSL only; all five payload manifest hashes verified.
- All shell blocks in the three guides passed bash -n; parent inspected boot backup, stop/restore and artifact paths plus audio and palette nonoverwrite guards.
- Speaker protection acceptance gate now specifies unresolved physical thresholds, independent measurements, per-unit calibration, failure behavior and lifecycle evidence. No claim of physical implementation or certification.
- Camera patch applied on exact isolated base with fuzz=0. Six protected audio patches verified and applied to historical source overlay; three-way integration reveals seven unresolved source conflicts, retained in ignored review artifacts.
- All 13 review entries addressed (three duplicate edge observations share fixes); no finding deferred. Physical testing remains an explicit overall-goal gap.
