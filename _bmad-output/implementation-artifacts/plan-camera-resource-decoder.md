---
title: 'Decode camera resource packages with byte provenance'
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
baseline_revision: cf57f8885b0ecf6665d780aea440540f8c93b484
context: []
---

<frozen-after-approval reason="continuation of authorized camera and sensor investigation">

## Intent

Continue Phase 1 with reproducible offline analysis of the camera resource files available in the local Windows DriverStore. Establish the container layout, preserve every decoded value's provenance and produce an evidence-backed comparison with the speculative camera DTS. Physical Fedora enumeration is still pending: only WSL-labelled smoke captures exist.

## Boundaries & Constraints

Keep existing history, build paths and all user-owned untracked files. Parse files as data: no driver execution, GPIO writes, streaming, firmware changes, PAM changes or speculative DTS activation. Keep raw inputs and decoded outputs local under ignored output/research paths. Commit only decoder source, synthetic tests, plans and reviewed findings. Distinguish observed resource tuples from inferred Linux semantics and board presence. Do not equate Windows GPIO numbers or resource IDs with Linux bindings without corroboration. No remote operations.

## I/O & Edge-Case Matrix

| State | Expected behavior |
|---|---|
| Valid nested AeoB container | JSON with header, ordered arguments, absolute offsets, lengths, raw hex and SHA256 provenance |
| Unaligned arguments, short data and 64-bit integer | Advance by 4 + max(4, DataLength), never align to 4; preserve full 8-byte integer and flag wider-than-V1 form |
| Truncation, bad signature/length/count or package overrun | Clear offset-specific error, no successful partial document |
| Unknown argument type | Preserve type and opaque raw bytes with warning; never fabricate child structure |
| Excess bytes/depth/nodes | Fail clearly within fixed bounds |
| Existing output or output aliases an input | Refuse overwrite, preserve original bytes |
| Invalid second input in batch | Nonzero exit, no newly published JSON output |

</frozen-after-approval>

## Code Map

- `docs/rea/INITIAL_STATIC_FINDINGS.md`: previous hashes, package origins, INF mappings and header observations; update historical decoder-unknown statement with a link, not erase the chronology.
- `docs/rea/PHASE_1_CAMERA_SENSORS.md`: camera/ALS roadmap, no physical claims. Add link to new resource analysis.
- `dts/camera-sp11.dtsi`: inactive hypotheses, front/rear/IR GPIO110/111/112 and MCLK24MHz currently unsupported; compare without changing code.
- Windows source root `/mnt/c/Windows/System32/DriverStore/FileRepository` contains `surfacecam{front,rear,aux}sensor_extension8380.inf_arm64_*`. Relevant triples: SCFG_FRONT_MSHW0490 + CAMF_RES_MSHW0490, REAR0491 + CAMS0491, AUX0492 + CAMI0492. Multiple supported board variants exist.
- Preliminary byte walk of selected files exactly consumes one nested type3 package after 12-byte header. Strings type1, integers type0, buffers type2; observed integer DataLength8 despite Microsoft V1 union documentation using ULONG. Preserve width, no truncation.
- Public sources: Microsoft Learn ACPI_EVAL_OUTPUT_BUFFER_V1 and ACPI_METHOD_ARGUMENT_V1, ReactOS acpiioct.h (official Doxygen) for signature/type/stride definitions. Interpret neither source as documentation for vendor resource tuple semantics.

## Tasks & Acceptance

Implementation agent owns only decoder and its tests, plus implementation notes in this plan. Parent owns actual private-file analysis, findings docs and roadmap edits. No commits or extra agents from implementer.

- [x] `scripts/decode-camera-resources.py`: Python standard library CLI taking one or more explicit file paths, optional `--output` JSON path (otherwise stdout), no implicit DriverStore scan or hardware access. Input reads capped at 1MiB+1, max depth32 and total nodes10000. Validate minimum header12, signature bytes AeoB, declared length exactly file length and argument count. Parse sequences with bounds and minimum argument storage8; package3 recurses inside its declared data span. Preserve unknown types opaquely. Report filename/path, SHA256, parser SHA256, schema version, header and ordered nodes with absolute header/data offsets, declared payload length, storage span, raw hex, kind and decoded value or children. Preserve short-data storage padding separately so all bytes have provenance. Integer lengths4/8 supported; other lengths rejected; warn on 8-byte extension. Strings require ASCII and final NUL; preserve raw bytes and trailing-NUL detail. Package and unknown data may be empty, subject to minimum storage. Do not duplicate full raw hex on every package ancestor; package spans plus children/padding are enough for provenance. Catch filesystem/decode errors cleanly. Read/validate all batch inputs before publishing, exclusive output creation; do not create directories implicitly. Refuse output reuse including alias/symlink cases. Keep output deterministic for same parser/input except explicit input path provenance.
- [x] `tests/test_camera_resources.py`: synthetic bytes only, no Windows binaries required. Cover matrix with nested packages, mixed types, unaligned offsets, empty/short buffer with nonzero padding, 4/8-byte integers including high bits, bad signature/header/length/count, short argument/package overrun, nested residual bytes, missing string terminator/nonASCII, unknown type retained, bounds/depth/node limits, missing inputs, CLI stdout and exclusive output refusal, batch failure without output and unchanged input/output hashes. Assert byte offsets and exact values, not just parse success.
- [x] Parent `docs/rea/CAMERA_RESOURCE_FINDINGS.md`: record format rationale, Microsoft/ReactOS primary URLs, decoder limits, reproducible commands, source hashes and INF board mappings; summarize selected front/rear/IR package sequences with offsets, GPIO/clock contradictions and unknown semantics. Keep full decodes ignored. Add any further actual REA sensor-binary observations with hashes and limitations.
- [x] Parent `docs/rea/INITIAL_STATIC_FINDINGS.md`, `docs/rea/PHASE_1_CAMERA_SENSORS.md`: link new findings and update next resource-analysis step. Record ALS live route and physical sensor identities still unresolved.

Acceptance: Given local matching packages, when decoded, then the reviewed report cites source digests and exact field locations and separates parsed structure from hardware meaning. Given malformed or hostile data, when parsed, then bounds prevent partial or misleading success. Given no new Fedora inventory, when describing progress, then no Windows package observation is promoted into a physical binding claim.

## Implementation Notes

- Native read-only Windows PnP/CIM queries through WSL confirmed Surface Pro 11 host identity, matching MSHW0490/0491/0492 camera IDs, and display/keyboard sensor platforms. Their driver-compatible matching ID MSHW0488 resolves to active oem126.inf, whose hash matches the analyzed qcSensors.inf. This is Windows evidence; physical Fedora correlation remains pending.

- Parent decoded six selected local files and independently compared 595 nodes; exact byte reconstruction matched every original. New resource report records offsets, GPIO/clock contradictions, vendor-semantics limits, module-data prefixes and actual REA platform disassembly capture. No physical Fedora capture has arrived.

- Implemented a standard-library, explicit-input CLI in `scripts/decode-camera-resources.py`. JSON schema version 1 wraps ordered `documents` with the decoder source SHA256. Each document records input path/name, SHA256, complete header bytes and ordered argument nodes.
- Node offsets are absolute. Argument header bytes, leaf payload bytes and short-storage padding are distinct fields; package payload is represented by children without copying ancestor payload hex. Synthetic reconstruction proves exact byte coverage. String `value` removes one required final NUL and preserves earlier NULs; `trailing_nul_count` explicitly records the entire terminal run.
- Validation enforces exact file length/count, package spans, integer widths, ASCII terminators, 1MiB reads plus one sentinel byte, depth 32 and 10000 total nodes. Unknown types remain opaque with warnings; 8-byte integers preserve high bits and carry the V1-width warning.
- Batch inputs are all validated before serializing/publishing. Fixed aggregate limits are 16MiB, 50000 nodes and 128 files; per-file limits remain 1MiB, depth32 and 10000 nodes. Inputs must be regular files, checked before opening and again on the opened descriptor; nonblocking opening prevents FIFO replacement races from blocking. Output is written completely to a private temporary file in its existing parent, then atomically published with `os.link` (no replacement). Owned temporary files are cleaned after write/publication errors; existing paths, symlinks and aliases remain protected. Errors name their input and byte offset where decoding fails.
- Integer nodes include exact `value_decimal` and `value_hex` strings alongside numeric `value` and little-endian `raw_hex`; JavaScript numeric consumers must use the strings above 2**53-1. These interoperability and batch limits are documented in CLI help/docstring.
- Synthetic tests cover lossless byte provenance, nested mixed types and unaligned offsets, empty/short payload padding, malformed data, per-file/aggregate limits, deterministic stdout, valid batch ordering, failed-batch publication safety, injected write/publication failures, concurrent destination creation, FIFO rejection with a timeout guard, filesystem errors and preserved input/output hashes. Focused verification: all 16 methods in `test_camera_resources.py` pass. Private-resource execution and findings remain assigned to the parent agent.

## Plan Change Log

## Review Triage Log

Review pass 1: 6 medium, 2 low, 4 false; no high findings or material unresolved findings. Verification-gap lens reported no gaps. Each independently filed finding is retained below before grouping.

| Lens / finding | Verdict | Route and evidence |
|---|---|---|
| Blind: partial output on failed write | medium | patch: completed private temporary file is linked atomically without replacement; injected write/publication failures and destination races tested. |
| Blind: special input blocks | medium | patch: regular-file checks before and after nonblocking open reject FIFOs/devices; real FIFO rejection covered with timeout guard. |
| Blind: aggregate batch unbounded | medium | patch: fixed byte/node/file batch bounds added; lowered-limit tests prove failure before output and acceptance at exact boundary. |
| Blind: wide JSON integers round | medium | patch: exact decimal/hex strings added alongside numeric value and raw bytes; high-bit integer test and documentation updated. |
| Blind: missing delays/state3 inventory | low | patch: complete ordered DSTATE0/3 descriptor inventory added with offsets, including delay values and explicit unknown units. |
| Blind: REA command lacks saved artifact | low | patch: mkdir and explicit JSON output redirection added to reproduction command. |
| Blind: report lacks parser identity | medium | patch: final generating decoder SHA256 recorded in committed report; regenerated private JSON and reverified 595 nodes and byte reconstruction. |
| Edges: output failure leaves file | medium | patch: same verified cause as blind publication finding; atomic no-replace publication prevents partially written final JSON. |
| Intent: selected vs all local variants | false | no defect: target-specific variants were selected explicitly; subsequent native Windows present IDs corroborate those board IDs. No exhaustive DriverStore coverage claimed. |
| Intent: synthetic vs actual evidence | false | no defect: parent executed six actual decodes and independent 595-node byte walk, then exact reconstruction. Tests remain portable without proprietary fixtures. |
| Intent: tuple structure vs semantics | false | no defect: inferred electrical meaning and Linux mapping are explicitly unresolved; no active DTS bindings changed. |
| Intent: private inputs required for reproduction | false | no defect: owned proprietary inputs remain local by design; committed reports retain hashes, offsets and parser identity for reproducible reacquisition. |

## Verification

- `/usr/bin/python3 -m unittest discover -s tests -p test_camera_resources.py -v`
- Decode selected local resource files into ignored `output/phase1-camera-resources/`; compare byte offsets/values with independent struct walk.
- `git diff --check`; review only owned artifacts before local commit.

Final verification: all 16 decoder tests pass after patches. Six local resources were reprocessed by the final parser; independent comparison covered 595 nodes and reconstructed all source bytes exactly. Exact integer strings, private source retention, parser digest and diff whitespace verified. Four review lenses completed, with all material findings fixed. No driver, active DTS, ISO or authentication settings changed.
