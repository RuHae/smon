#!/usr/bin/env python3
"""Generate deterministic README screenshots for all color schemes."""

import argparse
import asyncio
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = Path(__file__).resolve()

MAIN_SCREENSHOT = ("default", REPO_ROOT / "docs/smon-screenshot.svg")

GALLERY_OUTPUTS: list[tuple[str, Path]] = [
    ("default", REPO_ROOT / "docs/smon-theme-default.svg"),
    ("ocean", REPO_ROOT / "docs/smon-theme-ocean.svg"),
    ("sunset", REPO_ROOT / "docs/smon-theme-sunset.svg"),
    ("graphite", REPO_ROOT / "docs/smon-theme-graphite.svg"),
]

MAIN_SIZE = (170, 45)
GALLERY_SIZE = (136, 34)


def _build_render_env(xdg_config_home: str) -> dict[str, str]:
    """Build env for deterministic colorful screenshot rendering."""
    env = os.environ.copy()
    env.pop("NO_COLOR", None)
    env["TERM"] = "xterm-256color"
    env["COLORTERM"] = "truecolor"
    env["PY_COLORS"] = "1"
    env["SMON_FAKE_DATA"] = "1"
    env["XDG_CONFIG_HOME"] = xdg_config_home
    return env


def _write_theme_config(xdg_config_home: Path, theme: str) -> None:
    config_dir = xdg_config_home / "smon"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "config.toml"
    config_path.write_text(f'color_scheme = "{theme}"\n', encoding="utf-8")


async def _capture_single(output: Path, width: int, height: int) -> None:
    """Capture one screenshot using the current env/config."""
    sys.path.insert(0, str(REPO_ROOT / "src"))
    from rich.terminal_theme import MONOKAI  # noqa: E402
    from main import SlurmDashboard  # noqa: E402

    app = SlurmDashboard()
    app.ansi_theme_dark = MONOKAI
    app.ansi_theme_light = MONOKAI

    output.parent.mkdir(parents=True, exist_ok=True)
    async with app.run_test(size=(width, height)) as pilot:
        await pilot.pause(1.2)
        app.save_screenshot(filename=output.name, path=str(output.parent))

    print(output.relative_to(REPO_ROOT))


def _run_single_capture(theme: str, output: Path, size: tuple[int, int]) -> None:
    """Run a single themed capture in a fresh subprocess."""
    width, height = size
    with tempfile.TemporaryDirectory(prefix="smon-screenshot-") as temp_dir:
        xdg_config_home = Path(temp_dir)
        _write_theme_config(xdg_config_home, theme)

        cmd = [
            sys.executable,
            str(SCRIPT_PATH),
            "--capture-single",
            "--output",
            str(output),
            "--width",
            str(width),
            "--height",
            str(height),
        ]
        subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            env=_build_render_env(str(xdg_config_home)),
            check=True,
        )


def _capture_all() -> None:
    # Main README screenshot (larger)
    _run_single_capture(MAIN_SCREENSHOT[0], MAIN_SCREENSHOT[1], MAIN_SIZE)

    # Theme gallery screenshots (smaller)
    for theme, output in GALLERY_OUTPUTS:
        _run_single_capture(theme, output, GALLERY_SIZE)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate README screenshots for all supported themes."
    )
    parser.add_argument(
        "--capture-single",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output path for single-capture mode.",
    )
    parser.add_argument(
        "--width",
        type=int,
        help="Render width for single-capture mode.",
    )
    parser.add_argument(
        "--height",
        type=int,
        help="Render height for single-capture mode.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if args.capture_single:
        if args.output is None or args.width is None or args.height is None:
            raise SystemExit(
                "--output, --width, and --height are required with --capture-single"
            )
        output = args.output
        if not output.is_absolute():
            output = REPO_ROOT / output
        asyncio.run(_capture_single(output, args.width, args.height))
        return

    _capture_all()


if __name__ == "__main__":
    main()
