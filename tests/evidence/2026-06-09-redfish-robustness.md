# 2026-06-09 — redfish/gather 견고화 사이클 (fault-injection 하네스 + crash 가드)

## 배경 (사용자 요청)

> "전에 시뮬레이터랑 mock 데이터를 가지고 프로젝트를 견고하게 해달라는 요청을 했었다.
> 하지만 개더링 로직 및 하네스 및 등등 의 것들은 개선을 하지않은채 끝나버렸다.
> 프로젝트를 전수조사해서 개선을 해라."

git 확인 결과 직전 사이클 6 커밋(`ff952bf7`/`df76332b`/`f73224a1`/`e47cdd4b`/`59027bb7`/
`a3ff5b4e`)은 전부 `tests/`·`docs/`·`.claude/`·`Jenkinsfile` 만 변경 — production gather 로직
(`redfish_gather.py`/`os-gather`/`esxi-gather`/`common`)은 0 줄. 즉 record/replay 하네스는
현재 출력을 **golden 으로 고정(characterization)** 만 했고 **버그까지 고정**. 시뮬레이터/mock
인프라를 **실제 코드 견고화에 사용하지 않은** 상태.

## 전수조사 (Explore ×3 + Plan ×1, 교차검증)

- redfish_gather.py: 외부 BMC 신뢰 불가 JSON 파싱. 변형 입력 시나리오 ~40% crash.
- 기존 방어 헬퍼 `_safe`(L252)/`_safe_int`(L65) 존재하나 **multi_node 정규화 경로는 bare int()**
  로 일관성 깨짐(L2858/2976-77/2985/3019).
- 기존 `make_replayer` seam = 변형 입력 주입에 그대로 재사용 가능.
- **교차검증으로 false positive 제거**: Explore 가 지목한 L3365(이미 try/except)·L3175
  (현 call graph 안전)는 Plan 이 반증 → P0 제외.

## 환경 제약

Python 3.11.9 + pytest 9.0.2 동작 / `ansible-playbook` **CLI 부재**(Windows). → redfish 엔진
(순수 Python)·precheck_bundle.py 는 **로컬 100% pytest 검증**. Ansible YAML 은 Jinja2 렌더
레벨까지 검증 후 **전체 통합은 Jenkins Agent**.

## 변경 (TDD: 변형 입력 RED → 가드 GREEN → golden 불변)

| Phase | 변경 | 검증 |
|---|---|---|
| 1 | `tests/integration/mutation.py` (신규) — recording 변형 레이어(RFC-6901/결정론/deep-copy). characterization 하네스를 **fault-injection** 하네스로 승격 | pytest |
| 2 (P0) | `_summarize_partition_disks`/`_normalize_cpu_raw`/`_normalize_memory_raw` bare `int()`/`//` → `_safe_int`. CSUS/Superdome BMC 가 cores/capacity 를 **문자열** 반환 시 모듈 전체 죽던 것(envelope 0) 방어 | pytest(golden 52 byte 불변) |
| 3 (P1) | `_p()` 비-str @odata.id → 무효 path(ServiceRoot 오인 회피) + firmware split isinstance. 1 멤버 @odata.id 오염이 **섹션 전체**(firmware 23건) silent 손실 유발하던 것 → 오염 멤버만 skip | pytest |
| 4 (P2) | `MAX_COLLECTION_MEMBERS=1024` + `_capped`(firmware/memory/drives). 악성/버그 BMC 수천 멤버 → 멤버당 `_get` 무경계 hang 방어. multi_node `partitions[0].get('id')` 방어 | pytest |
| 5 | precheck `_try_redfish_auth` Members[0] 비-dict 가드 + data skeleton 3-파일 동기화 pytest + merge_fragment `list+dict` 충돌 가드(Jinja2 렌더 검증) | pytest(merge 는 Jenkins 통합 후속) |

## 검증 결과 (실측)

```
python -m pytest tests/ -q --ignore=tests/e2e_browser
  → 906 passed, 4 skipped   (직전 868 + 신규 robustness 38)
golden 불변: test_hpe_emulator_replay + test_dmtf_mockup_replay → 52 passed (byte 동일, 매 fix 후 재확인)
전체 collected: 875 → 913 (+38), test_*.py 52 → 57 파일
```

- e2e_browser 2건(Jenkins master `10.100.64.152:8080` Playwright)은 **본 변경 무관** —
  사이트 Jenkins 미도달(네트워크 격리). robustness 게이트에서 제외.

## 핵심 불변식 (golden churn 0)

모든 가드는 **변형 입력에서만** 동작 변경 — 정상 입력은 `_safe_int(n)==int(n)`, cap≫실 멤버수,
mapping 제외가 정상 list+list 불변. ∴ golden suite byte 불변이 안전망. golden 키가 바뀌면 fix 가
정상 경로 침범 → 좁힘.

## 커밋

```
8a917cb test: redfish fault-injection mutation 하네스 추가
ad1fc8d fix: multi_node 정규화 bare int() crash 가드 (P0)
c037ee3 fix: 비-str @odata.id 섹션 전체손실 방어 (P1)
dee9bfe fix: 무경계 collection 순회 상한 + partition id 방어 (P2)
efe582b fix: precheck Systems Members[0] 비-dict 가드 + skeleton sync 테스트
6378453 fix: merge_fragment list+dict 충돌 가드 (additive)
```

## 후속 (Jenkins Agent)

- merge_fragment.yml 가드 **전체 ansible 통합 검증**(Jinja2 렌더는 로컬 통과) — NEXT_ACTIONS.
- (사용자 결정) 여타 Ansible YAML 견고화(os/esxi raw-fallback 파싱)는 별도 cycle.
