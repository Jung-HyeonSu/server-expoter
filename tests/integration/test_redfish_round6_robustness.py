"""redfish Round 6 robustness 회귀 (수렴 tail).

  - #1 _fetch_service_root 비-dict ServiceRoot JSON
  - #6 gather_network MTUSize 문자열 → int
  - #8 account_service_get 무경계 계정 cap
"""
from __future__ import annotations

import pytest

import emulator_harness as H

rg = H.rg


def _fake_get(tree):
    def fake(bmc_ip, path, username, password, timeout, verify_ssl):
        return (200, tree[path], None) if path in tree else (404, {}, "HTTP 404: Not Found")
    return fake


def test_fetch_service_root_non_dict(monkeypatch):
    """ServiceRoot 가 비-dict JSON('string'/숫자) → None 반환(계약 위반 방어)."""
    monkeypatch.setattr(rg, "_get_noauth", lambda *a, **k: (200, "not_a_dict", None))
    root, errs = rg._fetch_service_root("1.2.3.4", "u", "p", 5, False)
    assert root is None and errs  # 비-dict → None + error


def test_fetch_service_root_dict_unchanged(monkeypatch):
    monkeypatch.setattr(rg, "_get_noauth", lambda *a, **k: (200, {"Vendor": "Dell"}, None))
    root, errs = rg._fetch_service_root("1.2.3.4", "u", "p", 5, False)
    assert root == {"Vendor": "Dell"}


def test_gather_network_mtu_string_to_int(monkeypatch):
    monkeypatch.setattr(rg, "_get", _fake_get({
        "Systems/1": {"EthernetInterfaces": {"@odata.id": "/redfish/v1/Systems/1/EthernetInterfaces"}},
        "Systems/1/EthernetInterfaces": {"Members": [{"@odata.id": "/redfish/v1/Systems/1/EthernetInterfaces/1"}]},
        "Systems/1/EthernetInterfaces/1": {"Id": "1", "MTUSize": "9000", "MACAddress": "00:11:22:33:44:55"},
    }))
    nics, errs = rg.gather_network("1.2.3.4", "/redfish/v1/Systems/1", "u", "p", 5, False)
    assert nics and nics[0]["mtu"] == 9000 and isinstance(nics[0]["mtu"], int)


def test_account_service_members_capped(monkeypatch):
    """수천 계정 → cap 이하로 절단 (무경계 순회 방어)."""
    cap = rg.MAX_COLLECTION_MEMBERS
    big = {"Members": [{"@odata.id": f"/redfish/v1/AccountService/Accounts/{i}"} for i in range(cap + 500)]}
    monkeypatch.setattr(rg, "_get", _fake_get({
        "AccountService": {"Accounts": {"@odata.id": "/redfish/v1/AccountService/Accounts"}},
        "AccountService/Accounts": big,
    }))
    root, accounts, errors = rg.account_service_get("1.2.3.4", "u", "p", 5, False)
    assert len(accounts) <= cap  # 절단됨 (각 계정 GET 은 404 라 빈 dict 안 쌓이지만 순회는 cap)
