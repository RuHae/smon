from __future__ import annotations

import slurm_backend

from fixture_loader import load_scontrol_show_node_output


def test_get_cluster_stats_parses_real_scontrol_fixture(monkeypatch):
    show_node_output = load_scontrol_show_node_output()
    monkeypatch.setattr(slurm_backend, "run_slurm_command", lambda _cmd: show_node_output)

    nodes, theoretical, real = slurm_backend.get_cluster_stats()

    assert len(nodes) == 35
    assert theoretical == (2218, 3920, 230, 280)
    assert real == (3920, 280)


def test_get_cluster_stats_parses_representative_gpu_nodes(monkeypatch):
    show_node_output = load_scontrol_show_node_output()
    monkeypatch.setattr(slurm_backend, "run_slurm_command", lambda _cmd: show_node_output)

    nodes, _theoretical, _real = slurm_backend.get_cluster_stats()
    by_name = {node["name"]: node for node in nodes}

    assert by_name["cn01"]["g_t"] == 8
    assert by_name["cn01"]["g_u"] == 6

    assert by_name["cn02"]["g_t"] == 8
    assert by_name["cn02"]["g_u"] == 4

    assert by_name["cn06"]["g_t"] == 8
    assert by_name["cn06"]["g_u"] == 3

    assert by_name["cn20"]["g_t"] == 8
    assert by_name["cn20"]["g_u"] == 1

    assert by_name["cn13"]["g_u"] == 0
    assert by_name["cn18"]["g_u"] == 0
