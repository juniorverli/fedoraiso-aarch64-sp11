# Camera and sensor research

Keep private acquisition data in `raw/` and proprietary binary inputs or local
REA sessions in `private/`; these directories are ignored. Keep reviewed,
sanitized analysis in `reports/`. Start with
[Phase 1](../../docs/rea/PHASE_1_CAMERA_SENSORS.md).

Each capture needs UTC acquisition time, owner/device source, OS, actual running
kernel release plus package/source revision, loaded DTB hash where known, and
actual firmware versions/full hashes. Record unknown values as unknown. Preserve
full SHA256 manifests locally. Never infer a running version from this checkout's
static build manifest. WSL smoke checks must always retain their WSL label.

For binary analysis record full original SHA256, original filename, package and
version, tool/version, exact command, source offsets/lines and output provenance.
Separate observations from inferences and record conflicting evidence. Keep raw
logs private: selected metadata omits serial fields, but no automatic anonymity
is promised. A sanitized handoff contains only manually reviewed excerpts and
hash references, never proprietary inputs or biometric images. Use
[the report template](reports/evidence-template.md).
