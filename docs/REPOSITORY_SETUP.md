# Repository setup

This checkout preserves its existing `master` branch, history, index and remotes.
The bootstrap creates missing directories; it does not commit, set a remote or
change the active branch. Run it again safely:

```bash
./scripts/init-repository.sh
```

To initialize a separate project (paths with spaces are supported):

```bash
./scripts/init-repository.sh '/path/to/new investigation'
```

A fresh target starts on `main` and creates only directories, this checkout's
ignore template and a short layout README. Clone or copy the existing repository
to transfer tools, tests and the roadmap; bootstrap does not copy these files.
For an existing ignore file, bootstrap verifies representative raw/private paths
and fails with the missing rules if they are not protected. It preserves the
owner's ignore content and index. A target within another repository is refused; choose
its root or a location outside it. Existing files are preserved.

| Path | Purpose |
| --- | --- |
| `docs/rea/` | Reviewed plans, analysis and driver roadmap |
| `research/camera-sensors/reports/` | Sanitized reports and evidence ledgers |
| `research/camera-sensors/raw/` | Ignored, private Fedora captures and local smoke checks |
| `research/camera-sensors/private/` | Ignored proprietary binaries and local REA inputs |
| `scripts/`, `tests/` | Reproducible tools and hardware independent tests |
| `configs/`, `patches/` | Reviewed configuration and future evidence backed patches |
| `_bmad-output/` | Authored investigation plans; runtime excluded from selective staging |

Build output, ISO files, Python caches, environments, local REA sessions,
credentials and editor temporary files are ignored. `_bmad/render/` is generated;
authored plans remain visible. The installed `_bmad/` runtime is not included in
this change; use selective staging to keep unrelated local files out. Ignore rules do not scrub existing Git history or
stop tracking files already committed. Inspect individual paths before staging.
Local proprietary binaries and raw logs must stay in the ignored research paths.

Review and record only selected artifacts, for example:

```bash
git status --short
git diff --check
git diff -- docs/rea/PHASE_1_CAMERA_SENSORS.md
git add -- scripts/init-repository.sh scripts/collect-camera-sensor-evidence.py
git add -- docs/REPOSITORY_SETUP.md docs/rea/PHASE_1_CAMERA_SENSORS.md
git diff --cached --stat
git diff --cached
git commit -m 'Add camera and sensor investigation tools'
```

Add other reviewed files explicitly as needed. The local Portuguese research
notes and existing untracked BMAD files belong to the user; leave them unstaged.
No GitHub remote URL has been supplied. When the owner supplies one, replace the
placeholder below; if `origin` already exists inspect it before making changes:

```bash
git remote -v
git remote add origin '<OWNER_SUPPLIED_GITHUB_URL>'
git push -u origin HEAD
```

These are manual publication commands, not steps performed by the bootstrap.
Begin hardware investigation with [Phase 1](rea/PHASE_1_CAMERA_SENSORS.md).
