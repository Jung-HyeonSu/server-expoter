"""redfish Round 10 회귀 — multi_node errors 가 status 에 반영되는지 (수렴 tail).

#0 main() 은 _collect_multi_node_topology 의 errors(401/403 포함)를 all_errors 에 merge 후
   _compute_final_status 호출해야 한다. 누락 시 multi_node 인증 실패가 success/partial 로 오분류.
   main() 은 ansible stub 으로 직접 호출 불가 → main()의 merge 라인을 1:1 재현 + 다운스트림
   _compute_final_status 의 401→failed 강제를 함께 검증.
"""
from __future__ import annotations
import emulator_harness as H
rg = H.rg


def test_multi_node_auth_error_forces_failed():
    """multi_node 401 errors merge → final status 'failed' (merge 누락 시 success 오분류)."""
    all_errors = [{"section": "system", "message": "ok-ish"}]
    multi_node = {"errors": [{"section": "multi_node.managers",
                              "message": "HTTP 401: Unauthorized", "detail": "auth denied"}]}
    # main() Round-10 merge 라인 재현
    if isinstance(multi_node, dict):
        all_errors.extend(multi_node.get("errors") or [])
    st, clean = rg._compute_final_status(["system"], [], all_errors)
    assert st == "failed"  # 401 감지 → failed. merge 없었으면 'success'(failed 섹션 0)


def test_no_multi_node_errors_unchanged():
    """multi_node=None(단일노드) → merge no-op, 기존 status 로직 불변."""
    all_errors = []
    multi_node = None
    if isinstance(multi_node, dict):
        all_errors.extend(multi_node.get("errors") or [])
    st, clean = rg._compute_final_status(["system", "cpu"], [], all_errors)
    assert st == "success"


def test_multi_node_dict_errors_merge_present_in_source():
    """main() 소스에 merge 라인이 실재하는지 회귀(누락 시 본 테스트 실패)."""
    import inspect
    src = inspect.getsource(rg.main)
    assert "multi_node.get('errors')" in src or 'multi_node.get("errors")' in src, \
        "main() 에서 multi_node errors merge 누락 (Round 10 회귀)"
