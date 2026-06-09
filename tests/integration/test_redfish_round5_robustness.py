"""redfish Round 5 robustness 회귀 (수렴 — 잔여 배열 루프 폐쇄).

  - #0 _normalize_storage_raw 비-dict volume
  - #4 gather_power 비-list PowerSupplies (dict)
  - #5 _extract_storage_volumes 비-list Volumes Members
"""
from __future__ import annotations

import pytest

import emulator_harness as H

rg = H.rg


def _fake_get(tree):
    def fake(bmc_ip, path, username, password, timeout, verify_ssl):
        return (200, tree[path], None) if path in tree else (404, {}, "HTTP 404: Not Found")
    return fake


def test_normalize_storage_non_dict_volume():
    out = rg._normalize_storage_raw({"controllers": [], "volumes": [None, "junk",
                                     {"name": "v0", "total_mb": 1024}]})  # 가드 전: None.get
    assert isinstance(out, dict)
    lv = out.get("logical_volumes") or []
    assert any(v.get("name") == "v0" for v in lv)  # 유효 volume 보존


def test_gather_power_dict_powersupplies(monkeypatch):
    """PowerSupplies 가 dict(비-list) → _dicts 로 graceful (가드 전: dict 키 순회 noise)."""
    monkeypatch.setattr(rg, "_get", _fake_get({
        "Chassis/1/Power": {"PowerSupplies": {"psu0": {"Name": "PSU0"}},  # dict not list
                            "PowerControl": [{"PowerConsumedWatts": 100}]},
    }))
    result, errs = rg.gather_power("1.2.3.4", "/redfish/v1/Chassis/1", "u", "p", 5, False)
    assert isinstance(result.get("power_supplies"), list)  # 비-dict 컬렉션 → 빈 list (crash/noise 없음)


def test_extract_storage_volumes_dict_members(monkeypatch):
    monkeypatch.setattr(rg, "_get", _fake_get({
        "C/Volumes": {"Members": {"bad": "dict"}},  # 비-list
    }))
    vols, errs = rg._extract_storage_volumes(
        {"Volumes": {"@odata.id": "/redfish/v1/C/Volumes"}}, "ctrl0", "1.2.3.4", "u", "p", 5, False)
    assert vols == []  # 가드 전: dict 키 순회
