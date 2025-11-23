#!/bin/bash
# Definitive Build Script for Nexus v5.0.0 by RazorBackRoar
set -euo pipefail
APP_NAME="Nexus"
APP_VERSION="5.0.0"
PYTHON_EXE="$HOME/.venvs/razor/bin/python"
ICON_SOURCE="resources/Nexus.icns"
ICON_FIXED="resources/Nexus_fixed.icns"
CODESIGN_IDENTITY_DEFAULT="GitHub: RazorBackRoar"
IDENTITIES=$(security find-identity -p codesigning -v 2>/dev/null || true)
if echo "$IDENTITIES" | grep -q "${CODESIGN_IDENTITY_DEFAULT}"; then
  CODESIGN_IDENTITY="${CODESIGN_IDENTITY_DEFAULT}"
else
  CODESIGN_IDENTITY="-"
fi
BLUE='\033[0;34m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
echo -e "${BLUE}🚀 Starting build process for ${APP_NAME}...${NC}"

# Increment version
# echo -e "\n${BLUE}0. Incrementing version...${NC}"
# "$PYTHON_EXE" version_bump.py
# echo -e "   - ${GREEN}Version updated${NC}"

# Check for and eject any mounted Nexus volumes before building
if hdiutil info | grep -q "/Volumes/${APP_NAME}"; then
  echo -e "${YELLOW}⚠️  Mounted ${APP_NAME} volume detected - ejecting...${NC}"
  hdiutil detach "/Volumes/${APP_NAME}" -force 2>/dev/null || true
  sleep 1
  echo -e "   - ${GREEN}Volume ejected${NC}"
fi

echo -e "\n${BLUE}1. Verifying Python interpreter...${NC}"
if [ ! -x "$PYTHON_EXE" ]; then echo -e "${RED}❌ Error: Python not found at '${PYTHON_EXE}'.${NC}"; exit 1; fi
echo -e "   - ${GREEN}Using Python interpreter: $(${PYTHON_EXE} --version)${NC}"
echo -e "\n${BLUE}2. Installing dependencies...${NC}"
"$PYTHON_EXE" -m pip install -r requirements.txt
echo -e "   - ${GREEN}Dependencies are up to date.${NC}"
echo -e "\n${BLUE}3. Verifying and rebuilding app icon...${NC}"
if [ ! -f "$ICON_SOURCE" ]; then echo -e "${RED}❌ Error: AppIcon.icns not found.${NC}"; exit 1; fi
"$PYTHON_EXE" utils/icon_generator.py "$ICON_SOURCE" "$ICON_FIXED" && mv "$ICON_FIXED" "$ICON_SOURCE"
echo -e "   - ${GREEN}Icon processed successfully.${NC}"
echo -e "\n${BLUE}4. Cleaning build artifacts...${NC}"

# Remove build directories, app, and DMG
rm -rf build/ 2>/dev/null || true
rm -rf dist/Nexus.app 2>/dev/null || true
rm -f dist/Nexus.dmg 2>/dev/null || true
rm -f dist/Nexus_temp.dmg 2>/dev/null || true
rm -f *.dmg 2>/dev/null || true

# Remove Python cache files
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true

echo -e "   - ${GREEN}Cleanup complete${NC}"
echo -e "\n${BLUE}5. Building the .app bundle (ARM64 only)...${NC}"
"$PYTHON_EXE" setup.py py2app --arch=arm64 2>&1 | tee build.log || { echo -e "${RED}❌ Build failed.${NC}"; exit 1; }
echo -e "   - ${GREEN}Application bundle created.${NC}"
echo -e "\n${BLUE}6. Applying signature and entitlements...${NC}"
APP_PATH="dist/${APP_NAME}.app"
codesign --force --deep --sign "$CODESIGN_IDENTITY" --entitlements entitlements.plist "$APP_PATH"
echo -e "   - ${GREEN}App signed with identity:${NC} ${BLUE}${CODESIGN_IDENTITY}${NC}"
echo -e "\n${BLUE}7. Creating .dmg disk image...${NC}"
DMG_PATH="dist/${APP_NAME}.dmg"
DMG_STAGING_DIR="dist/${APP_NAME}_dmg"
DMG_TEMP="dist/${APP_NAME}_temp.dmg"
rm -f "$DMG_PATH" "$DMG_TEMP"
rm -rf "$DMG_STAGING_DIR"
mkdir -p "$DMG_STAGING_DIR"
cp -R "$APP_PATH" "$DMG_STAGING_DIR/"
cp "README.md" "$DMG_STAGING_DIR/README.txt"
cp "LICENSE.txt" "$DMG_STAGING_DIR/License.txt"
ln -s /Applications "$DMG_STAGING_DIR/Applications" || true
rm -f "$DMG_STAGING_DIR/.DS_Store"

# Create temporary DMG
hdiutil create -volname "${APP_NAME}" -srcfolder "$DMG_STAGING_DIR" -ov -format UDRW "$DMG_TEMP"

# Mount it without showing Finder
MOUNT_DIR=$(hdiutil attach "$DMG_TEMP" -nobrowse | grep "Volumes" | awk '{print $3}')

# Set window size (compact, no scrollbars)
echo '
   tell application "Finder"
     tell disk "'${APP_NAME}'"
       open
       set current view of container window to icon view
       set toolbar visible of container window to false
       set statusbar visible of container window to false
       set the bounds of container window to {100, 100, 540, 560}
       set viewOptions to the icon view options of container window
       set arrangement of viewOptions to not arranged
       set icon size of viewOptions to 80
       set position of item "'${APP_NAME}'.app" of container window to {110, 90}
       set position of item "Applications" of container window to {310, 90}
       set position of item "README.txt" of container window to {110, 260}
       set position of item "License.txt" of container window to {310, 260}
       update without registering applications
       delay 1
       close
     end tell
   end tell
' | osascript

# Unmount
hdiutil detach "$MOUNT_DIR" -force
sleep 3
# Ensure fully detached
while hdiutil info | grep -q "$MOUNT_DIR"; do
  sleep 1
done

# Convert to compressed
hdiutil convert "$DMG_TEMP" -format UDZO -o "$DMG_PATH"
rm -f "$DMG_TEMP"
rm -rf "$DMG_STAGING_DIR"

echo -e "   - ${GREEN}Disk image created successfully.${NC}"
echo -e "\n${BLUE}8. Opening DMG in Finder (window will stay open)...${NC}"
open "$DMG_PATH" || echo -e "${YELLOW}⚠️ Unable to auto-open DMG. Open it manually at '$DMG_PATH'${NC}"
echo -e "\n${GREEN}🎉 Build successful!${NC}"
APP_SIZE=$(du -sh "$APP_PATH" | cut -f1)
DMG_SIZE=$(du -sh "$DMG_PATH" | cut -f1)
echo -e "   - 📦 App Path: ${BLUE}${APP_PATH}${NC}"
echo -e "   - 📀 DMG Path: ${BLUE}${DMG_PATH}${NC}"
echo -e "   - 📊 App Size: ${BLUE}${APP_SIZE}${NC}"
echo -e "   - 📊 DMG Size: ${BLUE}${DMG_SIZE}${NC}"
echo -e "\n${GREEN}🚀 To run, use: open '${APP_PATH}'${NC}"
echo -e "${GREEN}💿 To mount DMG, use: open '${DMG_PATH}'${NC}\n"
