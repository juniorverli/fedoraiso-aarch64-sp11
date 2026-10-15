#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# Surface Pro 11 Live Wayland Camera Preview
set -euo pipefail

if [[ -z ${SURFACE_CAMERA_IGNORE_WSL:-} ]]; then
    case "$(uname -r)" in
        *[Mm]icrosoft*|*WSL*)
            echo 'Execute no Fedora físico do Surface; WSL não fornece a câmera CSI.' >&2
            exit 1
            ;;
    esac
fi

target="${1:-front}"
list_out=$(surface-cam --list 2>&1 || true)

if [[ "$target" == "front" ]]; then
    cam_id=$(echo "$list_out" | grep -iE 'imx681|camera@1a' | head -n1 | grep -oE '\([^)]+\)' | tr -d '()' || true)
    [[ -n "$cam_id" ]] || cam_id=$(echo "$list_out" | grep -iE 'front' | head -n1 | grep -oE '\([^)]+\)' | tr -d '()' || true)
    [[ -n "$cam_id" ]] || cam_id=$(echo "$list_out" | grep -iE 'imx681|camera@1a' | head -n1 | awk '{print $1}' | tr -d ':' || true)
elif [[ "$target" == "rear" ]]; then
    cam_id=$(echo "$list_out" | grep -iE 'ov13858|camera@10|camera@36' | head -n1 | grep -oE '\([^)]+\)' | tr -d '()' || true)
    [[ -n "$cam_id" ]] || cam_id=$(echo "$list_out" | grep -iE 'back|rear' | head -n1 | grep -oE '\([^)]+\)' | tr -d '()' || true)
    [[ -n "$cam_id" ]] || cam_id=$(echo "$list_out" | grep -iE 'ov13858|camera@10|camera@36' | head -n1 | awk '{print $1}' | tr -d ':' || true)
else
    cam_id="$target"
fi

if [[ "$cam_id" =~ ^[0-9]+$ ]]; then
    resolved_id=$(echo "$list_out" | grep -E "^${cam_id}:" | grep -oE '\([^)]+\)' | tr -d '()' || true)
    [[ -z "$resolved_id" ]] || cam_id="$resolved_id"
fi

if [[ -z "$cam_id" ]]; then
    echo "Não foi possível identificar a câmera '$target'. Executando surface-cam --list:" >&2
    surface-cam --list >&2
    exit 1
fi

zoom="${2:-${SURFACE_CAMERA_ZOOM:-1.0}}"

echo "Iniciando preview da câmera $cam_id no Wayland..."
export LD_LIBRARY_PATH="/opt/surface-camera/lib64${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export LIBCAMERA_IPA_MODULE_PATH="/opt/surface-camera/lib64/libcamera/ipa"
export LIBCAMERA_IPA_PROXY_PATH="/opt/surface-camera/libexec/libcamera"
export LIBCAMERA_IPA_CONFIG_PATH="/opt/surface-camera/share/libcamera/ipa"
export GST_PLUGIN_PATH="/opt/surface-camera/lib64/gstreamer-1.0${GST_PLUGIN_PATH:+:$GST_PLUGIN_PATH}"

crop_pipeline=""
if python3 -c "import sys; sys.exit(0 if float('$zoom') > 1.0 else 1)" 2>/dev/null; then
    if gst-inspect-1.0 videocrop >/dev/null 2>&1; then
        read -r crop_x crop_y <<< $(python3 -c "
z = float('$zoom')
w, h = 1920, 1080
cx = int((w - w/z) / 2)
cy = int((h - h/z) / 2)
print(f'{cx} {cy}')
")
        crop_pipeline="! videocrop left=$crop_x right=$crop_x top=$crop_y bottom=$crop_y ! videoscale"
        echo "Aplicando zoom digital de ${zoom}x (recorte central para webcam normal)..."
    fi
fi

if gst-inspect-1.0 bayer2rgb >/dev/null 2>&1; then
    eval "exec gst-launch-1.0 -e libcamerasrc camera-name=\"\$cam_id\" ! bayer2rgb ! videoconvert $crop_pipeline ! waylandsink"
else
    eval "exec gst-launch-1.0 -e libcamerasrc camera-name=\"\$cam_id\" ! videoconvert $crop_pipeline ! waylandsink"
fi
