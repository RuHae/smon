import os
import subprocess

from fake_slurm_fixtures import get_fake_cluster_name


DASHBOARD_TITLE = "🚀 HPC CLUSTER MONITOR"
REFRESH_RATE = 2.0


def _is_truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


USE_FAKE_DATA = _is_truthy(os.environ.get("SMON_FAKE_DATA"))


def get_cluster_name() -> str:
    if USE_FAKE_DATA:
        return get_fake_cluster_name()
    return subprocess.getoutput("hostname").upper()


CLUSTER_NAME = get_cluster_name()
