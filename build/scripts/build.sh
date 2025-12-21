#!/bin/bash
# Definitive Build Script for Nexus by RazorBackRoar
set -euo pipefail

APP_NAME="Nexus"

# Use system Python 3.13 directly - no virtual environment
PYTHON_EXE="/opt/homebrew/bin/python3.13"

if [ ! -x "$PYTHON_EXE" ]; then
  echo "❌ Python 3.13 not found at $PYTHON_EXE"
  exit 1
fi

get_pyproject_version() {
  "$PYTHON_EXE" - <<'PY'
import pathlib, re, sys
pyproject = pathlib.Path('pyproject.toml')
if not pyproject.exists():
    sys.exit('pyproject.toml not found')
match = re.search(r'version\s*=\s*"([^"\n]+)"', pyproject.read_text(encoding='utf-8'))
if not match:
    sys.exit('Unable to locate version in pyproject.toml')
print(match.group(1))
PY
}

APP_VERSION="$(get_pyproject_version)"
ICON_SOURCE="assets/icons/Nexus.icns"
ICON_FIXED="assets/icons/Nexus_fixed.icns"
CODESIGN_IDENTITY="-"

BLUE='\033[0;34m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
echo -e "${BLUE}🚀 Starting build process for ${APP_NAME} v${APP_VERSION}...${NC}"
echo -e "${YELLOW}📌 Using Python: $($PYTHON_EXE --version)${NC}"

# Check for and eject any mounted Nexus volumes before building
if hdiutil info | grep -q "/Volumes/${APP_NAME}"; then
  echo -e "${YELLOW}⚠️  Mounted ${APP_NAME} volume detected - ejecting...${NC}"
  hdiutil detach "/Volumes/${APP_NAME}" -force 2>/dev/null || true
  sleep 1
fi

echo -e "\n${BLUE}1. Installing dependencies...${NC}"
"$PYTHON_EXE" -m pip install -r requirements.txt -q
echo -e "   - ${GREEN}Dependencies ready${NC}"

echo -e "\n${BLUE}2. Verifying app icon...${NC}"
if [ ! -f "$ICON_SOURCE" ]; then echo -e "${RED}❌ Error: AppIcon.icns not found.${NC}"; exit 1; fi
"$PYTHON_EXE" src/scripts/icon_generator.py "$ICON_SOURCE" "$ICON_FIXED" && mv "$ICON_FIXED" "$ICON_SOURCE"
echo -e "   - ${GREEN}Icon processed${NC}"

echo -e "\n${BLUE}3. Cleaning build artifacts...${NC}"
rm -rf build/temp Nexus.egg-info/ 2>/dev/null || true
rm -rf build/dist/Nexus.app build/dist/Nexus_dmg build/dist/Nexus.dmg 2>/dev/null || true
rm -f *.dmg 2>/dev/null || true
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
echo -e "   - ${GREEN}Cleanup complete${NC}"

echo -e "\n${BLUE}4. Building .app bundle (ARM64)...${NC}"
"$PYTHON_EXE" setup.py py2app --arch=arm64 2>&1 | tee build/build.log || { echo -e "${RED}❌ Build failed.${NC}"; exit 1; }
echo -e "   - ${GREEN}Application bundle created${NC}"

echo -e "\n${BLUE}5. Signing app...${NC}"
APP_PATH="build/dist/${APP_NAME}.app"
codesign --force --deep --sign "$CODESIGN_IDENTITY" --entitlements src/nexus/config/entitlements.plist "$APP_PATH"
echo -e "   - ${GREEN}App signed${NC}"

echo -e "\n${BLUE}6. Creating DMG...${NC}"
DMG_PATH="build/dist/${APP_NAME}.dmg"
DMG_STAGING_DIR="build/dist/${APP_NAME}_dmg"
DMG_TEMP="build/dist/${APP_NAME}_temp.dmg"
rm -f "$DMG_PATH" "$DMG_TEMP"
rm -rf "$DMG_STAGING_DIR"
mkdir -p "$DMG_STAGING_DIR"
cp -R "$APP_PATH" "$DMG_STAGING_DIR/"
ln -s /Applications "$DMG_STAGING_DIR/Applications" || true
rm -f "$DMG_STAGING_DIR/.DS_Store"

hdiutil create -volname "${APP_NAME}" -srcfolder "$DMG_STAGING_DIR" -ov -format UDRW "$DMG_TEMP"

echo -e "   - ${BLUE}🎨 Styling DMG window...${NC}"
DEVICE=$(hdiutil attach -readwrite -noverify -noautoopen "$DMG_TEMP" | egrep '^/dev/' | sed 1q | awk '{print $1}')
sleep 2

osascript <<EOF
tell application "Finder"
    tell disk "${APP_NAME}"
        open
        delay 1
        set current view of container window to icon view
        set toolbar visible of container window to false
        set statusbar visible of container window to false
        set the bounds of container window to {200, 200, 680, 540}
        set theViewOptions to the icon view options of container window
        set arrangement of theViewOptions to not arranged
        set icon size of theViewOptions to 100
        set position of item "${APP_NAME}.app" of container window to {120, 120}
        set position of item "Applications" of container window to {360, 120}
        update without registering applications
        delay 1
        close
    end tell
end tell
EOF

hdiutil detach "$DEVICE" -force
hdiutil convert "$DMG_TEMP" -format UDZO -o "$DMG_PATH"
rm -f "$DMG_TEMP"
rm -rf "$DMG_STAGING_DIR"

echo -e "   - ${GREEN}DMG created${NC}"

echo -e "\n${BLUE}7. Cleanup...${NC}"
rm -rf "$APP_PATH" build/temp Nexus.egg-info/
echo -e "   - ${GREEN}Build artifacts removed${NC}"

DMG_SIZE=$(du -sh "$DMG_PATH" | cut -f1)
echo -e "\n${GREEN}🎉 Build successful!${NC}"
echo -e "   - 📀 DMG: ${BLUE}${DMG_PATH}${NC} (${DMG_SIZE})"
echo -e "\n${GREEN}💿 To install: open '${DMG_PATH}'${NC}\n"
