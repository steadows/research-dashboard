#!/usr/bin/env bash
set -euo pipefail

# build-icns.sh — Converts assets/app-icon.png to scripts/AppIcon.icns
# Requires: sips (macOS built-in), iconutil (macOS built-in)
# Usage: ./scripts/build-icns.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SOURCE_PNG="$PROJECT_ROOT/assets/app-icon.png"
ICONSET_DIR="$SCRIPT_DIR/AppIcon.iconset"
OUTPUT_ICNS="$SCRIPT_DIR/AppIcon.icns"

if [[ ! -f "$SOURCE_PNG" ]]; then
  echo "ERROR: Source icon not found at $SOURCE_PNG" >&2
  exit 1
fi

echo "Building AppIcon.icns from $SOURCE_PNG..."

# Clean up any existing iconset
rm -rf "$ICONSET_DIR"
mkdir -p "$ICONSET_DIR"

# All 10 required sizes for a complete .iconset
# Format: icon_<size>x<size>[@2x].png — actual pixel dimensions shown as comments
sips -z 16   16   "$SOURCE_PNG" --out "$ICONSET_DIR/icon_16x16.png"       # 16x16 @1x
sips -z 32   32   "$SOURCE_PNG" --out "$ICONSET_DIR/icon_16x16@2x.png"    # 16x16 @2x
sips -z 32   32   "$SOURCE_PNG" --out "$ICONSET_DIR/icon_32x32.png"       # 32x32 @1x
sips -z 64   64   "$SOURCE_PNG" --out "$ICONSET_DIR/icon_32x32@2x.png"    # 32x32 @2x
sips -z 128  128  "$SOURCE_PNG" --out "$ICONSET_DIR/icon_128x128.png"     # 128x128 @1x
sips -z 256  256  "$SOURCE_PNG" --out "$ICONSET_DIR/icon_128x128@2x.png"  # 128x128 @2x
sips -z 256  256  "$SOURCE_PNG" --out "$ICONSET_DIR/icon_256x256.png"     # 256x256 @1x
sips -z 512  512  "$SOURCE_PNG" --out "$ICONSET_DIR/icon_256x256@2x.png"  # 256x256 @2x
sips -z 512  512  "$SOURCE_PNG" --out "$ICONSET_DIR/icon_512x512.png"     # 512x512 @1x
sips -z 1024 1024 "$SOURCE_PNG" --out "$ICONSET_DIR/icon_512x512@2x.png"  # 512x512 @2x

echo "Generated 10 icon sizes in $ICONSET_DIR"

iconutil -c icns "$ICONSET_DIR" -o "$OUTPUT_ICNS"

# Clean up temporary iconset directory
rm -rf "$ICONSET_DIR"

echo "Built: $OUTPUT_ICNS"
