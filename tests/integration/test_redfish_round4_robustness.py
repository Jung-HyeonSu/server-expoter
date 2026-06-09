"""redfish Round 4 robustness/correctness 회귀 (수렴 tail).

  - #2 _capped 비-list 방어 + #11 _compute_final_status 비-str detail
  - #0/#1 AssociatedPortGUIDs / SimpleStorage Devices 비-list
  - #7/#8 gather_system total_gib / gather_memory rank·width 문자열 → int
"""
from __future__ import annotations

import pytest

import emulator_harness as H

rg = H.rg


def _fake_get(tree):
    def fake(bmc_ip, path, username, password, timeout, verify_ssl):
        return (200, tree[path], None) if path in tree else (404, {}, "HTTP 404: Not Found")
    return fake


# ── #2 _capped 비-list ──
def test_capped_non_list_coerced():
    assert rg._capped({"a": 1}, "x", []) == []   # dict → []
    assert rg._capped(42) == [] and rg._capped(None) == []
    assert rg._capped([1, 2, 3]) == [1, 2, 3]     # 정상 list 불변


# ── #11 _compute_final_status 비-str detail ──
def test_compute_final_status_non_str_detail():
    # detail 이 int(404) → 'HTTP 401' in 404 TypeError 방어 (가드 전: crash)
    st, clean = rg._compute_final_status(["cpu"], ["power"], [{"detail": 404, "message": ["x"]}])
    assert st in ("success", "partial", "failed")


# ── #1 SimpleStorage Devices 비-list ──
def test_simple_storage_non_list_devices(monkeypatch):
    monkeypatch.setattr(rg, "_get", _fake_get({
        "Systems/1/SimpleStorage/1": {"Id": "1", "Name": "SS", "Devices": 42},  # 비-list
    }))
    controllers, errs = rg._gather_simple_storage(
        "1.2.3.4", [{"@odata.id": "/redfish/v1/Systems/1/SimpleStorage/1"}], "u", "p", 5, False)
    assert isinstance(controllers, list)  # 가드 전: for dev in 42 → TypeError


# ── #7 gather_system total_gib 문자열 → int ──
def test_gather_system_total_gib_string_to_int(monkeypatch):
    monkeypatch.setattr(rg, "_get", _fake_get({
        "Systems/1": {"Id": "1", "Manufacturer": "Generic",
                      "MemorySummary": {"TotalSystemMemoryGiB": "2048"}},
    }))
    data, errs = rg.gather_system("1.2.3.4", "/redfish/v1/Systems/1", "generic",
                                  "u", "p", 5, False, None)
    assert data["memory_summary"]["total_gib"] == 2048
    assert isinstance(data["memory_summary"]["total_gib"], int)


# ── #8 gather_memory rank/width 문자열 → int ──
def test_gather_memory_rank_width_string_to_int(monkeypatch):
    monkeypatch.setattr(rg, "_get", _fake_get({
        "Systems/1/Memory": {"Members": [{"@odata.id": "/redfish/v1/Systems/1/Memory/d1"}]},
        "Systems/1/Memory/d1": {"Id": "d1", "CapacityMiB": 16384, "RankCount": "2",
                                "DataWidthBits": "64", "BusWidthBits": "72"},
    }))
    out, errs = rg.gather_memory("1.2.3.4", "/redfish/v1/Systems/1", "u", "p", 5, False)
    slot = out["slots"][0]
    assert slot["rank_count"] == 2 and slot["data_width_bits"] == 64 and slot["bus_width_bits"] == 72
    assert isinstance(slot["rank_count"], int)
