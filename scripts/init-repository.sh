#!/usr/bin/env bash
# Scaffold an existing root, or explicitly create a separate repository.
set -euo pipefail
source_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
if (( $# > 1 )); then
    echo "Usage: $0 [target-directory]" >&2
    exit 2
fi
target=${1:-$source_root}
# Resolve without creating directories before the nested-repository check.
target=$(realpath -m -- "$target")
probe=$target
while [[ ! -d "$probe" ]]; do probe=$(dirname -- "$probe"); done
if root=$(git -C "$probe" rev-parse --show-toplevel 2>/dev/null); then
    root=$(cd -- "$root" && pwd -P)
    if [[ "$root" != "$target" ]]; then
        echo "Refusing nested target '$target' inside repository '$root'. Use its root or a separate target." >&2
        exit 1
    fi
elif [[ -e "$target/.git" ]]; then
    echo "Cannot inspect existing Git metadata in '$target'." >&2
    exit 1
else
    if (( $# == 0 )); then
        echo 'Fresh initialization requires an explicit target directory.' >&2
        exit 1
    fi
    mkdir -p -- "$target"
    git -C "$target" init -b main
    if [[ ! -e "$target/.gitignore" ]]; then cp -- "$source_root/.gitignore" "$target/.gitignore"; fi
    if [[ ! -e "$target/README.md" ]]; then
        cat > "$target/README.md" <<'LAYOUT'
# Camera and sensor investigation

Reviewed analysis belongs in docs/rea and research/camera-sensors/reports.
Keep raw captures in research/camera-sensors/raw and proprietary inputs in
research/camera-sensors/private; both are ignored. Scripts, configs, tests and
patches contain reproducible tooling. No remote is configured automatically.
LAYOUT
    fi
fi
# Check effective protection without editing an owner's ignore rules or index.
missing=0
for evidence_path in research/camera-sensors/raw/bootstrap-check research/camera-sensors/private/bootstrap-check; do
    if ! git -C "$target" check-ignore -q -- "$evidence_path"; then
        printf 'Missing ignore protection for %s; add /%s/ to %s/.gitignore.\n' \
            "$evidence_path" "${evidence_path%/*}" "$target" >&2
        missing=1
    fi
done
if (( missing )); then exit 1; fi
mkdir -p -- "$target/docs/rea" "$target/research/camera-sensors/reports" \
    "$target/research/camera-sensors/raw" "$target/research/camera-sensors/private" \
    "$target/scripts" "$target/configs" "$target/tests" "$target/patches"
printf 'Investigation layout ready: %s\n' "$target"
