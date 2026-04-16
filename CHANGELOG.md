# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.5.0] - 2026-04-16

### Added
- Batch kill action (`X`) to cancel all jobs matching a user and/or job name prefix at once.
  Opens a two-step flow: a criteria form (pre-filled from the active filter) followed by a
  confirmation screen showing the exact count and a preview of job IDs before executing.
- Persistent filter state: active filter (user + job name prefix) is automatically saved to
  `~/.config/smon/config.toml` under a `[filter]` section and restored on next launch.
  Filter state is per-user by nature of the XDG config path.

## [0.4.2] - 2026-02-25

### Added
- Startup-focused regression tests for duplicate job rendering scenarios in `smon_dashboard`.
- Additional `squeue` duplicate test cases in `slurm_backend` for repeated rows and repeated job IDs.

### Fixed
- Prevent duplicate job rows at startup by deduplicating job IDs before rendering the jobs table.
- Initialize jobs table columns before first data paint to avoid startup render inconsistencies.
- Ignore pre-runtime reactive compact-mode updates that could trigger redundant startup table refreshes.

## [0.4.1] - 2026-02-23

### Added
- Regression tests for GPU parsing in `slurm_backend`, including realistic `scontrol show node -o` fixture coverage and obfuscated `squeue` job cases.
- CI workflow running tests on pull requests and pushes to `main`.

### Fixed
- Correct GPU parsing for typed GRES values such as `gpu:h100:1` and `gres/gpu:h100:1` so model digits are not misread as GPU counts.
- Preserve per-node GPU semantics in job parsing (`per-node * nodes`) while keeping `gpu_total`/`total_gpu` as explicit totals.

## [0.4.0] - 2026-02-23

### Added
- Configuration file support via `~/.config/smon/config.toml` with documented example in `config.example.toml`.
- Manual refresh action (`r`) for on-demand Slurm data reloads.
- Configurable startup preferences for compact mode, default pane, and visible job columns.
- Configurable dashboard color schemes (`default`, `ocean`, `sunset`, `graphite`) via `color_scheme`.
- README theme gallery showing screenshots for all built-in color schemes.

### Changed
- Enforced HPC-conformant Slurm polling policy: default auto-refresh is now 120 seconds, with a minimum allowed interval of 120 seconds.
- Auto-refresh can be disabled for manual-only operation while keeping `r` available.
- Full jobs table columns are now configurable instead of fixed.
- Updated README with a community-tool disclaimer, HPC policy compliance notes, configuration docs, and contributor list.
- Updated help screen keybindings and README screenshot to reflect manual refresh and current behavior.
- `make screenshot` now generates all README theme screenshots in one run.
- Theme gallery screenshots now render at smaller dimensions than the main README screenshot.

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

[Unreleased]: https://github.com/RuHae/smon/compare/v0.4.2...HEAD
[0.4.2]: https://github.com/RuHae/smon/compare/v0.4.1...v0.4.2
[0.4.1]: https://github.com/RuHae/smon/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/RuHae/smon/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/RuHae/smon/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/RuHae/smon/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/RuHae/smon/releases/tag/v0.1.0
