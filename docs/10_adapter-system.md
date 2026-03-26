# 10. Adapter 시스템

## 개요

Adapter 시스템은 벤더/세대/OS가 늘어나도 **YAML 파일 추가만으로 확장**할 수 있는 선언적 레지스트리입니다.

운영자는 코드를 수정하지 않고 `adapters/` 디렉토리에 YAML 파일을 추가/수정하여 새로운 장비를 지원할 수 있습니다.

## 디렉토리 구조

```
adapters/
  registry.yml              # 마스터 인덱스
  redfish/
    redfish_generic.yml      # 범용 (priority: 0)
    dell_idrac.yml           # Dell 기본 (priority: 10)
    dell_idrac9.yml          # Dell iDRAC 9 (priority: 100)
    dell_idrac8.yml          # Dell iDRAC 8 (priority: 50)
    hpe_ilo.yml              # HPE 기본
    hpe_ilo5.yml             # HPE iLO 5
    cisco_cimc.yml           # Cisco CIMC (신규)
    ...
  os/
    linux_generic.yml        # Linux 범용
    linux_rhel.yml           # RHEL 계열
    windows_generic.yml      # Windows 범용
    ...
  esxi/
    esxi_generic.yml         # ESXi 범용
    esxi_7x.yml              # ESXi 7.x
    ...
```

## Adapter YAML 구조

```yaml
adapter_id: redfish_dell_idrac9    # 고유 ID
channel: redfish                    # 수집 채널 (redfish/os/esxi)
priority: 100                       # 우선순위 (높을수록 우선)
version: "1.0.0"                    # adapter 버전
generic: false                      # true면 fallback adapter

match:                              # 매칭 조건 (모두 충족해야 선택)
  vendor: ["Dell", "Dell Inc."]     # 벤더명 목록
  firmware_patterns: ["iDRAC.*9"]   # 펌웨어 정규식 패턴
  model_patterns: []                # 모델 정규식 패턴
  os_type: linux                    # OS 유형 (os 채널용)
  distribution_patterns: ["RHEL"]   # 배포판 패턴 (os 채널용)
  version_patterns: ["^7\\."]       # 버전 패턴 (esxi 채널용)

capabilities:
  sections_supported: [system, hardware, bmc, ...] # 수집 가능 섹션

collect:                            # 수집 태스크 경로
  standard_tasks: "redfish-gather/tasks/collect_standard.yml"
  oem_tasks: "redfish-gather/tasks/vendors/dell/collect_oem.yml"

normalize:
  standard_tasks: "redfish-gather/tasks/normalize_standard.yml"
  oem_tasks: "redfish-gather/tasks/vendors/dell/normalize_oem.yml"

credentials:
  profile: "redfish_dell"           # vault 프로파일명
  fallback_profiles: ["redfish_default"]

graceful_degradation:
  critical_sections: [system, hardware]  # 실패 시 abort
  optional_sections: [firmware, power]   # 실패해도 continue

diagnosis:
  not_supported_message: "..."       # Redfish 미지원 시 메시지
```

## Adapter 선택 흐름

```
1. precheck_bundle (Phase 1)
   → ping → port → protocol → auth 진단
   → probe_facts 획득 (vendor, firmware, model)

2. detect_vendor
   → vendor_aliases.yml 기반 정규화
   → _rf_probe_facts 생성

3. adapter_loader (lookup plugin)
   → adapters/<channel>/*.yml 스캔
   → match 조건 평가
   → 점수 계산: priority × 1000 + specificity × 10 + match_score
   → 최고 점수 adapter 반환

4. 선택된 adapter 기반으로:
   → credentials.profile → vault 로딩
   → collect.oem_tasks → OEM 수집 실행 여부
   → capabilities → 실패 시 지원 섹션 목록
```

## 점수 계산

| 요소 | 가중치 | 설명 |
|------|--------|------|
| priority | × 1000 | YAML에 명시된 우선순위 |
| specificity | × 10 | match 조건 개수/유형에 따른 점수 |
| match_score | × 1 | 실제 매칭 성공 보너스 (vendor +20, model +25, firmware +25) |
| generic | -40 | generic adapter 감점 |

**예시**: Dell iDRAC 9 (firmware 매칭)
- priority=100 × 1000 = 100,000
- specificity = vendor(10) + firmware(20) = 30 × 10 = 300
- match_score = vendor(20) + firmware(25) = 45
- **총점: 100,345**

**예시**: Dell 기본 adapter (firmware 정보 없음)
- priority=10 × 1000 = 10,000
- specificity = vendor(10) = 10 × 10 = 100
- match_score = vendor(20) = 20
- **총점: 10,120**

## 새 장비 추가 방법

### 벤더 감지 — `_BUILTIN_VENDOR_MAP`

`redfish_gather.py`의 `_detect_vendor_from_service_root()`는 `_BUILTIN_VENDOR_MAP` 딕셔너리를 사용하여
모든 벤더(dell, hpe, lenovo, supermicro, cisco)를 감지합니다.

새 벤더 추가 시 `_BUILTIN_VENDOR_MAP`에 항목 추가 + adapter YAML 생성만으로
벤더 감지 로직 변경 없이 자동 지원됩니다.

### 새 벤더 (예: Fujitsu)

1. `common/vars/vendor_aliases.yml`에 벤더 매핑 추가:
   ```yaml
   fujitsu:
     - "Fujitsu"
     - "FUJITSU"
     - "FUJITSU LIMITED"
   ```

2. `adapters/redfish/fujitsu_irmc.yml` 생성

3. (선택) `redfish-gather/tasks/vendors/fujitsu/` 에 OEM 태스크 추가

4. (선택) `vault/redfish/redfish_fujitsu.yml` 에 인증 정보 추가

**site.yml 수정 불필요!**

### 새 OS 배포판 (예: Rocky Linux)

1. `adapters/os/linux_rocky.yml` 생성 (distribution_patterns에 "Rocky" 추가)

### 새 ESXi 버전

1. `adapters/esxi/esxi_9x.yml` 생성 (version_patterns에 "^9\\." 추가)

## redfish_gather.py vs Adapter 역할 분리

| 계층 | 담당 |
|------|------|
| API 호출 (HTTP) | `redfish_gather.py` — 13개 표준 endpoint 직접 호출 |
| 벤더 감지 | `redfish_gather.py` — `detect_vendor()` |
| 데이터 정규화 | adapter YAML + normalize tasks |
| 필드 매핑 | adapter capabilities + normalize tasks |

## 설계 원칙 (실장비 검증 확정)

1. **URI 패턴 하드코딩 금지** — 컬렉션 Members[0]에서 동적 취득
2. **StorageControllers fallback 필수** — HPE Gen11+ 는 Controllers 링크 사용
3. **null 허용 필드 명시** — 벤더마다 누락 필드 다름 (adapter에서 `optional_fields` 정의)
4. **SimpleStorage는 fallback 전용** — Storage 실패 시만 시도
5. **OEM은 최소 사용** — 표준 필드로 충분한 항목이 대부분

## 핵심 파일

| 파일 | 역할 |
|------|------|
| `module_utils/adapter_common.py` | 벤더 정규화, match 평가, 점수 계산 |
| `lookup_plugins/adapter_loader.py` | Ansible lookup plugin (adapter 스캔+선택) |
| `common/vars/vendor_aliases.yml` | 벤더명 정규화 매핑 |
| `adapters/registry.yml` | 마스터 인덱스 |
