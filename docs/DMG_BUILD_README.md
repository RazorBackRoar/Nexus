# Building a DMG for Nexus

Use the shared Apps workspace guide:
- [Docs/dmg_build_guide.md](/Users/home/Workspace/Apps/Docs/dmg_build_guide.md)

For Nexus specifically, run from `/Users/home/Workspace/Apps`:

```bash
uv run --project .razorcore razorbuild Nexus
```

If `razorbuild` is already on your `PATH`:

```bash
razorbuild Nexus
```

Repo-specific build inputs:
- [Nexus.spec](/Users/home/Workspace/Apps/Nexus/Nexus.spec)
- app assets under `assets/`

Current notes:
- the primary DMG path is the shared `razorbuild` flow, not a repo-local `build-dmg.sh`
- layout is controlled by the shared build script
- if `create-dmg` is unavailable, the build can still fall back to a plain `hdiutil` DMG without the locked Finder layout

Quick troubleshooting:
- if packaging is wrong, inspect [Nexus.spec](/Users/home/Workspace/Apps/Nexus/Nexus.spec) first
- if DMG layout is wrong, inspect [Docs/dmg_build_guide.md](/Users/home/Workspace/Apps/Docs/dmg_build_guide.md) and [.razorcore/universal-build.sh](/Users/home/Workspace/Apps/.razorcore/universal-build.sh)
- if assets are missing, verify the repo-local `assets/` inputs bundled by `Nexus.spec`
