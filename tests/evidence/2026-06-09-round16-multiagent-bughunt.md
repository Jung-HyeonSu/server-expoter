# Round 16 — 멀티에이전트 적대적 버그헌트 루프 (2026-06-09)

## 개요

사용자 요청: "프로젝트 전체에서 버그/개선 사항을 끝까지 찾아라. 수정 후 재검수해 새 문제가
없는지 확인하고, 멀티에이전트로 서로의 결과를 교차 검토하며, 누적 버그가 0이 될 때까지
반복하라. 고친 부분이 다른 기능을 깨뜨리지 않았는지도 반드시 확인하라."

방법: Workflow 기반 멀티에이전트 오케스트레이션. 매 pass 마다 다수의 finder agent 가 영역별로
결함을 탐지하고, **독립 skeptic agent** 가 각 finding 을 실제 코드 기준으로 **반증(refute)** 시도
→ 살아남은 것만 confirmed. confirmed 는 메인 세션이 코드에서 직접 재검증(rule 95 R2) +
Jinja2 렌더 / Python 실행으로 동작 확인(rule verification) 후 fix. 각 pass 는 직전 pass 의
**diff 를 적대적으로 재검수**(회귀 검출) + 신규 영역 탐색을 함께 수행.

## 기준선 (offline)

- pytest: **1022 passed, 4 skipped** (시작) → **1029 passed, 4 skipped** (종료; +7 회귀 테스트)
  - 명령: `pytest tests/ --ignore=tests/e2e_browser -m "not live"`
  - e2e_browser 1건은 live Jenkins(10.100.64.152:8080) 도달 필요 — 본 환경 미도달, **코드 버그 아님**
- `verify_vendor_boundary.py` / `verify_harness_consistency.py` / `output_schema_drift_check.py` PASS
- 환경 제약: 본 환경(Windows)에 `ansible-playbook` CLI 부재 → playbook 런타임 검증은 Jenkins Agent 위임.
  검증 가능 게이트 = **pytest + py_compile + yaml.safe_load + Jinja2 직접 렌더 + scripts/ai/verify_*.py + hook**

## pass 별 결과

| Pass | 영역 | candidates | confirmed | fixed | refuted | diff-회귀 |
|---|---|---|---|---|---|---|
| 1 | 9 영역 (redfish core/sections/multinode+account / precheck / py-plugins / ansible normalize·os·esxi-redfish / adapters-schema) | 12 | 10 | 9 | 2 | — |
| 2 | R1 diff 회귀검수 + 신규(rf system/oem/detect · net/fw/boot/thermal · esxi · plugins · normalize) | 3 | 1 | 1 | 2 | **0** |
| 3 | R2 diff 회귀 + parse-heavy task files (os-linux/os-windows/esxi-collect/redfish-tasks) | 2 | 2 | 2 | 0 | **0** |
| 4 | R3 diff 회귀 + normalize-jinja / windows-rest / cross-cutting | 2 | 2 | 2 | 0 | **0** |
| grep-sweep | None-class / membership-class 전수 (에이전트 보완) | — | 1 | 1 | — | — |
| 5 | **수렴 확인** (cumulative diff 회귀 + rf-lib-remaining/os-linux/esxi holistic) | 0 | **0** | 0 | 0 | **0** |

**총 15 fix.** confirmed 추이: **10 → 1 → 2 → 2 → 0 (수렴)**.
**회귀 검수: pass 2~5 diff reviewer 전부 confirmed 0건** — 내 fix 가 기존 기능을 깨뜨리지 않음을
**4연속 pass** 독립 검증.

## 교차검토 충돌 1건 — 해소 (listening_ports)

pass 1 에서 두 verifier 가 정반대 판정:
- Linux finder: `listening_ports` 는 `int[]` 가 정본, gather_runtime 의 `str[]` 가 버그 → int[] 로 고쳐라
- Windows refuter: `str[]` 가 정본(de-facto), `int[]` 아티팩트가 stale → 코드 정상

**메인 세션 ground-truth 조사로 해소**: 정본 빌더 `gather_runtime.yml`(Linux+Windows 양쪽) + 5개
`schema/output_examples/*.jsonc`(`// (string)` 주석) + 실장비 캡처(cycle-016 / jenkins-full-sweep)
모두 **`str[]`**. `int[]` 은 field_dictionary 주석 + docs + 2 baseline 만(stale). Linux 를 int[] 로
"고쳤다면" Linux↔Windows **불일치(회귀)** 를 새로 유발할 뻔. → **코드 무변경, stale int[] 아티팩트를
str[] 로 정정**. 어떤 테스트도 listening_ports 타입을 assert 하지 않음(OS_CRITICAL/FIELD_MAP/ARRAY_FIELDS
부재) 확인 → baseline 변경 안전.

## 적용한 fix (파일별)

### redfish-gather/library/redfish_gather.py
- **[crash]** `gather_power`: `PowerControl` 자체가 비-list(dict/int) 오염 시 `pc_list[0]` KeyError(0)/
  TypeError → power 섹션 전체(이미 수집한 PSU 포함) 유실. `isinstance(pc_list, list)` 가드 추가 (sibling
  PowerSupplies `_dicts` 패턴 일관)
- **[improvement]** multi-node `gather_managers_multi`/`gather_systems_multi`/`gather_chassis_multi` 멤버
  순회에 `_capped` DoS 상한 적용 (file 전역 컨벤션 일관 — 멤버당 1~6 GET)

### common/library/precheck_bundle.py
- **[crash]** `tcp_check`/`ssh_banner_check`: `socket.socket()` 를 try 밖에서 호출 → IPv6 비활성 host 의
  AF_INET6 주소군에서 `OSError(EAFNOSUPPORT)` 가 모듈 전체를 죽임. try 안으로 이동 + `sock=None` +
  finally 가드 → 다음 주소군(IPv4) graceful
- **[improvement]** `http_get`: urlopen 을 `with` 컨텍스트로 → 응답 소켓 결정적 close (probe+auth 다회 호출)

### module_utils/adapter_common.py
- **[crash]** 빈 `match:`(YAML null → `{'match': None}`) adapter 1개가 `adapter_specificity`/
  `adapter_match_score` 의 `None.get()` AttributeError 로 **adapter_loader 전체 lookup abort**(매칭된 정상
  adapter 까지 유실). 3 함수 `adapter.get("match") or {}` 정규화

### os-gather (Linux + Windows)
- **[crash, HIGH]** windows `gather_cpu`: JSON null/비-str `manufacturer` 에 `'GenuineIntel' in None`
  TypeError → block rescue → **host 전체 failed**(전 섹션 유실). `(x | default('') or '') | string` 강제
  (summary + fragment 2곳). default('') 는 undefined 만 치환하는 함정
- **[improvement]** windows `gather_memory` summary: null Manufacturer/PartNumber 가 `'None'` 문자열로
  누설 → slots 루프와 동일 truthy 가드
- **[improvement]** windows `gather_network`: ① null-speed NIC 가 summary group 에 포함(Linux 가드 일관)
  ② null `status` link_status `'none'` 누설 → `if n.status` truthy 로 `'unknown'` fallback
- **[improvement]** linux `gather_users`: uid 가 문자열이라 `sort(attribute='uid')` lexicographic(999>1000
  역전) → int 키 수치 정렬(출력 dict 보조키 미노출, 2 경로)
- **[improvement]** linux `gather_storage`: lsblk virtio disk `"model": null` → `is defined` 통과 후
  `None|trim='None'` 누설 → truthy 가드(2 경로). **grep-sweep 검출(에이전트 미검출)**

### esxi-gather/tasks/collect_runtime.yml
- **[logic]** default gateway: vnic-fallback 의 `{% set gw %}` 가 `for` 루프 안이라 loop-scoped → 바깥
  미반영(vnic-only 토폴로지에서 gateway 유실). `namespace(v=...)` 로 정정(normalize_network 패턴 일관)

### redfish-gather/tasks/normalize_standard.yml
- **[logic]** null `ProcessorType` 가 `default('')` 통과 후 `'NONE'` 이 되어 CPU 필터에서 **제외**(주석
  의도 "null=CPU 간주" + Python `_normalize_cpu_raw` `or ''` 와 반대 → legacy-BMC CPU 미집계).
  `default('', true)` 로 falsy(None) → '' 강제

### schema / docs (listening_ports 정정 — 코드 무변경)
- `schema/field_dictionary.yml` 주석 `int[]`→`str[]`, `docs/contract/02-output-envelope.md`, `docs/ai/CURRENT_STATE.md`,
  `schema/baseline_v1/{ubuntu,rhel810_raw_fallback}_baseline.json` (실장비 캡처 = str[] 근거)

## 반증된 finding (false positive — 미수정)

| finding | 반증 사유 |
|---|---|
| normalize_vendor substring 매칭 오탐 | R15 에서 이미 adjudicate, 의도된 fallback, 현 트리거 0 (canonical 입력만 도달) |
| windows listening_ports str[] = 버그 | str[] 가 정본(위 충돌 해소 참조) — 코드 정상 |
| adapter_loader non-dict facts 미coerce | facts 는 module probe_facts(항상 dict) 유래 — 비-dict 비현실 |
| build_correlation serial_number `is defined` 누락 | `undefined is mapping` → False(무crash), `_merged_data.system` 항상 init — cosmetic |

## 미적용 (deferred — 런타임 영향 0)

- vendor `tasks/vendors/{fujitsu,quanta,hpe,...}/collect_oem.yml`/`normalize_oem.yml`: 어떤 include 도
  없어 **전혀 실행 안 됨**(intentional placeholder, CLAUDE.md "placeholder 상태" 명시). 내부 `when:`
  가드가 `_rf_raw_collect.systems`(모듈 미emit 키) 참조라 wiring 시에도 dead — 향후 OEM 확장 시 모듈에서
  raw Oem 보존 + 본 파일 repoint 필요. NEXT_ACTIONS 등재.
- Jinja 템플릿 회귀 하네스 부재(Ansible Jinja unit-test 패턴 미존재) — windows cpu/storage/network 등
  본 cycle fix 는 Jinja2 직접 렌더로 검증했으나 영속 회귀 테스트는 baseline 의존. NEXT_ACTIONS 등재.

## 추가 검증 (class grep-sweep + 프로젝트 detector)

| sweep / detector | 결과 |
|---|---|
| None-class (`default('')`/`default(none)`/`is defined` → JSON null 미처리) | 잔여 0 (5건 fix 후 grep empty) |
| membership-class (`'lit' in <None-able-uncoerced>`) | 잔여 0 (windows cpu 외 전부 `\| lower/string` coerce 또는 `x in [list]`) |
| loop-scope (`pre_commit_jinja_namespace_check.py` 77 YAML 전수) | flagged **0/77** |
| `verify_vendor_boundary.py` / `verify_harness_consistency.py` / `output_schema_drift_check.py` | PASS |

## 회귀 (영향 분석)

- pytest 1029 PASS (+7: power 컨테이너 타입 3 / multi-node cap 3 / adapter null-match 1)
- baseline 변경(ubuntu/rhel810 listening_ports): 실장비 캡처 근거 + 어떤 테스트도 타입 미assert → 회귀 0
- 코드 fix 전부 **Additive** — 정상 입력 동작 불변(Jinja2 렌더 / Python 실행으로 before/after 동등 확인)

## 결론

confirmed 추이 **10 → 1 → 2 → 2 → 0**. pass 5 (수렴 게이트) `CONVERGED: true`. 3대 재발 class
(None-handling / membership / loop-scope) grep-sweep + 프로젝트 detector 로 전수 확인. 4연속 diff-회귀
검수 0건. **누적 버그 0 수렴 + 부작용 0 검증 완료.**
