# T-01 — HPE adapter 오선택 (DL380 Gen11 → hpe_ilo7)

## 우선순위
**MED** — 현재 sections 8/10 수집 정상 작동. OEM tasks 가 Gen12 specific path 사용 시 silent fail 가능성.

## 영역
- `redfish-gather/tasks/detect_vendor.yml` (probe facts 추출)
- `redfish-gather/library/redfish_gather.py` (무인증 probe 응답)
- `module_utils/adapter_common.py` (adapter 점수 + disqualify 로직)
- `adapters/redfish/hpe_*.yml` (priority 및 match.firmware_patterns)

## 증상

직전 세션 빌드 #139 (`main` HEAD = `80b280be`) 결과:

```
ip=10.50.11.231 vendor=hpe adapter=redfish_hpe_ilo7 sections=8/10 status=success
                                  ↑↑↑
                                  실제 host = DL380 Gen11 (iLO 6 v1.73)
                                  정확 매칭 = redfish_hpe_ilo6 (priority=100)
                                  현재 매칭 = redfish_hpe_ilo7 (priority=120, Gen12 adapter)
```

## 근본 원인 (직전 세션 시뮬레이션 결과)

`module_utils/adapter_common.py` 의 `adapter_match_score` 점수 시뮬레이션:

| 케이스 | facts | 선택된 adapter | 비고 |
|---|---|---|---|
| A | vendor=HPE, model=`ProLiant DL380 Gen11`, firmware=`iLO 6 v1.73` | hpe_ilo6 (100345) | **정확** |
| B | vendor=HPE, model=`ProLiant DL380 Gen11`, firmware=`` | hpe_ilo6 (100320) | 정확 |
| **C** | **vendor=HPE, model=``, firmware=``** | **hpe_ilo7 (120520)** | **오선택** |

→ 케이스 C 가 실제 발생. detect_vendor probe 가 무인증으로 model/firmware 추출 못 한 것.

## 검증 근거

직전 세션 무인증 curl (`https://10.50.11.231/redfish/v1/` admin/__REDACTED__ 미사용):

```
ServiceRoot:
  Vendor: HPE
  Product: ProLiant DL380 Gen11    ← 무인증으로도 사용 가능
  Oem.Hpe 키 존재
```

그러나 `detect_vendor.yml` 의 facts.firmware / facts.model 추출 path:

```yaml
firmware: "{{ ((_rf_probe_result.data | default({}, true)).get('bmc') | default({}, true)).get('firmware_version', '') }}"
model: "{{ ((_rf_probe_result.data | default({}, true)).get('system') | default({}, true)).get('model', '') }}"
```

`_rf_probe_result.data.bmc.firmware_version` 와 `data.system.model` 만 사용. `_rf_probe_result.data.system_root.product` 같은 ServiceRoot 직접 추출 없음. → 무인증 probe 가 Manager/Systems 인증 요구 path 에서 None 반환 → facts empty.

## 작업 계획

### Step 1: 가설 검증 (15분)

`redfish-gather/library/redfish_gather.py` 의 probe 함수 (무인증 호출) 가 어디까지 채우는지 확인:
- ServiceRoot 응답을 어떻게 `data.*` 로 매핑하는지
- `data.system_root` 또는 `data.product` 같은 ServiceRoot 직접 추출 필드 있는지

### Step 2: 옵션 비교 (option-generator skill)

| 옵션 | 영향 |
|---|---|
| **A. ServiceRoot Product 활용** | `detect_vendor.yml` 에 `model: ServiceRoot.Product` fallback path 추가. HPE / Dell 등 ServiceRoot 에 Product 노출 vendor 만 효과 |
| **B. probe 무인증으로 Manager/Systems 시도** | 무인증 401 응답 normal — 일부 BMC 가 무인증 일부 path 허용 시 활용 |
| **C. priority 재조정** | `hpe_ilo7` priority 120 → 90 (model_patterns Gen12 명시 없을 때 hpe_ilo6 우선). 다만 commit `1387b505` 가 ilo7 priority 의도 — 사용자 확인 필요 |
| **D. adapter_match_score 에 facts empty 케이스 fallback 로직** | facts.firmware + facts.model 모두 empty 시 priority 가장 낮은 adapter 우선 (보수적 선택) |

권장: **A + 회귀 시 hpe_ilo6 매칭 검증**. ServiceRoot.Product 는 무인증 응답에 있음 (직전 세션 실증).

### Step 3: 구현 + 회귀

- `task-impact-preview` 먼저 (MED 리스크 — adapter 영역)
- Fix 적용
- Jenkins `hshwang-gather` 빌드 (loc=git, target_type=redfish, bmc_ip=10.50.11.231)
- envelope 검증: `diagnosis.details.adapter_candidate == 'redfish_hpe_ilo6'`
- 다른 vendor 회귀 (Dell idrac10 / Lenovo xcc3 / Cisco ucs_xseries) 영향 0 확인

### Step 4: evidence 갱신

`tests/evidence/2026-05-11-hpe-ilo6-gen11-adapter-fail.md` 의 잔여 후속 #1 항목 RESOLVED 처리.

## 산출물

- `redfish-gather/tasks/detect_vendor.yml` (또는 `library/redfish_gather.py`) 패치 1건
- Jenkins 빌드 회귀 통과 (envelope 확인)
- `tests/evidence/2026-05-11-hpe-ilo6-gen11-adapter-fail.md` 갱신
- commit + push (github + gitlab)

## 위험

- 다른 vendor 의 probe facts 추출 path 가 같은 코드를 공유 — 변경 시 회귀 영향
- ServiceRoot.Product 형식이 vendor 별로 다를 수 있음 (Dell / Cisco 표준 미확인)
