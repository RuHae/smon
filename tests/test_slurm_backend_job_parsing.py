from __future__ import annotations

import slurm_backend


def _build_squeue_output() -> str:
    header = (
        "JOBID USER STATE TIME LEFT PRIO NODES REASON GRES NAME CPU MEM PART "
        "ACCOUNT QOS SUBMIT DEP"
    )
    rows = [
        "100001 user01 RUNNING 00:10:00 00:50:00 100 1 cn01 gres/gpu:h100:4 train_a 64 256G all acct01 normal 2026-02-23T10:00:00 (null)",
        "100002 user02 RUNNING 00:15:00 00:45:00 110 2 cn02 gres/gpu:h100:1 train_b 64 256G all acct02 normal 2026-02-23T10:05:00 (null)",
        "100003 user03 RUNNING 00:05:00 00:55:00 120 1 cn03 gres/gpu:1 train_c 64 256G all acct03 normal 2026-02-23T10:10:00 (null)",
        "100004 user04 RUNNING 00:20:00 00:40:00 130 4 cn04 gpu_total=64 train_d 64 256G all acct04 normal 2026-02-23T10:15:00 (null)",
        "100005 user05 RUNNING 00:25:00 00:35:00 140 1 cn05 (null) train_e 64 256G all acct05 normal 2026-02-23T10:20:00 (null)",
    ]
    return "\n".join([header, *rows])


def _build_squeue_output_with_duplicate_rows() -> str:
    base = _build_squeue_output().splitlines()
    header = base[0]
    rows = base[1:]
    # Reproduce production symptom: same job rows repeated in the output.
    return "\n".join([header, *rows, *rows])


def _build_squeue_output_with_same_id_different_submit() -> str:
    header = (
        "JOBID USER STATE TIME LEFT PRIO NODES REASON GRES NAME CPU MEM PART "
        "ACCOUNT QOS SUBMIT DEP"
    )
    rows = [
        "100001 user01 PENDING 00:00:00 00:50:00 100 1 (Priority) gres/gpu:h100:4 ruler-dt-de 64 256G all acct01 normal 2026-02-24T13:25:09 (null)",
        # Same job repeated with updated runtime/submit rendering from another snapshot.
        "100001 user01 PENDING 00:00:00 00:49:59 100 1 (Priority) gres/gpu:h100:4 ruler-dt-de 64 256G all acct01 normal 2026-02-24T13:25:10 (null)",
        "100002 user02 PENDING 00:00:00 00:40:00 110 2 (Priority) gres/gpu:h100:1 longbench-dt-de 128 1T all acct02 normal 2026-02-24T13:44:30 (null)",
    ]
    return "\n".join([header, *rows])


def _build_squeue_output_with_long_array_task_ids() -> str:
    header = (
        "JOBID USER STATE TIME LEFT PRIO NODES REASON GRES NAME CPU MEM PART "
        "ACCOUNT QOS SUBMIT DEP"
    )
    rows = [
        f"288764_{task} user01 RUNNING 01:00:00 12:00:00 100 1 cn01 "
        "gres/gpu:h100:2 train 32 256G all acct01 normal "
        "2026-09-02T14:48:45 (null)"
        for task in (1, 10, 11, 12, 13, 14, 15)
    ]
    return "\n".join([header, *rows])


def test_get_job_stats_parses_typed_and_untyped_gpu_counts(monkeypatch):
    monkeypatch.setattr(slurm_backend, "run_slurm_command", lambda _cmd: _build_squeue_output())

    jobs = slurm_backend.get_job_stats()
    jobs_by_id = {job["id"]: job for job in jobs}

    assert jobs_by_id["100001"]["gpu"] == "4"
    assert jobs_by_id["100002"]["gpu"] == "2"
    assert jobs_by_id["100003"]["gpu"] == "1"
    assert jobs_by_id["100004"]["gpu"] == "64"
    assert jobs_by_id["100005"]["gpu"] == "-"


def test_get_job_stats_deduplicates_repeated_rows(monkeypatch):
    monkeypatch.setattr(
        slurm_backend,
        "run_slurm_command",
        lambda _cmd: _build_squeue_output_with_duplicate_rows(),
    )

    jobs = slurm_backend.get_job_stats()

    assert len(jobs) == 5
    assert [job["id"] for job in jobs] == [
        "100001",
        "100002",
        "100003",
        "100004",
        "100005",
    ]


def test_get_job_stats_deduplicates_same_job_id_with_changed_submit(monkeypatch):
    monkeypatch.setattr(
        slurm_backend,
        "run_slurm_command",
        lambda _cmd: _build_squeue_output_with_same_id_different_submit(),
    )

    jobs = slurm_backend.get_job_stats()

    assert len(jobs) == 2
    assert [job["id"] for job in jobs] == ["100001", "100002"]


def test_get_job_stats_preserves_long_array_task_ids(monkeypatch):
    def fake_run(cmd: str) -> str:
        # A precision on %i is a maximum width in squeue.  %.8i truncates
        # 288764_10 through 288764_15 to the same apparent ID, 288764_1.
        assert 'squeue --all --format="%i ' in cmd
        assert "%.8i" not in cmd
        return _build_squeue_output_with_long_array_task_ids()

    monkeypatch.setattr(slurm_backend, "run_slurm_command", fake_run)

    jobs = slurm_backend.get_job_stats()

    assert [job["id"] for job in jobs] == [
        "288764_1",
        "288764_10",
        "288764_11",
        "288764_12",
        "288764_13",
        "288764_14",
        "288764_15",
    ]
