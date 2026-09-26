# Building a DMG for Nexus

Nexus ships through `scripts/build-mac.sh`, which calls the shared RazorBackRoar branding and DMG scripts. The app is Swift 6 / SwiftUI. It is not a PyInstaller build.

## Quick build

From the Nexus repository root:

```bash
./scripts/build-mac.sh
# or: razorbuild Nexus
```

## Troubleshooting

| Symptom | What to try |
|---------|-------------|
| Safari automation blocked | System Settings → Privacy & Security → Automation |
| Private window does not open | Enable Accessibility for Nexus. Do not fall back to a standard window. |
| DMG layout check fails | The shared packager locks a 500×420 window and 128px icons. Do not fork a custom layout. |

## Related docs

- [BUILD_AND_RELEASE.md](../BUILD_AND_RELEASE.md)
