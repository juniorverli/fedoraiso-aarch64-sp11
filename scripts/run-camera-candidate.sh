#!/usr/bin/env bash
# Run the isolated camera stack without replacing distribution libraries.
set -euo pipefail

if [[ -z ${SURFACE_CAMERA_IGNORE_WSL:-} ]]; then
    case "$(uname -r)" in
        *[Mm]icrosoft*|*WSL*)
            echo 'Execute no Fedora físico do Surface; WSL não fornece a câmera CSI.' >&2
            exit 1
            ;;
    esac
fi

repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
if [[ -n ${SURFACE_CAMERA_PREFIX:-} ]]; then
    candidate_prefix=$SURFACE_CAMERA_PREFIX
elif [[ -x /opt/surface-camera/bin/cam ]]; then
    candidate_prefix=/opt/surface-camera
else
    candidate_prefix="$repo_root/output/libcamera-integration/stage/opt/surface-camera"
fi
candidate_prefix=$(realpath -e -- "$candidate_prefix")
test -x "$candidate_prefix/bin/cam" || {
    echo 'Candidato ausente: compile ou extraia o bundle e defina SURFACE_CAMERA_PREFIX.' >&2
    exit 1
}
test -r "$candidate_prefix/share/libcamera/ipa/simple/imx681.yaml" || {
    echo 'Tuning IMX681 ausente no candidato; pare e confira o manifesto.' >&2
    exit 1
}
for required in lib64/libcamera.so.0.7 lib64/libcamera-base.so.0.7 \
    lib64/libcamera/ipa/ipa_soft_simple.so libexec/libcamera/soft_ipa_proxy; do
    test -r "$candidate_prefix/$required" || {
        echo "Candidato incompleto: $required; confira o manifesto." >&2
        exit 1
    }
done
test -x "$candidate_prefix/libexec/libcamera/soft_ipa_proxy" || exit 1

export LD_LIBRARY_PATH="$candidate_prefix/lib64${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export LIBCAMERA_IPA_MODULE_PATH="$candidate_prefix/lib64/libcamera/ipa"
export LIBCAMERA_IPA_PROXY_PATH="$candidate_prefix/libexec/libcamera"
export LIBCAMERA_IPA_CONFIG_PATH="$candidate_prefix/share/libcamera/ipa"

# No arguments enumerates only. Recording needs explicit cam capture arguments.
if (( $# == 0 )); then
    set -- --list
fi
exec "$candidate_prefix/bin/cam" "$@"
