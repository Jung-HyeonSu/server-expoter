"""비밀번호 단독 PATCH 계약 / Locked 조건부 전송 / 재인증 확인 간격.

배경 — 2026-08-12 git 리전 실장비 통제 실험 (HPE iLO6 / ProLiant DL380 Gen11 /
Redfish 1.20.0, 계정 /redfish/v1/AccountService/Accounts/4):

    {Password:<길이위반>}                       -> HTTP 400 iLO.2.36.InvalidPasswordLength
    {Password:<길이위반>, Enabled, RoleId}      -> HTTP 200 Base.1.19.AccountModified
    {Enabled, RoleId}          (Password 없음)  -> HTTP 200 Base.1.19.AccountModified
    {Password, Enabled, Locked, RoleId}         -> HTTP 400 iLO.2.36.PropertyNotWritableOrUnknown ['Locked']

  같은 값인데 단독으로 보내면 길이 검사에 걸리고, 다른 속성과 묶으면 통과한다.
  즉 iLO 는 Password 가 다른 속성과 함께 오면 **검사도 적용도 하지 않고 버린다.**
  그런데 응답은 200 + AccountModified 라 성공과 구분되지 않는다 — 아무 속성도 바뀌지 않는
  {Enabled, RoleId} PATCH 도 똑같은 메시지를 준다. 그래서 응답만으로는 절대 알 수 없고,
  Family 가 쓰기 **전에** 방식을 정해야 한다.

  이 결함의 관측된 결과(수정 전): PATCH 가 200 으로 수락되고 write_accepted=true 인데
  표준 자격 재인증은 계속 401 → verification=failed → 표준 Gathering 실패.
  2회 연속 실행에서 동일 재현.

두 번째 결함: 재인증 확인 간격이 장비가 선언한 인증 실패 패널티보다 짧았다.
  iLO 는 AuthFailureDelayTimeSeconds=10 / AuthFailuresBeforeDelay=1 을 선언한다.
  고정 (0,1,5)=6초 안의 재인증은 비밀번호를 옳게 썼어도 전부 401 이 된다.
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

TARGET = "infraops"
SLOT = "/redfish/v1/AccountService/Accounts/4"


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    monkeypatch.setattr(rg.time, "sleep", lambda *_: None)


def _account(**over):
    a = {"slot_uri": SLOT, "id": "4", "username": TARGET, "role_id": "Administrator",
         "enabled": True, "locked": None, "account_types": None,
         "password_change_required": False, "has_username_key": True}
    a.update(over)
    return a


def _disc(accounts, role_ids=("Administrator", "Operator", "ReadOnly"), service=None):
    return {
        "service_uri": "AccountService", "accounts_uri": "AccountService/Accounts",
        "roles_uri": "AccountService/Roles",
        "service": service if service is not None else {},
        "policy": rg._account_policy_of(service),
        "role_ids": list(role_ids), "accounts": list(accounts),
        "member_total": len(accounts), "member_read": len(accounts),
        "enumeration": rg.ENUM_COMPLETE, "manager": None, "errors": [],
        "auth_status": 200,
    }


def _install(monkeypatch, accounts, service=None, role_ids=("Administrator", "Operator", "ReadOnly")):
    """PATCH 본문을 기록하고, 재조회/재인증은 항상 통과시키는 seam."""
    bodies = []
    monkeypatch.setattr(rg, "account_service_discover",
                        lambda *a, **k: _disc(accounts, role_ids, service))
    monkeypatch.setattr(rg, "_patch",
                        lambda ip, path, body, u, p, t, v, extra_headers=None:
                        (bodies.append(dict(body)), (200, {}, None))[1])
    monkeypatch.setattr(rg, "_get", lambda *a, **k: (200, {"UserName": TARGET,
                                                          "RoleId": "Administrator",
                                                          "Enabled": True}, None))
    monkeypatch.setattr(rg, "_get_response_etag", lambda *a, **k: None)
    return bodies


def _provision(vendor, **kw):
    return rg.account_service_provision(
        "10.0.0.1", vendor, "rec", "<rec>", TARGET, "<tgt>",
        "Administrator", 5, False, dryrun=False, **kw)


# ── Locked 는 실제로 잠겼을 때만 보낸다 ──────────────────────────────────────
def test_locked_is_not_sent_when_account_is_not_locked(monkeypatch):
    """잠기지 않은 계정에 Locked:false 를 보내는 것은 no-op 인데 본문 전체를 죽인다.

    실측: iLO6 는 ManagerAccount 에 Locked 속성이 아예 없어 HTTP 400 으로 요청 전체를
    거부했고, Lenovo XCC 는 노출은 하되 read-only 라 거부했다. 두 경우 모두 drop 후
    retry 라는 **추가 쓰기 1회**로만 통과했다 (Lockout 예산 낭비).
    """
    bodies = _install(monkeypatch, [_account(locked=False)])
    _provision("lenovo")
    assert bodies, "PATCH 가 나가지 않았다"
    assert "Locked" not in bodies[0], f"잠기지 않았는데 Locked 를 보냈다: {bodies[0]}"


def test_locked_is_not_sent_when_device_does_not_expose_it(monkeypatch):
    bodies = _install(monkeypatch, [_account(locked=None)])
    _provision("lenovo")
    assert "Locked" not in bodies[0]


def test_locked_false_is_sent_when_account_is_actually_locked(monkeypatch):
    """잠금 해제 경로는 **Locked 가 writable 인 Family 에서** 그대로 살아 있어야 한다.

    2026-08-12 (rev.2): vendor 를 lenovo → huawei 로 바꿨다. Lenovo XCC 는 `Locked` 를
    GET 에만 노출하고 공식 Account Update 목록에는 없어(03 §14) 이제 보내지 않는다.
    Huawei 최신 iBMC 는 `Locked` 를 GET/PATCH 로 공식 정의한다(07 §5.1).
    "Locked 를 전 Vendor 에서 제거" 도 "전 Vendor 에 전송" 도 둘 다 틀렸다.
    """
    bodies = _install(monkeypatch, [_account(locked=True)])
    _provision("huawei")
    assert bodies[0].get("Locked") is False


# ── Family 계약: 비밀번호 단독 PATCH ─────────────────────────────────────────
def test_hpe_ilo5plus_writes_password_alone(monkeypatch):
    """iLO 계열은 Password 를 단독으로 써야 실제로 적용된다."""
    bodies = _install(monkeypatch, [_account()])
    out = _provision("hpe")
    assert out["family"] == "hpe_ilo5plus"
    assert out.get("isolated_write") is True
    assert set(bodies[0]) == {"Password"}, f"첫 PATCH 가 단독이 아니다: {sorted(bodies[0])}"


def test_hpe_no_followup_patch_when_nothing_else_differs(monkeypatch):
    """권한/활성이 이미 맞으면 추가 쓰기를 하지 않는다 (쓰기 1회)."""
    bodies = _install(monkeypatch, [_account(enabled=True, role_id="Administrator")])
    out = _provision("hpe")
    assert len(bodies) == 1, f"불필요한 추가 PATCH: {bodies}"
    assert out.get("followup_properties") in (None, [])


def test_hpe_followup_patch_only_carries_properties_that_differ(monkeypatch):
    bodies = _install(monkeypatch, [_account(enabled=False, role_id="ReadOnly")])
    out = _provision("hpe")
    assert set(bodies[0]) == {"Password"}
    assert len(bodies) == 2, "달라진 속성이 있는데 후속 PATCH 가 없다"
    assert set(bodies[1]) == {"Enabled", "RoleId"}
    assert out["followup_accepted"] is True
    assert out["followup_properties"] == ["Enabled", "RoleId"]


def test_non_isolated_family_still_bundles_password(monkeypatch):
    """Lenovo XCC 사이트 실측(비밀번호 단독 PATCH 시 권한 cache 손상)을 회귀시키지 않는다."""
    bodies = _install(monkeypatch, [_account()])
    out = _provision("lenovo")
    assert out.get("isolated_write") in (None, False)
    assert "Password" in bodies[0] and "Enabled" in bodies[0] and "RoleId" in bodies[0]


# ── 실제 iLO 의미를 재현한 수렴 테스트 ───────────────────────────────────────
def _ilo_device(monkeypatch, accounts, stored="<old>", target="<tgt>"):
    """실측한 iLO 동작을 그대로 흉내 내는 가짜 장비.

    - 본문에 Locked 가 있으면            -> 400 PropertyNotWritableOrUnknown
    - Password 가 다른 속성과 함께 오면  -> 200 AccountModified, **비밀번호는 안 바뀜**
    - Password 단독                      -> 200 AccountModified, 비밀번호 반영
    - Systems GET 은 저장된 비밀번호와 일치할 때만 200
    """
    state = {"password": stored}
    modified = {"@Message.ExtendedInfo": [{"MessageId": "Base.1.19.AccountModified"}]}
    rejected = {"error": {"@Message.ExtendedInfo": [
        {"MessageId": "iLO.2.36.PropertyNotWritableOrUnknown", "MessageArgs": ["Locked"]}]}}

    def _fake_patch(ip, path, body, u, p, t, v, extra_headers=None):
        if "Locked" in body:
            return 400, rejected, None
        if "Password" in body and len(body) == 1:
            state["password"] = body["Password"]
        return 200, modified, None

    def _fake_get(ip, path, u, p, t, v, *a, **k):
        if str(path).rstrip("/").endswith("Systems"):
            return (200, {}, None) if p == state["password"] else (401, {}, "HTTP 401")
        return 200, {"UserName": TARGET, "RoleId": "Administrator", "Enabled": True}, None

    monkeypatch.setattr(rg, "account_service_discover",
                        lambda *a, **k: _disc(accounts))
    monkeypatch.setattr(rg, "_patch", _fake_patch)
    monkeypatch.setattr(rg, "_get", _fake_get)
    monkeypatch.setattr(rg, "_get_response_etag", lambda *a, **k: None)
    return state


def test_hpe_repair_converges_against_real_ilo_semantics(monkeypatch):
    """수정 후: 표준 비밀번호가 실제로 적용되고 재인증까지 통과한다."""
    state = _ilo_device(monkeypatch, [_account()])
    out = _provision("hpe")
    assert state["password"] == "<tgt>", "비밀번호가 장비에 반영되지 않았다"
    assert out["write_accepted"] is True
    assert out["verification"] == "verified"
    assert out["recovered"] is True


def test_bundled_password_would_not_have_converged(monkeypatch):
    """회귀 방지: 묶어서 보내면 200 이 나와도 비밀번호가 안 바뀐다는 사실 자체를 고정한다."""
    state = _ilo_device(monkeypatch, [_account()])
    code, resp, err = rg._patch("10.0.0.1", SLOT,
                                {"Password": "<tgt>", "Enabled": True, "RoleId": "Administrator"},
                                "rec", "<rec>", 5, False)
    assert code == 200, "장비는 성공처럼 응답한다"
    assert rg.rejected_patch_properties(resp) == set(), "거부 신호도 없다"
    assert state["password"] == "<old>", "그런데 비밀번호는 바뀌지 않았다"


# ── 재인증 확인 간격 ─────────────────────────────────────────────────────────
def test_verify_delays_default_when_device_declares_no_penalty():
    assert rg.account_verify_delays({}) == rg.ACCOUNT_VERIFY_DELAYS
    assert rg.account_verify_delays(None) == rg.ACCOUNT_VERIFY_DELAYS
    assert rg.account_verify_delays({"auth_failure_delay_seconds": 0,
                                     "lockout_duration": 0}) == rg.ACCOUNT_VERIFY_DELAYS


def test_verify_delays_outlast_declared_auth_failure_penalty():
    """iLO 가 선언한 10초를 6초짜리 확인으로 덮으면 옳게 쓴 비밀번호도 401 이 된다."""
    delays = rg.account_verify_delays({"auth_failure_delay_seconds": 10})
    assert sum(delays) > 10, f"총 대기 {sum(delays)}s 가 선언된 패널티 10s 를 넘지 않는다"
    assert delays[:len(rg.ACCOUNT_VERIFY_DELAYS)] == rg.ACCOUNT_VERIFY_DELAYS


def test_verify_delays_use_lockout_duration_when_larger():
    delays = rg.account_verify_delays({"auth_failure_delay_seconds": 2, "lockout_duration": 20})
    assert sum(delays) > 20


def test_verify_delays_are_capped():
    delays = rg.account_verify_delays({"lockout_duration": 100000})
    assert sum(delays) <= rg.ACCOUNT_VERIFY_MAX_TOTAL_SECONDS


def test_verify_schedule_is_reported(monkeypatch):
    service = {"Oem": {"Hpe": {"AuthFailureDelayTimeSeconds": 10}}}
    _install(monkeypatch, [_account()], service=service)
    out = _provision("hpe")
    assert sum(out["verify_schedule_seconds"]) > 10
    assert out["policy"]["auth_failure_delay_seconds"] == 10


# ── Oem 패널티 읽기는 namespace 이름에 의존하지 않는다 ───────────────────────
@pytest.mark.parametrize("namespace", ["Hpe", "Hp", "Dell", "Lenovo", "Public", "SomeNewVendor"])
def test_auth_failure_delay_is_read_from_any_oem_namespace(namespace):
    """rule 12 R1: Oem namespace 이름으로 분기하지 않는다. 키 이름만 본다."""
    policy = rg._account_policy_of({"Oem": {namespace: {"AuthFailureDelayTimeSeconds": 7,
                                                       "AuthFailuresBeforeDelay": 1}}})
    assert policy["auth_failure_delay_seconds"] == 7
    assert policy["auth_failures_before_delay"] == 1


def test_auth_failure_delay_absent_stays_none():
    assert rg._account_policy_of({})["auth_failure_delay_seconds"] is None
    assert rg._account_policy_of({"Oem": {"Hpe": {}}})["auth_failure_delay_seconds"] is None
    assert rg._account_policy_of({"Oem": "not-a-dict"})["auth_failure_delay_seconds"] is None


def test_auth_failure_delay_ignores_non_integer():
    assert rg._account_policy_of(
        {"Oem": {"Hpe": {"AuthFailureDelayTimeSeconds": "10"}}}
    )["auth_failure_delay_seconds"] is None
    assert rg._account_policy_of(
        {"Oem": {"Hpe": {"AuthFailureDelayTimeSeconds": True}}}
    )["auth_failure_delay_seconds"] is None
