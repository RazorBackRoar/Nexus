#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR/.."
APP_NAME="Nexus"
BUNDLE_ID="com.razorbackroar.nexus.app"
VERSION="$(sed -n 's/.*"version".*"\([^"]*\)".*/\1/p' "$PROJECT_DIR/Sources/Nexus/Resources/version.json")"

RELEASE_DIR="$PROJECT_DIR/build/Release"
APP_PATH="$RELEASE_DIR/$APP_NAME.app"
DMG_PATH="$RELEASE_DIR/$APP_NAME.dmg"
EXEC_PATH="$PROJECT_DIR/.build/release/$APP_NAME"
ICON_SOURCE="$PROJECT_DIR/assets/icons/Nexus.icns"
RAZORCORE_DIR="$(cd "$SCRIPT_DIR/../../.razorcore" && pwd)"

echo "Building Nexus ${VERSION}..."
cd "$PROJECT_DIR"
swift build -c release

echo "Packaging $APP_NAME.app..."
rm -rf "$APP_PATH"
mkdir -p "$APP_PATH/Contents/MacOS" "$APP_PATH/Contents/Resources"
cp "$EXEC_PATH" "$APP_PATH/Contents/MacOS/$APP_NAME"
cp "$PROJECT_DIR/Sources/Nexus/Resources/version.json" "$APP_PATH/Contents/Resources/version.json"
if [[ -f "$ICON_SOURCE" ]]; then
    cp "$ICON_SOURCE" "$APP_PATH/Contents/Resources/AppIcon.icns"
fi
RESOURCE_BUNDLE="$PROJECT_DIR/.build/release/${APP_NAME}_${APP_NAME}.bundle"
if [[ -d "$RESOURCE_BUNDLE" ]]; then
    cp -R "$RESOURCE_BUNDLE" "$APP_PATH/Contents/Resources/"
fi

cat > "$APP_PATH/Contents/Info.plist" <<PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>$APP_NAME</string>
    <key>CFBundleDisplayName</key>
    <string>$APP_NAME</string>
    <key>CFBundleIdentifier</key>
    <string>$BUNDLE_ID</string>
    <key>CFBundleVersion</key>
    <string>$VERSION</string>
    <key>CFBundleShortVersionString</key>
    <string>$VERSION</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>CFBundleExecutable</key>
    <string>$APP_NAME</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>LSMinimumSystemVersion</key>
    <string>14.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSAppleEventsUsageDescription</key>
    <string>Nexus opens links in Safari and reads the titles and addresses of your open tabs when you ask it to.</string>
    <key>NSAccessibilityUsageDescription</key>
    <string>Nexus uses Accessibility only to open a Safari Private window. Without it, private opens stop instead of falling back to a normal window.</string>
    <key>NSHumanReadableCopyright</key>
    <string>Copyright © $(date +%Y) RazorBackRoar. All rights reserved.</string>
</dict>
</plist>
PLIST_EOF

chmod +x "$APP_PATH/Contents/MacOS/$APP_NAME"
xattr -cr "$APP_PATH"
"$RAZORCORE_DIR/patch-app-branding.sh" "$APP_PATH"
codesign --force --deep --sign - "$APP_PATH"

mkdir -p "$RELEASE_DIR"
"$RAZORCORE_DIR/package-dmg.sh" \
  --app "$APP_PATH" \
  --dmg "$DMG_PATH" \
  --app-name "$APP_NAME" \
  --volname "$APP_NAME"

rm -rf "$APP_PATH" "$RELEASE_DIR/.previous-build"
echo "Build complete: $DMG_PATH and ${HOME}/Desktop/${APP_NAME}.dmg"
