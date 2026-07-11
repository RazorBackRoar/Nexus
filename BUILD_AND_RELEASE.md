# Build & Release — Nexus

Organization-standard build and release guide for
[RazorBackRoar/Nexus](https://github.com/RazorBackRoar/Nexus).

## Overview

Nexus is a native macOS app built with **Python 3.14**, **uv**, and
**PySide6**, packaged as an Apple Silicon `.app` / `.dmg`.

## Platform Requirements

| Requirement | Value |
|-------------|-------|
| OS | macOS 12+ (Apple Silicon recommended) |
| Arch | `arm64` |
| Python | **3.14** (uv-managed) |
| Package manager | [uv](https://github.com/astral-sh/uv) — do not use `pip` / `venv` |

## Prerequisites

```zsh
# Install uv if needed: https://docs.astral.sh/uv/
cd /path/to/Nexus
uv sync
```

In the RazorBackRoar workspace layout, `Apps/.razorcore` is an editable sibling
dependency providing shared `razorcore` tooling.

## Development Build

```zsh
uv sync
uv run python -m nexus.main
```

### Quality gates

```zsh
uv run ruff check .
uv run ty check src --python-version 3.14
uv run pytest tests/ -q
```

CI on `main` runs the same quality job (see `.github/workflows/ci.yml`).

## Packaging

Preferred (workspace tooling):

```zsh
razorbuild Nexus
# Output: dist/Nexus.dmg
```

`razorbuild` runs the shared PyInstaller + DMG pipeline used by other Python
RazorBackRoar apps.

## Release Process

1. Ensure `main` is green (CI) and the working tree is clean.
2. Confirm the version in `pyproject.toml` matches the intended release.
3. Build the DMG (`razorbuild Nexus`).
4. Smoke-test the `.app` (launch, core happy path, quit cleanly).
5. Create a GitHub Release on
   [RazorBackRoar/Nexus/releases](https://github.com/RazorBackRoar/Nexus/releases)
   and attach `dist/Nexus.dmg`.
6. Tag the release to match the version (for example `vX.Y.Z`).

## Versioning Expectations

- Semantic Versioning (`MAJOR.MINOR.PATCH`) in `pyproject.toml`.
- Manifest files are the source of truth — do not hand-edit version strings in
  unrelated docs during a normal save/release flow.
- Workspace version sync may update `Apps/Docs/CONTEXT.md`; keep tables aligned.

## Troubleshooting

| Symptom | What to try |
|---------|-------------|
| `uv sync` fails resolving `razorcore` | Ensure sibling `Apps/.razorcore` exists, or use the CI vendor wheel path documented in `ci/` |
| Gatekeeper blocks first launch | Right-click → **Open** (ad-hoc signed builds) |
| PyInstaller missing modules | Rebuild with a clean `dist/` / `build/`; check `*.spec` excludes |
| Tests fail under QThread | Ensure a `QCoreApplication` fixture exists for the suite |

## Related Docs

- [README.md](README.md) — product overview
- [CONTRIBUTING.md](CONTRIBUTING.md) — PR workflow
- [SECURITY.md](SECURITY.md) — vulnerability reporting
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) — community standards
