#!/bin/bash
# SPDX-License-Identifier: BSD-3-Clause
# Surface Pro 11 Camera Privacy Indicator Helper
# Dispatches camera privacy LED state commands via Surface Aggregator Module (SAM)

set -euo pipefail

STATE="${1:-off}"

# Target SAM Camera Subsystem device node
SAM_DEV="/dev/surface/aggregator"

case "${STATE}" in
    on|1)
        # Power rail VREG_CAM_AVDD_FRONT is active; signal SAM to illuminate front privacy LED
        if [ -e "${SAM_DEV}" ]; then
            # SAM target 0x01, category 0x14 (Camera/Sensor status indicator)
            echo "1" > /sys/class/leds/surface::camera_privacy/brightness 2>/dev/null || true
        fi
        ;;
    off|0)
        if [ -e "${SAM_DEV}" ]; then
            echo "0" > /sys/class/leds/surface::camera_privacy/brightness 2>/dev/null || true
        fi
        ;;
    *)
        echo "Usage: $0 {on|off}" >&2
        exit 1
        ;;
esac
