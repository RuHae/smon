from __future__ import annotations

import asyncio

import smon_dashboard
from smon_dashboard import SlurmDashboard, _build_workload_stats, _dedupe_jobs_by_id
from smon_screens import JobDetailScreen, JobFilterScreen


def test_dedupe_jobs_by_id_removes_repeated_ids_preserving_order():
    jobs = [
        {"id": "86672", "name": "ruler-dt-de"},
        {"id": "86676", "name": "longbench-dt-de"},
        {"id": "86672", "name": "ruler-dt-de"},
        {"id": "86661", "name": "raim_hybrid_original"},
    ]

    deduped = _dedupe_jobs_by_id(jobs)

    assert [job["id"] for job in deduped] == ["86672", "86676", "86661"]


def test_watch_show_compact_is_ignored_before_mount(monkeypatch):
    app = SlurmDashboard()

    def fail(*_args, **_kwargs):
        raise AssertionError("should not run before mount")

    monkeypatch.setattr(app, "rebuild_job_columns", fail)
    monkeypatch.setattr(app, "update_data", fail)

    app.watch_show_compact(True)


def test_user_filter_is_case_insensitive_substring_match():
    app = SlurmDashboard()
    app.job_filter_user = "28COX"
    app.job_filter_prefix = ""
    jobs = [
        {"user": "mk28coxi", "name": "first"},
        {"user": "other", "name": "second"},
    ]

    assert app._filter_jobs(jobs) == [jobs[0]]
    assert app._build_filter_status(total_jobs=2, visible_jobs=1).startswith(" U~=28COX ")


def test_filter_enter_applies_without_opening_job_details(monkeypatch):
    monkeypatch.setattr(
        smon_dashboard,
        "get_cluster_stats",
        lambda: ([], (0, 0, 0, 0), (0, 0)),
    )
    monkeypatch.setattr(
        smon_dashboard,
        "get_job_stats",
        lambda: [
            {
                "id": "288764_0",
                "user": "mk28coxi",
                "name": "train",
                "account": "jackal_ai",
                "state": "RUNNING",
                "prio": "8",
                "left": "12:00:00",
                "gpu": "2",
                "cpu": "32",
                "mem": "256G",
                "nodes": "1",
                "reason": "cn01",
                "qos": "normal",
                "part": "all",
                "dep": "",
                "time": "01:00:00",
                "submit": "2026-09-02T14:48:45",
            }
        ],
    )
    monkeypatch.setattr(smon_dashboard, "save_filter_state", lambda *_args: None)

    async def exercise() -> None:
        app = SlurmDashboard()
        async with app.run_test() as pilot:
            app.action_show_filter()
            await pilot.pause()
            assert isinstance(app.screen, JobFilterScreen)

            user_input = app.screen.query_one("#filter-user-input")
            user_input.value = "28cox"
            await pilot.press("enter")
            await pilot.pause()

            assert not isinstance(app.screen, JobDetailScreen)
            assert app.job_filter_user == "28cox"

            await pilot.press("w")
            assert app.workload_collapsed
            assert app.has_class("-workload-collapsed")
            await pilot.press("w")
            assert not app.workload_collapsed

    asyncio.run(exercise())


def test_workload_stats_are_user_scoped_and_array_aware():
    jobs = [
        {
            "id": "288764_9",
            "user": "mk28coxi",
            "name": "tsfm-t2-scientific",
            "state": "RUNNING",
            "gpu": "2",
        },
        {
            "id": "288764_[10-31%8]",
            "user": "mk28coxi",
            "name": "tsfm-t2-scientific",
            "state": "PENDING",
            "gpu": "2",
        },
        {"id": "288900", "user": "mk28coxi", "state": "RUNNING", "gpu": "4"},
        {"id": "288901", "user": "other", "state": "RUNNING", "gpu": "8"},
    ]
    array_progress = [
        {
            "array_id": "288764",
            "done": 8,
            "running": 1,
            "pending": 22,
            "failed": 1,
            "other": 0,
            "total": 32,
        }
    ]

    stats = _build_workload_stats(jobs, "mk28coxi", array_progress)

    assert stats["gpus"] == 6
    assert stats["running"] == 2
    assert stats["pending"] == 22
    assert stats["array_count"] == 1
    assert stats["arrays"] == [
        {**array_progress[0], "name": "tsfm-t2-scientific"}
    ]
