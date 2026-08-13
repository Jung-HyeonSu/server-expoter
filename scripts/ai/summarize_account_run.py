#!/usr/bin/env python3
"""Redfish 실행 로그(json_only stdout)에서 계정 Reconcile 결과만 뽑아 요약한다.

왜 필요한가:
    실장비 검증 결과를 사람이 눈으로 읽으려면 envelope 전문을 펼쳐야 하는데, 정작
    확인해야 할 것은 몇 개뿐이다 — **표준 계정으로 수집했는가 / 계정 쓰기가 몇 건
    나갔는가 / 어떤 Family 로 판정했는가 / 그 판정의 근거 수준은 무엇인가**.
    2차 실행에서 Write 0 인지도 이 요약으로 바로 비교할 수 있어야 한다.

비밀번호나 그 파생값은 출력하지 않는다 (envelope 자체에 없다).

사용:
    python3 scripts/ai/summarize_account_run.py <run.log> [<run2.log> ...]
"""
from __future__ import annotations

import json
import sys

WRITE_METHODS = {"patch_existing", "patch_empty_slot", "post_new", "delete_repost"}


def envelopes(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            # envelope 은 한 줄 JSON 이지만 **필드 순서는 고정이 아니다**
            # (build_output.yml 작성 순서 / 실패 fallback 경로가 다르다).
            # 첫 키 이름으로 찾으면 경로에 따라 놓친다 — 파싱해서 확인한다.
            if not (line.startswith('{') and '"target_type"' in line):
                continue
            try:
                obj = json.loads(line)
            except ValueError:
                continue
            if isinstance(obj, dict) and 'diagnosis' in obj:
                yield obj


def write_count(acct):
    """이번 실행에서 실제 계정 쓰기가 일어났는가.

    dryrun 이거나 method 가 쓰기 계열이 아니면 0 이다. HTTP status 가 아니라
    **어떤 경로를 탔는가**로 센다 — 2xx 를 성공으로 읽지 않는 계약과 같은 이유다.
    """
    if not acct or acct.get("dryrun") or not acct.get("attempted"):
        return 0
    return 1 if acct.get("method") in WRITE_METHODS else 0


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    rc = 0
    for path in argv[1:]:
        print(f"=== {path} ===")
        total_writes = 0
        for env in envelopes(path):
            det = env.get("diagnosis", {}).get("details", {}) or {}
            acct = det.get("account_service") or {}
            auth = det.get("auth") or {}
            sections = env.get("sections") or {}
            # section 상태 정본은 build_sections.yml 이다: success / not_supported / failed.
            ok = sum(1 for v in sections.values() if v == "success")
            writes = write_count(acct)
            total_writes += writes
            print(f"{env.get('ip'):<15} vendor={str(env.get('vendor')):<7} "
                  f"status={env.get('status'):<8} sections={ok}/{len(sections)} "
                  f"used_role={str(auth.get('used_role')):<9} "
                  f"scope={det.get('credential_scope')}")
            if acct.get("attempted"):
                print(f"{'':15} account: dryrun={acct.get('dryrun')} "
                      f"presence={acct.get('presence')} method={acct.get('method')} "
                      f"recovered={acct.get('recovered')} "
                      f"verification={acct.get('verification')}")
                print(f"{'':15} family={acct.get('family')} "
                      f"evidence={acct.get('evidence')} "
                      f"isolation={acct.get('isolation_basis')} "
                      f"write_http={acct.get('write_http_status')} "
                      f"accepted={acct.get('write_accepted')}")
            else:
                print(f"{'':15} account: 미진입 (표준 인증 성공 → Write 0)")
        print(f"--- account write count: {total_writes}")
        if total_writes:
            rc = max(rc, 1)
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))
