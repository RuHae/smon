#!/usr/bin/env python3
"""Generate a deterministic README screenshot with colorful fake data."""

import asyncio
import os
import sys
from pathlib import Path

# Force colorful rendering in CI and remote shells where NO_COLOR/TERM=dumb is set.
os.environ.pop("NO_COLOR", None)
os.environ["TERM"] = "xterm-256color"
os.environ["COLORTERM"] = "truecolor"
os.environ["PY_COLORS"] = "1"
os.environ["SMON_FAKE_DATA"] = "1"

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from rich.terminal_theme import MONOKAI  # noqa: E402
from main import SlurmDashboard  # noqa: E402


async def _capture() -> None:
    app = SlurmDashboard()
    app.ansi_theme_dark = MONOKAI
    app.ansi_theme_light = MONOKAI

    output = Path("docs/smon-screenshot.svg")
    output.parent.mkdir(parents=True, exist_ok=True)

    async with app.run_test(size=(170, 45)) as pilot:
        await pilot.pause(1.2)
        app.save_screenshot(filename=output.name, path=str(output.parent))

    print(output)


if __name__ == "__main__":
    asyncio.run(_capture())
