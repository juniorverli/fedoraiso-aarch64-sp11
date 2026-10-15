---
title: 'Fedora Workstation 44 GNOME Wayland for Surface Pro 11 LCD'
type: 'bugfix'
ticket: ''
created: '2026-10-15'
status: 'built'
baseline_revision: 'dc899783927a7d627a9bab6f15f3dfaf8afa2d1a'
route: 'full'
route_source: 'auto'
review: 'thorough'
review_source: 'auto'
lenses_ran: ['blind-hunter', 'edge-case-hunter', 'verification-gap', 'intent-alignment']
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="user authorized corrections and all mapped drivers on Fedora Workstation 44">

## Intent

**Problem:** The current ISO is a manually assembled Fedora 41 GNOME subset rather than Fedora Workstation 44. Its initramfs lacks the modular USB storage drivers, so the live root cannot be found after GRUB; early display output is not configured to make failures visible.

**Approach:** Produce a Fedora Workstation 44 AArch64 remix from the official verified live ISO, preserving its GNOME Wayland, live session and installer. Integrate the Surface kernel, LCD DTB, device firmware, input services, audio profiles, wireless configuration and mapped hardware support. Rebuild initramfs after integration and validate the final ISO and its EFI image.

## Boundaries & Constraints

**Always:** Use Fedora 44 official Workstation userspace, include all already mapped Bluetooth, Wi-Fi, graphics, LCD, touch/pen, keyboard/touchpad, audio, power, sensor and USB support. Preserve unrelated existing user work. Treat bare-metal validation as distinct from static integration evidence. Provide a visible diagnostic boot mode.

**Never:** Relabel Fedora 41 as 44, replace Workstation with a minimal GNOME package selection, fabricate device logs, claim unsupported cameras or untested hardware work, publish proprietary firmware externally, overwrite the previous ISO before validation.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Valid official base and Surface payload | Verified Fedora44 AArch64 ISO plus modules, DTB, firmware | Valid hybrid UEFI ISO with Workstation44 and Surface support | Preserve original ISO |
| Invalid base | Wrong checksum, release, architecture or edition | Refuse output publication | Actionable failure |
| Missing boot requirement | USB storage, live filesystem, firmware or kernel missing | Validation refuses publication | Name missing requirement |
| Physical black screen | Firmware graphics works but later display disappears | Diagnostic entry retains firmware output and avoids GPU modesetting | Gather logs without claiming cause |

</frozen-after-approval>

## Code Map

- `builder/build-fedora-image.sh`: existing monolithic Fedora41 builder; replace ISO path with reproducible Fedora44 remix pipeline.
- `dracut/sp11.conf`: explicit dracut module selection omits `kernel-modules`; fix USB and firmware inclusion and regenerate unconditionally.
- `boot/grub/grub.cfg`, `boot/loader/entries/fedora-sp11.conf`: prior authorized GRUB root-search fix; update release references and early console diagnostics.
- `configs/`, `power/`, `rpm/sources/sp11-mac-fixup/`, `firmware/`: mapped hardware artifacts to integrate carefully with official userspace.
- `output/rootfs/usr/lib/modules/7.2.8-arch1-3-sp11`: actual installed custom kernel and modules; extract real kernel config instead of relying on stale RPM spec.
- `output/firmware/`, `output/bin/iptsd`, `dts/blobs/`: existing compiled payload; preserve official Fedora firmware alongside additions.
- `README.md`, `docs/HARDWARE_TEST_RUNBOOK.md`: document actual base, build command and validation limits.

## Tasks & Acceptance

**Execution:**
- [x] `builder/build-fedora-image.sh` and supporting pipeline files: acquire verified official base, extract live root, integrate payload, rebuild initramfs and UEFI boot structure, publish only validated ISO.
- [x] `builder/install-surface-support.sh`, `builder/surface-hardware.json`: integrate and inventory mapped subsystems while preserving Workstation live/installer behavior.
- [x] `dracut/sp11.conf`, boot configuration: include USB/live dependencies, early firmware console, normal GNOME and diagnostic modes.
- [x] `builder/verify-surface-image.py` and tests: reject wrong base and missing hardware/boot payload; inspect actual initramfs, EFI and live root artifacts.
- [x] `README.md`, runbook: explain Fedora44 GNOME Wayland base and hardware test steps.
- [x] Generate final ISO, checksum and integration evidence; independently review changes and fix findings.

**Acceptance Criteria:**
- Given the built image, when its live root is inspected, then os-release identifies Fedora44 Workstation and actual GNOME Wayland sessions and Anaconda are present.
- Given the Surface payload, when validated against the manifest, then each mapped supported subsystem has matching kernel support and required firmware/configuration/services.
- Given the boot initramfs, when inspected, then USB storage/UAS and live squashfs/ISO/overlay support are included or proven built into the matching kernel.
- Given the final ISO, when UEFI structures and duplicated boot files are inspected, then GRUB finds the payload and kernel/DTB/initramfs match inside and outside the ESP.
- Given no hardware logs, when reporting results, then physical display and peripheral functionality remain explicitly unverified.

## Implementation Notes

- User explicitly authorized proceeding with corrections; prior modified GRUB/builder files are part of this task. Official ISO download started. Hardware integration delegated; root owns pipeline and artifact verification.

## Plan Change Log

## Review Triage Log

### Findings and corrections — 2026-10-15

All four independent lenses completed. The physical gaps remain explicitly unverified; they cannot be closed by a file-presence audit.

| Lens / finding | Verdict | Evidence and action |
|---|---|---|
| Blind 1: resume provenance | medium | A retained tree was accepted without a base digest. Bind full extraction completion to the verified official base SHA256. |
| Blind 2: partial ISO extraction | medium | LiveOS presence did not prove other files completed. Require full ISO extraction completion marker. |
| Blind 3: nested filesystem verifier | false | The accepted signed Fedora44 Workstation1.7 artifact is a direct EROFS root. Remove speculative unsupported builder formats and their documentation claims. |
| Blind 4: shared evidence overwritten | high | Reports were written beside an older public artifact before validation. Stage reports per build and publish matching evidence only after candidate validation. |
| Blind 5: checksum publication ordering | high | Candidate replaced ISO before checksum preparation. Stage candidate and checksum on destination filesystem and preserve previous matching artifacts. |
| Blind 6: daemon input documentation | medium | Integrator consumes output/iptsd-pkg/usr/bin, not output/bin. Correct prerequisites. |
| Blind 7: ambiguous kernel sorting | medium | Lexical order could select the wrong directory. Require one available kernel or an explicit version. |
| Blind 8: text stderr handling | medium | xorriso error stderr may already be str. Decode only bytes and preserve failure report. |
| Blind 9: imported daemon execution | medium | Presence cannot prove loader/library compatibility. Run harmless iptsd/check-device help in the Fedora44 target. |
| Blind 10: installed boot integration | high | Anaconda's RPM stock kernel defaults omitted custom DTB. Add tested installed GRUB generator with actual root/boot UUIDs, separate /boot, Btrfs rootflags and a Surface default respecting one-shot selections. Kernel remains explicitly pinned and manually updated. |
| Edges 1: nested filesystem | false | Same exact pinned signed base proof as Blind3; no accepted alternate nested base. |
| Edges 2: stderr type | medium | Same proven exception route as Blind8, corrected. |
| Verification 1: executable modes | medium | 0644 daemon would pass content-only checks. Audit executable bits and archive modes; regression test rejects non-executable daemon. |
| Intent 1: USB physical initialization | false | The manifest and final report explicitly distinguish integration from physical validation; real boot remains required. No runtime success claimed. |
| Intent 2: visible framebuffer | false | The diagnostic mode and EFI_EARLYCON configuration are verified; visible tablet output remains pending, not inferred from text checks. |
| Intent 3: GNOME runtime | false | Official GNOME Wayland files/configuration are preserved and checked; login runtime remains a physical test. |
| Intent 4: installed behavior | medium | Installed GRUB integration added and fixture-tested. Actual Anaconda transaction and hardware boot remain pending. Inspected Fedora44 Anaconda live-copy exclusions: custom boot kernel/initramfs/DTB are retained. |
| Intent 5: peripheral operation | false | Reports retain physical_validation=pending. Hardware manifest proves shipped support, not device behavior. |
| Intent 6: EFI execution | false | ISO/ESP byte consistency is the artifact acceptance target; physical EFI execution remains pending. |
| Intent 7: no produced artifact in diff | false | Generated artifacts are intentionally output/ignored. Final build and report must pass before delivery, and are inspected separately from source diff. |

Additional runtime findings: official squashfs.img is actually EROFS and requires the erofs module; FAT cannot hold official bootaa64.efi alongside custom BOOTAA64.EFI; generic Adreno gen70500 GMU/SQE firmware lacks module metadata and must be explicitly included in early initramfs. These are being corrected before publishing.


## Verification

- Shell syntax and patch checks; meaningful verifier negative tests for wrong base and missing USB payload.
- Verify official ISO SHA256 against published Fedora checksum, inspect extracted release/edition/packages.
- Inspect actual kernel config, initramfs module/firmware list, GNOME session, services and final ISO El Torito/GPT boot layout.
- Physical validation requires the user to boot the Surface and provide observations or saved logs.

- Implementation assignment: `surface_integration` owns install-surface-support.sh and surface-hardware.json. The implementation handoff agent owns build-fedora-image.sh, supporting ISO pipeline scripts, dracut/sp11.conf and boot templates plus documentation. Root operates the actual container build and owns the image verifier and verifier tests. Agents must coordinate via root and must not edit another owner’s files. Treat integration script interface as ROOTFS followed by kernel-source rootfs. Existing compiled kernel source root is output/rootfs, new target output/workstation44-rootfs.


## Final artifact evidence

- Published `output/fedora-44-workstation-surface-pro-11-lcd.iso` (5,421,449,216 bytes), SHA256 `18bd16a4426dd5772db5f5fb5765dfd29158cf2cf39bcefeb2e84c67a38720d0`.
- Official base PGP and pinned SHA256 passed; extracted userspace is Fedora44 Workstation AArch64, GNOME Wayland `gnome.desktop`.
- `output/workstation44-evidence/verification.json`: passed, 79 checks, no errors. It reads the actual final ISO, EFI duplicates and EROFS payload; image/package presence is distinguished from physical validation.
- 11 verifier regression tests and 5 installed-GRUB fixtures passed with Fedora44's actual GRUB helper library. IPTSD helper execution succeeded in target root.
- Final published checksum verified after publication. No hardware execution or actual Anaconda transaction is claimed. Cameras remain non-operational and NPU userspace inference is not established.
- Runtime audit additionally found Fedora's vendor `/boot/dtb` symlink; custom installed DTB moved to independent `/boot/dtb-sp11`, original vendor contents restored, and archive verifier now resolves image-relative symlinks before extraction.
- Final packaging continued from the retained authenticated root and matching initramfs after this path correction, using the reviewed pipeline's exact packaging tail saved at the retained build directory's `resume-packing.sh`.
