"""redfish Round 9 robustness 회귀 (기존 가드 완성).

  - #1 gather_bmc NameServers 비-str element (Gateway 와 동일 isinstance)
"""
from __future__ import annotations
import pytest
import emulator_harness as H
rg = H.rg


def _fake_get(tree):
    def fake(bmc_ip, path, username, password, timeout, verify_ssl):
        return (200, tree[path], None) if path in tree else (404, {}, "HTTP 404: Not Found")
    return fake


def test_gather_bmc_non_str_nameservers(monkeypatch):
    """NameServers 에 비-str(int/dict) 섞임 → 비-str 미누적(str 만)."""
    monkeypatch.setattr(rg, "_get", _fake_get({
        "Managers/1": {"Id": "1", "EthernetInterfaces": {"@odata.id": "/redfish/v1/Managers/1/EthernetInterfaces"}},
        "Managers/1/EthernetInterfaces": {"Members": [{"@odata.id": "/redfish/v1/Managers/1/EthernetInterfaces/1"}]},
        "Managers/1/EthernetInterfaces/1": {"NameServers": ["8.8.8.8", 12345, {"x": 1}, "1.1.1.1"]},
    }))
    data, errs = rg.gather_bmc("1.2.3.4", "/redfish/v1/Managers/1", "hpe", "u", "p", 5, False)
    ns = ((data or {}).get("_network_meta") or {}).get("name_servers") or []
    assert all(isinstance(x, str) for x in ns)  # 비-str(12345/{}) 미누적
    assert "8.8.8.8" in ns and "1.1.1.1" in ns  # 정상 str 보존
