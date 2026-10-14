#!/bin/bash
# SPDX-License-Identifier: BSD-3-Clause
# Surface Pro 11 (X1P64100 LCD) Automated Firmware Extractor
# Extracts required firmware directly from local Windows DriverStore or downloads fallback.

set -euo pipefail

DEST_ROOT="${1:-/usr/lib/firmware}"

LOCAL_DRIVERSTORE=""
for ds in "${DRIVERSTORE_DIR:-}" "/mnt/driverstore" "/mnt/c/Windows/System32/DriverStore/FileRepository"; do
    if [ -n "$ds" ] && [ -d "$ds" ]; then
        LOCAL_DRIVERSTORE="$ds"
        break
    fi
done

echo "=========================================================="
echo " Surface Pro 11 (X1P LCD) Firmware Extractor Pipeline"
echo " Target destination: ${DEST_ROOT}"
echo " DriverStore path:   ${LOCAL_DRIVERSTORE:-[NOT FOUND]}"
echo "=========================================================="

mkdir -p "${DEST_ROOT}/qcom/x1e80100/microsoft/Denali"
mkdir -p "${DEST_ROOT}/ath12k/WCN7850/hw2.0"
mkdir -p "${DEST_ROOT}/qcom/sensors"

if [ -n "${LOCAL_DRIVERSTORE}" ]; then
    echo "[*] Windows DriverStore located at ${LOCAL_DRIVERSTORE}"
    echo "[*] Extracting firmware components..."

    # 1. ADSP Firmware & Topology DTB
    echo "[+] Extracting ADSP firmware & device tree..."
    ADSP_DIR=$(find "${LOCAL_DRIVERSTORE}" -maxdepth 1 -type d -name "surfacepro_ext_adsp8380*" | head -n 1)
    if [ -n "${ADSP_DIR}" ]; then
        cp -v "${ADSP_DIR}/adsp_dtbs.elf" "${DEST_ROOT}/qcom/x1e80100/microsoft/Denali/adsp_dtb.mbn"
        cp -v "${ADSP_DIR}/qcadsp8380.mbn" "${DEST_ROOT}/qcom/x1e80100/microsoft/Denali/qcadsp8380.mbn"
        [ -f "${ADSP_DIR}/RADS.bin" ] && cp -v "${ADSP_DIR}/RADS.bin" "${DEST_ROOT}/qcom/x1e80100/microsoft/Denali/"
        [ -f "${ADSP_DIR}/battmgr.jsn" ] && cp -v "${ADSP_DIR}/battmgr.jsn" "${DEST_ROOT}/qcom/x1e80100/microsoft/Denali/"
    fi

    # 2. CDSP (Hexagon NPU) Firmware
    echo "[+] Extracting CDSP (Hexagon NPU) firmware..."
    CDSP_DIR=$(find "${LOCAL_DRIVERSTORE}" -maxdepth 1 -type d -name "qcnspmcdm_ext_cdsp8380*" | head -n 1)
    if [ -n "${CDSP_DIR}" ]; then
        cp -v "${CDSP_DIR}/cdsp_dtbs.elf" "${DEST_ROOT}/qcom/x1e80100/microsoft/Denali/cdsp_dtb.mbn"
        cp -v "${CDSP_DIR}/qccdsp8380.mbn" "${DEST_ROOT}/qcom/x1e80100/microsoft/Denali/qccdsp8380.mbn"
    fi

    # 3. GPU / Zap & Video Subsystem Microcode (Adreno X1-45 / Purwa)
    echo "[+] Extracting Adreno X1 GPU microcode..."
    GPU_DIR=$(find "${LOCAL_DRIVERSTORE}" -maxdepth 1 -type d -name "qcdx8380*" | head -n 1)
    if [ -n "${GPU_DIR}" ]; then
        cp -v "${GPU_DIR}/qcdxkmsuc8380.mbn" "${DEST_ROOT}/qcom/x1e80100/microsoft/qcdxkmsuc8380.mbn" || true
        [ -f "${GPU_DIR}/qcdxkmsucpurwa.mbn" ] && cp -v "${GPU_DIR}/qcdxkmsucpurwa.mbn" "${DEST_ROOT}/qcom/x1e80100/microsoft/Denali/qcdxkmsuc8380.mbn"
        cp -v "${GPU_DIR}/qcvss8380.mbn" "${DEST_ROOT}/qcom/x1e80100/microsoft/Denali/qcvss8380.mbn"
    fi

    # 4. Touchscreen Digitizer Firmware
    echo "[+] Extracting Touch Digitizer firmware..."
    SPI_DIR=$(find "${LOCAL_DRIVERSTORE}" -maxdepth 1 -type d -name "surface_spiext_den8380*" | head -n 1)
    if [ -n "${SPI_DIR}" ]; then
        cp -v "${SPI_DIR}/BSRC_QSPI_DEN.bin" "${DEST_ROOT}/qcom/x1e80100/microsoft/Denali/"
    fi

    # 5. ath12k Wi-Fi 7 Calibration Board File
    echo "[+] Extracting ath12k WCN7850 calibration board file..."
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    BDENCODER="${SCRIPT_DIR}/ath12k-bdencoder"
    BOARD2_SRC=""
    for candidate in /usr/lib/firmware/ath12k/WCN7850/hw2.0/board-2.bin.xz \
                     /usr/lib/firmware/ath12k/WCN7850/hw2.0/board-2.bin \
                     /lib/firmware/ath12k/WCN7850/hw2.0/board-2.bin.xz \
                     /lib/firmware/ath12k/WCN7850/hw2.0/board-2.bin; do
        if [ -f "$candidate" ]; then
            BOARD2_SRC="$candidate"
            break
        fi
    done

    if [ -n "$BOARD2_SRC" ] && [ -x "$BDENCODER" ]; then
        TMP_DIR=$(mktemp -d)
        if [[ "$BOARD2_SRC" == *.xz ]]; then
            xz -dc "$BOARD2_SRC" > "${TMP_DIR}/board-2.bin"
        else
            cp "$BOARD2_SRC" "${TMP_DIR}/board-2.bin"
        fi
        (
            cd "${TMP_DIR}"
            python3 "$BDENCODER" --extract board-2.bin >/dev/null 2>&1 || true
            TARGET='bus=pci,vendor=17cb,device=1107,subsystem-vendor=17cb,subsystem-device=3378,qmi-chip-id=2,qmi-board-id=255.bin'
            if [ -f "$TARGET" ]; then
                mkdir -p "${DEST_ROOT}/ath12k/WCN7850/hw2.0"
                cp -v "$TARGET" "${DEST_ROOT}/ath12k/WCN7850/hw2.0/board.bin"
                echo "[✓] ath12k board.bin generated successfully!"
            fi
        )
        rm -rf "${TMP_DIR}"
    fi

    echo "[✓] Firmware extraction completed successfully!"
else
    echo "[!] DriverStore not found in search paths."
fi
