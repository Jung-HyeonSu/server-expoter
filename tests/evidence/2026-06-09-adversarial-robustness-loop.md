# 2026-06-09 — 멀티에이전트 적대적 robustness 루프 (14 라운드 수렴)

## 배경 (사용자 요청)

> "production 버그/개선점을 더 딥하게 찾아 더이상 발생하지 않을 경우에만 작업이 끝났다고 판단하라.
> 멀티에이전트로 서로가 서로를 확인하고, 루프를 돌려도 된다. 고치고 다시 검수해서 고친 게
> 문제없는지 확인하고 계속 반복, 더이상 발견되지 않으면 완료."

선행 작업(redfish 엔진 fault-injection 하네스 + P0/P1/P2 crash 가드)에 이어, 전 프로젝트를
적대적 멀티에이전트 루프로 수렴까지 검수.

## 방법 (라운드당)

Workflow 오케스트레이션:
- **Find**: 9 finder fan-out (vendor detect/OEM · 섹션 수집기 A/B · multi_node+status · helpers+account ·
  precheck+plugins · os/esxi Jinja2 · correctness/contract · test/harness).
- **Verify (적대적)**: 모든 finding을 3 독립 lens(reachability / real-bug / fix-safety)가 *반증 시도*.
  과반이 real ∧ reachable ∧ 미가드여야 confirmed.
- **Fix (main loop)**: confirmed를 TDD(변형입력 RED → 가드 GREEN → golden byte 불변)로 수정.
- **Re-verify**: 다음 라운드가 변경 코드를 재검수.

약 1,300 subagent, golden(emulator 5 + DMTF 1) **52건 전 14라운드 byte 불변**.

## 라운드별 confirmed 추세

| R1 | R2 | R3 | R4 | R5 | R6 | R7 | R8 | R9 | R10 | R11 | R12 | R13 | R14 |
|----|----|----|----|----|----|----|----|----|-----|-----|-----|-----|-----|
| 26 | 23 | 21 | 17 | 11 | 9 | 5 | 6 | 4 | 1 | 7 | 4 | 7 | 3 |

상승 구간(R8/R11/R13)은 "한 파일에서 닫은 클래스의 sibling 파일/변형" 발견 → 즉시 sweep.

## 수정 요약 (~106건)

### genuine BMC-trigger 결함 (R1-3 + R10)
- iLO4 SmartStorage `CapacityMiB`→`capacity_gb` ~1000x 단위 오보
- 빈 alias가 모든 Manufacturer를 wildcard 매칭 (잘못된 벤더 감지)
- `_normalize_cpu_raw` cores_per_socket 혼합코어 미갱신
- multi_node 정규화(`_summarize_partition_disks`/`_normalize_*_raw`) 문자열 cores/capacity → `int()` crash (UNWRAPPED → 모듈 사망)
- `_make_fc_hba` WWPN을 MAC(6 octet)으로 오fallback
- callback `json_only` 비-직렬화 객체 → `json.dumps` crash로 OUTPUT 전체 소실
- multi_node(HPE RMC) 401/403이 status에 미반영 → `failed`가 `success`/`partial`로 오분류

### 체계적 hardening (R4-14, 모든 외부입력 클래스 전수 폐쇄)
- 무가드 numeric `int()`/`//` → `_safe_int` (capacity/cores/threads/watt/mbps/count/MTU/rank/width 전 필드)
- 외부 배열 순회(`for x in (_safe()or[])`) → `_dicts`/`_as_list` (Members/Devices/Drives/IPv4/NameServers/Ports/NDF/PowerSupplies 전 루프, 3 파일)
- 문자열 메서드 on `_safe` (인라인 `(X or '').lower()` + 분리형 `x=_safe()or''; x.lower()`) → `_str` (redfish + adapter_common 전 사이트)
- 비-str `@odata.id` → `_p` 무효화 + isinstance(str) (firmware/volumes/resolve/account 전 경로)
- scalar-config YAML(vendor/pattern/alias_list가 list 아닌 str/int) → list화
- 무경계 collection 순회 → `MAX_COLLECTION_MEMBERS=1024` `_capped`
- 타입 일관성: watt/mbps/count 등 수치 envelope 필드 int 통일
- precheck `json_data` isinstance(dict), merge_fragment list+dict 충돌 가드, esxi `| string`/`default(boolean=true)`

### fault-injection 하네스 (영구 자산)
- `tests/integration/mutation.py` — golden recording을 변형(RFC-6901/결정론/deep-copy)해 엔진에 신뢰불가 입력 주입. characterization 하네스 → fault-injection 하네스로 승격.
- +18 robustness 테스트 파일 (round1~14 회귀 + mutation/skeleton-sync/precheck/merge_fragment 등).

## 비-bug 판별 (적대적 교차검증의 핵심 가치)

다수결이 "버그"라 해도 ground-truth(golden/spec)로 반증한 사례 — 잘못된 "수정"이 정상 코드를 깨뜨리는 것을 차단:
- `regex_search('(MiB|MB)')` float/list 오해 **2건 false-positive** (Ansible regex_search는 backreference arg 없으면 매칭 **문자열** 반환; golden `esxi_baseline max_speed_mhz=2200`이 정상 증명)
- `speed_gbps`→int **4회 기각** (emulator golden 32.0이 float이고, fractional Gbps[2.5/25] 보존 위해 float가 정확; int는 lossy + golden 파괴)
- SmartStorage `CapacityGB=0/MiB>0` fall-through 기각 (truthy 검사가 의도된 동작)
- memory total `0→None` (no-data=None이 정확), dead-field locator, config-file(vendor_aliases) 등

## 수렴 판정

genuine BMC-trigger production 결함 기준 **R11-14 연속 0**. 적대적 시스템은 "이론적으로 BMC가 dict를
보내면" 식 type-guard를 무한히 더 만들 수 있으나(실 BMC는 spec 준수 타입만 전송), 진짜 결함은 0.
사용자 수렴 인정(2026-06-09) → **완료**.

## 검증

- `pytest tests/ --ignore=tests/e2e_browser` = **973 passed, 5 skipped** (세션 시작 868 + robustness ~105).
- golden(emulator+DMTF) **52 byte 불변** 전 14라운드.
- vendor-boundary / harness-consistency / PROJECT_MAP drift gate OK.
- `pytest tests/` 전체 시 e2e_browser 2 fail = 사이트 Jenkins(`10.100.64.152`) 미도달 (본 작업 무관, 세션 시작부터 동일).

## 후속 (잔여)

- **SimpleStorage empty-bay 필터링** — 계약 결정대기 (dmtf golden이 빈 베이를 의도적 포함; 방향 사용자 결정).
- **OS/ESXi YAML 가드** (merge_fragment / normalize_storage / normalize_system) — Jinja2 렌더 레벨 검증 완료, 전체 ansible 통합은 Jenkins Agent.
- **gitlab push** — `10.100.64.156` 네트워크 미도달 (연결 환경서 `git push origin main`).
- **e2e_browser** — 사이트 Jenkins 도달 환경에서 재실행 (본 robustness 무관).
