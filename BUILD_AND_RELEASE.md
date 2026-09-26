# Build & Release — Nexus

Organization-standard build and release guide for
[RazorBackRoar/Nexus](https://github.com/RazorBackRoar/Nexus).

## Overview

Nexus is a native macOS app built with **Swift 6** and **SwiftUI**, packaged as an Apple Silicon `.app` / `.dmg`.

## Platform Requirements

| Requirement | Value |
|-------------|-------|
| OS | macOS 14+ (Apple Silicon) |
| Arch | `arm64` |
| Language | Swift 6 (`swift-tools-version: 6.3`) |
| Package | Swift Package Manager |

## Development

```zsh
cd /path/to/Nexus
swift test
swift run
```

### Quality gates

```zsh
swift build
swift test
```

CI on `main` runs the same job (see `.github/workflows/ci.yml`).

## Packaging

```zsh
./scripts/build-mac.sh
# or: razorbuild Nexus
```

That script calls the shared `patch-app-branding.sh` and `package-dmg.sh` helpers. Nexus does not use PyInstaller or the Python `razorcore` library.

## Release Process

1. Ensure `main` is green (CI) and the working tree is clean.
2. Confirm the version in `Sources/Nexus/Resources/version.json`.
3. Build the DMG (`./scripts/build-mac.sh`).
4. Smoke-test the `.app` (launch, bookmarks, Safari open, quit cleanly).
5. Publish with `razorapps ship` after human UAT.

## Versioning

- Semantic Versioning in `Sources/Nexus/Resources/version.json` (currently 3.0.0).

## Troubleshooting

| Symptom | What to try |
|---------|-------------|
| Gatekeeper blocks first launch | Right-click → **Open** (ad-hoc signed builds) |
| Safari automation blocked | System Settings → Privacy & Security → Automation, and Accessibility for Private windows |
| `swift test` fails | Run from the Nexus repo root with the full Xcode toolchain |
