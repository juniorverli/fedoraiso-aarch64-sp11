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
    cam_id=$(echo "$list_out" | grep -iE 'imx681|camera@1a' | head -n1 | awk '{print $1}' | tr -d ':' || true)
    [[ -n "$cam_id" ]] || cam_id=$(echo "$list_out" | grep -oE '\([^\)]*camera@1a\)' | tr -d '()' | head -n1 || true)
elif [[ "$target" == "rear" ]]; then
    cam_id=$(echo "$list_out" | grep -iE 'ov13858|camera@10' | head -n1 | awk '{print $1}' | tr -d ':' || true)
    [[ -n "$cam_id" ]] || cam_id=$(echo "$list_out" | grep -oE '\([^\)]*camera@10\)' | tr -d '()' | head -n1 || true)
else
    cam_id="$target"
fi

if [[ -z "$cam_id" ]]; then
    echo "Não foi possível identificar a câmera '$target'. Executando surface-cam --list:" >&2
    surface-cam --list >&2
    exit 1
fi

echo "Iniciando preview da câmera $cam_id no Wayland..."
export LD_LIBRARY_PATH="/opt/surface-camera/lib64${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export LIBCAMERA_IPA_MODULE_PATH="/opt/surface-camera/lib64/libcamera/ipa"
export LIBCAMERA_IPA_PROXY_PATH="/opt/surface-camera/libexec/libcamera"
export LIBCAMERA_IPA_CONFIG_PATH="/opt/surface-camera/share/libcamera/ipa"
export GST_PLUGIN_PATH="/opt/surface-camera/lib64/gstreamer-1.0${GST_PLUGIN_PATH:+:$GST_PLUGIN_PATH}"

exec gst-launch-1.0 -e libcamerasrc camera-name="$cam_id" ! videoconvert ! waylandsink
