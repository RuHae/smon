from __future__ import annotations

import json
from pathlib import Path

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "scontrol.json"


def load_scontrol_show_node_output() -> str:
    data = json.loads(FIXTURE_PATH.read_text())
    return data["show_node"]
