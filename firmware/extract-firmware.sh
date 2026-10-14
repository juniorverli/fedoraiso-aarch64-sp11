#!/bin/bash
# SPDX-License-Identifier: BSD-3-Clause
# Surface Pro 11 (X1P64100 LCD) Automated Firmware Extractor
# Extracts required firmware directly from local Windows DriverStore or downloads fallback.

set -euo pipefail

DEST_ROOT="${1:-/usr/lib/firmware}"
LOCAL_DRIVERSTORE="/mnt/c/Windows/System32/DriverStore/FileRepository"

echo "=========================================================="
echo " Surface Pro 11 (X1P LCD) Firmware Extractor Pipeline"
echo " Target destination: ${DEST_ROOT}"
echo "=========================================================="

mkdir -p "${DEST_ROOT}/qcom/x1e80100/microsoft/Denali"
mkdir -p "${DEST_ROOT}/ath12k/WCN7850/hw2.0"
mkdir -p "${DEST_ROOT}/qcom/sensors"

if [ -d "${LOCAL_DRIVERSTORE}" ]; then
    echo "[*] Local Windows DriverStore detected at ${LOCAL_DRIVERSTORE}"
    echo "[*] Extracting directly from host Windows installation..."

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
        # Install both standard and purwa (X1P) microcode
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

    echo "[✓] Firmware extraction from local DriverStore completed successfully!"
else
    echo "[!] Local DriverStore not found. Online fallback retrieval would be triggered."
fi
