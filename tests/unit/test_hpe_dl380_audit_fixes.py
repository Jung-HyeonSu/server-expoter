"""HPE DL380 Gen12 (iLO7) 실 미러 검수 회귀 — 2026-06-15.

tests/redfish-probe/redfish_full_mirror.py 로 실장비(HPE ProLiant DL380 Gen12,
iLO7 RedfishVersion 1.22.1)에서 전수 미러링한 raw Redfish 응답 기준으로 발견한
라이브러리 버그 2건의 회귀 테스트.

FIX-A (cpu_summary.health HealthRollup fallback):
    실측 raw /redfish/v1/Systems/1 ProcessorSummary.Status = {'HealthRollup':'OK'}
    (Health 키 부재). 기존 gather_system 은 Status.Health 만 읽어 cpu_summary.health=null
    유실. memory_summary / drives / volumes 와 동일하게 HealthRollup fallback 추가.

FIX-B (NetworkAdapter Port MAC from Ethernet.AssociatedMACAddresses):
    실측 raw Chassis/1/NetworkAdapters/<id>/Ports/<n> 은 구 NetworkPort 의 top-level
    AssociatedNetworkAddresses 가 아니라 Ethernet.AssociatedMACAddresses 에 MAC 을 둔다
    (Broadcom Ethernet) / FC 포트는 동일 키에 WWPN(FibreChannel={}). 기존 코드는
    AssociatedNetworkAddresses 만 읽어 adapters[].mac / ports[].associated_address 전부
    null 유실. Ethernet.AssociatedMACAddresses / FibreChannel.AssociatedWWNs fallback 추가
    (구 필드 우선 — F48 테스트 보존). FC 포트의 WWPN 은 cls in (FibreChannel/FCoE/InfiniBand)
    guard 로 adapter.mac 에 오기재되지 않는다 (실측: FC adapter mac=null 유지).
"""
from __future__ import annotations

import sys
import types
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "redfish-gather" / "library"))

_stub_basic = types.ModuleType("ansible.module_utils.basic")
_stub_basic.AnsibleModule = object
_stub_module_utils = types.ModuleType("ansible.module_utils")
_stub_module_utils.basic = _stub_basic
_stub_ansible = types.ModuleType("ansible")
_stub_ansible.module_utils = _stub_module_utils
sys.modules.setdefault("ansible", _stub_ansible)
sys.modules.setdefault("ansible.module_utils", _stub_module_utils)
sys.modules.setdefault("ansible.module_utils.basic", _stub_basic)

import redfish_gather as rg  # noqa: E402


def _mk_get(responses):
    """순차 응답 list → _get mock."""
    it = iter(responses)

    def fake(bmc_ip, path, username, password, timeout, verify_ssl):
        return next(it)

    return fake


# ── FIX-A: cpu_summary.health HealthRollup fallback ──────────────────────────

def test_cpu_summary_health_healthrollup_fallback(monkeypatch) -> None:
    """HPE 실측: ProcessorSummary.Status 에 HealthRollup 만 있을 때 cpu_summary.health='OK'."""
    system_data = {
        "@odata.id": "/redfish/v1/Systems/1",
        "Manufacturer": "HPE",
        "Model": "HPE ProLiant Compute DL380 Gen12",
        "ProcessorSummary": {"Count": 2, "Model": "Intel(R) Xeon(R) 6527P",
                             "Status": {"HealthRollup": "OK"}},  # Health 키 부재 (실측)
    }
    monkeypatch.setattr(rg, "_get", _mk_get([(200, system_data, None)]))
    result, errors = rg.gather_system("10.1.1.1", "/redfish/v1/Systems/1", "hpe",
                                      "u", "p", 30, False)
    assert result["cpu_summary"]["health"] == "OK"  # 가드 전: None (유실)
    assert result["cpu_summary"]["model"] == "Intel(R) Xeon(R) 6527P"


def test_cpu_summary_health_prefers_explicit_health(monkeypatch) -> None:
    """Status.Health 명시 시 그 값 우선 (HealthRollup 과 달라도 Health 가 권위)."""
    system_data = {
        "@odata.id": "/redfish/v1/Systems/1",
        "ProcessorSummary": {"Count": 1, "Status": {"Health": "Warning",
                                                    "HealthRollup": "OK"}},
    }
    monkeypatch.setattr(rg, "_get", _mk_get([(200, system_data, None)]))
    result, _ = rg.gather_system("10.1.1.1", "/redfish/v1/Systems/1", "hpe",
                                 "u", "p", 30, False)
    assert result["cpu_summary"]["health"] == "Warning"


def test_cpu_summary_health_none_when_absent(monkeypatch) -> None:
    """Health / HealthRollup 둘 다 없으면 None 유지 (faithful — 날조 금지)."""
    system_data = {
        "@odata.id": "/redfish/v1/Systems/1",
        "ProcessorSummary": {"Count": 1, "Status": {"State": "Enabled"}},
    }
    monkeypatch.setattr(rg, "_get", _mk_get([(200, system_data, None)]))
    result, _ = rg.gather_system("10.1.1.1", "/redfish/v1/Systems/1", "hpe",
                                 "u", "p", 30, False)
    assert result["cpu_summary"]["health"] is None


# ── FIX-B: Port MAC from Ethernet.AssociatedMACAddresses ─────────────────────

def _adapter_with_port(port_extra: dict):
    """단일 NetworkAdapter + 단일 Ethernet Port mock 응답 시퀀스 생성."""
    chassis_uri = "/redfish/v1/Chassis/1"
    adapters_coll = {"Members": [{"@odata.id": "/redfish/v1/Chassis/1/NetworkAdapters/A"}]}
    adapter_a = {
        "Id": "A", "Manufacturer": "Broadcom", "Model": "BCM57414",
        "Controllers": [{"ControllerCapabilities": {"NetworkPortCount": 1}}],
        "Ports": {"@odata.id": "/redfish/v1/Chassis/1/NetworkAdapters/A/Ports"},
    }
    ports_coll = {"Members": [{"@odata.id": "/redfish/v1/Chassis/1/NetworkAdapters/A/Ports/1"}]}
    port_1 = {"Id": "1", "Name": "Ethernet Port 1", "LinkStatus": "LinkUp",
              "Status": {"Health": "OK"}}
    port_1.update(port_extra)
    return chassis_uri, [(200, adapters_coll, None), (200, adapter_a, None),
                         (200, ports_coll, None), (200, port_1, None)]


def test_port_mac_from_ethernet_associated_macaddresses(monkeypatch) -> None:
    """신 Port resource: top-level AssociatedNetworkAddresses 부재, MAC 은
    Ethernet.AssociatedMACAddresses 에만 존재 → adapter.mac + port.associated_address 채움."""
    chassis_uri, seq = _adapter_with_port({
        "PortType": "Ethernet",
        "Ethernet": {"AssociatedMACAddresses": ["14:23:f3:b0:7a:40"]},
        # top-level AssociatedNetworkAddresses 없음 (실측 HPE DL380)
    })
    monkeypatch.setattr(rg, "_get", _mk_get(seq))
    out, _ = rg.gather_network_adapters_chassis("10.1.1.1", chassis_uri, "u", "p", 30, False)
    assert out["adapters"][0]["mac"] == "14:23:f3:b0:7a:40"   # 가드 전: None (유실)
    assert out["ports"][0]["associated_address"] == "14:23:f3:b0:7a:40"


def test_port_assoc_network_addresses_still_preferred(monkeypatch) -> None:
    """구 NetworkPort top-level AssociatedNetworkAddresses 존재 시 그 값 우선 (F48 보존).

    Ethernet.AssociatedMACAddresses 와 다른 값을 줘도 top-level 이 이긴다."""
    chassis_uri, seq = _adapter_with_port({
        "PortType": "Ethernet",
        "AssociatedNetworkAddresses": ["aa:bb:cc:dd:ee:01"],
        "Ethernet": {"AssociatedMACAddresses": ["99:99:99:99:99:99"]},
    })
    monkeypatch.setattr(rg, "_get", _mk_get(seq))
    out, _ = rg.gather_network_adapters_chassis("10.1.1.1", chassis_uri, "u", "p", 30, False)
    assert out["ports"][0]["associated_address"] == "aa:bb:cc:dd:ee:01"
    assert out["adapters"][0]["mac"] == "aa:bb:cc:dd:ee:01"


def test_fc_port_wwn_not_folded_into_adapter_mac(monkeypatch) -> None:
    """HPE FC 포트 quirk: WWPN 이 Ethernet.AssociatedMACAddresses 에 들어있고 FibreChannel={}.
    → cls=FibreChannel guard 로 adapter.mac 에 오기재 안 됨 (실측: FC adapter mac=null 유지),
       port.associated_address 에는 WWPN 노출, fc_hbas 에 entry 생성."""
    chassis_uri, seq = _adapter_with_port({
        "LinkNetworkTechnology": "FibreChannel",
        "FibreChannel": {},  # 비어있음 (실측 HPE DL380 — WWN 은 Ethernet 키에)
        "Ethernet": {"AssociatedMACAddresses": ["51:40:2E:C0:20:8F:39:30"]},
    })
    monkeypatch.setattr(rg, "_get", _mk_get(seq))
    out, _ = rg.gather_network_adapters_chassis("10.1.1.1", chassis_uri, "u", "p", 30, False)
    assert out["adapters"][0]["mac"] is None  # FC WWPN 이 mac 으로 오기재되지 않음
    assert out["ports"][0]["associated_address"] == "51:40:2E:C0:20:8F:39:30"
    assert len(out["fc_hbas"]) == 1
    assert out["fc_hbas"][0]["port_type"] == "FibreChannel"
