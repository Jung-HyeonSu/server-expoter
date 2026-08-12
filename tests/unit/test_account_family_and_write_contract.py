"""Account Family 선택 / 벤더별 쓰기 성공 계약 / 검증 의무화 / lockout·check_mode.

배경 (2026-08-12, 9 Vendor 공식 조사):
  같은 vendor 안에서도 계정 Write 계약이 갈린다. 그래서 vendor 이름 하나로 쓰기 방식을
  정하고 실패하면 다른 payload 로 순차 재시도하던 구조를 없앴다. 읽기 단계에서 Family 를
  확정하고, 확정된 방식 하나만 실행한 뒤, 결과를 벤더 계약으로 해석한다.
"""
from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from account_seam import as_discovery as _as_discovery_raw  # noqa: E402


def _as_discovery(fn, **overrides):
    return _as_discovery_raw(fn, rg, **overrides)


def _disc(accounts=None, role_ids=None, service=None, manager=None, policy=None):
    return {
        "service_uri": "AccountService", "accounts_uri": "AccountService/Accounts",
        "roles_uri": "AccountService/Roles",
        "service": service if service is not None else {},
        "policy": policy or rg._account_policy_of(None),
        "role_ids": list(role_ids or []),
        "accounts": list(accounts or []),
        "member_total": len(accounts or []), "member_read": len(accounts or []),
        "enumeration": rg.ENUM_COMPLETE, "manager": manager, "errors": [],
        "auth_status": 200,
    }


def _slots(n, filled=()):
    return [{"slot_uri": f"/redfish/v1/AccountService/Accounts/{i}", "id": str(i),
             "username": (filled[i - 1] if i <= len(filled) else ""),
             "role_id": "Administrator", "enabled": bool(i <= len(filled) and filled[i - 1]),
             "has_username_key": True}
            for i in range(1, n + 1)]


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    monkeypatch.setattr(rg.time, "sleep", lambda *_: None)


# ── Family 선택 ──────────────────────────────────────────────────────────────
def test_family_is_deterministic_and_defaults_to_generic():
    d = _disc()
    fam, reasons = rg.resolve_account_family("no_such_vendor", d, None)
    assert fam["id"] == "generic_collection_post"
    assert fam["evidence"] == "unverified"
    assert reasons
    assert rg.resolve_account_family("no_such_vendor", d, None)[0]["id"] == fam["id"]


def _dell_mgr(firmware, model):
    return {"firmware_version": firmware, "model": model, "manager_type": "BMC"}


def test_dell_idrac10_protects_reserved_root_slot():
    """iDRAC10 은 ID 1(IPMI anonymous) 뿐 아니라 ID 2(default root)도 예약이다.

    source: dell.com/.../idrac10_1.20.xx_ug/configuring-local-users

    2026-08-12: 세대 근거를 adapter hint 가 아니라 **Firmware** 로 고정했으므로
    이 테스트도 장비가 주는 값으로 다시 앵커한다 (iDRAC10 = 1.x, iDRAC9 = 4.x~7.x).
    """
    fam, _ = rg.resolve_account_family(
        "dell", _disc(_slots(16), manager=_dell_mgr("1.20.55.10", "17G Monolithic")), None)
    assert fam["id"] == "dell_idrac10_slot_patch"
    assert set(fam["reserved_slot_ids"]) == {"1", "2"}
    old, _ = rg.resolve_account_family(
        "dell", _disc(_slots(16), manager=_dell_mgr("7.10.70.00", "16G Monolithic")), None)
    assert set(old["reserved_slot_ids"]) == {"1"}


def test_dell_generation_comes_from_firmware_not_adapter_hint():
    """실장비 회귀 (git 10.100.15.34, 2026-08-12).

    실제는 iDRAC9 / PowerEdge R760 / FW 7.10.70.00 인데 Adapter 가
    redfish_dell_idrac10 을 골랐고(무인증 probe 라 model/firmware fact 가 비어
    priority 만으로 결정됨), 그 adapter_id 가 그대로 Family 세대 근거로 쓰여
    dell_idrac10_slot_patch 가 선택됐다. 예약 슬롯이 {1} 이 아니라 {1,2} 가 되어
    **쓰기 대상 슬롯 URI 가 달라진다** (이 장비에선 slot 2 를 root 가 써서 가려졌을 뿐).
    """
    disc = _disc(_slots(16), manager=_dell_mgr("7.10.70.00", "16G Monolithic"))
    fam, reasons = rg.resolve_account_family("dell", disc, "redfish_dell_idrac10")
    assert fam["id"] == "dell_slot_patch", "adapter hint 가 Firmware 를 이겼다"
    assert set(fam["reserved_slot_ids"]) == {"1"}
    assert fam["evidence"] == "proven"
    assert any("fw_major=7" in r for r in reasons), f"세대 근거가 안 남았다: {reasons}"


def test_dell_idrac10_detected_from_firmware_even_with_idrac9_hint():
    """반대 방향도 성립해야 한다 — hint 가 idrac9 여도 Firmware 1.x 면 iDRAC10."""
    disc = _disc(_slots(16), manager=_dell_mgr("1.20.55.10", "17G Monolithic"))
    fam, _ = rg.resolve_account_family("dell", disc, "redfish_dell_idrac9")
    assert fam["id"] == "dell_idrac10_slot_patch"
    assert set(fam["reserved_slot_ids"]) == {"1", "2"}


def test_dell_falls_back_to_hint_only_when_device_gives_no_generation_signal():
    """Firmware/Model 을 못 읽으면 그때만 hint 를 쓴다 (기존 동작 유지 — 회귀 0)."""
    disc = _disc(_slots(16))
    assert rg.resolve_account_family("dell", disc, "redfish_dell_idrac10")[0]["id"] \
        == "dell_idrac10_slot_patch"
    assert rg.resolve_account_family("dell", disc, None)[0]["id"] == "dell_slot_patch"


def test_dell_generation_changes_the_write_target_slot():
    """두 Family 는 이름만 다른 게 아니다 — 예약 슬롯이 달라 PATCH 대상이 갈린다."""
    # slot 1 예약, slot 2 만 비어 있는 상태.
    accounts = _slots(16, filled=("", "", "u3", "u4", "u5", "u6", "u7", "u8",
                                  "u9", "u10", "u11", "u12", "u13", "u14", "u15", "u16"))
    for a in accounts:
        if a["id"] == "1":
            a["username"] = "reserved"
    fam9, _ = rg.resolve_account_family(
        "dell", _disc(accounts, manager=_dell_mgr("7.10.70.00", "16G Monolithic")), None)
    fam10, _ = rg.resolve_account_family(
        "dell", _disc(accounts, manager=_dell_mgr("1.20.55.10", "17G Monolithic")), None)
    assert "2" not in set(fam9["reserved_slot_ids"])
    assert "2" in set(fam10["reserved_slot_ids"]), \
        "iDRAC10 이 slot 2 를 예약하지 않으면 default root 슬롯을 덮어쓸 수 있다"


def test_cisco_family_comes_from_observed_role_vocabulary():
    """RoleId 어휘가 Family 를 가른다 — adapter 이름보다 실제 Resource 가 우선이다."""
    cimc, why = rg.resolve_account_family(
        "cisco", _disc(role_ids=["admin", "user", "read-only"]), None)
    assert cimc["id"] == "cisco_cimc_collection_post_id"
    assert cimc["needs_explicit_id"] is True

    bmc, _ = rg.resolve_account_family(
        "cisco", _disc(role_ids=["Administrator", "Operator", "ReadOnly"]), None)
    assert bmc["id"] == "cisco_bmc_dynamic"
    assert bmc["needs_explicit_id"] is False, "최신 Cisco BMC 는 Id 를 클라이언트가 정하지 않는다"


def test_cisco_xseries_without_evidence_stays_generic():
    """UCS X-Series 는 공식 Account 계약 미확보 — CIMC 방식을 적용하면 안 된다."""
    fam, _ = rg.resolve_account_family("cisco", _disc(), "redfish_cisco_ucs_xseries")
    assert fam["id"] == "generic_collection_post"
    assert fam["evidence"] == "unverified"


# ── Capability > adapter hint (실측으로 확인된 계약을 assertion 으로 고정) ─────
#
# 2026-08-12 감사에서 드러난 공백: Cisco 계약은 코드로는 옳지만, 기존 테스트는
#   (a) Role 어휘 + adapter_id=None 또는 (b) adapter hint + 빈 어휘
# 두 경우만 다뤘다. 즉 **어휘와 hint 가 서로 다른 것을 가리키는** 실제 사이트 상황이
# 한 건도 없었다. 그 상태로 hint 검사를 어휘 검사보다 위로 옮겨도 전 테스트가 통과한다.
def test_cisco_role_vocabulary_beats_conflicting_adapter_hint():
    """실측 10.100.15.2: adapter 는 ucs_xseries 로 오선택됐지만 Family 는 CIMC 로 옳게 잡혔다.

    장비가 준 Roles 어휘 = admin/user/readonly/SNMPOnly (Administrator 없음).
    """
    d = _disc(role_ids=["admin", "user", "readonly", "SNMPOnly"])
    fam, why = rg.resolve_account_family("cisco", d, "redfish_cisco_ucs_xseries")
    assert fam["id"] == "cisco_cimc_collection_post_id"
    assert fam["needs_explicit_id"] is True
    assert rg.choose_role_id(fam, "Administrator", d) == "admin"
    assert any("roles" in r for r in why), f"hint 이 아니라 어휘 근거라는 흔적이 없다: {why}"


def test_cisco_modern_bmc_is_not_forced_to_cimc_admin_by_hint():
    """반대 방향 — 과거처럼 모든 Cisco 에 RoleId=admin 을 강제하면 안 된다."""
    d = _disc(role_ids=["Administrator", "Operator", "ReadOnly"])
    fam, _ = rg.resolve_account_family("cisco", d, "redfish_cisco_cimc")
    assert fam["id"] == "cisco_bmc_dynamic"
    assert rg.choose_role_id(fam, "Administrator", d) == "Administrator"
    assert "Id" not in rg.build_create_payload(fam, "infraops", "<pw>", "Administrator")


def test_cisco_exposing_both_role_names_prefers_modern_family():
    """`admin` 과 `Administrator` 를 동시에 노출하면 표준 이름 쪽을 쓴다."""
    d = _disc(role_ids=["admin", "Administrator"])
    fam, _ = rg.resolve_account_family("cisco", d, None)
    assert fam["id"] == "cisco_bmc_dynamic"
    assert rg.choose_role_id(fam, "Administrator", d) == "Administrator"


def test_lenovo_purley_detected_by_prepopulated_slots():
    """Purley 는 빈 slot 이 미리 깔려 있고 PATCH 로 계정을 만든다 (POST 아님).

    source: pubs.lenovo.com/xcc-restapi/create_an_account_intel_p_based_patch
    """
    purley, _ = rg.resolve_account_family(
        "lenovo", _disc(_slots(12, filled=("USERID",))), "redfish_lenovo_xcc")
    assert purley["create_method"] == "slot_patch"

    dynamic, _ = rg.resolve_account_family(
        "lenovo", _disc(_slots(2, filled=("USERID", "svc"))), "redfish_lenovo_xcc")
    assert dynamic["create_method"] == "collection_post"
    assert dynamic["password_change_required"] is False


def test_lenovo_xcc3_requires_redfish_account_type():
    fam, _ = rg.resolve_account_family("lenovo", _disc(), "redfish_lenovo_xcc3")
    assert fam["account_types"] == ("Redfish",)
    assert "HostBootStrap" in fam["reserved_slot_ids"]


def test_supermicro_split_generation_detected_by_capability_not_name():
    """계정 분리 세대는 Generation 이 아니라 AccountTypes / Firmware 로 판정한다.

    source: supermicro.com/.../redfish-user-guide/.../accounts.htm
            (Gen13 01.05.xx+, Gen14 01.02.xx.xx+ 부터 IPMI/Redfish 계정 분리)
    """
    with_types = _disc([{"username": "ADMIN", "account_types": ["Redfish"],
                         "has_username_key": True}])
    fam, _ = rg.resolve_account_family("supermicro", with_types, None)
    assert fam["id"] == "supermicro_split_account"
    assert fam["account_types"] == ("Redfish",)

    old_fw, _ = rg.resolve_account_family(
        "supermicro", _disc(manager={"firmware_version": "01.01.05"}), "redfish_supermicro_x13")
    assert old_fw["id"] == "supermicro_legacy", "분리 이전 Firmware 를 분리 세대로 봤다"

    new_fw, _ = rg.resolve_account_family(
        "supermicro", _disc(manager={"firmware_version": "01.05.12"}), "redfish_supermicro_x13")
    assert new_fw["id"] == "supermicro_split_account"


def test_supermicro_x9_has_no_redfish_evidence():
    fam, _ = rg.resolve_account_family("supermicro", _disc(), "redfish_supermicro_x9")
    assert fam["evidence"] == "unverified"


def test_hpe_rmc_is_not_treated_as_ilo():
    """CSUS 3200 / Superdome Flex 는 iLO 가 아니라 RMC 다 — iLO payload 를 쓰면 안 된다."""
    for hint in ("redfish_hpe_csus_3200", "redfish_hpe_superdome_flex"):
        fam, _ = rg.resolve_account_family("hpe", _disc(), hint)
        assert fam["id"] == "generic_collection_post"
        assert fam["oem_privileges_namespace"] is None


def test_inspur_m6_requires_etag_and_oem_status():
    fam, _ = rg.resolve_account_family(
        "inspur", _disc(service={"Oem": {"Public": {"PasswordComplexityCheckEnabled": 1}}}), None)
    assert fam["id"] == "inspur_m6"
    assert fam["etag_required"] is True
    assert fam["write_success"] == "inspur_oem_status"


# ── RoleId 선택 ──────────────────────────────────────────────────────────────
def test_role_id_prefers_what_the_device_supports():
    fam = rg.account_family("cisco_cimc_collection_post_id")
    d = _disc(role_ids=["admin", "user", "read-only"])
    assert rg.choose_role_id(fam, "Administrator", d) == "admin"

    modern = rg.account_family("cisco_bmc_dynamic")
    d2 = _disc(role_ids=["Administrator", "Operator"])
    assert rg.choose_role_id(modern, "Administrator", d2) == "Administrator"


def test_role_id_falls_back_to_case_insensitive_match():
    fam = rg.account_family("generic_collection_post")
    d = _disc(role_ids=["administrator", "operator"])
    assert rg.choose_role_id(fam, "Administrator", d) == "administrator"


def test_role_id_unchanged_when_device_lists_nothing():
    fam = rg.account_family("generic_collection_post")
    assert rg.choose_role_id(fam, "Administrator", _disc()) == "Administrator"


# ── 쓰기 응답 해석 ───────────────────────────────────────────────────────────
def test_inspur_oem_status_decides_success_not_http_code():
    """Inspur M6 는 HTTP 200 + Oem.Public.Status 0 이어야 성공이다.

    source: 浪潮英信服务器 Redfish用户手册 V1.2 §4.4 (Status 0 = success)
    """
    fam = rg.account_family("inspur_m6")
    ok, _ = rg.interpret_write_response(fam, 200, {"Oem": {"Public": {"Status": 0}}}, None)
    assert ok is True
    bad, reason = rg.interpret_write_response(
        fam, 200, {"Oem": {"Public": {"Status": 5}}}, None)
    assert bad is False and "Status=5" in reason


def test_generic_family_ignores_oem_status():
    fam = rg.account_family("generic_collection_post")
    ok, _ = rg.interpret_write_response(fam, 200, {"Oem": {"Public": {"Status": 5}}}, None)
    assert ok is True, "Inspur 전용 계약을 전 vendor 에 적용하면 안 된다"


def test_body_level_rejection_beats_2xx_for_every_family():
    body = {"@Message.ExtendedInfo": [{
        "MessageId": "Base.1.12.PropertyNotWritable",
        "Message": "The property Locked is a read only property and cannot be assigned a value.",
        "MessageArgs": ["Locked"]}]}
    for fid in ("dell_slot_patch", "generic_collection_post", "huawei_ibmc"):
        ok, reason = rg.interpret_write_response(rg.account_family(fid), 200, body, None)
        assert ok is False and "Locked" in reason


def test_message_args_are_only_read_for_property_message_ids():
    """정보성 메시지의 MessageArgs 를 거부 속성으로 오인하지 않는다.

    종전에는 MessageId 를 보지 않고 모든 MessageArgs 문자열을 거부 속성으로 취급해,
    성공 응답에 딸린 안내 하나가 재시도에서 Enabled/RoleId 를 떨어뜨릴 수 있었다.
    """
    informational = {"@Message.ExtendedInfo": [{
        "MessageId": "Base.1.12.Success",
        "Message": "Successfully Completed Request.",
        "MessageArgs": ["Enabled", "RoleId"]}]}
    assert rg.rejected_patch_properties(informational) == set()


# ── 검증 의무화 (audit H-1) ──────────────────────────────────────────────────
def test_post_create_without_reauth_is_never_success(monkeypatch):
    """POST 2xx 만으로 recovered=true 를 반환하는 경로가 더는 없다."""
    monkeypatch.setattr(rg, "account_service_discover",
                        _as_discovery(lambda *a, **k: ({}, [], [])))
    monkeypatch.setattr(rg, "_post",
                        lambda *a, **k: (201, {"@odata.id": "/redfish/v1/AccountService/Accounts/5"}, None))
    monkeypatch.setattr(rg, "_get", lambda *a, **k: (401, {}, "HTTP 401"))

    for vendor in ("hpe", "lenovo", "supermicro", "huawei", "inspur", "fujitsu", "quanta"):
        out = rg.account_service_provision(
            "10.0.0.1", vendor, "rec", "<rec>", "infraops", "<tgt>",
            "Administrator", 5, False, dryrun=False)
        assert out["recovered"] is False, f"{vendor}: 검증 없이 성공으로 보고했다"
        assert out["verification"] == "failed"
        assert out["write_accepted"] is True, f"{vendor}: 쓰기 수락 사실은 남아야 한다"


def test_verification_none_only_when_nothing_was_written(monkeypatch):
    monkeypatch.setattr(rg, "account_service_discover",
                        _as_discovery(lambda *a, **k: ({}, [], [])))
    monkeypatch.setattr(rg, "_post", lambda *a, **k: (201, {}, None))
    monkeypatch.setattr(rg, "_get", lambda *a, **k: (200, {}, None))
    out = rg.account_service_provision(
        "10.0.0.1", "hpe", "rec", "<rec>", "infraops", "<tgt>",
        "Administrator", 5, False, dryrun=False)
    assert out["verification"] == "verified"


# ── check_mode / dryrun ──────────────────────────────────────────────────────
def test_check_mode_blocks_every_write():
    """`ansible-playbook --check` 로 실제 PATCH/POST 가 나가던 결함 (audit H-2).

    모듈은 supports_check_mode=True 를 선언해 두고 module.check_mode 를 한 번도
    읽지 않았다. Ansible 은 선언이 있으면 태스크를 skip 하지 않고 모듈을 실행한다.
    """
    src = (REPO / "redfish-gather/library/redfish_gather.py").read_text(encoding="utf-8")
    assert "module.check_mode" in src, "check_mode 를 읽지 않는다"
    idx = src.index("if mode == 'account_provision':")
    body = src[idx:idx + 2500]
    assert "or bool(module.check_mode)" in body, "check_mode 가 쓰기 차단에 연결되지 않았다"


def test_dryrun_records_what_would_have_been_written(monkeypatch):
    """dry-run 은 쓰기 0건이면서 '무엇을 쓸 예정이었는지' 를 남긴다."""
    monkeypatch.setattr(rg, "account_service_discover",
                        _as_discovery(lambda *a, **k: ({}, _slots(12, filled=("root",)), [])))
    writes = []
    monkeypatch.setattr(rg, "_post", lambda *a, **k: writes.append("post"))
    monkeypatch.setattr(rg, "_patch", lambda *a, **k: writes.append("patch"))
    out = rg.account_service_provision(
        "10.0.0.1", "dell", "rec", "<rec>", "infraops", "<tgt>",
        "Administrator", 5, False, dryrun=True)
    assert writes == []
    assert out["verification"] == "skipped"
    assert out["presence"] == rg.PRESENCE_ABSENT
    assert out["family"] == "dell_slot_patch"
    assert out["create_method"] == "slot_patch"
    assert out["slot_uri"], "어느 슬롯에 쓸 예정이었는지가 없다"


# ── lockout 예산 ─────────────────────────────────────────────────────────────
def test_auth_budget_counts_failed_standard_auth(monkeypatch):
    monkeypatch.setattr(rg, "account_service_discover",
                        _as_discovery(lambda *a, **k: (
                            {}, [{"slot_uri": "/redfish/v1/AccountService/Accounts/3",
                                  "id": "3", "username": "infraops",
                                  "role_id": "Administrator", "enabled": True,
                                  "has_username_key": True}], [])))
    monkeypatch.setattr(rg, "_patch", lambda *a, **k: (200, {}, None))
    monkeypatch.setattr(rg, "_get", lambda b, path, *a, **k:
                        (401, {}, "HTTP 401") if str(path).endswith("Systems")
                        else (200, {"UserName": "infraops", "Enabled": True}, None))
    out = rg.account_service_provision(
        "10.0.0.1", "dell", "rec", "<rec>", "infraops", "<tgt>",
        "Administrator", 5, False, dryrun=False)
    assert out["auth_budget"]["infraops"] == len(rg.ACCOUNT_VERIFY_DELAYS)
    assert out["verify_attempts"] == len(rg.ACCOUNT_VERIFY_DELAYS)


def test_policy_incompatibility_is_diagnosed_but_not_blocking(monkeypatch):
    """정책 범위를 벗어나도 **차단하지 않고** 시도한 뒤 응답으로 확정한다 (사용자 결정)."""
    svc = {"MinPasswordLength": 16, "MaxPasswordLength": 20,
           "Accounts": {"@odata.id": "/redfish/v1/AccountService/Accounts"}}
    monkeypatch.setattr(rg, "account_service_discover",
                        _as_discovery(lambda *a, **k: (svc, [], [])))
    posted = []
    monkeypatch.setattr(rg, "_post",
                        lambda b, p_, body, *a, **k: (posted.append(p_), (201, {}, None))[1])
    monkeypatch.setattr(rg, "_get", lambda *a, **k: (200, {}, None))

    out = rg.account_service_provision(
        "10.0.0.1", "supermicro", "rec", "<rec>", "infraops", "short",
        "Administrator", 5, False, dryrun=False)
    assert posted, "정책 비호환을 이유로 쓰기를 막았다 (차단하지 않기로 결정했다)"
    assert out["policy"]["within_declared_bounds"] is False
    assert out["policy"]["min_password_length"] == 16
    joined = " ".join(f'{e.get("message")}' for e in out["errors"])
    assert "길이 정책 범위를 벗어납니다" in joined


def test_policy_never_records_password_length(monkeypatch):
    """정책 진단에 비밀번호 길이 자체를 남기지 않는다 (탐색 공간 축소 방지)."""
    svc = {"MinPasswordLength": 8, "MaxPasswordLength": 20,
           "Accounts": {"@odata.id": "/redfish/v1/AccountService/Accounts"}}
    monkeypatch.setattr(rg, "account_service_discover",
                        _as_discovery(lambda *a, **k: (svc, [], [])))
    monkeypatch.setattr(rg, "_post", lambda *a, **k: (201, {}, None))
    monkeypatch.setattr(rg, "_get", lambda *a, **k: (200, {}, None))
    out = rg.account_service_provision(
        "10.0.0.1", "supermicro", "rec", "<rec>", "infraops", "Sup3rSecret!x",
        "Administrator", 5, False, dryrun=False)
    assert set(out["policy"]) == {
        "min_password_length", "max_password_length", "lockout_threshold",
        "lockout_duration", "auth_failure_delay_seconds",
        "supported_account_types", "within_declared_bounds"}
    assert "password_length" not in str(out["policy"]).replace("min_password_length", "") \
        .replace("max_password_length", "")


# ── ETag / If-Match ──────────────────────────────────────────────────────────
def test_if_match_only_sent_for_families_that_require_it(monkeypatch):
    """ETag 는 Family 가 요구할 때만 쓴다 (bmcweb If-Match crash 회피 유지)."""
    accounts = [{"slot_uri": "/redfish/v1/AccountService/Accounts/1", "id": "1",
                 "username": "infraops", "role_id": "Administrator",
                 "enabled": True, "has_username_key": True}]
    svc = {"Oem": {"Public": {}}, "Accounts": {"@odata.id": "/redfish/v1/AccountService/Accounts"}}
    seen = {}

    def fake_patch(bmc_ip, path, body, u, p, t, v, extra_headers=None):
        seen["headers"] = extra_headers
        return 200, {"Oem": {"Public": {"Status": 0}}}, None

    monkeypatch.setattr(rg, "account_service_discover",
                        _as_discovery(lambda *a, **k: (svc, accounts, [])))
    monkeypatch.setattr(rg, "_patch", fake_patch)
    monkeypatch.setattr(rg, "_get_response_etag", lambda *a, **k: 'W/"abc123"')
    monkeypatch.setattr(rg, "_get", lambda *a, **k: (200, {}, None))

    out = rg.account_service_provision(
        "10.0.0.1", "inspur", "rec", "<rec>", "infraops", "<tgt>",
        "Administrator", 5, False, dryrun=False)
    assert out["family"] == "inspur_m6"
    assert seen["headers"] == {"If-Match": 'W/"abc123"'}
    assert out["recovered"] is True


def test_non_etag_family_calls_patch_without_header_argument(monkeypatch):
    """ETag 가 필요 없는 Family 는 종전 시그니처 그대로 `_patch` 를 부른다."""
    accounts = [{"slot_uri": "/redfish/v1/AccountService/Accounts/1", "id": "1",
                 "username": "infraops", "role_id": "Administrator",
                 "enabled": True, "has_username_key": True}]
    calls = []

    def fake_patch(bmc_ip, path, body, u, p, t, v):   # extra_headers 인자 없음
        calls.append(path)
        return 200, {}, None

    monkeypatch.setattr(rg, "account_service_discover",
                        _as_discovery(lambda *a, **k: ({}, accounts, [])))
    monkeypatch.setattr(rg, "_patch", fake_patch)
    monkeypatch.setattr(rg, "_get", lambda *a, **k: (200, {}, None))
    out = rg.account_service_provision(
        "10.0.0.1", "dell", "rec", "<rec>", "infraops", "<tgt>",
        "Administrator", 5, False, dryrun=False)
    assert calls and out["recovered"] is True


# ── 상태 수렴 시나리오 (사용자 지시 §17 Contract) ────────────────────────────
def _existing(**over):
    acc = {"slot_uri": "/redfish/v1/AccountService/Accounts/3", "id": "3",
           "username": "infraops", "role_id": "Administrator", "enabled": True,
           "locked": False, "has_username_key": True,
           "account_types": None, "password_change_required": None}
    acc.update(over)
    return acc


def _repair(monkeypatch, account, vendor="lenovo", adapter_id=None, reread=None):
    sent = []

    def fake_patch(bmc_ip, path, body, u, p, t, v):
        sent.append(dict(body))
        return 200, {}, None

    monkeypatch.setattr(rg, "account_service_discover",
                        _as_discovery(lambda *a, **k: ({}, [account], [])))
    monkeypatch.setattr(rg, "_patch", fake_patch)
    monkeypatch.setattr(rg, "_get", lambda b, path, *a, **k:
                        (200, {}, None) if str(path).endswith("Systems")
                        else (200, reread or {"UserName": "infraops", "Enabled": True}, None))
    out = rg.account_service_provision(
        "10.0.0.1", vendor, "rec", "<rec>", "infraops", "<tgt>",
        "Administrator", 5, False, dryrun=False, adapter_id=adapter_id)
    return out, sent


def test_disabled_account_is_repaired_and_reported(monkeypatch):
    out, sent = _repair(monkeypatch, _existing(enabled=False))
    assert out["recovered"] is True and out["verification"] == "verified"
    assert sent[0]["Enabled"] is True
    joined = " ".join(e.get("message", "") for e in out["errors"])
    assert "비활성" in joined, "비밀번호 불일치와 계정 비활성을 구분해 남기지 않았다"


def test_locked_account_is_repaired_and_reported(monkeypatch):
    out, sent = _repair(monkeypatch, _existing(locked=True))
    assert sent[0]["Locked"] is False
    joined = " ".join(e.get("message", "") for e in out["errors"])
    assert "잠금" in joined


def test_role_drift_is_written_with_supported_role(monkeypatch):
    out, sent = _repair(monkeypatch, _existing(role_id="ReadOnly"))
    assert sent[0]["RoleId"] == "Administrator"
    assert out["recovered"] is True


def test_password_change_required_is_cleared_only_when_device_exposes_it(monkeypatch):
    """장비가 그 속성을 실제로 노출할 때만 끈다 — 미지원 속성을 추측해 보내지 않는다.

    Lenovo TSM 은 생성 시 미지정이면 default true 라 즉시 접근이 막힌다. 반대로
    Purley XCC 와 Huawei 는 이 속성이 없다.
    source: pubs.lenovo.com/tsm/post_create_new_account,
            pubs.lenovo.com/xcc-restapi/account_properties_get (Purley = not available)
    """
    out, sent = _repair(monkeypatch, _existing(password_change_required=True))
    assert sent[0]["PasswordChangeRequired"] is False

    out2, sent2 = _repair(monkeypatch, _existing(password_change_required=None))
    assert "PasswordChangeRequired" not in sent2[0]


def test_account_types_are_converged_only_when_family_requires(monkeypatch):
    """XCC2/XCC3·Supermicro 분리 세대는 AccountTypes 에 Redfish 가 없으면 인증이 막힌다."""
    acc = _existing(account_types=["IPMI"])
    out, sent = _repair(monkeypatch, acc, vendor="lenovo", adapter_id="redfish_lenovo_xcc3")
    assert "Redfish" in sent[0]["AccountTypes"]
    assert "IPMI" in sent[0]["AccountTypes"], "기존 AccountTypes 를 지우면 안 된다"

    out2, sent2 = _repair(monkeypatch, _existing(account_types=["IPMI"]), vendor="dell")
    assert "AccountTypes" not in sent2[0], "요구하지 않는 Family 에 AccountTypes 를 보냈다"


def test_post_write_state_mismatch_is_surfaced(monkeypatch):
    """재인증이 되더라도 계정 상태가 기대와 다르면 그 사실이 결과에 남는다."""
    out, _ = _repair(monkeypatch, _existing(),
                     reread={"UserName": "someone_else", "Enabled": True})
    assert out["recovered"] is True          # 자격은 통했다
    assert out["post_write_state"]["username"] == "someone_else"
    joined = " ".join(f'{e.get("message")} {e.get("detail")}' for e in out["errors"])
    assert "상태가 기대와 다릅니다" in joined


def test_ansible_gate_no_longer_treats_verification_none_as_success():
    """`verification='none'` 을 성공으로 인정하던 한 줄을 없앴다 (audit H-1 / D-3)."""
    text = (REPO / "redfish-gather/tasks/account_service.yml").read_text(encoding="utf-8")
    code = "\n".join(l for l in text.splitlines() if not l.lstrip().startswith("#"))
    assert "verification in ['verified', 'none']" not in code
    assert "verification == 'verified'" in code
