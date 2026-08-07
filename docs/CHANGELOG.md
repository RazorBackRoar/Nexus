# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic
Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Capped PySide6 below v7 to prevent silent dependency breakage.

## [2.0.0] - 2026-07-16

### Added

- Quick Save column with dated URL blocks and `Ctrl+Shift+S`
- Bookmark groups with Save Group dialog and draggable rows
- Copy Rich Links (Apple Notes HTML clipboard)
- Drag-and-drop `.txt`/`.csv`/`.md` onto URL table
- Cosmic/metallic UI refresh and color-coded default tabs
- Bookmark recovery from `.bak` on load failure

### Changed

- Retired legacy sidebar tabs (`Future`, `Hey`, `Sort`)
- Widgets package split into `gui/widgets/` modules

## [1.0.0] - 2024-12-10

### Added

- Initial release
