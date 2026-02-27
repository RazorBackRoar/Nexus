# Security Ownership

Updated: 2026-02-27

## Sensitive Hotspots
- `src/nexus/core/safari.py` (`command_exec`)
- `src/nexus/core/bookmarks.py` (`local_priv_data`)
- `src/nexus/utils/url_processor.py` (`input_boundary`)

## Current Risk
- Bus factor is `1` across AppleScript command execution and Safari data parsing paths.

## Mitigations Applied
- Added explicit hotspot ownership in `.github/CODEOWNERS`.
- Existing core tests retained as required baseline:
  - `tests/core/test_safari_controller.py`
  - `tests/test_bookmarks.py`
  - `tests/utils/test_url_processor.py`

## Required to Fully Close Risk
1. Add at least one additional human maintainer for each sensitive path.
2. Enforce code-owner review requirement in branch protection.
3. Run quarterly handoff drills for Safari automation and bookmark parsing.
