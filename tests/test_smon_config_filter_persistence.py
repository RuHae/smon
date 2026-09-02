from __future__ import annotations

from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib

from smon_config import DASHBOARD_VERSION, SmonConfig, save_filter_state
from smon_version import SMON_VERSION


def test_filter_state_survives_config_reload(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    config_path = SmonConfig.get_config_path()
    config_path.parent.mkdir(parents=True)
    config_path.write_text("refresh_interval = 240\n", encoding="utf-8")

    save_filter_state("28cox", "tsfm-t2", config_path=config_path)

    persisted = tomllib.loads(config_path.read_text(encoding="utf-8"))
    assert persisted["refresh_interval"] == 240
    assert persisted["filter"] == {"user": "28cox", "prefix": "tsfm-t2"}

    restored = SmonConfig.load()
    assert restored.saved_filter_user == "28cox"
    assert restored.saved_filter_prefix == "tsfm-t2"


def test_visible_version_matches_project_version():
    project_file = Path(__file__).resolve().parents[1] / "pyproject.toml"
    project = tomllib.loads(project_file.read_text(encoding="utf-8"))

    assert SMON_VERSION == project["project"]["version"]
    assert DASHBOARD_VERSION == f"v{SMON_VERSION}"
