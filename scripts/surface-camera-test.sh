#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# Surface Pro 11 Camera Diagnostic and Capture Test
# Validates sensor modules, CAMSS enumeration, and executes test captures.
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo -e "${BOLD}${BLUE}=== Surface Pro 11: Camera Verification Suite ===${NC}"

# Refuse WSL environment where CSI physical path is unavailable
if [[ -z ${SURFACE_CAMERA_IGNORE_WSL:-} ]]; then
    case "$(uname -r)" in
        *[Mm]icrosoft*|*WSL*)
            echo -e "${RED}[ERROR] WSL environment detected.${NC}" >&2
            echo "Physical MIPI CSI cameras are only accessible on bare-metal Fedora on Surface Pro 11." >&2
            exit 1
            ;;
    esac
fi

# 1. Kernel and driver check
running_kver=$(uname -r)
echo -e "\n${BOLD}${BLUE}[1/4] Checking kernel and drivers...${NC}"
echo "Running kernel: $running_kver"

case "$running_kver" in
    *sp11-exp*|*camera*|*x1p1*)
        echo -e "  Kernel profile: ${GREEN}Camera-enabled Surface candidate${NC}"
        ;;
    *)
        echo -e "  Kernel profile: ${YELLOW}Stock or safe fallback kernel${NC}"
        echo -e "  ${YELLOW}Notice: Sensor drivers (imx681) may not be present in this kernel.${NC}"
        ;;
esac

for mod in qcom_camss imx681 ov13858; do
    if lsmod 2>/dev/null | grep -q "^$mod\b"; then
        echo -e "  Module $mod: ${GREEN}loaded${NC}"
    else
        echo -e "  Module $mod: ${YELLOW}not loaded, attempting modprobe...${NC}"
        sudo -n modprobe "$mod" 2>/dev/null || modprobe "$mod" 2>/dev/null || true
        if lsmod 2>/dev/null | grep -q "^$mod\b"; then
            echo -e "  Module $mod: ${GREEN}loaded successfully${NC}"
        else
            echo -e "  Module $mod: ${YELLOW}not present in running kernel (check kernel profile)${NC}"
        fi
    fi
done

# 2. Camera enumeration via surface-cam
echo -e "\n${BOLD}${BLUE}[2/4] Enumerating cameras via surface-cam...${NC}"
if ! command -v surface-cam >/dev/null 2>&1; then
    echo -e "${RED}[ERROR] surface-cam command not found in PATH.${NC}" >&2
    exit 1
fi

list_output=$(surface-cam --list 2>&1) || {
    echo -e "${RED}[FAIL] surface-cam --list failed with status $?:${NC}"
    echo "$list_output"
    exit 1
}

echo "$list_output"

# Identify Front (IMX681) and Rear (OV13858) IDs
front_id=$(echo "$list_output" | grep -iE 'imx681|camera@1a' | head -n1 | awk '{print $1}' | tr -d ':' || true)
rear_id=$(echo "$list_output" | grep -iE 'ov13858|camera@10' | head -n1 | awk '{print $1}' | tr -d ':' || true)

if [[ -z "$front_id" ]]; then
    front_id=$(echo "$list_output" | grep -oE '\([^\)]*camera@1a\)' | tr -d '()' | head -n1 || true)
fi
if [[ -z "$rear_id" ]]; then
    rear_id=$(echo "$list_output" | grep -oE '\([^\)]*camera@10\)' | tr -d '()' | head -n1 || true)
fi

echo -e "\n${BOLD}Enumeration Result:${NC}"
if [[ -n "$front_id" ]]; then
    echo -e "  Front Camera (IMX681):  ${GREEN}$front_id${NC}"
else
    echo -e "  Front Camera (IMX681):  ${YELLOW}Not detected${NC}"
fi

if [[ -n "$rear_id" ]]; then
    echo -e "  Rear Camera  (OV13858): ${GREEN}$rear_id${NC}"
else
    echo -e "  Rear Camera  (OV13858): ${YELLOW}Not detected${NC}"
fi

if [[ -z "$front_id" && -z "$rear_id" ]]; then
    echo -e "\n${YELLOW}[WARN] No Surface cameras were enumerated by libcamera.${NC}"
    echo "Possible causes:"
    echo "  1. Running an unsupported kernel (current kernel: $(uname -r))."
    echo "  2. Sensor hardware not powered or probe error in CAMSS."
    echo "     Check kernel log: sudo dmesg | grep -iE 'camss|imx681|ov13858|csi'"
    exit 2
fi

# 3. Test capture
timestamp=$(date -u +%Y%m%dT%H%M%SZ)
target_dir="${SURFACE_CAMERA_CAPTURE_DIR:-$HOME/surface-camera-test-$timestamp}"
mkdir -m 700 -p "$target_dir"
echo -e "\n${BOLD}${BLUE}[3/4] Running capture validation (saving frames to $target_dir)...${NC}"

test_sensor() {
    local label="$1"
    local cam_id="$2"
    local sensor_dir="$target_dir/$label"
    mkdir -m 700 -p "$sensor_dir"

    echo -e "\n${BOLD}Testing ${label^^} camera ($cam_id)...${NC}"

    # Query info
    echo "  - Querying camera stream info..."
    if timeout --signal=INT --kill-after=5 15 surface-cam --camera "$cam_id" --info > "$sensor_dir/info.log" 2>&1; then
        echo -e "    ${GREEN}[PASS] Stream formats and properties retrieved${NC}"
    else
        echo -e "    ${RED}[FAIL] Could not retrieve camera stream info${NC}"
        return 1
    fi

    # RAW capture (3 frames)
    echo "  - Capturing 3 RAW frames..."
    if timeout --signal=INT --kill-after=5 30 surface-cam --camera "$cam_id" \
        --stream role=raw --capture=3 --metadata \
        --file="$sensor_dir/raw-#.bin" > "$sensor_dir/raw.log" 2>&1; then
        raw_count=$(ls -1 "$sensor_dir"/raw-*.bin 2>/dev/null | wc -l)
        if (( raw_count >= 3 )); then
            echo -e "    ${GREEN}[PASS] RAW capture completed ($raw_count frames)${NC}"
        else
            echo -e "    ${RED}[FAIL] Expected 3 RAW frames, got $raw_count${NC}"
        fi
    else
        echo -e "    ${RED}[FAIL] RAW capture command failed or timed out${NC}"
    fi

    # Viewfinder RGB888 PPM capture (3 frames)
    echo "  - Capturing 3 Viewfinder (PPM) frames..."
    if timeout --signal=INT --kill-after=5 30 surface-cam --camera "$cam_id" \
        --stream role=viewfinder,pixelformat=RGB888 --capture=3 --metadata \
        --file="$sensor_dir/preview-#.ppm" > "$sensor_dir/preview.log" 2>&1; then
        ppm_count=$(ls -1 "$sensor_dir"/preview-*.ppm 2>/dev/null | wc -l)
        if (( ppm_count >= 3 )); then
            echo -e "    ${GREEN}[PASS] Viewfinder PPM capture completed ($ppm_count frames)${NC}"
            # Verify PPM format
            python3 - "$sensor_dir" <<'PY' || true
from pathlib import Path
import sys
for p in sorted(Path(sys.argv[1]).glob('preview-*.ppm')):
    with p.open('rb') as f:
        magic = f.readline()
        if magic != b'P6\n':
            print(f'    Warning: Invalid PPM magic in {p.name}: {magic}')
            continue
        dims = f.readline().split()
        w, h = int(dims[0]), int(dims[1])
        depth = f.readline()
        size = p.stat().st_size
        print(f'    Validated {p.name}: {w}x{h} ({size} bytes)')
PY
        else
            echo -e "    ${RED}[FAIL] Expected 3 PPM frames, got $ppm_count${NC}"
        fi
    else
        echo -e "    ${RED}[FAIL] Viewfinder capture failed or timed out${NC}"
    fi
}

if [[ -n "$front_id" ]]; then
    test_sensor "front" "$front_id" || true
fi

if [[ -n "$rear_id" ]]; then
    test_sensor "rear" "$rear_id" || true
fi

# 4. Telemetry and journal logs
echo -e "\n${BOLD}${BLUE}[4/4] Collecting kernel journal and checksums...${NC}"
sudo -n journalctl -k -b -n 250 --no-pager > "$target_dir/journal-kernel.log" 2>&1 || journalctl -k -b -n 250 --no-pager > "$target_dir/journal-kernel.log" 2>&1 || true

(cd "$target_dir" && sha256sum */*.bin */*.ppm */*.log 2>/dev/null > SHA256SUMS.txt || true)

echo -e "\n${BOLD}${GREEN}=== Camera Verification Complete ===${NC}"
echo "Evidence directory: $target_dir"
if [[ -f "$target_dir/SHA256SUMS.txt" && -s "$target_dir/SHA256SUMS.txt" ]]; then
    echo "Captured files:"
    cat "$target_dir/SHA256SUMS.txt"
fi
