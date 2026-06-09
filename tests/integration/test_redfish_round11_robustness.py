"""redfish Round 11 회귀 — string-method 분리형 + status 403 in message.

  - #1 _extract_storage_drives: drive_name = _safe()or'' 후 .lower() (분리형 비-str)
  - #2 _compute_final_status: detail 아닌 message 측 HTTP 403 도 failed 강제 (multi_node 403)
"""
from __future__ import annotations
import emulator_harness as H
rg = H.rg


def _fake_get(tree):
    def fake(ip, path, u, p, t, v):
        return (200, tree[path], None) if path in tree else (404, {}, "HTTP 404: Not Found")
    return fake


def test_compute_final_status_403_in_message():
    """multi_node 403 가 message 에만 있어도 failed (가드 전: success 오분류)."""
    st, clean = rg._compute_final_status(
        ["system"], [], [{"section": "multi_node.managers",
                          "message": "Managers 컬렉션 실패: HTTP 403: Forbidden"}])
    assert st == "failed"


def test_compute_final_status_401_in_message():
    st, clean = rg._compute_final_status(
        ["system"], [], [{"message": "HTTP 401: Unauthorized"}])
    assert st == "failed"


def test_extract_storage_drives_non_str_name(monkeypatch):
    """Drive Name 이 비-str(int) → drive_name.lower() AttributeError 방어 (분리형 string-method)."""
    monkeypatch.setattr(rg, "_get", _fake_get({
        "C/Drives/0": {"Id": "0", "Name": 123, "CapacityBytes": 1000000000000,
                       "MediaType": "SSD"},
    }))
    sdata = {"Drives": [{"@odata.id": "/redfish/v1/C/Drives/0"}]}
    drives, errs = rg._extract_storage_drives(sdata, "1.2.3.4", "u", "p", 5, False)  # 가드 전: 123.lower()
    assert isinstance(drives, list)
