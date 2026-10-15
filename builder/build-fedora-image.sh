#!/bin/bash
# SPDX-License-Identifier: BSD-3-Clause
# Run the Fedora 44 remix pipeline in a native AArch64 Fedora build container.
set -euo pipefail
WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ ${1:-} == --inside-container ]]; then
    exec bash "$WORKSPACE_DIR/builder/remix-fedora-workstation.sh"
fi
exec docker run --rm --privileged --platform linux/arm64 \
    -v "$WORKSPACE_DIR:/workspace" \
    -e FEDORA_BASE_ISO -e FEDORA_CHECKSUM_FILE -e SURFACE_KERNEL_SOURCE \
    -e SURFACE_KERNEL_VERSION -e SURFACE_ISO_OUTPUT -e SURFACE_RESUME_BUILD \
    fedora:44 bash /workspace/builder/build-fedora-image.sh --inside-container
