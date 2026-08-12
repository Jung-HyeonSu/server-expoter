"""`common/tasks/credential/resolve_and_load.yml` 계약 회귀 (2026-08-12).

판정 로직은 Ansible 템플릿에 있으므로 **production YAML 에서 템플릿을 그대로 뽑아
렌더**한다 (합성 fixture 가 아니다). 렌더 하네스는
tests/e2e/test_failure_reason_contract.py 것을 재사용한다.

잠그는 계약:
    T9   vault 파일 부재      → credential_set_missing
    T10  복호화 실패          → credential_set_undecryptable
    T11  accounts 비어 있음   → empty_accounts (현행 동작 유지)
    T18  재실행 시 자동 반영  → cacheable 0건 / host facts 미등록 (rule 27 R6)
    T19  Secret 비노출        → Secret 을 만지는 태스크는 전부 no_log
    hard cut                  → flat vault 로의 runtime fallback 부재
"""
from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
TASK_REL = "common/tasks/credential/resolve_and_load.yml"
TASK_PATH = REPO / TASK_REL

_spec = importlib.util.spec_from_file_location(
    "_failure_reason_contract_harness",
    REPO / "tests" / "e2e" / "test_failure_reason_contract.py",
)
_harness = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_harness)
_env = _harness._env
_iter_tasks = _harness._iter_tasks

sys.path.insert(0, str(REPO / "module_utils"))
from credential_common import normalize_accounts  # noqa: E402


def _tasks() -> list[dict[str, Any]]:
    """block / rescue / always 안까지 평탄화한 태스크 목록 (generator 를 list 로 고정)."""
    doc = list(yaml.safe_load_all(TASK_PATH.read_text(encoding="utf-8")))[0]
    return list(_iter_tasks(doc))


TASKS = _tasks()
RAW = TASK_PATH.read_text(encoding="utf-8")


def _code_only(text: str) -> str:
    """주석을 제거한 실행 부분만. 주석 속 언급은 동작이 아니다."""
    out = []
    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            continue
        idx = line.find(" #")
        out.append(line[:idx] if idx >= 0 else line)
    return "\n".join(out)


CODE = _code_only(RAW)


def _task_named(part: str) -> dict[str, Any]:
    for task in TASKS:
        if part in (task.get("name") or ""):
            return task
    raise AssertionError(f"{TASK_REL} 에 {part!r} 태스크가 없다")


def _set_fact_template(name_part: str, key: str) -> str:
    facts = _task_named(name_part).get("ansible.builtin.set_fact") or {}
    assert key in facts, f"{name_part!r} 에 {key!r} 없음"
    return facts[key]


def _ansible_env():
    """Ansible 의 `is failed` 테스트를 추가한 렌더 환경.

    NativeEnvironment 에는 없는 Ansible 고유 test 라, 없으면 production 템플릿을
    그대로 렌더할 수 없다.
    """
    env = _env()
    env.tests["failed"] = lambda v: bool(v.get("failed")) if isinstance(v, dict) else bool(
        getattr(v, "failed", False)
    )
    return env


def _render(template: str, ctx: dict[str, Any]) -> Any:
    return _ansible_env().from_string(template).render(**ctx)


_TPL_OUTCOME = _set_fact_template("classify load outcome", "_cred_load_outcome")


def _outcome(exists: bool, load_failed: bool, accounts: list) -> str:
    """production 템플릿으로 outcome 을 계산한다."""
    result = _render(_TPL_OUTCOME, {
        "_cred_vault_stat": {"stat": {"exists": exists}},
        "_cred_vault_load": {"failed": load_failed},
        "_cred_accounts": accounts,
    })
    return str(result).strip()


# ── T9 / T10 / T11: outcome 분류 ─────────────────────────────────────────────
def test_missing_vault_file():
    assert _outcome(exists=False, load_failed=False, accounts=[]) == "credential_set_missing"


def test_undecryptable_vault():
    assert _outcome(exists=True, load_failed=True, accounts=[]) == "credential_set_undecryptable"


def test_empty_accounts():
    assert _outcome(exists=True, load_failed=False, accounts=[]) == "empty_accounts"


def test_loaded():
    accounts = [{"username": "u", "password": "p", "label": "l", "role": "primary"}]
    assert _outcome(exists=True, load_failed=False, accounts=accounts) == "loaded"


def test_missing_beats_undecryptable():
    """파일이 없으면 '복호화 실패' 로 오인하면 안 된다 — 운영자가 볼 원인이 다르다."""
    assert _outcome(exists=False, load_failed=True, accounts=[]) == "credential_set_missing"


def test_outcome_values_are_the_documented_enum():
    found = set(re.findall(r"'(credential_set_\w+|empty_accounts|loaded|not_resolved)'", CODE))
    assert found <= {
        "credential_set_missing", "credential_set_undecryptable",
        "empty_accounts", "loaded", "not_resolved",
    }, f"문서화되지 않은 outcome 값: {found}"


# ── T18: vault 변경 자동 반영 (rule 27 R6) ───────────────────────────────────
def test_no_cacheable_option():
    """`cacheable` 이 들어오면 fact_cache 에 남아 vault 변경이 다음 run 에 반영되지 않는다."""
    assert "cacheable" not in CODE.lower(), (
        f"{TASK_REL}: cacheable 사용 — vault 자동 반영이 깨진다 (rule 27 R6)"
    )


def test_uses_include_vars_not_vars_files():
    """`vars_files` 는 play 파싱 시점에 죽어 OUTPUT 을 못 만든다 (rule 11 envelope 소실)."""
    assert "include_vars" in CODE
    assert "vars_files" not in CODE


def test_include_vars_uses_name_scope():
    """`name:` 없이 로드하면 vault 의 top-level 키가 host var 로 흘러든다."""
    inc = _task_named("include vault")["ansible.builtin.include_vars"]
    assert inc.get("name") == "_cred_vault_data"


# ── T19: Secret 비노출 ───────────────────────────────────────────────────────
def test_secret_touching_tasks_have_no_log():
    """vault 내용을 만지는 태스크는 전부 no_log 여야 한다."""
    must_no_log = ("include vault", "normalize accounts")
    for part in must_no_log:
        task = _task_named(part)
        assert task.get("no_log") is True, f"{part!r} 태스크에 no_log 누락"


def test_summary_debug_prints_no_secret():
    """요약 debug 는 개수와 label 만 출력한다 — username / password 를 찍지 않는다."""
    msg = _task_named("summary")["ansible.builtin.debug"]["msg"]
    assert "password" not in msg
    assert "username" not in msg
    assert "attribute='label'" in msg or 'attribute="label"' in msg
    assert "| length" in msg


def test_no_verbose_dump_of_vault_data():
    """`_cred_vault_data` 를 통째로 debug 하는 태스크가 없어야 한다."""
    for task in TASKS:
        dbg = task.get("ansible.builtin.debug") or {}
        for value in dbg.values():
            assert "_cred_vault_data" not in str(value), (
                f"{task.get('name')!r} 가 vault 내용을 통째로 출력한다"
            )
        assert "var" not in dbg or "_cred_vault_data" not in str(dbg.get("var")), (
            f"{task.get('name')!r} 가 debug var 로 vault 를 노출한다"
        )


# ── hard cut: flat vault 로의 runtime fallback 부재 ──────────────────────────
@pytest.mark.parametrize("legacy", [
    "vault/linux.yml", "vault/windows.yml", "vault/esxi.yml", "vault/redfish/",
])
def test_no_runtime_fallback_to_flat_vault(legacy):
    """구 경로를 런타임에 다시 여는 코드가 있으면 hard cut 이 아니다.

    이게 있으면 신규 vault 준비가 덜 된 상태에서도 '성공한 것처럼' 보여
    이관 실패를 조용히 감춘다.
    """
    assert legacy not in CODE, f"{TASK_REL} 에 구 vault 경로 {legacy!r} 참조"


def test_no_cross_scope_loop():
    """여러 vault 경로를 순회 시도하는 구조가 없어야 한다 (다른 Location/Vendor 금지)."""
    for task in TASKS:
        if "include_vars" in " ".join(task.keys()):
            assert "loop" not in task, (
                f"{task.get('name')!r} 가 include_vars 를 loop 로 돈다 — 교차 시도 구조"
            )


def test_unresolved_scope_never_builds_a_path():
    """scope 를 못 정했으면 include_vars 자체를 타지 않아야 한다."""
    resolved_block = None
    doc = list(yaml.safe_load_all(RAW))[0]
    for node in doc:
        if isinstance(node, dict) and "block" in node:
            resolved_block = node
            break
    assert resolved_block is not None, "resolved block 이 없다"
    assert resolved_block.get("when") == "_cred_reason == 'resolved'", (
        "vault 로딩 block 이 reason=resolved 로 가드되지 않는다"
    )


# ── 정규화 위임 (구현 SoT 1개) ───────────────────────────────────────────────
def test_accounts_normalisation_is_delegated_to_the_filter():
    """Jinja 인라인으로 정규화를 복제하지 않는다 — 순서 보존 계약이 갈라진다."""
    tpl = _set_fact_template("normalize accounts", "_cred_accounts")
    assert "credential_accounts" in tpl, "공통 필터를 쓰지 않는다"
    assert "legacy_single" not in tpl, "정규화 로직이 Jinja 로 복제됐다"


def test_filter_matches_python_reference():
    """필터가 부르는 함수와 이 테스트가 부르는 함수가 같은 구현인지 (동치 확인)."""
    sys.path.insert(0, str(REPO / "filter_plugins"))
    from credential_accounts import credential_accounts

    data = {"accounts": [
        {"username": "b", "role": "recovery"},
        {"username": "a", "role": "primary"},
    ]}
    assert credential_accounts(data) == normalize_accounts(data)
    assert [x["username"] for x in credential_accounts(data)] == ["b", "a"], (
        "필터가 순서를 바꾼다"
    )


# ── 실패해도 envelope 을 잃지 않는다 (rule 11) ───────────────────────────────
def test_task_never_hard_fails():
    """이 task 파일이 `fail:` 로 play 를 죽이면 OUTPUT 이 사라진다.

    판정 결과만 넘기고, 실패 처리는 호출 측 block/rescue 가 한다.
    """
    for task in TASKS:
        assert "ansible.builtin.fail" not in task, (
            f"{task.get('name')!r} 가 fail 을 쓴다 — envelope 소실 위험 (rule 11)"
        )
    inc = _task_named("include vault")
    assert inc.get("failed_when") is False


def test_stat_runs_on_controller():
    """vault 는 controller 파일이다. 대상 host 로 stat 하면 인증 전이라 실패한다."""
    stat_task = _task_named("stat vault file")
    assert stat_task.get("delegate_to") == "localhost"
    assert stat_task.get("become") is False
