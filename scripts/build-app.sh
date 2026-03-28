#!/usr/bin/env bash
set -euo pipefail

# build-app.sh — Assembles dist/Research Dashboard.app for macOS
# Prerequisites: caddy (brew install caddy), node/npm, conda env research-dashboard
# Usage: ./scripts/build-app.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
APP_DIR="$PROJECT_ROOT/dist/Research Dashboard.app"
CONTENTS_DIR="$APP_DIR/Contents"
MACOS_DIR="$CONTENTS_DIR/MacOS"
RESOURCES_DIR="$CONTENTS_DIR/Resources"

# ---------------------------------------------------------------------------
# 0. Prerequisite checks
# ---------------------------------------------------------------------------
if ! command -v caddy &>/dev/null; then
  echo "WARNING: caddy not found. The app bundle will not function without it." >&2
  echo "Install with: brew install caddy" >&2
  echo "" >&2
fi

if ! command -v npm &>/dev/null; then
  echo "ERROR: npm not found. Cannot build Next.js frontend." >&2
  exit 1
fi

if [[ ! -f "$PROJECT_ROOT/assets/app-icon.png" ]]; then
  echo "ERROR: Icon source not found at $PROJECT_ROOT/assets/app-icon.png" >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# 1. Pre-build Next.js frontend
# ---------------------------------------------------------------------------
echo "Building Next.js frontend..."
cd "$PROJECT_ROOT/web"
npm run build
cd "$PROJECT_ROOT"
echo "Next.js build complete."

# ---------------------------------------------------------------------------
# 2. Build the .icns icon
# ---------------------------------------------------------------------------
echo "Building AppIcon.icns..."
bash "$SCRIPT_DIR/build-icns.sh"

if [[ ! -f "$SCRIPT_DIR/AppIcon.icns" ]]; then
  echo "ERROR: build-icns.sh did not produce $SCRIPT_DIR/AppIcon.icns" >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# 3. Assemble the .app bundle structure
# ---------------------------------------------------------------------------
echo "Assembling $APP_DIR..."

rm -rf "$APP_DIR"
mkdir -p "$MACOS_DIR"
mkdir -p "$RESOURCES_DIR"

# ---------------------------------------------------------------------------
# 4. Write .launcher-config (project root baked at build time)
# ---------------------------------------------------------------------------
cat > "$RESOURCES_DIR/.launcher-config" <<EOF
PROJECT_ROOT=$PROJECT_ROOT
EOF

# ---------------------------------------------------------------------------
# 5. Install launcher executable
# ---------------------------------------------------------------------------
cp "$SCRIPT_DIR/launcher.sh" "$MACOS_DIR/launcher"
chmod +x "$MACOS_DIR/launcher"

# ---------------------------------------------------------------------------
# 6. Install icon
# ---------------------------------------------------------------------------
cp "$SCRIPT_DIR/AppIcon.icns" "$RESOURCES_DIR/AppIcon.icns"

# ---------------------------------------------------------------------------
# 7. Write Info.plist
# ---------------------------------------------------------------------------
cat > "$CONTENTS_DIR/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleIdentifier</key>
    <string>com.stevemeadows.research-dashboard</string>
    <key>CFBundleName</key>
    <string>Research Dashboard</string>
    <key>CFBundleDisplayName</key>
    <string>Research Dashboard</string>
    <key>CFBundleExecutable</key>
    <string>launcher</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>CFBundleVersion</key>
    <string>1</string>
    <key>LSMinimumSystemVersion</key>
    <string>12.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>LSUIElement</key>
    <false/>
</dict>
</plist>
EOF

# ---------------------------------------------------------------------------
# 8. Strip quarantine (required for macOS 15+ Sequoia — no right-click bypass)
# ---------------------------------------------------------------------------
xattr -cr "$APP_DIR"

# ---------------------------------------------------------------------------
# 9. Touch to bust macOS bundle cache (icon + metadata refresh)
# ---------------------------------------------------------------------------
touch "$APP_DIR"

echo ""
echo "Build complete: $APP_DIR"
echo ""
echo "To install system-wide (enables Spotlight):"
echo "  cp -r \"$APP_DIR\" /Applications/"
echo ""
echo "To run directly:"
echo "  open \"$APP_DIR\""
