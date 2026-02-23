import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from fake_slurm_fixtures import get_fake_cluster_name

# Try tomllib (Python 3.11+), fall back to tomli
try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None  # type: ignore


DASHBOARD_TITLE = "🚀 HPC CLUSTER MONITOR"

# Minimum refresh interval enforced for cluster policy compliance
MIN_REFRESH_INTERVAL = 120

# Default refresh interval (2 minutes)
DEFAULT_REFRESH_INTERVAL = 120

# All valid job column keys
ALL_JOB_COLUMNS = [
    "id", "name", "user", "account", "state", "prio", "left",
    "gpu", "cpu", "mem", "nodes", "reason", "qos", "part", "dep", "time", "submit"
]


def _is_truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


USE_FAKE_DATA = _is_truthy(os.environ.get("SMON_FAKE_DATA"))


def get_cluster_name() -> str:
    if USE_FAKE_DATA:
        return get_fake_cluster_name()
    return subprocess.getoutput("hostname").upper()


CLUSTER_NAME = get_cluster_name()


@dataclass
class SmonConfig:
    """Runtime configuration for smon."""

    refresh_interval: int = DEFAULT_REFRESH_INTERVAL
    auto_refresh: bool = True
    compact_mode: bool = False
    default_pane: str = "jobs"
    job_columns: list[str] = field(default_factory=lambda: ALL_JOB_COLUMNS.copy())

    @classmethod
    def get_config_path(cls) -> Path:
        """Return the XDG-compliant config file path."""
        xdg_config = os.environ.get("XDG_CONFIG_HOME", "")
        if xdg_config:
            config_dir = Path(xdg_config) / "smon"
        else:
            config_dir = Path.home() / ".config" / "smon"
        return config_dir / "config.toml"

    @classmethod
    def load(cls) -> "SmonConfig":
        """Load configuration from file, with validation and defaults."""
        config = cls()
        config_path = cls.get_config_path()

        if not config_path.exists():
            return config

        if tomllib is None:
            print(
                "Warning: tomli/tomllib not available, using defaults. "
                "Install tomli for Python < 3.11.",
                file=sys.stderr,
            )
            return config

        try:
            with open(config_path, "rb") as f:
                data = tomllib.load(f)
        except Exception as e:
            print(f"Warning: Failed to parse config file: {e}", file=sys.stderr)
            return config

        # Parse refresh_interval with minimum enforcement
        if "refresh_interval" in data:
            try:
                interval = int(data["refresh_interval"])
                if interval < MIN_REFRESH_INTERVAL:
                    print(
                        f"Warning: refresh_interval={interval}s is below minimum "
                        f"({MIN_REFRESH_INTERVAL}s). Using {MIN_REFRESH_INTERVAL}s.",
                        file=sys.stderr,
                    )
                    interval = MIN_REFRESH_INTERVAL
                config.refresh_interval = interval
            except (ValueError, TypeError):
                print(
                    f"Warning: Invalid refresh_interval value, using default.",
                    file=sys.stderr,
                )

        # Parse auto_refresh
        if "auto_refresh" in data:
            config.auto_refresh = bool(data["auto_refresh"])

        # Parse compact_mode
        if "compact_mode" in data:
            config.compact_mode = bool(data["compact_mode"])

        # Parse default_pane
        if "default_pane" in data:
            pane = str(data["default_pane"]).lower()
            if pane in ("jobs", "nodes"):
                config.default_pane = pane
            else:
                print(
                    f"Warning: Invalid default_pane '{pane}', using 'jobs'.",
                    file=sys.stderr,
                )

        # Parse job_columns with validation
        if "job_columns" in data:
            columns = data["job_columns"]
            if isinstance(columns, list):
                valid_columns = []
                for col in columns:
                    col_str = str(col).lower()
                    if col_str in ALL_JOB_COLUMNS:
                        valid_columns.append(col_str)
                    else:
                        print(
                            f"Warning: Unknown job column '{col}', ignoring.",
                            file=sys.stderr,
                        )
                if valid_columns:
                    config.job_columns = valid_columns
                else:
                    print(
                        "Warning: No valid job_columns specified, using defaults.",
                        file=sys.stderr,
                    )

        return config


# Load config at module initialization
CONFIG = SmonConfig.load()

# Legacy compatibility - REFRESH_RATE now comes from config
REFRESH_RATE = float(CONFIG.refresh_interval)
