# 11. Gather 구조 설명

## Fragment 기반 수집 철학

각 gather_*.yml / normalize_*.yml 은 전체 JSON 을 만들지 않는다.
자기 역할에 해당하는 **fragment** 만 생성하고, `merge_fragment.yml` 을 호출한다.
공통 builder 가 fragment 들을 병합해 최종 JSON 을 만든다.

```
raw collect
→ normalize (gather별)
→ fragment 생성 (_data_fragment + _sections_*_fragment + _errors_fragment)
→ merge_fragment.yml 호출 (누적 병합)
→ build_sections / build_status / build_errors / build_output (공통)
→ schema_version 주입
→ OUTPUT
```

**새 수집 항목 추가 방법:**
1. 새 `gather_xxx.yml` 작성 → fragment 생성 → `merge_fragment.yml` 호출
2. `site.yml` 에 `include_tasks` 한 줄 추가
3. `site.yml`, `build_output.yml` 전체를 수정할 필요 없음

---

## 전체 흐름

```
포털 → Jenkins (target_type: os|esxi|redfish)
     → inventory.sh (ip 만 처리)
     → vault 자동 로딩
     → init_fragments.yml   ← 누적 변수 초기화
     → tasks/ (수집 → 각자 fragment 생성 → merge_fragment)
     → build_sections / build_status / build_errors
     → build_meta / build_correlation
     → build_output → schema_version 주입
     → OUTPUT 태스크 → callback plugin 캡처 → 포털
```

---

## os-gather

```
site.yml Play1: 포트 감지 (SSH 22 / WinRM 5985/5986)
  → 성공: _os_linux 또는 _os_windows 그룹에 등록
  → 실패: build_failed_output.yml 공통 모듈로 failed OUTPUT 생성
          ↓
site.yml Play2 (Linux):
  common/init_fragments.yml     ← 누적 변수 초기화
  adapter_loader (os 채널)      ← adapter 선택
  tasks/linux/preflight.yml     → Python 경로, 명령 존재 확인
  tasks/linux/gather_system.yml → system fragment → merge_fragment
  tasks/linux/gather_cpu.yml    → cpu fragment → merge_fragment
  tasks/linux/gather_memory.yml → memory fragment (dmidecode) → merge_fragment
  tasks/linux/gather_storage.yml → storage fragment (lsblk+mounts) → merge_fragment
  tasks/linux/gather_network.yml → network fragment (gw/dns/speed) → merge_fragment
  tasks/linux/gather_users.yml  → users fragment (getent+lastlog) → merge_fragment
  tasks/normalize/build_output.yml → build_sections/status/errors/output

site.yml Play3 (Windows): 동일 구조, tasks/windows/*
```

---

## esxi-gather

```
site.yml (1 Play):
  common/init_fragments.yml
  tasks/collect_facts.yml      → _e_raw_facts, _e_facts_ok
  tasks/collect_config.yml     → _e_raw_config, _e_config_ok
  tasks/collect_datastores.yml → _e_raw_ds, _e_ds_ok
  tasks/normalize_system.yml   → system/hardware/cpu/memory fragment → merge_fragment
  tasks/normalize_network.yml  → network fragment → merge_fragment
  tasks/normalize_storage.yml  → storage fragment (partial 판정 반영) → merge_fragment
  build_sections / build_status / build_errors / build_output
```

---

## redfish-gather

```
site.yml (1 Play):
  common/init_fragments.yml
  precheck_bundle              → 4단계 진단 (ping→port→protocol→auth)
  tasks/detect_vendor.yml      → _rf_detected_vendor
  adapter_loader (redfish)     → _selected_adapter (벤더별 adapter 자동 선택)
  tasks/load_vault.yml         → vault/redfish/{vendor}.yml
  tasks/collect_standard.yml   → _rf_raw_collect, _rf_vendor
    └ gather_storage()         → Storage 실패 시 SimpleStorage fallback
  tasks/normalize_standard.yml → 전체 표준 fragment → merge_fragment
  _selected_adapter.oem_tasks  → OEM fragment → merge_fragment (adapter 기반 동적 로딩)
  build_sections / build_status / build_errors / build_meta / build_correlation / build_output
```

### Redfish Safe Common 5 필드 (normalize_standard.yml 반영)

| 위치 | 필드 | 타입 |
|------|------|------|
| `hardware` | `health` | string\|null (OK/Warning/Critical) |
| `hardware` | `power_state` | string\|null (On/Off/PoweringOn/PoweringOff) |
| `physical_disks[]` | `serial` | string\|null |
| `physical_disks[]` | `failure_predicted` | boolean\|null |
| `physical_disks[]` | `predicted_life_percent` | integer\|null (0-100) |

**디스크 필터 정책**: CapacityBytes == 0 또는 Name에 "empty" 포함 시 드라이브 skip.
HPE `PredictedMediaLifeLeftPercent` float 값은 int()로 변환.

> **Conditional 필드 (보류)**: hardware.sku, PowerConsumedWatts, PowerCapacityWatts,
> PowerMetrics.*, Proc.MaxSpeedMHz, PSU.Health, NIC.LinkStatus 등은 벤더 간 일관성 미확보로 보류.

### 지원 벤더

dell, hpe, lenovo, supermicro, cisco (5개 벤더)
- Cisco: adapter `redfish_cisco_cimc`, vault `vault/redfish/cisco.yml`

---

## callback_plugins/json_only.py

- `name: OUTPUT` 태스크의 `msg` 만 stdout 으로 캡처
- 나머지 Ansible 출력 전부 억제
- 프로젝트 루트 `callback_plugins/json_only.py` 단일 사본 유지 (`ansible.cfg`의 `callback_plugins = ./callback_plugins`로 참조)

---

## inventory.sh

- 우선순위: ① `INVENTORY_JSON` 환경변수 → ② `.inventory_input.json` 파일 (Jenkinsfile `writeFile` 생성)
- Jenkins `ansiblePlaybook` 플러그인은 `environment` 블록의 멀티라인 환경변수를 전달하지 못하므로 파일 fallback 필수
- `inventory_hostname = ip`
- 계정 정보 없음 (vault 에서 자동 로딩)
