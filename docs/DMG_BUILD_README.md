# Building a DMG for Nexus

Nexus ships as `dist/Nexus.dmg` via the shared RazorBackRoar `razorbuild`
pipeline (PyInstaller + DMG packaging).

## Quick build

From the Nexus repository root:

```bash
razorbuild Nexus
# Output: dist/Nexus.dmg
```

In the Apps workspace layout, run from `Apps/` when sibling `.razorcore` is
available. Dev preview without a full DMG: `./run_preview.sh`.

## Repo-specific inputs

| File / directory | Purpose |
|------------------|---------|
| `Nexus.spec` | PyInstaller analysis, hidden imports, bundled `assets/` |
| `assets/icons/Nexus.icns` | Dock / Finder icon (may be gitignored until force-added) |
| `src/nexus/config/entitlements.plist` | AppleEvents for Safari automation |

If the packaged app fails to launch or cannot control Safari, inspect
`Nexus.spec` and entitlements before changing runtime Python code.

## Troubleshooting

| Symptom | What to try |
|---------|-------------|
| Missing PySide6 modules | `Nexus.spec` `hiddenimports` |
| Safari automation blocked | System Settings → Privacy & Security → Automation |
| `razorcore` not found locally | Sibling `../.razorcore` for dev; `ci/vendor/` wheel for CI |

## Related docs

- [BUILD_AND_RELEASE.md](../BUILD_AND_RELEASE.md)
- [docs/ARCHITECTURE.md](ARCHITECTURE.md)
