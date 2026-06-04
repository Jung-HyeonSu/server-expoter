"""HP CSUS 3200 사이트 사고 회귀 — vendor=hp 오선택 + hardware null fix.

cycle 2026-06-04 (사용자 사이트 실측): HPE Compute Scale-up Server 3200 (CSUS 3200)
수집 시 envelope vendor='hp' (→ 'hpCsus' 여야 함) + data.hardware.vendor/model=null.

근본 원인 (워크플로 adversarial 검증 + 실 adapter 시뮬레이션):
  - B1: 무인증 probe 벤더 감지에 "Compute Scale-up Server 3200" 시그니처 부재.
  - B2: hpe_ilo6 (priority=100) 은 model_patterns 부재라 절대 실격 안 됨 → 구 CSUS(96)/
        Superdome(95) 가 모델 매치해도 priority 로 패배.
  - A1: gather_system 이 System.Manufacturer/Model 부재 시 Chassis 폴백 없음.

Fix:
  - B1: _BMC_PRODUCT_HINTS 에 'compute scale-up server' / 'csus 3200' → 'hpe' (복합 키만).
  - B2: hpe_csus_3200 priority 96→102, hpe_superdome_flex 95→101 (iLO6 catch-all 위).
  - A1: gather_system Chassis.Manufacturer/Model 폴백 (result 값 None 일 때만, Additive).

본 테스트는 실 adapter YAML + 실 adapter_common 점수 + 실 gather_system 코드로 검증 (mock 입력).
ADR-2026-06-04-csus-adapter-priority.
"""
from __future__ import annotations

import glob
import sys
import types
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "module_utils"))
sys.path.insert(0, str(REPO / "redfish-gather" / "library"))

# ansible.module_utils.basic 는 Unix-only `grp` 를 import — Windows dev box 대비 stub.
# (Linux CI 에서는 setdefault 가 no-op 이거나 stub 이 우선 — AnsibleModule 은 gather_system 미사용.)
_stub_basic = types.ModuleType("ansible.module_utils.basic")
_stub_basic.AnsibleModule = object
_stub_mu = types.ModuleType("ansible.module_utils")
_stub_mu.basic = _stub_basic
_stub_ansible = types.ModuleType("ansible")
_stub_ansible.module_utils = _stub_mu
sys.modules.setdefault("ansible", _stub_ansible)
sys.modules.setdefault("ansible.module_utils", _stub_mu)
sys.modules.setdefault("ansible.module_utils.basic", _stub_basic)

from adapter_common import (  # noqa: E402
    load_vendor_aliases,
    adapter_matches,
    adapter_score,
)
import redfish_gather as rg  # noqa: E402

ALIASES = load_vendor_aliases(str(REPO / "common" / "vars" / "vendor_aliases.yml"))
VA = yaml.safe_load((REPO / "common" / "vars" / "vendor_aliases.yml").read_text(encoding="utf-8"))


def _load_redfish_adapters():
    out = []
    for p in sorted(glob.glob(str(REPO / "adapters" / "redfish" / "*.yml"))):
        d = yaml.safe_load(Path(p).read_text(encoding="utf-8")) or {}
        d["_filename"] = Path(p).name
        out.append(d)
    return out


ADAPTERS = _load_redfish_adapters()


def _by_id(aid):
    for a in ADAPTERS:
        if a.get("adapter_id") == aid:
            return a
    raise AssertionError(f"adapter {aid} 부재")


def _select(facts):
    """adapter_loader._match_and_score + sort 와 동일 로직 (실 점수 함수 사용)."""
    matched = []
    for a in ADAPTERS:
        if adapter_matches(a, facts, ALIASES):
            sc = adapter_score(a, facts, ALIASES)
            if sc > -9999:
                matched.append((sc, a))
    matched.sort(key=lambda x: x[0], reverse=True)
    return matched[0][1].get("adapter_id") if matched else None


def _out_vendor(adapter_id, rf_vendor):
    """site.yml _out_vendor 매핑과 동일."""
    ad = VA.get("adapter_output_display") or {}
    vd = VA.get("vendor_output_display") or {}
    return ad.get(adapter_id) or vd.get(rf_vendor, rf_vendor)


# ── B2: priority 일관성 ──────────────────────────────────────────────────────


def test_csus_superdome_priority_above_ilo6_below_ilo7():
    csus = _by_id("redfish_hpe_csus_3200")["priority"]
    sdf = _by_id("redfish_hpe_superdome_flex")["priority"]
    ilo6 = _by_id("redfish_hpe_ilo6")["priority"]
    ilo7 = _by_id("redfish_hpe_ilo7")["priority"]
    assert csus == 102, f"CSUS priority=102 기대, 실제 {csus}"
    assert sdf == 101, f"Superdome priority=101 기대, 실제 {sdf}"
    assert ilo6 < sdf < csus < ilo7, (
        f"iLO6({ilo6}) < Superdome({sdf}) < CSUS({csus}) < iLO7({ilo7}) 순서 위반"
    )


# ── B1+B2: 실 사고 시나리오 — CSUS 모델 → hpCsus 선택 (firmware 비어도) ───────


def test_csus_model_selects_csus_not_ilo6_firmware_empty():
    """사고 핵심: model=CSUS, firmware='' (RMC fw 가 facts 에 없을 때) → hpCsus."""
    facts = {"vendor": "HPE", "model": "Compute Scale-up Server 3200", "firmware": ""}
    winner = _select(facts)
    assert winner == "redfish_hpe_csus_3200", f"CSUS 선택 기대, 실제 {winner}"
    assert _out_vendor(winner, "hpe") == "hpCsus"


def test_csus_model_selects_csus_firmware_present():
    facts = {"vendor": "HPE", "model": "Compute Scale-up Server 3200", "firmware": "3.10.00"}
    winner = _select(facts)
    assert winner == "redfish_hpe_csus_3200"
    assert _out_vendor(winner, "hpe") == "hpCsus"


def test_superdome_model_selects_superdome_firmware_empty():
    facts = {"vendor": "HPE", "model": "Superdome Flex 280", "firmware": ""}
    winner = _select(facts)
    assert winner == "redfish_hpe_superdome_flex"
    assert _out_vendor(winner, "hpe") == "hpCsus"


# ── 무회귀: 정상 HPE / Dell ──────────────────────────────────────────────────


def test_normal_proliant_gen11_still_ilo6():
    facts = {"vendor": "HPE", "model": "ProLiant DL380 Gen11", "firmware": "iLO 6 v1.73"}
    winner = _select(facts)
    assert winner == "redfish_hpe_ilo6", f"Gen11 → iLO6 기대, 실제 {winner}"
    assert _out_vendor(winner, "hpe") == "hp"


def test_normal_proliant_gen12_still_ilo7():
    facts = {"vendor": "HPE", "model": "ProLiant DL380 Gen12", "firmware": "1.16.00"}
    winner = _select(facts)
    assert winner == "redfish_hpe_ilo7"
    assert _out_vendor(winner, "hpe") == "hp"


def test_empty_facts_hpe_still_ilo7_unchanged():
    """facts 전부 비면 priority 최상위 iLO7 — B2 가 이 동작을 바꾸지 않음."""
    facts = {"vendor": "HPE", "model": "", "firmware": ""}
    assert _select(facts) == "redfish_hpe_ilo7"


def test_dell_unaffected_by_b2():
    facts = {"vendor": "Dell Inc.", "model": "PowerEdge R760", "firmware": "7.10.30"}
    winner = _select(facts)
    assert winner == "redfish_dell_idrac9", f"Dell → idrac9 기대, 실제 {winner}"
    assert _out_vendor(winner, "dell") == "dell"


# ── B1: 무인증 probe 벤더 감지 ───────────────────────────────────────────────


def test_b1_detect_csus_product_as_hpe():
    assert rg._detect_vendor_from_service_root({"Product": "Compute Scale-up Server 3200"}) == "hpe"
    assert rg._detect_vendor_from_service_root({"Name": "CSUS 3200 Redfish Service"}) == "hpe"


def test_b1_no_collision_other_vendors():
    """복합 키만 추가 → 비-HPE Product/Name 와 substring 충돌 없음."""
    assert rg._detect_vendor_from_service_root({"Product": "Integrated Dell Remote Access Controller"}) == "dell"
    assert rg._detect_vendor_from_service_root({"Product": "Cisco Systems Inc"}) == "cisco"
    assert rg._BMC_PRODUCT_HINTS.get("compute scale-up server") == "hpe"
    assert rg._BMC_PRODUCT_HINTS.get("csus 3200") == "hpe"
    # 단독 'csus' / 'compute' 는 추가 안 됨 (충돌 위험)
    assert "csus" not in rg._BMC_PRODUCT_HINTS
    assert "compute" not in rg._BMC_PRODUCT_HINTS


# ── A1: gather_system Chassis 폴백 ───────────────────────────────────────────


def _patch_get(monkeypatch, system_data, chassis_data):
    def fake_get(bmc_ip, path, username, password, timeout, verify_ssl):
        if "Chassis" in path:
            return 200, chassis_data, None
        return 200, system_data, None
    monkeypatch.setattr(rg, "_get", fake_get)


def test_a1_chassis_fallback_fills_null_hardware(monkeypatch):
    """CSUS: System.Manufacturer/Model=None → Chassis 에서 보충."""
    _patch_get(
        monkeypatch,
        {"Manufacturer": None, "Model": None, "SerialNumber": "MOCK-P0", "UUID": "u1"},
        {"Manufacturer": "HPE", "Model": "Compute Scale-up Server 3200 Base"},
    )
    res, _ = rg.gather_system("1.2.3.4", "/redfish/v1/Systems/Partition0", "hpe",
                              "u", "p", 5, False, chassis_uri="/redfish/v1/Chassis/Base")
    assert res["manufacturer"] == "HPE"
    assert res["model"] == "Compute Scale-up Server 3200 Base"


def test_a1_does_not_override_present_values(monkeypatch):
    """정상 Dell: System 값 존재 → Chassis 가 덮어쓰지 않음 (무회귀)."""
    _patch_get(
        monkeypatch,
        {"Manufacturer": "Dell Inc.", "Model": "PowerEdge R760", "SerialNumber": "S", "UUID": "u2"},
        {"Manufacturer": "HPE", "Model": "SHOULD_NOT_APPEAR"},
    )
    res, _ = rg.gather_system("1.2.3.4", "/redfish/v1/Systems/1", "dell",
                              "u", "p", 5, False, chassis_uri="/redfish/v1/Chassis/1")
    assert res["manufacturer"] == "Dell Inc."
    assert res["model"] == "PowerEdge R760"


def test_a1_blank_chassis_normalizes_to_none(monkeypatch):
    """빈문자열/공백 Chassis → None 유지 ('' 회귀 차단)."""
    _patch_get(
        monkeypatch,
        {"Manufacturer": None, "Model": None, "SerialNumber": None, "UUID": None},
        {"Manufacturer": "   ", "Model": ""},
    )
    res, _ = rg.gather_system("1.2.3.4", "/redfish/v1/Systems/1", "hpe",
                              "u", "p", 5, False, chassis_uri="/redfish/v1/Chassis/1")
    assert res["manufacturer"] is None
    assert res["model"] is None
