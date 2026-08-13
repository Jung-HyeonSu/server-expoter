# ADR 2026-08-13 — Redfish vendor OEM task 층 제거

- 상태: Accepted
- 결정: 사용자 (2026-08-13 대화)
- 작성: AI (Claude Code)
- 관련 rule: 12 R3 (vendor 확장 지점), 22 (fragment 철학), 92 R2 (Additive)

## 컨텍스트 (Why)

`redfish-gather/tasks/vendors/` 에 9 vendor × collect/normalize = 18개 task 파일이
있었고, `adapters/redfish/*.yml` 25개가 `collect.oem_tasks` / `normalize.oem_tasks`
로 이들을 가리켰다. `site.yml` 이 표준 normalize 뒤에 이 단계를 include 했다.

처음에는 "dell/lenovo/supermicro 3종이 placeholder" 로 봤다. 조사해 보니 그보다
나빴다 — **18개 전부가 모듈 출력에 없는 경로를 읽고 있었다.**

### 코드 근거

`redfish_gather` 모듈이 실제로 내보내는 것:

| 위치 | 내용 |
|---|---|
| `redfish_gather.py:7238-7243` | 최상위 반환에 `systems` / `chassis` / `managers` 가 **없다** |
| `:4793-4811` | `data` 하위에 `chassis` 가 **없다** |
| grep `"'Oem':"` | 대문자 `Oem` 을 출력 키로 쓰는 곳 **0건** |
| `:2089`, `:2102`, `:2288-2300` | 소문자 `'oem'` 에 정제된 형태로만 내보낸다 |

그런데 task 들이 읽던 경로는 이랬다.

- fujitsu / quanta / hpe — `_rf_raw_collect.systems[0].Oem.*`
  → `when: ... systems is defined` 가 **항상 거짓**
- cisco / huawei / inspur — `_rf_raw_collect.data.system.Oem.*`,
  `data.chassis.Oem.*` → `| default({})` 가 **항상 `{}`**
- dell / lenovo / supermicro — 5개 fragment 를 빈 값으로 set_fact 하고 끝 (placeholder)

### 실장비 확인

lab BMC 8대(Dell 5, Cisco 1, HPE 1, Lenovo 1)의 성공 envelope 를 열어 봤다.

| 확인 항목 | 결과 |
|---|---|
| task 가 쓴다던 `data.bmc.oem_<vendor>` | **8대 전부 0개** |
| 라이브러리가 채우는 `data.bmc.oem` | **8대 전부 존재** |

CSUS/Superdome 도 같다 — `hpe_csus_3200_baseline.json` 에 task 가 쓴다던
`data.bmc.oem_hpe_superdome` 은 없고 `data.multi_node` 가 있다. 후자는
`manager_layout` 을 받은 라이브러리(`_collect_multi_node_topology`)가 채운 것이다.

### 부수 사실

- `redfish-gather/tasks/vendors/cisco/*` 는 어떤 adapter 도 가리키지 않는 dead file 이었다
- 성공 경로에는 `merge_fragment` 호출이 없었다 (rescue 경로에만). 그래서 설령 task 가
  fragment 를 채웠어도 **직접 merge 를 부르지 않으면 조용히 사라지는** 구조였다

## 결정 (What)

vendor OEM task 층을 통째로 제거한다.

- `adapters/redfish/*.yml` 25개에서 `oem_tasks` 선언 **50건** 제거.
  `strategy: standard_plus_oem` 표기도 `standard_only` 로 정정 (읽는 코드는 없지만
  사람이 본다)
- `redfish-gather/tasks/vendors/` 18개 파일 + 9개 디렉터리 삭제
- `redfish-gather/site.yml` 의 OEM block 제거. 그 자리에 제거 사유를 주석으로 남긴다

**envelope 변화 0.** 어차피 빈 fragment 였다. `data.system.oem` / `data.bmc.oem` /
`data.multi_node` 는 라이브러리 경로라 그대로 남는다.

### 앞으로 OEM 확장이 필요하면

라이브러리의 `_extract_oem_{hpe,dell,lenovo,supermicro,cisco}`(`:1530~1726`)와
Manager OEM(`:2288-2300`)을 넓힌다. mock 과 테스트가 이미 있는 검증된 경로다.
Ansible task 층에서 별도 `uri` 를 부르는 방식은 인증·타임아웃·계정 잠금을 다시
다뤄야 해서 비용이 크다.

rule 12 R3 의 "vendor 확장 지점" 은 adapter YAML 과
`redfish-gather/tasks/vendors/` 둘 다였는데, 후자가 사라졌다. adapter YAML 이
남아 있으므로 vendor 차이를 공통 코드에 넣지 않는다는 계약 자체는 유지된다.

## 결과 (Impact)

- adapter 25개 수정, task 18개 삭제, site.yml block 1개 제거
- 테스트 2건을 계약이 바뀐 만큼 다시 썼다
  - `test_huawei_normalize_oem_key_is_oem_tasks` → `test_no_adapter_declares_vendor_oem_tasks`
    + `test_vendor_oem_task_directory_is_gone` (선언·디렉터리가 되살아나는 것을 막는다)
  - `test_m_e2_collect_oem_reuses_hpe` → `test_m_e2_multi_node_comes_from_manager_layout_not_oem_task`
    (지켜야 할 계약은 OEM task 가 아니라 `vendor_notes.manager_layout` 이다)
- pytest 3,045 통과 / 3채널 syntax-check 통과 / envelope 변화 0

## 대안 비교 (Considered)

**(A) 입력 경로를 고쳐 살린다.** 18개 파일의 `systems[0].Oem.*` 를 실제 키
`data.system.oem` 으로 바꾸고 `merge_fragment` 호출을 넣는다. 기각 —
그러면 `bmc.oem_<vendor>` 에 값이 차기 시작해 **envelope 가 바뀐다**. schema 3종
갱신 + 영향 vendor baseline 회귀가 따라붙는다(rule 13 R1). 게다가 그 값은
라이브러리가 이미 `data.bmc.oem` 으로 내보내는 것과 **같은 원본**이라, 같은 데이터를
두 경로로 내보내게 된다.

**(B) placeholder 3종만 지운다.** 처음 승인받은 범위다. 기각 — 조사 결과 나머지
6개도 같은 이유로 무효였다. 3개만 지우면 "나머지는 동작한다" 는 인상을 남긴다.

**(C) 그대로 둔다.** 기각 — 죽은 include 가 25개 adapter 에 선언으로 박혀 있으면
다음 작업자가 "OEM 은 여기서 확장한다" 고 읽는다. 실제로 2026-08-10 에 huawei/inspur
의 키 이름을 고치는 작업이 있었는데, 키를 고쳐도 어차피 값이 안 나오는 상태였다.
