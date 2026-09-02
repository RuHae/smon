import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from fake_slurm_fixtures import get_fake_cluster_name
from smon_version import SMON_VERSION

# Try tomllib (Python 3.11+), fall back to tomli
try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None  # type: ignore


DASHBOARD_TITLE = f"🚀 HPC CLUSTER MONITOR v{SMON_VERSION}"

# Minimum refresh interval enforced for cluster policy compliance
MIN_REFRESH_INTERVAL = 120

# Default refresh interval (2 minutes)
DEFAULT_REFRESH_INTERVAL = 120

DEFAULT_COLOR_SCHEME = "default"

# All valid job column keys
ALL_JOB_COLUMNS = [
    "id", "name", "user", "account", "state", "prio", "left",
    "gpu", "cpu", "mem", "nodes", "reason", "qos", "part", "dep", "time", "submit"
]


COLOR_SCHEMES: dict[str, dict[str, str]] = {
    "default": {
        "brand_title": "bold cyan",
        "brand_cluster": "bold magenta",
        "brand_clock": "bold green",
        "cpu_total": "cyan",
        "cpu_active": "blue",
        "gpu_total": "magenta",
        "gpu_active": "purple",
        "pane_accent": "#64748b",
        "pane_header_bg": "#1f2937",
        "pane_header_fg": "#e5e7eb",
        "refresh_bg": "#065f46",
        "refresh_fg": "#d1fae5",
        "mode_normal_bg": "#1e3a8a",
        "mode_normal_fg": "#dbeafe",
        "status_normal_bg": "#334155",
        "status_normal_fg": "#e2e8f0",
        "footer_key_normal_bg": "#1e3a8a",
        "footer_key_normal_fg": "#dbeafe",
        "filter_normal_inactive_bg": "#1f2937",
        "filter_normal_inactive_fg": "#9ca3af",
        "filter_normal_active_bg": "#0f766e",
        "filter_normal_active_fg": "#ccfbf1",
        "mode_toggle_bg": "#f59e0b",
        "mode_toggle_fg": "#1f2937",
        "status_toggle_bg": "#7c2d12",
        "status_toggle_fg": "#ffedd5",
        "footer_key_toggle_bg": "#f59e0b",
        "footer_key_toggle_fg": "#1f2937",
        "filter_toggle_inactive_bg": "#92400e",
        "filter_toggle_inactive_fg": "#ffedd5",
        "filter_toggle_active_bg": "#facc15",
        "filter_toggle_active_fg": "#1f2937",
        "job_state_running": "green",
        "job_state_other": "yellow",
        "node_metric_ok": "green",
        "node_metric_hot": "red",
        "node_state_idle": "green",
        "node_state_bad": "red",
    },
    "ocean": {
        "brand_title": "bold #38bdf8",
        "brand_cluster": "bold #22d3ee",
        "brand_clock": "bold #34d399",
        "cpu_total": "#38bdf8",
        "cpu_active": "#0ea5e9",
        "gpu_total": "#14b8a6",
        "gpu_active": "#2dd4bf",
        "pane_accent": "#0ea5e9",
        "pane_header_bg": "#0f172a",
        "pane_header_fg": "#dbeafe",
        "refresh_bg": "#0f766e",
        "refresh_fg": "#ccfbf1",
        "mode_normal_bg": "#0c4a6e",
        "mode_normal_fg": "#e0f2fe",
        "status_normal_bg": "#1e3a5f",
        "status_normal_fg": "#dbeafe",
        "footer_key_normal_bg": "#0369a1",
        "footer_key_normal_fg": "#e0f2fe",
        "filter_normal_inactive_bg": "#1e293b",
        "filter_normal_inactive_fg": "#94a3b8",
        "filter_normal_active_bg": "#155e75",
        "filter_normal_active_fg": "#cffafe",
        "mode_toggle_bg": "#f97316",
        "mode_toggle_fg": "#1f2937",
        "status_toggle_bg": "#9a3412",
        "status_toggle_fg": "#ffedd5",
        "footer_key_toggle_bg": "#f97316",
        "footer_key_toggle_fg": "#1f2937",
        "filter_toggle_inactive_bg": "#7c2d12",
        "filter_toggle_inactive_fg": "#fed7aa",
        "filter_toggle_active_bg": "#fb923c",
        "filter_toggle_active_fg": "#431407",
        "job_state_running": "#22c55e",
        "job_state_other": "#f59e0b",
        "node_metric_ok": "#22c55e",
        "node_metric_hot": "#ef4444",
        "node_state_idle": "#34d399",
        "node_state_bad": "#f87171",
    },
    "sunset": {
        "brand_title": "bold #f59e0b",
        "brand_cluster": "bold #fb7185",
        "brand_clock": "bold #fde047",
        "cpu_total": "#f59e0b",
        "cpu_active": "#fb7185",
        "gpu_total": "#a78bfa",
        "gpu_active": "#c084fc",
        "pane_accent": "#fb7185",
        "pane_header_bg": "#3f1d2e",
        "pane_header_fg": "#ffe4e6",
        "refresh_bg": "#9a3412",
        "refresh_fg": "#ffedd5",
        "mode_normal_bg": "#7f1d1d",
        "mode_normal_fg": "#fee2e2",
        "status_normal_bg": "#4a2235",
        "status_normal_fg": "#ffe4e6",
        "footer_key_normal_bg": "#be123c",
        "footer_key_normal_fg": "#fff1f2",
        "filter_normal_inactive_bg": "#4b2838",
        "filter_normal_inactive_fg": "#fbcfe8",
        "filter_normal_active_bg": "#9d174d",
        "filter_normal_active_fg": "#fdf2f8",
        "mode_toggle_bg": "#fde047",
        "mode_toggle_fg": "#713f12",
        "status_toggle_bg": "#854d0e",
        "status_toggle_fg": "#fef3c7",
        "footer_key_toggle_bg": "#fde047",
        "footer_key_toggle_fg": "#713f12",
        "filter_toggle_inactive_bg": "#92400e",
        "filter_toggle_inactive_fg": "#ffedd5",
        "filter_toggle_active_bg": "#f97316",
        "filter_toggle_active_fg": "#431407",
        "job_state_running": "#4ade80",
        "job_state_other": "#fbbf24",
        "node_metric_ok": "#4ade80",
        "node_metric_hot": "#fb7185",
        "node_state_idle": "#86efac",
        "node_state_bad": "#fda4af",
    },
    "graphite": {
        "brand_title": "bold #d1d5db",
        "brand_cluster": "bold #9ca3af",
        "brand_clock": "bold #e5e7eb",
        "cpu_total": "#9ca3af",
        "cpu_active": "#6b7280",
        "gpu_total": "#d1d5db",
        "gpu_active": "#a3a3a3",
        "pane_accent": "#6b7280",
        "pane_header_bg": "#111827",
        "pane_header_fg": "#e5e7eb",
        "refresh_bg": "#374151",
        "refresh_fg": "#f3f4f6",
        "mode_normal_bg": "#4b5563",
        "mode_normal_fg": "#f9fafb",
        "status_normal_bg": "#1f2937",
        "status_normal_fg": "#e5e7eb",
        "footer_key_normal_bg": "#4b5563",
        "footer_key_normal_fg": "#f9fafb",
        "filter_normal_inactive_bg": "#111827",
        "filter_normal_inactive_fg": "#9ca3af",
        "filter_normal_active_bg": "#374151",
        "filter_normal_active_fg": "#f3f4f6",
        "mode_toggle_bg": "#9ca3af",
        "mode_toggle_fg": "#111827",
        "status_toggle_bg": "#3f3f46",
        "status_toggle_fg": "#fafafa",
        "footer_key_toggle_bg": "#9ca3af",
        "footer_key_toggle_fg": "#111827",
        "filter_toggle_inactive_bg": "#52525b",
        "filter_toggle_inactive_fg": "#e4e4e7",
        "filter_toggle_active_bg": "#d4d4d8",
        "filter_toggle_active_fg": "#18181b",
        "job_state_running": "#86efac",
        "job_state_other": "#fcd34d",
        "node_metric_ok": "#86efac",
        "node_metric_hot": "#fca5a5",
        "node_state_idle": "#a7f3d0",
        "node_state_bad": "#fda4af",
    },
}

AVAILABLE_COLOR_SCHEMES = sorted(COLOR_SCHEMES.keys())


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
    color_scheme: str = DEFAULT_COLOR_SCHEME
    saved_filter_user: str = ""
    saved_filter_prefix: str = ""

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
                    "Warning: Invalid refresh_interval value, using default.",
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

        # Parse color_scheme
        if "color_scheme" in data:
            scheme = str(data["color_scheme"]).strip().lower()
            if scheme in COLOR_SCHEMES:
                config.color_scheme = scheme
            else:
                options = ", ".join(AVAILABLE_COLOR_SCHEMES)
                print(
                    f"Warning: Invalid color_scheme '{scheme}', using "
                    f"'{DEFAULT_COLOR_SCHEME}'. Available: {options}.",
                    file=sys.stderr,
                )

        # Parse saved filter state from [filter] sub-table
        filter_data = data.get("filter", {})
        if isinstance(filter_data, dict):
            config.saved_filter_user = str(filter_data.get("user", "")).strip()
            config.saved_filter_prefix = str(filter_data.get("prefix", "")).strip()

        return config


def save_filter_state(user: str, prefix: str, config_path: Path | None = None) -> None:
    """Persist filter state to the [filter] section of the config file.

    Reads the existing file (if any), updates or inserts the [filter] block,
    and writes it back without touching the rest of the file.
    """
    if config_path is None:
        config_path = SmonConfig.get_config_path()

    # Read existing content (preserve user comments / other settings)
    if config_path.exists():
        try:
            raw = config_path.read_text(encoding="utf-8")
        except OSError:
            raw = ""
    else:
        raw = ""
        # Ensure parent directory exists
        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            return

    new_filter_block = f'[filter]\nuser = "{user}"\nprefix = "{prefix}"\n'

    # Replace existing [filter] block (everything from the header to the next
    # section header or end-of-file), or append if absent.
    import re as _re
    pattern = _re.compile(
        r'^\[filter\][^\[]*',
        _re.MULTILINE | _re.DOTALL,
    )
    if pattern.search(raw):
        updated = pattern.sub(new_filter_block, raw)
    else:
        # Append with a blank line separator
        separator = "\n" if raw and not raw.endswith("\n\n") else ""
        updated = raw + separator + new_filter_block

    try:
        config_path.write_text(updated, encoding="utf-8")
    except OSError:
        pass


# Load config at module initialization
CONFIG = SmonConfig.load()
ACTIVE_COLOR_SCHEME = COLOR_SCHEMES[CONFIG.color_scheme]

# Legacy compatibility - REFRESH_RATE now comes from config
REFRESH_RATE = float(CONFIG.refresh_interval)
