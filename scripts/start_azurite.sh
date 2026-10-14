#!/usr/bin/env bash
# Shell script to start Azurite local emulator on Linux/macOS
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AZURITE_DIR="$SCRIPT_DIR/../.azurite"
mkdir -p "$AZURITE_DIR"

echo "=========================================================="
echo " Starting Azurite Local Azure Storage Emulator..."
echo " Location: $AZURITE_DIR"
echo " Blob Endpoint: http://127.0.0.1:10000/devstoreaccount1"
echo "=========================================================="

azurite --silent --skipApiVersionCheck --location "$AZURITE_DIR" --blobHost 127.0.0.1 --blobPort 10000
