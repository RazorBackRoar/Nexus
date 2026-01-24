# Building DMG for Nexus

## Quick Start

```bash
./build-dmg.sh
```

## Configuration

Edit `dmg-config.json` to customize:

- Window size and position
- Icon positions
- Background image
- Volume icon
- Additional files to include

## Creating the .DS_Store Template

1. Create a test folder that matches your DMG layout
2. Arrange icons exactly as you want them
3. Close the Finder window
4. Copy the .DS_Store to dmg-template/

```bash
mkdir test-layout
cd test-layout
# Add your files and arrange them
cd ..
cp test-layout/.DS_Store dmg-template/.DS_Store
rm -rf test-layout
```

## Troubleshooting

- If window size is wrong, check `window` settings in dmg-config.json
- If icons aren't positioned, verify names in `icon_positions` match exactly
- To force AppleScript styling, remove dmg-template/.DS_Store
