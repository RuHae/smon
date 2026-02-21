# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2026-02-21

### Added
- Interactive job filtering in the jobs pane by exact user and job-name prefix, with case-insensitive AND matching.
- Filter dialog (`/`) to set user and prefix filters, plus quick clear (`z`).
- Bottom statusline filter pill showing active filter state and visible/total job counts.

### Changed
- chore: add a dedicated fake Slurm fixture backend, GPU-heavy demo dataset, and deterministic screenshot generation for README/docs.
- Refactor the TUI from a single-file layout into focused modules:
  `main.py` (entrypoint), `smon_dashboard.py`, `smon_screens.py`, `slurm_backend.py`, `smon_clipboard.py`, and `smon_config.py`.
- Simplify imports by removing conditional fallback imports and standardizing on one module import path.
- Keep runtime behavior unchanged while improving maintainability and navigation in the codebase.
- Updated the shortcut manual and README to document filter controls and matching behavior.
- Removed filter field placeholders and reduced footer clutter by hiding pane-focus shift bindings from the bottom key hint bar while keeping the shortcuts functional.

## [0.2.0] - 2026-02-20

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

## [0.1.0] - 2026-01-30

### Added
- Initial `smon` release.

[Unreleased]: https://github.com/RuHae/smon/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/RuHae/smon/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/RuHae/smon/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/RuHae/smon/releases/tag/v0.1.0
