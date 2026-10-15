#!/bin/bash
# SPDX-License-Identifier: BSD-3-Clause
# Backup all original Windows drivers (Surface & Qualcomm Snapdragon X) from DriverStore.

set -euo pipefail

DEST_DIR="${1:-$HOME/surface-windows-drivers-backup}"
SRC_DRIVERSTORE="/mnt/c/Windows/System32/DriverStore/FileRepository"

if [ ! -d "$SRC_DRIVERSTORE" ]; then
    echo "[-] Erro: DriverStore do Windows não encontrado em: $SRC_DRIVERSTORE" >&2
    echo "    Certifique-se de que a partição C: está montada em /mnt/c." >&2
    exit 1
fi

echo "=========================================================="
echo " Surface Pro 11 - Backup de Drivers Originais do Windows"
echo " Origem:  $SRC_DRIVERSTORE"
echo " Destino: $DEST_DIR"
echo "=========================================================="

mkdir -p "$DEST_DIR"

echo "[*] Identificando pacotes de drivers Surface e Qualcomm..."
PACKAGE_COUNT=$(find "$SRC_DRIVERSTORE" -maxdepth 1 -type d \( -iname "*surface*" -o -iname "*qc*" -o -iname "*qcom*" -o -iname "*ath12k*" \) | wc -l)

echo "[+] Encontrados $PACKAGE_COUNT pacotes essenciais do Surface e Qualcomm."
echo "[*] Copiando drivers para $DEST_DIR..."

find "$SRC_DRIVERSTORE" -maxdepth 1 -type d \( -iname "*surface*" -o -iname "*qc*" -o -iname "*qcom*" -o -iname "*ath12k*" \) -exec cp -r -t "$DEST_DIR" {} +

echo "[✓] Cópia concluída com sucesso!"
echo "[*] Tamanho total do backup:"
du -sh "$DEST_DIR"

echo ""
echo "[!] ATENÇÃO: Se for formatar o Windows para instalar o Fedora nativamente,"
echo "    copie este diretório para um PENDRIVE ou DISCO EXTERNO antes da instalação!"
