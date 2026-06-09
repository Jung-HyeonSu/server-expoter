"""redfish Round 2 robustness/correctness 회귀.

  - #1 _normalize_cpu_raw: 혼합 코어 same-model → cores_per_socket 평균 갱신
  - #8 _is_404_only_error: 비-str detail/message → 'in' TypeError 방어
  - #5/#11/#12 gather_power: PSU/PowerControl capacity watt int 통일
  - #13 _extract_storage_controller_info: 비-list ctrl Members 방어
  - #15 _resolve_all_member_uris: 비-list Members 방어
  - #18 gather_network: SpeedMbps int 통일
"""
from __future__ import annotations

import pytest

import emulator_harness as H

rg = H.rg


def _fake_get(tree):
    def fake(bmc_ip, path, username, password, timeout, verify_ssl):
        return (200, tree[path], None) if path in tree else (404, {}, "HTTP 404: Not Found")
    return fake


# ── #1 cores_per_socket ──
def test_cpu_mixed_cores_same_model_cores_per_socket():
    procs = [{"model": "Xeon Gold", "total_cores": 10, "processor_type": "CPU"},
             {"model": "Xeon Gold", "total_cores": 8, "processor_type": "CPU"}]
    g = rg._normalize_cpu_raw(procs)["summary"]["groups"][0]
    assert g["sockets"] == 2 and g["total_cores"] == 18
    assert g["cores_per_socket"] == 9  # (10+8)//2, 가드 전엔 10(첫 CPU 값)


def test_cpu_uniform_cores_unchanged():
    """동일 코어 same-model → cores_per_socket 불변(golden 호환)."""
    procs = [{"model": "X", "total_cores": 12, "processor_type": "CPU"},
             {"model": "X", "total_cores": 12, "processor_type": "CPU"}]
    g = rg._normalize_cpu_raw(procs)["summary"]["groups"][0]
    assert g["cores_per_socket"] == 12 and g["total_cores"] == 24


# ── #8 _is_404_only_error non-str ──
def test_is_404_only_error_non_str_detail_no_crash():
    assert rg._is_404_only_error([{"detail": 404, "message": ["x"]}]) is False  # 가드 전: TypeError
    # 정상 404 분류 불변
    assert rg._is_404_only_error([{"detail": "HTTP 404: Not Found"}]) is True


# ── #5/#11/#12 power capacity int ──
def test_power_capacity_string_to_int(monkeypatch):
    monkeypatch.setattr(rg, "_get", _fake_get({
        "Chassis/1/Power": {
            "PowerSupplies": [{"Name": "PSU1", "PowerCapacityWatts": "800"}],
            "PowerControl": [{"PowerConsumedWatts": "100", "PowerCapacityWatts": "1600",
                              "PowerMetrics": {}}],
        }}))
    result, _ = rg.gather_power("1.2.3.4", "/redfish/v1/Chassis/1", "u", "p", 5, False)
    assert result["power_supplies"][0]["power_capacity_w"] == 800
    assert result["power_control"]["power_capacity_watts"] == 1600
    assert isinstance(result["power_control"]["power_capacity_watts"], int)


# ── #13 ctrl Members non-list ──
def test_controller_info_dict_ctrl_members_graceful(monkeypatch):
    monkeypatch.setattr(rg, "_get", _fake_get({"C/Controllers": {"Members": {"bad": "dict"}}}))
    out, errs = rg._extract_storage_controller_info(
        {"Controllers": {"@odata.id": "/redfish/v1/C/Controllers"}}, "1.2.3.4", "u", "p", 5, False)
    assert isinstance(out, dict)  # 가드 전: KeyError


# ── #15 _resolve_all_member_uris non-list ──
def test_resolve_all_members_dict_graceful(monkeypatch):
    monkeypatch.setattr(rg, "_get", _fake_get({"Systems": {"Members": {"bad": "dict"}}}))
    members, st, err = rg._resolve_all_member_uris("1.2.3.4", "/redfish/v1/Systems", "u", "p", 5, False)
    assert members == []  # 가드 전: dict 키 순회 → 빈 결과(이제 명시적)


# ── #18 gather_network SpeedMbps int ──
def test_network_speed_mbps_string_to_int(monkeypatch):
    monkeypatch.setattr(rg, "_get", _fake_get({
        "Systems/1": {"EthernetInterfaces": {"@odata.id": "/redfish/v1/Systems/1/EthernetInterfaces"}},
        "Systems/1/EthernetInterfaces": {"Members": [{"@odata.id": "/redfish/v1/Systems/1/EthernetInterfaces/1"}]},
        "Systems/1/EthernetInterfaces/1": {"Id": "1", "SpeedMbps": "1000", "MACAddress": "00:11:22:33:44:55"},
    }))
    nics, errs = rg.gather_network("1.2.3.4", "/redfish/v1/Systems/1", "u", "p", 5, False)
    assert nics and nics[0]["speed_mbps"] == 1000 and isinstance(nics[0]["speed_mbps"], int)
