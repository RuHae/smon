from __future__ import annotations

from smon_dashboard import SlurmDashboard, _dedupe_jobs_by_id


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
