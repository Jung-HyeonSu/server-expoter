# Adapter Matrix — 실장비 검증 기반

> 검증일: 2026-03-18

## 1. 현재 Adapter 구조 개요

adapter 시스템은 `lookup_plugins/adapter_loader.py`가 `adapters/` 디렉토리의 YAML 파일을 로드하여,
`match` 조건 기반으로 최적 adapter를 선택하는 구조.

## 2. redfish_gather.py 수집 vs adapter 역할 분리

현재 코드에서 **실제 Redfish API 호출은 `redfish_gather.py` 모듈이 전부 담당**.
adapter는 normalize 단계에서 벤더별 필드 매핑 차이를 처리하는 역할.

| 계층 | 담당 |
|------|------|
| API 호출 (HTTP) | `redfish_gather.py` — 13개 표준 endpoint 직접 호출 |
| 벤더 감지 | `redfish_gather.py` — `detect_vendor()` |
| 데이터 정규화 | adapter YAML + `field_mapper.py` |
| 필드 매핑 | adapter capabilities + normalize tasks |

## 3. 실장비 기준 Adapter 매칭 예상

### Lenovo (ThinkSystem SR650 V2)
- Manufacturer: "Lenovo"
- Model: "ThinkSystem SR650 V2"
- BMC: XCC
- 예상 매칭: `redfish_lenovo_xcc_generic` → (없으면) `redfish_generic`

### HPE (ProLiant DL380 Gen11)
- Manufacturer: "HPE"
- Model: "ProLiant DL380 Gen11"
- BMC: iLO 6
- 예상 매칭: `redfish_hpe_ilo6_generic` → `redfish_hpe_ilo5_generic` → `redfish_generic`

### Dell (PowerEdge R740)
- Manufacturer: "Dell Inc."
- Model: "PowerEdge R740"
- BMC: iDRAC 9 (14G)
- 예상 매칭: `redfish_dell_idrac9_generic` → `redfish_generic`

### Cisco (UCS C-Series)
- Manufacturer: "Cisco Systems Inc."
- Model: "UCS C220 M5", "UCS C240 M6" 등
- BMC: CIMC
- 예상 매칭: `redfish_cisco_cimc` → `redfish_generic`
- Vault: `vault/redfish/cisco.yml`

## 4. Adapter 초안 — 실장비 검증 기반

### 4-1. Dell iDRAC 9 Current Adapter

```yaml
adapter_id: redfish_dell_idrac9_current
match:
  vendor: dell
  model_pattern: "PowerEdge R7[34]0"
  bmc_model_pattern: "14G"
priority: 80
specificity: high

capabilities:
  system: standard
  bmc: standard
  processors: standard
  memory: standard
  storage: standard        # StorageControllers 인라인 배열 사용
  network: standard
  firmware: standard       # FirmwareInventory 개별 조회 필요
  power: standard

uri_patterns:
  system: "Systems/System.Embedded.1"
  manager: "Managers/iDRAC.Embedded.1"
  chassis: "Chassis/System.Embedded.1"

notes:
  - SimpleStorage도 지원 (fallback 불필요)
  - StorageControllers 인라인 배열 사용
  - Drive.Status.Health 미제공 — null 허용 필요
  - Redfish 1.6.0 (구형) — PowerSubsystem/ThermalSubsystem 미지원
  - Oem.Dell.DellSystem.LifecycleControllerVersion 선택적 수집
```

### 4-2. HPE iLO 6 Adapter (구현 완료 — `adapters/redfish/hpe_ilo6.yml`)

```yaml
adapter_id: redfish_hpe_ilo6
match:
  vendor: ["HPE", "Hewlett Packard Enterprise"]
  firmware_patterns: ["iLO.*6", "^1\\.[5-9]"]
priority: 100

capabilities:
  system: standard
  bmc: standard
  processors: standard
  memory: standard
  storage: controllers_link   # StorageControllers 없음 → Controllers 서브링크 필요!
  network: minimal            # SpeedMbps, LinkStatus, Status 미제공
  firmware: standard
  power: standard

uri_patterns:
  system: "Systems/1"
  manager: "Managers/1"
  chassis: "Chassis/1"

critical_fix:
  - Storage Controllers → /Storage/{id}/Controllers 링크 드릴다운 추가 필요
  - EthernetInterfaces 필드 최소 → SpeedMbps=null, LinkStatus=null 허용

notes:
  - Redfish 1.20.0 (최신)
  - ProcessorSummary.Status.Health 미제공
  - MemorySummary.Status.Health 미제공 (HealthRollup만)
  - IndicatorLED 미제공 (IndicatorLED deprecated in newer Redfish → LocationIndicatorActive 사용?)
  - Drive.Manufacturer 미제공
  - Oem.Hpe 구조 광범위 — PostState, ServerSignature 선택적
```

### 4-3. Lenovo XCC Current Adapter

```yaml
adapter_id: redfish_lenovo_xcc_current
match:
  vendor: lenovo
  model_pattern: "ThinkSystem.*"
  bmc_model_pattern: ".*XClarity.*"
priority: 80
specificity: high

capabilities:
  system: standard
  bmc: standard_minus_health  # Manager.Status.Health 미제공!
  processors: standard
  memory: standard
  storage: standard           # StorageControllers 인라인 배열 사용
  network: standard
  firmware: standard
  power: standard

uri_patterns:
  system: "Systems/1"
  manager: "Managers/1"
  chassis: "Chassis/1"

critical_fix:
  - Manager Status.Health 미제공 → null 허용 또는 Status.State로 추론

notes:
  - Redfish 1.15.0
  - SimpleStorage 미지원 (404)
  - PowerControl 3개 항목 (시스템 전체 + CPU + 기타)
  - PSU PowerCapacityWatts가 일부 null
  - SoftwareId 제공됨 — component 필드에 활용 가능
  - Oem.Lenovo 구조 있음 — ProductName 선택적
```

### 4-4. Cisco CIMC Adapter (신규)

```yaml
adapter_id: redfish_cisco_cimc
match:
  vendor: ["cisco", "Cisco Systems Inc.", "Cisco Systems, Inc."]
  firmware_patterns: ["CIMC.*"]
priority: 80
specificity: high

capabilities:
  system: standard
  bmc: standard
  processors: standard
  memory: standard
  storage: standard
  network: standard
  firmware: standard
  power: standard

uri_patterns:
  system: "Systems/WZP-XXXXX"    # 동적 탐색 (Members[0])
  manager: "Managers/CIMC"
  chassis: "Chassis/1"

notes:
  - Redfish 표준 준수도 높음
  - CapacityBytes == 0 드라이브 (FlexFlash) 필터 필요
  - vault: vault/redfish/cisco.yml
  - _BUILTIN_VENDOR_MAP에 등록으로 자동 감지
```

## 5. Adapter 우선순위 정책

| 순위 | Adapter 타입 | Priority | 조건 |
|------|-------------|----------|------|
| 1 | vendor_model_specific | 90 | vendor + model 정확 매칭 |
| 2 | vendor_bmc_generic | 80 | vendor + BMC 세대 매칭 |
| 3 | vendor_generic | 60 | vendor만 매칭 |
| 4 | generic | 10 | 모든 벤더 fallback |

## 6. 실장비 검증으로 확정된 Adapter 설계 원칙

1. **URI 패턴 하드코딩 금지** — 컬렉션 Members[0]에서 동적 취득 (현재 코드 정확)
2. **StorageControllers fallback 필수** — HPE Gen11+ 는 Controllers 링크 사용
3. **null 허용 필드 명시** — 벤더마다 누락 필드 다름 (adapter에서 `optional_fields` 정의)
4. **SimpleStorage는 fallback 전용** — Storage 실패 시만 시도 (현재 코드 정확)
5. **OEM은 최소 사용** — 표준 필드로 충분한 항목이 대부분
