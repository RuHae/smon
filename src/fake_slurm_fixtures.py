"""Fake Slurm fixtures for screenshots and local demo mode."""

from __future__ import annotations

import re

FAKE_CLUSTER_NAME = "DEMO-CLUSTER"


def _node_line(
    name: str,
    state: str,
    cpu_alloc: int,
    cpu_tot: int,
    alloc_mem: int,
    real_mem: int,
    gres: str,
    gpu_alloc: int = 0,
) -> str:
    alloc_tres = f"cpu={cpu_alloc},mem={alloc_mem}M"
    if "gpu" in gres:
        alloc_tres += f",gres/gpu={gpu_alloc}"
    return (
        f"NodeName={name} State={state} CPUAlloc={cpu_alloc} CPUTot={cpu_tot} "
        f"AllocMem={alloc_mem} RealMemory={real_mem} Gres={gres} AllocTRES={alloc_tres}"
    )


def _build_fake_node_lines() -> list[str]:
    lines: list[str] = []

    # 12 CPU nodes (64 CPU each)
    for i in range(1, 13):
        if i in {7}:
            state = "DOWN"
        elif i in {11}:
            state = "DRAIN"
        elif i % 6 == 0:
            state = "IDLE"
        else:
            state = "MIXED"

        if state in {"DOWN", "DRAIN"}:
            cpu_alloc = 0
        elif state == "IDLE":
            cpu_alloc = 4 + ((i * 3) % 12)
        else:
            cpu_alloc = min(62, 22 + ((i * 5) % 38))

        alloc_mem = min(255000, cpu_alloc * 3600 + (i % 5) * 2048)
        lines.append(
            _node_line(
                name=f"cpu-a{i:02d}",
                state=state,
                cpu_alloc=cpu_alloc,
                cpu_tot=64,
                alloc_mem=alloc_mem,
                real_mem=257000,
                gres="(null)",
            )
        )

    # 48 GPU nodes (64 CPU + 8 GPU each)
    for i in range(1, 49):
        if i in {12, 24, 36, 48}:
            state = "MAINT"
        elif i % 5 == 0:
            state = "ALLOCATED"
        elif i % 7 == 0:
            state = "IDLE"
        else:
            state = "MIXED"

        if state == "MAINT":
            cpu_alloc = 0
            gpu_alloc = 0
        elif state == "ALLOCATED":
            cpu_alloc = 62 + (i % 2)
            gpu_alloc = 8
        elif state == "IDLE":
            cpu_alloc = 8 + ((i % 3) * 4)
            gpu_alloc = 0
        else:
            cpu_alloc = 28 + ((i * 4) % 28)
            gpu_alloc = 3 + (i % 5)

        alloc_mem = min(513000, cpu_alloc * 6500 + gpu_alloc * 16000)
        lines.append(
            _node_line(
                name=f"gpu-a{i:02d}",
                state=state,
                cpu_alloc=cpu_alloc,
                cpu_tot=64,
                alloc_mem=alloc_mem,
                real_mem=515000,
                gres="gpu:8",
                gpu_alloc=gpu_alloc,
            )
        )

    # 4 high-memory nodes (64 CPU each)
    for i in range(1, 5):
        state = "NO_RESPOND" if i == 4 else "MIXED"
        cpu_alloc = 0 if state == "NO_RESPOND" else 40 + (i * 6)
        alloc_mem = 0 if state == "NO_RESPOND" else min(1023000, cpu_alloc * 14500)
        lines.append(
            _node_line(
                name=f"hm-a{i:02d}",
                state=state,
                cpu_alloc=cpu_alloc,
                cpu_tot=64,
                alloc_mem=alloc_mem,
                real_mem=1024000,
                gres="(null)",
            )
        )

    return lines


def _job(
    job_id: str,
    user: str,
    state: str,
    time: str,
    left: str,
    prio: str,
    nodes: str,
    reason: str,
    gres: str,
    name: str,
    cpu: str,
    mem: str,
    part: str,
    account: str,
    qos: str,
    submit: str,
    dep: str,
) -> dict[str, str]:
    return {
        "id": job_id,
        "user": user,
        "state": state,
        "time": time,
        "left": left,
        "prio": prio,
        "nodes": nodes,
        "reason": reason,
        "gres": gres,
        "name": name,
        "cpu": cpu,
        "mem": mem,
        "part": part,
        "account": account,
        "qos": qos,
        "submit": submit,
        "dep": dep,
    }


_FAKE_JOBS = [
    _job("451950", "alice", "RUNNING", "17:52:11", "30:07:49", "4900", "6", "gpu-a[01-06]", "gpu_total=64", "trained_AGI_encoder", "384", "2048G", "gpu", "ml_lab", "gpu_ultra", "2026-02-20T18:40:00", "(null)"),
    _job("451951", "alice", "RUNNING", "06:14:03", "17:45:57", "4850", "4", "gpu-a[07-10]", "gpu:8", "attention_is_all_you_need", "256", "1536G", "gpu", "ml_lab", "gpu_high", "2026-02-21T01:10:00", "(null)"),
    _job("451952", "bob", "RUNNING", "01:42:50", "02:17:10", "4700", "1", "gpu-a11", "gpu:8", "cuda_out_of_memory_again", "64", "256G", "gpu", "ml_ops", "gpu_high", "2026-02-21T11:22:00", "(null)"),
    _job("451953", "bob", "PENDING", "00:00:00", "08:00:00", "4680", "8", "Priority", "gpu:4", "diffusion_lr_schedule", "512", "2048G", "gpu", "ml_ops", "std", "2026-02-21T12:02:11", "(null)"),
    _job("451954", "carol", "RUNNING", "03:28:41", "06:31:19", "4580", "3", "cpu-a[01-03]", "(null)", "vanishing_gradient_clinic", "192", "512G", "cpu", "research", "std", "2026-02-21T08:03:44", "(null)"),
    _job("451955", "carol", "RUNNING", "00:59:09", "03:00:51", "4520", "1", "cpu-a04", "(null)", "batch_norm_ablation", "64", "128G", "cpu", "research", "std", "2026-02-21T10:13:07", "(null)"),
    _job("451956", "dave", "PENDING", "00:00:00", "09:00:00", "4490", "2", "Resources", "gpu:8", "checkpoint_resume_ritual", "128", "640G", "gpu", "ml_platform", "std", "2026-02-21T12:15:40", "(null)"),
    _job("451957", "dave", "RUNNING", "11:10:22", "12:49:38", "4470", "5", "gpu-a[02-06]", "gpu:4", "int8_precision_diplomacy", "320", "1600G", "gpu", "ml_platform", "gpu_high", "2026-02-20T22:11:11", "(null)"),
    _job("451958", "eve", "PENDING", "00:00:00", "15:00:00", "4450", "6", "Dependency", "gpu:8", "moe_router_lottery", "384", "2304G", "gpu", "ml_research", "gpu_ultra", "2026-02-21T12:20:20", "afterok:451957"),
    _job("451959", "alice", "RUNNING", "05:01:02", "18:58:58", "4430", "2", "hm-a[01-02]", "(null)", "tensorboard_confessional", "128", "1024G", "bigmem", "ml_lab", "highmem", "2026-02-21T03:30:00", "(null)"),
    _job("451960", "bob", "RUNNING", "02:44:10", "01:15:50", "4410", "1", "gpu-a12", "gpu:8", "lora_rank_budget_review", "64", "320G", "gpu", "ml_ops", "gpu_high", "2026-02-21T09:05:00", "(null)"),
    _job("451961", "carol", "PENDING", "00:00:00", "05:00:00", "4390", "4", "AssocGrpCPU", "(null)", "reward_model_disagreement", "256", "768G", "cpu", "research", "std", "2026-02-21T12:22:10", "(null)"),
    _job("451962", "dave", "RUNNING", "00:40:16", "00:49:44", "4360", "1", "cpu-a05", "(null)", "nan_loss_postmortem", "64", "96G", "cpu", "ml_platform", "low", "2026-02-21T12:30:05", "(null)"),
    _job("451963", "eve", "RUNNING", "09:40:55", "06:19:05", "4320", "2", "gpu-a[03-04]", "gpu:8", "beam_search_tunnel_vision", "128", "768G", "gpu", "ml_research", "std", "2026-02-21T02:02:00", "(null)"),
    _job("451964", "alice", "PENDING", "00:00:00", "03:30:00", "4300", "1", "Resources", "gpu:8", "teacher_forcing_relapse", "64", "256G", "gpu", "ml_lab", "std", "2026-02-21T12:33:11", "(null)"),
    _job("451965", "bob", "RUNNING", "04:18:18", "07:41:42", "4280", "3", "cpu-a[06-08]", "(null)", "optimizer_state_mismatch", "192", "448G", "cpu", "ml_ops", "std", "2026-02-21T07:15:00", "(null)"),
    _job("451966", "carol", "RUNNING", "13:21:45", "10:38:15", "4250", "4", "gpu-a[05-08]", "gpu:6", "prompt_template_regression", "256", "1280G", "gpu", "research", "gpu_high", "2026-02-20T23:45:00", "(null)"),
    _job("451967", "dave", "PENDING", "00:00:00", "04:00:00", "4220", "2", "Priority", "gpu:8", "contrastive_collapse_recovery", "128", "768G", "gpu", "ml_platform", "std", "2026-02-21T12:36:51", "(null)"),
    _job("451968", "eve", "RUNNING", "00:26:12", "01:33:48", "4200", "1", "cpu-a09", "(null)", "dropout_still_overfits", "64", "128G", "cpu", "ml_research", "low", "2026-02-21T12:10:00", "(null)"),
    _job("451969", "alice", "RUNNING", "07:07:07", "00:52:53", "4180", "1", "cpu-a10", "(null)", "policy_gradient_variance", "64", "96G", "cpu", "ml_lab", "std", "2026-02-21T06:00:00", "(null)"),
    _job("451970", "bob", "RUNNING", "12:09:44", "03:50:16", "4160", "6", "cpu-a[07-12]", "(null)", "transformer_without_posenc", "384", "1152G", "cpu", "ml_ops", "std", "2026-02-21T01:55:00", "(null)"),
    _job("451971", "carol", "PENDING", "00:00:00", "06:00:00", "4140", "3", "Resources", "gpu:4", "latent_space_cartography", "192", "960G", "gpu", "research", "std", "2026-02-21T12:39:39", "(null)"),
    _job("451972", "dave", "RUNNING", "02:22:22", "05:37:38", "4120", "1", "gpu-a09", "gpu:8", "bayesian_bug_prior", "64", "288G", "gpu", "ml_platform", "std", "2026-02-21T09:44:00", "(null)"),
    _job("451973", "eve", "RUNNING", "14:01:30", "09:58:30", "4100", "2", "hm-a[03-04]", "(null)", "hyperparam_tuning_roulette", "128", "1536G", "bigmem", "ml_research", "highmem", "2026-02-20T21:30:00", "(null)"),
    _job("451974", "alice", "PENDING", "00:00:00", "02:00:00", "4080", "1", "Dependency", "(null)", "entropy_regularization_audit", "64", "128G", "cpu", "ml_lab", "low", "2026-02-21T12:41:22", "afterok:451969"),
    _job("451975", "bob", "RUNNING", "08:08:08", "07:51:52", "4060", "5", "gpu-a[01-05]", "gpu:5", "model_card_redaction", "320", "1400G", "gpu", "ml_ops", "gpu_high", "2026-02-21T04:04:00", "(null)"),
    _job("451976", "carol", "RUNNING", "01:16:40", "00:43:20", "4040", "1", "cpu-a11", "(null)", "attention_mask_off_by_one", "64", "160G", "cpu", "research", "std", "2026-02-21T11:50:00", "(null)"),
    _job("451977", "dave", "RUNNING", "03:33:33", "04:26:27", "4020", "2", "gpu-a[10-11]", "gpu:8", "validation_set_memorization", "128", "704G", "gpu", "ml_platform", "std", "2026-02-21T08:21:00", "(null)"),
    _job("451978", "alice", "PENDING", "00:00:00", "12:00:00", "4000", "4", "Priority", "gpu:8", "rlhf_label_budget", "256", "1024G", "gpu", "ml_lab", "std", "2026-02-21T12:45:00", "(null)"),
    _job("451979", "bob", "RUNNING", "00:50:50", "01:09:10", "3980", "1", "cpu-a12", "(null)", "train_val_leakage_audit", "64", "128G", "cpu", "ml_ops", "low", "2026-02-21T12:12:12", "(null)"),
    _job("451980", "carol", "PENDING", "00:00:00", "10:00:00", "3960", "3", "Resources", "gpu:8", "gradient_checkpointing_amnesia", "192", "960G", "gpu", "research", "std", "2026-02-21T12:46:00", "(null)"),
    _job("451981", "dave", "RUNNING", "01:11:22", "04:48:38", "3940", "2", "gpu-a[13-14]", "gpu:8", "kv_cache_fragmentation", "128", "768G", "gpu", "ml_platform", "std", "2026-02-21T10:40:00", "(null)"),
    _job("451982", "eve", "RUNNING", "02:02:02", "06:57:58", "3920", "1", "gpu-a15", "gpu:8", "fp16_underflow_watch", "64", "320G", "gpu", "ml_research", "std", "2026-02-21T09:10:00", "(null)"),
    _job("451983", "alice", "PENDING", "00:00:00", "07:30:00", "3900", "2", "Priority", "(null)", "eval_set_scope_creep", "128", "384G", "cpu", "ml_lab", "low", "2026-02-21T12:47:00", "(null)"),
    _job("451984", "bob", "RUNNING", "00:44:44", "01:15:16", "3880", "4", "gpu-a[16-19]", "gpu:4", "distributed_sampler_off_by_one", "256", "1200G", "gpu", "ml_ops", "gpu_high", "2026-02-21T11:35:00", "(null)"),
    _job("451985", "carol", "RUNNING", "03:03:03", "02:56:57", "3860", "1", "cpu-a09", "(null)", "reproducibility_seed_theater", "64", "160G", "cpu", "research", "std", "2026-02-21T08:25:00", "(null)"),
    _job("451986", "dave", "PENDING", "00:00:00", "05:45:00", "3840", "5", "Dependency", "gpu:4", "warmup_steps_eternity", "320", "1400G", "gpu", "ml_platform", "std", "2026-02-21T12:48:00", "afterok:451981"),
    _job("451987", "eve", "RUNNING", "04:44:04", "03:15:56", "3820", "2", "hm-a[01-02]", "(null)", "sharded_optimizer_tax", "128", "1400G", "bigmem", "ml_research", "highmem", "2026-02-21T07:32:00", "(null)"),
    _job("451988", "alice", "RUNNING", "00:31:31", "00:58:29", "3800", "1", "gpu-a20", "gpu:8", "token_budget_forecast", "64", "256G", "gpu", "ml_lab", "std", "2026-02-21T12:01:00", "(null)"),
    _job("451989", "bob", "PENDING", "00:00:00", "11:00:00", "3780", "6", "Priority", "gpu:8", "throughput_benchmark_theory", "384", "1800G", "gpu", "ml_ops", "gpu_high", "2026-02-21T12:49:00", "(null)"),
]

_FAKE_JOB_MAP = {job["id"]: job for job in _FAKE_JOBS}
_FAKE_NODE_LINES = _build_fake_node_lines()


def get_fake_cluster_name() -> str:
    return FAKE_CLUSTER_NAME


def _fake_scontrol_node_output() -> str:
    return "\n".join(_FAKE_NODE_LINES)


def _job_to_squeue_line(job: dict[str, str]) -> str:
    return " ".join(
        [
            job["id"],
            job["user"],
            job["state"],
            job["time"],
            job["left"],
            job["prio"],
            job["nodes"],
            job["reason"],
            job["gres"],
            job["name"],
            job["cpu"],
            job["mem"],
            job["part"],
            job["account"],
            job["qos"],
            job["submit"],
            job["dep"],
        ]
    )


def _fake_squeue_output() -> str:
    header = (
        "JOBID USER STATE TIME LEFT PRIO NODES REASON GRES NAME CPU MEM PART ACCOUNT QOS SUBMIT DEP"
    )
    state_order = {
        "PENDING": 0,
        "CONFIGURING": 1,
        "RUNNING": 2,
        "COMPLETING": 3,
        "SUSPENDED": 4,
    }

    def sort_key(job: dict[str, str]) -> tuple[int, int, str]:
        state_rank = state_order.get(job["state"], 99)
        # Within a state, higher priority first.
        return (state_rank, -int(job["prio"]), job["id"])

    lines = [header]
    lines.extend(_job_to_squeue_line(job) for job in sorted(_FAKE_JOBS, key=sort_key))
    return "\n".join(lines)


def _fake_uid_for_user(user: str) -> int:
    return 1000 + (sum(ord(c) for c in user) % 700)


def _mem_to_gib(mem: str) -> int:
    if mem.endswith("G"):
        return max(1, int(mem[:-1]))
    if mem.endswith("M"):
        return max(1, int(mem[:-1]) // 1024)
    return 8


def _seconds_to_hms(seconds: int) -> str:
    seconds = max(0, seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def _fake_job_detail(job_id: str) -> str:
    job = _FAKE_JOB_MAP.get(job_id)
    if not job:
        return (
            "JobId=0 JobName=unknown UserId=demo(1000) Account=demo QOS=std "
            "JobState=PENDING Reason=NotFound Dependency=(null) RunTime=00:00:00 "
            "TimeLimit=00:10:00 SubmitTime=2026-02-21T00:00:00 StartTime=Unknown "
            "Partition=cpu NodeList=(null) NumNodes=1 NumCPUs=1 Command=unknown "
            "WorkDir=/tmp StdOut=/tmp/unknown.out"
        )

    running_states = {"RUNNING", "COMPLETING", "CONFIGURING"}
    is_running = job["state"] in running_states
    node_list = job["reason"] if is_running else "(null)"
    reason = "None" if is_running else job["reason"]
    start_time = job["submit"] if is_running else "Unknown"
    dependency = job["dep"] if job["dep"] != "(null)" else "(null)"
    user = job["user"]
    name = job["name"]
    uid = _fake_uid_for_user(user)
    command = f"/opt/workflows/{name}.sh"
    workdir = f"/home/{user}/projects/{name}"
    stdout = f"/home/{user}/logs/{name}.out"

    return (
        f"JobId={job['id']} JobName={name} UserId={user}({uid}) "
        f"Account={job['account']} QOS={job['qos']} JobState={job['state']} "
        f"Reason={reason} Dependency={dependency} RunTime={job['time']} "
        f"TimeLimit={job['left']} SubmitTime={job['submit']} StartTime={start_time} "
        f"Partition={job['part']} NodeList={node_list} NumNodes={job['nodes']} "
        f"NumCPUs={job['cpu']} Command={command} WorkDir={workdir} StdOut={stdout}"
    )


def _fake_sstat(job_id: str) -> str:
    job = _FAKE_JOB_MAP.get(job_id)
    if not job or job["state"] != "RUNNING":
        return ""

    cpu = max(1, int(job["cpu"]))
    mem_gib = _mem_to_gib(job["mem"])
    seed = int(job_id[-2:])

    avg_cpu_seconds = 1800 + seed * 41
    ave_rss = max(2, int(mem_gib * 0.52))
    max_rss = max(ave_rss + 2, int(mem_gib * 0.71))
    disk_read = round(cpu * 0.58 + (seed % 11) * 1.6, 1)
    disk_write = round(disk_read * 0.47, 1)
    return (
        f"{_seconds_to_hms(avg_cpu_seconds)}|"
        f"{ave_rss}G|{max_rss}G|{disk_read}G|{disk_write}G"
    )


def run_fake_slurm_command(cmd: str) -> str:
    normalized = " ".join(cmd.split())
    if normalized == "scontrol show node -o":
        return _fake_scontrol_node_output()
    if normalized.startswith("squeue "):
        return _fake_squeue_output()
    if normalized.startswith("scontrol show job "):
        job_id = normalized.rsplit(" ", 1)[-1]
        return _fake_job_detail(job_id)
    if normalized.startswith("sstat -j "):
        parts = normalized.split()
        if len(parts) >= 3:
            job_id = parts[2].split(".")[0]
            return _fake_sstat(job_id)
        return ""
    if normalized.startswith("scancel "):
        return ""
    return ""
