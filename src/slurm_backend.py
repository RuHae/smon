import re
import subprocess

from fake_slurm_fixtures import run_fake_slurm_command
from smon_config import USE_FAKE_DATA


GPU_GRES_COUNT_PATTERN = re.compile(
    r"(?:^|,)\s*(?:gres/)?gpu:(?:(?:[^:,()\s]+):)?(\d+)(?=$|,|\()"
)
GPU_ALLOC_TRES_PATTERN = re.compile(r"(?:^|,)\s*gres/gpu(?::[^=,\s]+)?=(\d+)(?=$|,)")
GPU_TOTAL_PATTERN = re.compile(r"(?:gpu_total|total_gpu)[:=](\d+)")


def _parse_gres_gpu_count(gres_value: str) -> int:
    return sum(int(count) for count in GPU_GRES_COUNT_PATTERN.findall(gres_value))


def _parse_alloc_tres_gpu_count(alloc_tres: str) -> int:
    return sum(int(count) for count in GPU_ALLOC_TRES_PATTERN.findall(alloc_tres))


def _parse_gpu_total(gpu_field: str) -> int | None:
    match = GPU_TOTAL_PATTERN.search(gpu_field)
    if match:
        return int(match.group(1))
    return None


def _parse_gpu_per_node(gpu_field: str) -> int | None:
    counts = GPU_GRES_COUNT_PATTERN.findall(gpu_field)
    if counts:
        return sum(int(count) for count in counts)
    return None


def run_slurm_command(cmd: str) -> str:
    if USE_FAKE_DATA:
        return run_fake_slurm_command(cmd)
    return subprocess.getoutput(cmd)


def get_cluster_stats():
    try:
        output = run_slurm_command("scontrol show node -o")
    except Exception:
        return [], (0, 0, 0, 0), (0, 0)

    nodes_data = []
    t_cpu_u, t_cpu_t, t_gpu_u, t_gpu_t = 0, 0, 0, 0
    r_cpu_t, r_gpu_t = 0, 0

    offline_states = ["DOWN", "DRAIN", "FAIL", "MAINT", "NO_RESPOND"]

    for line in output.split("\n"):
        if not line.strip():
            continue
        tokens = line.split()
        data = {k: v for k, v in [t.split("=", 1) for t in tokens if "=" in t]}

        name = data.get("NodeName", "Unknown")
        state = data.get("State", "Unknown")
        c_u = int(data.get("CPUAlloc", 0))
        c_t = int(data.get("CPUTot", 0))
        m_u = int(data.get("AllocMem", 0))
        m_t = int(data.get("RealMemory", 1))

        gres_str = data.get("Gres", "")
        alloc_tres = data.get("AllocTRES", "")
        g_t = _parse_gres_gpu_count(gres_str)
        g_u = _parse_alloc_tres_gpu_count(alloc_tres)

        t_cpu_u += c_u
        t_cpu_t += c_t
        t_gpu_u += g_u
        t_gpu_t += g_t

        if not any(s in state for s in offline_states):
            r_cpu_t += c_t
            r_gpu_t += g_t

        nodes_data.append(
            {
                "name": name,
                "state": state,
                "c_u": c_u,
                "c_t": c_t,
                "m_u": m_u,
                "m_t": m_t,
                "g_u": g_u,
                "g_t": g_t,
            }
        )

    return nodes_data, (t_cpu_u, t_cpu_t, t_gpu_u, t_gpu_t), (r_cpu_t, r_gpu_t)


def get_job_stats():
    cmd = (
        'squeue --all --format="'
        "%.8i %.8u %.11T %.11M %.12L %.10Q %.4D %.40R %.20b %.40j "
        "%.6C %.8m %.10P %.20a %.10q %.20V %.20E"
        '" --sort=T'
    )
    try:
        output = run_slurm_command(cmd)
    except Exception:
        return []

    jobs_data = []
    seen_job_ids: set[str] = set()
    lines = output.split("\n")

    for line in lines[1:]:
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) < 17:
            continue

        job_id = parts[0]
        if job_id in seen_job_ids:
            continue
        seen_job_ids.add(job_id)

        gpu_count = "-"
        gpu_field = parts[8]
        try:
            # Fixture compatibility: explicit total markers are whole-job totals.
            explicit_total = _parse_gpu_total(gpu_field)
            if explicit_total is not None:
                gpu_count = str(explicit_total)
            else:
                per_node = _parse_gpu_per_node(gpu_field)
                if per_node is not None:
                    node_mult = int(parts[6])
                    gpu_count = str(node_mult * per_node)
        except Exception:
            pass

        dep = parts[16]
        if dep == "(null)" or dep == "N/A":
            dep = ""

        jobs_data.append(
            {
                "id": job_id,
                "user": parts[1],
                "state": parts[2],
                "time": parts[3],
                "left": parts[4],
                "prio": parts[5],
                "nodes": parts[6],
                "reason": parts[7],
                "gpu": gpu_count,
                "name": parts[9],
                "cpu": parts[10],
                "mem": parts[11],
                "part": parts[12],
                "account": parts[13],
                "qos": parts[14],
                "submit": parts[15],
                "dep": dep,
            }
        )

    return jobs_data


def get_job_details(job_id: str):
    details = {"raw": "", "sstat": ""}
    try:
        details["raw"] = run_slurm_command(f"scontrol show job {job_id}")
    except Exception:
        details["raw"] = "Error fetching job details."

    if "JobState=RUNNING" in details["raw"]:
        try:
            cmd = (
                f"sstat -j {job_id} --format=AveCPU,AveRSS,MaxRSS,"
                "MaxDiskRead,MaxDiskWrite -n -P"
            )
            sstat_out = run_slurm_command(cmd)
            details["sstat"] = sstat_out
        except Exception:
            pass

    return details
