# Dell 대표 시리얼 교정 — ServiceRoot.Oem.Dell.ServiceTag (2026-08-11)

> **대상**: Dell 채널 단독. 다른 벤더 무변경.
> **구현 커밋**: `0fb63799`
> **설계·조사 정본**: `docs/ai/contracts/serial-number.md` Part III (29절)

## 1. 무엇을 바꿨나

| | Before | After |
|---|---|---|
| Dell 대표 시리얼 원천 | `GET Systems/{id}` → `SerialNumber` | `GET /redfish/v1/` → `Oem.Dell.ServiceTag` |
| 폴백 | 없음 (null 허용) | 없음 (**실패 처리**) |

`data.hardware.serial` / `correlation.serial_number` 필드 자체와 배선은 무변경.
envelope 13 필드 / sections / field_dictionary entry 추가·삭제 0.

## 2. 실측 대조 (실장비 7대)

수집 명령 — 네트워크 0, 저장된 실장비 응답 재생:

```bash
python -m pytest tests/unit/test_dell_service_tag_serial.py -v
python -m pytest tests/integration/test_real_capture_replay.py -v
```

| 장비 / 출처 | `System.SerialNumber` (미사용) | **채택값 `Oem.Dell.ServiceTag`** |
|---|---|---|
| `real_dell_r740` 미러 (iDRAC9 7.00.00.184) | `CNIVC0098G0600` | **`J0KV603`** |
| `dell` fixture — R740 @10.50.11.162 | `CNIVC009CP0282` | **`2BJ8033`** |
| `dell_r760` fixture — R760 @10.100.15.27 | `CNIVC004950455` | **`64CXJ54`** |
| reference 미러 @10.100.15.28 | `CNIVC004950460` | **`29N1K54`** |
| reference 미러 @10.100.15.31 | `CNIVC004950423` | **`4BP2K54`** |
| reference 미러 @10.100.15.33 | `CNIVC0048R0468` | **`C3BXJ54`** |
| reference 미러 @10.100.15.34 (R760-6) | `CNIVC0048R0159` | **`GSBPK54`** |

7대 전부에서 `Oem.Dell.ServiceTag` 가 존재했고 `SerialNumber` 와 달랐다.

## 3. 동일 장비 채널 간 대조 — Dell R760-6

BMC `10.100.15.34` ↔ OS `10.100.64.96` (동일 물리 장비, `round13_baremetal_pair.json`).

| 채널 | 원천 | 값 |
|---|---|---|
| Redfish (교정 전) | `Systems/{id}.SerialNumber` | `CNIVC0048R0159` |
| **Redfish (교정 후)** | `ServiceRoot.Oem.Dell.ServiceTag` | **`GSBPK54`** |
| Linux | `/sys/class/dmi/id/product_serial` (SMBIOS Type 1) | `GSBPK54` (불변) |

**교정 전 DIFFERENT → 교정 후 SAME.**

재현:

```bash
python -c "
import sys, json, re
sys.path.insert(0, 'redfish-gather/library')
import types
for n in ('ansible','ansible.module_utils','ansible.module_utils.basic'):
    sys.modules.setdefault(n, types.ModuleType(n))
sys.modules['ansible.module_utils.basic'].AnsibleModule = object
import redfish_gather as rg
b = 'tests/reference/redfish/dell/10_100_15_34/'
root = json.load(open(b+'redfish_v1.json', encoding='utf-8'))['_data']
print('Redfish :', rg._resolve_serial_dell(root)[0])
t = open('tests/evidence/2026-04-29-deep-verify/linux/ubuntu-r760-6-baremetal/dmi_system.txt',
         encoding='utf-8', errors='replace').read()
print('Linux   :', re.search(r'Serial Number:\s*(\S+)', t).group(1))
"
```

출력:

```
Redfish : GSBPK54
Linux   : GSBPK54
```

SMBIOS 원본 (`2026-04-29-deep-verify/linux/ubuntu-r760-6-baremetal/`):

```
dmi_system.txt   (Type 1) Serial Number: GSBPK54
dmi_chassis.txt  (Type 3) Serial Number: GSBPK54
dmi_baseboard.txt(Type 2) Serial Number: .GSBPK54.CNIVC0048R0159.
```

→ `CNIVC…` 가 Type 2(보드)에만 있다는 사실이 "보드 제조 시리얼" 판단의 직접 근거다.

## 4. 최종 JSON 두 필드 동일성 (사용자 지시 검증 항목)

| envelope | `data.hardware.serial` | `correlation.serial_number` | raw `Oem.Dell.ServiceTag` | 일치 |
|---|---|---|---|---|
| `schema/baseline_v1/dell_baseline.json` | `2BJ8033` | `2BJ8033` | `2BJ8033` | O |
| `tests/fixtures/outputs/dell_r760_output.json` | `64CXJ54` | `64CXJ54` | `64CXJ54` | O |

`tests/e2e/test_redfish_baseline.py::TestDellServiceTagIsRepresentativeSerial` 가 회귀로 고정.
기대값은 하드코딩하지 않고 대응 fixture 의 `service_root.json` 에서 읽어 비교한다.

배선 무변경 확인: `redfish-gather/tasks/normalize_standard.yml` (system.serial → hardware.serial),
`common/tasks/normalize/build_correlation.yml` (hardware.serial 복사) 두 파일 `git diff` 빈 출력.

## 5. 폴백 금지 실증

Service Tag 를 못 얻은 14가지 경우(키 부재 4종 + 무효값 10종)에서, System 응답에
`SerialNumber` / `SKU` / `ChassisServiceTag` / `NodeID` 가 모두 정상 존재해도 결과 JSON 어디에도
그 값들이 등장하지 않고 `status=failed` 로 끝나는 것을 확인
(`test_never_falls_back_to_other_serial_candidates`).

## 6. 회귀 결과

| 대상 | 결과 |
|---|---|
| `tests/unit/test_dell_service_tag_serial.py` (신규 41건) | PASS |
| `tests/unit/` 전체 | 1186 passed |
| `tests/e2e/` | 416 passed, 6 skipped |
| `tests/integration/ -m "not live"` | 200 passed, 3 skipped |
| `tests/regression/` | 169 passed, 7 xfailed |
| `validate_field_dictionary.py` | PASS |
| `verify_vendor_boundary.py` / `verify_harness_consistency.py` | PASS |

비-Dell 무회귀: `real_hpe_dl380` / `real_lenovo_sr650` / `real_hpe_csus3200` 골든 재생성 없이 통과.
HPE CSUS `SGHD3TLNDD-000` 유지. baseline 10종 중 Dell 1종만 변경.

## 7. 실 Jenkins end-to-end 검증 (2026-08-11, 사후 추가)

오프라인 검증만으로 남겨뒀던 항목을 **실 Jenkins + 실 BMC** 로 닫았다.
Job `clovirone-server-gather` (`Jenkinsfile_portal`, SCM = GitHub `*/main`).

### 7-1. Redfish — 빌드 #188 (`target_type=redfish`, Dell 2대)

파라미터: `loc=git` / `inventory_json=[{"bmc_ip":"10.100.15.34"},{"bmc_ip":"10.100.15.27"}]` /
`deploymentEnvironmentId=1` / `callbackUrl=http://192.0.2.1:8086` (RFC 5737 미라우팅).

| BMC | `data.hardware.serial` | `correlation.serial_number` | status | errors |
|---|---|---|---|---|
| 10.100.15.27 | **`64CXJ54`** | **`64CXJ54`** | success | 0 |
| 10.100.15.34 | **`GSBPK54`** | **`GSBPK54`** | success | 0 |

- envelope **13 필드 정확히 일치** (누락 0 / 추가 0) — schema 무변경 실증
- **Stage 3 Validate Schema `RESULT: PASS`**
- 콘솔 전체에서 `CNIVC` **0회** — 보드 제조 시리얼이 envelope 어디에도 없음
- 빌드 결과 `UNSTABLE` 은 콜백 대상(미라우팅 주소) HTTP 408 timeout 3회 재시도 실패 때문이며
  수집 자체와 무관하다 (rule 31 R2 — 콜백 실패는 빌드를 fail 시키지 않음)

### 7-2. 동일 장비 채널 간 대조 — 빌드 #189 (`target_type=os`, 10.100.64.96)

| | Redfish (BMC 10.100.15.34) | OS (10.100.64.96) | |
|---|---|---|---|
| `correlation.serial_number` | `GSBPK54` | `GSBPK54` | **SAME** |
| `correlation.system_uuid` | `4c4c4544-0053-4210-8050-c7c04f4b3534` | 동일 | SAME (동일 장비 확정) |

`system_uuid` 가 같아 동일 물리 장비임이 확정된 상태에서 `serial_number` 가 일치한다.
**교정 전 DIFFERENT → 교정 후 SAME** 이 실 파이프라인 산출물로 증명됐다.
OS 채널은 `data.hardware=null` 이라 `correlation` 이 `data.system.serial_number` 분기를 타는
기존 구조도 그대로다 (추적 문서 9절).

## 8. 남은 한계 (미확인)
- **iDRAC7/8 미검증**: 해당 세대 실장비 fixture 부재. `DellServiceRoot` 미노출 펌웨어라면 수집이
  실패한다 (폴백 금지의 귀결). `docs/ai/NEXT_ACTIONS.md` 등재.
- **Dell 모듈러(블레이드) 미검증**: 보유 Dell 7대 전부 Monolithic. `ChassisServiceTag` 를 쓰지 않고
  `ServiceRoot.ServiceTag` 를 고른 이유가 모듈러 대응이지만, 실기기 확인은 못 했다.
