# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Bottom vim-style statusline with persistent mode indicator (`NORMAL` / `EDIT`).
- Keyboard shortcut manual (`?`) with immediate focus and vim/arrow scrolling.
- Pane layout control mode and pane focus/navigation enhancements.

### Changed
- Updated keybinding model to emphasize vim-style navigation and mode-based controls.
- Reduced non-critical popups to keep the UI less disruptive.
- Updated README to reflect current features, controls, and usage.

### Fixed
- PyInstaller build now includes Rich unicode data submodules for standalone binary runtime.
- Removed duplicate `main.py` app block and kept one canonical app definition/entrypoint.

## [0.1.0] - 2026-02-20

### Added
- Initial `smon` release.
