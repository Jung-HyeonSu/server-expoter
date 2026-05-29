# FIELD_USAGE_MATRIX — field × baseline 사용 실태 매트릭스

> 작성: 2026-05-11 / 측정 대상 #13 (rule 28 R1 — 신규)
> 정본: 본 매트릭스. 측정 스크립트: `scripts/ai/measure_field_usage_matrix.py` (Phase 1 도입 예정)
> TTL: 14일 / 무효화 trigger: `schema/field_dictionary.yml` 변경 / `schema/baseline_v1/*.json` 변경 / `adapters/*/*.yml` capabilities 변경

## 목적

`schema/field_dictionary.yml` 74 entries (Must 39 + Nice 29 + Skip 6) 각 필드가 9 baseline (실장비 회귀 기준선) 에서 **실제로 어떻게 채워지는가** 를 자동 측정한 매트릭스. 호출자 시스템 / 운영자 / 개발자가 어느 필드가 의미 있게 수집되는지 한눈에 파악. (2026-05-29 measure_field_usage_matrix.py 재생성)

본 매트릭스는 다음 3 분류 cycle 의 input:
1. **정말 수집 불가** (외부 시스템 spec 미제공) → `field_dictionary.yml` channel 배열 축소
2. **서버 미지원** (일부 vendor / 펌웨어 / 환경) → channel 유지 + `help_ko` 명시
3. **코드 버그** (외부 시스템 제공인데 코드 잘못) → 즉시 fix + 회귀

## 4 상태 (cell 값)

각 cell (field × baseline) 은 다음 4 상태 중 하나:

| 상태 | 의미 | 판정 근거 |
|---|---|---|
| `present` | 값 존재 (non-null) | baseline JSON leaf 가 non-null / non-empty |
| `null` | 명시적 null | baseline JSON leaf 가 `null` |
| `empty` | 빈 컨테이너 | baseline JSON leaf 가 `[]` 또는 `{}` (배열/객체 타입 한정) |
| `not_supported` | 섹션 자체 미지원 | baseline `sections.{section}=not_supported` |
| `missing` | key 자체 부재 | baseline JSON 에 path 자체가 없음 (channel 미지원) |

**판정 우선순위**: `not_supported > missing > empty > null > present`

## 분류 도출 룰

baseline 의 같은 `target_type` (channel) 그룹 안에서 cell 패턴 → 분류 도출:

| 패턴 | 분류 | 조치 |
|---|---|---|
| channel 의 모든 baseline 이 `null` / `empty` / `missing` | 1 (수집 불가) | `field_dictionary.yml` channel 배열에서 해당 channel 제거 |
| channel 의 일부 baseline `present`, 일부 `null` | 2 (서버 미지원) | channel 유지 + `help_ko` 에 채널별 동작 명시 |
| 한 baseline 만 `null` 인데 다른 baseline 은 `present` + 외부 시스템 spec 상 제공 | 3 (코드 버그) | 즉시 fix + tests/fixtures + tests/baseline 회귀 |
| `not_supported` | (분류 외) | adapter capabilities 명시. 매트릭스에서 N/A |

## Baseline 8 + Channel 매핑

| baseline 파일 | target_type | vendor | sections OK | 비고 |
|---|---|---|---|---|
| `dell_baseline.json` | redfish | dell | 8 | iDRAC9 |
| `hpe_baseline.json` | redfish | hpe | 8 | iLO6 |
| `lenovo_baseline.json` | redfish | lenovo | 8 | XCC |
| `cisco_baseline.json` | redfish | cisco | 8 | CIMC |
| `esxi_baseline.json` | esxi | cisco | 6 | ESXi 8.x on Cisco UCS |
| `rhel810_raw_fallback_baseline.json` | os | (null) | 6 | RHEL 8.10 Python 3.6 → raw fallback |
| `ubuntu_baseline.json` | os | (null) | 6 | Ubuntu LTS |
| `windows_baseline.json` | os | (null) | 6 | Windows Server (VM) |

**Channel 별 baseline 수**:
- Redfish: 4 (dell / hpe / lenovo / cisco) — supermicro 없음 (베어메탈 fixture 미보유)
- OS: 3 (rhel810_raw_fallback / ubuntu / windows)
- ESXi: 1 (esxi)

**알려진 제한** (분류 정확도 영향):
- Redfish supermicro baseline 부재 — supermicro 한정 코드 버그 검출 불가
- Windows / ESXi 가 VM 환경 — 베어메탈 한정 필드 (memory.slots / storage.physical_disks 등) 가 `[]` 로 떨어져도 분류 2 vs 3 모호. 보수적 분류 2 적용 + NEXT_ACTIONS 등재 (rule 50 R2 단계 10)

## Phase 2 사람 검토 결과 (2026-05-11)

자동 매트릭스 분류에 대한 사람 검토. 자동 결과 → 확정 분류 + 조치 매핑.

### Channel 축소 확정 (분류 1 → 본 cycle Phase 3 적용)

| Field | Channel 변경 | 근거 |
|---|---|---|
| `memory.visible_mb` | `[redfish, os, esxi]` → `[os, esxi]` | Redfish spec 미정의. 사용자 핵심 사례. help_ko 에 이미 명시. |
| `memory.installed_mb` | `[redfish, os, esxi]` → `[redfish, os]` | ESXi 는 ansible_memtotal_mb 만, installed_mb 미수집 |
| `storage.infiniband[]` | `[redfish, os, esxi]` → `[]` (또는 모두 유지하고 help 명시) | InfiniBand 환경 부재 — 모든 baseline empty. 보수적: channel 유지 + help_ko "InfiniBand 환경 한정" |
| `storage.hbas[]` | `[redfish, os, esxi]` → `[esxi]` | esxi baseline 만 present (FC HBA 환경 한정) |
| `network.adapters[]` | `[redfish, esxi]` → `[esxi]` | Redfish 4 baseline 모두 missing |
| `network.ports[]` | `[redfish]` → `[]` (또는 help_ko "구현 예정") | Redfish 4 baseline 모두 missing → 보수적: help_ko 갱신 |
| `network.driver_map[]` | `[os]` → `[]` (또는 help_ko "베어메탈 Linux 한정") | OS 3 baseline 모두 missing/empty |
| `system.runtime` | `[os]` → `[esxi]` | DRIFT-B: ESXi baseline 만 present, OS 3 baseline 모두 missing |

### Help_ko 갱신 (분류 2 — channel 유지 + vendor/환경별 동작 명시)

| Field | Channel | help_ko 갱신 내용 |
|---|---|---|
| `vendor` | 유지 | "OS 채널은 hardware 정보 미수집 시 null — 의도된 동작" 강조 |
| `hardware.sku` × redfish | 유지 | "Cisco UCS 는 sku 정의 안 됨 — null 정상" 추가 |
| `hardware.oem` × redfish | 유지 | "Cisco 는 OEM namespace 없음 — empty 정상" 추가 |
| `memory.installed_mb` × os | 유지 | "Ubuntu 는 dmidecode 권한 부족 시 null — 의도된 동작" 추가 |
| `storage.logical_volumes[].*` × redfish | 유지 | "RAID controller 없는 BMC (Lenovo SR670 mock / Cisco CIMC) 는 empty — 정상" |
| `storage.logical_volumes[].boot_volume` × redfish | 유지 | "Dell OEM DellVolume.BootVolumeSource 한정 — 다른 vendor null 정상" |
| `cpu.architecture` × {os, esxi} (현재) | 유지 | (현재 정확) |
| `diagnosis.failure_stage` × 3 channel | 유지 | "**conditional** — status=failed 시만 채워짐. success baseline 에서 null 정상" 강조 |

### 분류 3? 의심 — NEXT_ACTIONS 등재 (본 cycle 외 별도 fix)

| Field × baseline | 의심 사유 | 조치 (cycle 외) |
|---|---|---|
| `meta.duration_ms × cisco_baseline.json` | cisco 의 meta.duration_ms 가 null (started_at/finished_at 있는데 계산 누락) | cisco 실장비 baseline 재캡처 시 갱신 (rule 13 R4 실측 의무) |
| `cpu.summary × rhel810_raw_fallback_baseline.json` | RHEL raw fallback 의 cpu summary 빌더 누락 (ubuntu/windows 는 present) | os-gather/tasks/linux/gather_cpu.yml raw fallback 경로에 summary 빌더 추가 — 별도 cycle |

### 코드 버그 0건 (본 cycle 내 fix 의무 없음)

Phase 2 cycle 안에서 즉시 fix 대상 코드 버그 — **0건 확정**.
분류 3? 자동 식별 1건 (`storage.logical_volumes[].boot_volume × redfish`) 은 Dell OEM 한정 — 의도된 동작.
의심 2건 (`meta.duration_ms × cisco`, `cpu.summary × rhel810`) 은 NEXT_ACTIONS 별도 cycle 등재.

<!-- AUTO-GEN: FIELD_USAGE_MATRIX START -->

> 측정 스크립트 자동 갱신 결과 — 수동 편집 금지. 다음 측정 시 덮어씀.

# Field Usage Matrix — 측정 결과

- field_dictionary entries: 74
- baselines: 9
- 총 cells: 666

## 4 상태 카운트 (channel × state)

| Channel | present | null | empty | not_supported | missing | total |
|---|---|---|---|---|---|---|
| redfish | 174 | 11 | 11 | 36 | 64 | 296 |
| os | 104 | 10 | 33 | 24 | 51 | 222 |
| esxi | 29 | 1 | 18 | 10 | 16 | 74 |

## 분류 1 후보 (수집 불가 — channel 제거): 22

- `vendor` × os
- `storage.physical_disks[]` × esxi
- `diagnosis.failure_stage` × redfish
- `diagnosis.failure_stage` × os
- `diagnosis.failure_stage` × esxi
- `network.adapters[]` × redfish
- `network.ports[]` × redfish
- `network.driver_map[]` × os
- `storage.hbas[]` × redfish
- `storage.hbas[]` × os
- `storage.infiniband[]` × redfish
- `storage.infiniband[]` × os
- `storage.infiniband[]` × esxi
- `multi_node` × redfish
- `multi_node.enabled` × redfish
- `multi_node.layout` × redfish
- `multi_node.summary` × redfish
- `multi_node.partitions[]` × redfish
- `multi_node.managers[]` × redfish
- `multi_node.chassis[]` × redfish
- `diagnosis.details.multi_node_layout` × redfish
- `diagnosis.details.rmc_activation_check` × redfish

## 분류 2 후보 (서버 미지원 — help_ko 명시): 12

- `hardware.sku` × redfish
- `hardware.oem` × redfish
- `memory.installed_mb` × os
- `storage.logical_volumes[]` × redfish
- `storage.logical_volumes[].raid_level` × redfish
- `storage.logical_volumes[].member_drive_ids` × redfish
- `storage.logical_volumes[].controller_id` × redfish
- `storage.logical_volumes[].id` × redfish
- `storage.logical_volumes[].name` × redfish
- `storage.logical_volumes[].total_mb` × redfish
- `storage.logical_volumes[].health` × redfish
- `storage.logical_volumes[].state` × redfish

## 분류 3? 후보 (코드 버그 의심 — Phase 2 검증): 1

- `storage.logical_volumes[].boot_volume` × redfish


## Drift 검출 (17 entries)

- `diagnosis.details.multi_node_layout`:
  - DRIFT-A(redfish): 선언했지만 모든 baseline null/missing → channel 제거 후보
- `diagnosis.details.rmc_activation_check`:
  - DRIFT-A(redfish): 선언했지만 모든 baseline null/missing → channel 제거 후보
- `diagnosis.failure_stage`:
  - DRIFT-A(redfish): 선언했지만 모든 baseline null/missing → channel 제거 후보
  - DRIFT-A(os): 선언했지만 모든 baseline null/missing → channel 제거 후보
  - DRIFT-A(esxi): 선언했지만 모든 baseline null/missing → channel 제거 후보
- `multi_node`:
  - DRIFT-A(redfish): 선언했지만 모든 baseline null/missing → channel 제거 후보
- `multi_node.chassis[]`:
  - DRIFT-A(redfish): 선언했지만 모든 baseline null/missing → channel 제거 후보
- `multi_node.enabled`:
  - DRIFT-A(redfish): 선언했지만 모든 baseline null/missing → channel 제거 후보
- `multi_node.layout`:
  - DRIFT-A(redfish): 선언했지만 모든 baseline null/missing → channel 제거 후보
- `multi_node.managers[]`:
  - DRIFT-A(redfish): 선언했지만 모든 baseline null/missing → channel 제거 후보
- `multi_node.partitions[]`:
  - DRIFT-A(redfish): 선언했지만 모든 baseline null/missing → channel 제거 후보
- `multi_node.summary`:
  - DRIFT-A(redfish): 선언했지만 모든 baseline null/missing → channel 제거 후보
- `network.adapters[]`:
  - DRIFT-A(redfish): 선언했지만 모든 baseline null/missing → channel 제거 후보
- `network.driver_map[]`:
  - DRIFT-A(os): 선언했지만 모든 baseline null/missing → channel 제거 후보
- `network.ports[]`:
  - DRIFT-A(redfish): 선언했지만 모든 baseline null/missing → channel 제거 후보
- `storage.hbas[]`:
  - DRIFT-A(redfish): 선언했지만 모든 baseline null/missing → channel 제거 후보
  - DRIFT-A(os): 선언했지만 모든 baseline null/missing → channel 제거 후보
- `storage.infiniband[]`:
  - DRIFT-A(redfish): 선언했지만 모든 baseline null/missing → channel 제거 후보
  - DRIFT-A(os): 선언했지만 모든 baseline null/missing → channel 제거 후보
  - DRIFT-A(esxi): 선언했지만 모든 baseline null/missing → channel 제거 후보
- `storage.physical_disks[]`:
  - DRIFT-A(esxi): 선언했지만 모든 baseline null/missing → channel 제거 후보
- `vendor`:
  - DRIFT-A(os): 선언했지만 모든 baseline null/missing → channel 제거 후보

## 전수 매트릭스 (65 × 8)

| Field | Channel 선언 | cisco | dell | esxi | hpe | hpe_csus_3 | lenovo | rhel810_ra | ubuntu | windows | 분류 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `schema_version` | redfish,os,esxi | O | O | O | O | O | O | O | O | O | OK |
| `target_type` | redfish,os,esxi | O | O | O | O | O | O | O | O | O | OK |
| `collection_method` | redfish,os,esxi | O | O | O | O | O | O | O | O | O | OK |
| `ip` | redfish,os,esxi | O | O | O | O | O | O | O | O | O | OK |
| `hostname` | redfish,os,esxi | O | O | O | O | O | O | O | O | O | OK |
| `vendor` | redfish,os,esxi | O | O | O | O | O | O | n | n | n | os:1 |
| `meta` | redfish,os,esxi | O | O | O | O | O | O | O | O | O | OK |
| `correlation` | redfish,os,esxi | O | O | O | O | O | O | O | O | O | OK |
| `status` | redfish,os,esxi | O | O | O | O | O | O | O | O | O | OK |
| `sections.*` | redfish,os,esxi | O | O | O | O | O | O | O | O | O | OK |
| `hardware.health` | redfish | O | O | _ | O | O | O | - | - | - | OK |
| `hardware.sku` | redfish | n | O | _ | O | O | O | - | - | - | redfish:2 |
| `hardware.oem` | redfish | e | O | _ | O | e | O | - | - | - | redfish:2 |
| `memory.total_basis` | redfish,os,esxi | O | O | O | O | O | O | O | O | O | OK |
| `memory.installed_mb` | redfish,os | O | O | _ | O | O | O | O | n | O | os:2 |
| `memory.visible_mb` | os,esxi | _ | _ | O | _ | n | _ | O | O | O | OK |
| `storage.physical_disks[]` | redfish,os,esxi | O | O | e | O | e | O | O | O | O | esxi:1 |
| `storage.physical_disks[].id` | redfish,os | O | O | e | O | e | O | O | O | O | OK |
| `storage.physical_disks[].predicted_life_percent` | redfish | O | O | e | O | e | O | _ | _ | _ | OK |
| `storage.controllers[].drives[]` | redfish | O | O | e | O | e | O | e | e | e | OK |
| `storage.logical_volumes[]` | redfish | O | O | e | O | e | e | e | e | e | redfish:2 |
| `storage.logical_volumes[].raid_level` | redfish | O | O | e | O | e | e | e | e | e | redfish:2 |
| `storage.logical_volumes[].member_drive_ids` | redfish | O | O | e | O | e | e | e | e | e | redfish:2 |
| `storage.logical_volumes[].controller_id` | redfish | O | O | e | O | e | e | e | e | e | redfish:2 |
| `storage.logical_volumes[].id` | redfish | O | O | e | O | e | e | e | e | e | redfish:2 |
| `storage.logical_volumes[].name` | redfish | O | O | e | O | e | e | e | e | e | redfish:2 |
| `storage.logical_volumes[].total_mb` | redfish | O | O | e | O | e | e | e | e | e | redfish:2 |
| `storage.logical_volumes[].health` | redfish | O | O | e | O | e | e | e | e | e | redfish:2 |
| `storage.logical_volumes[].state` | redfish | O | O | e | O | e | e | e | e | e | redfish:2 |
| `storage.logical_volumes[].boot_volume` | redfish | n | O | e | n | e | e | e | e | e | redfish:3? |
| `network.interfaces[].link_status` | redfish,os,esxi | O | O | O | O | e | O | O | O | O | OK |
| `power.power_supplies[].state` | redfish | O | O | - | O | n | O | - | - | - | OK |
| `cpu.cores_physical` | redfish,os,esxi | O | O | O | O | O | O | O | O | O | OK |
| `firmware[].component` | redfish | O | O | - | O | e | O | - | - | - | OK |
| `users[]` | os | - | - | - | - | - | - | O | O | O | OK |
| `users[].name` | os | - | - | - | - | - | - | O | O | O | OK |
| `users[].uid` | os | - | - | - | - | - | - | O | O | O | OK |
| `users[].groups` | os | - | - | - | - | - | - | O | O | O | OK |
| `users[].home` | os | - | - | - | - | - | - | O | O | O | OK |
| `users[].last_access_time` | os | - | - | - | - | - | - | O | O | O | OK |
| `bmc.ip` | redfish | O | O | - | O | n | O | - | - | - | OK |
| `correlation.host_ip` | redfish,os,esxi | O | O | O | O | O | O | O | O | O | OK |
| `diagnosis.auth_success` | redfish,os,esxi | O | O | O | O | O | O | O | O | O | OK |
| `hardware.power_state` | redfish | O | O | _ | O | O | O | - | - | - | OK |
| `storage.physical_disks[].failure_predicted` | redfish | O | O | e | O | e | O | _ | _ | _ | OK |
| `network.interfaces[].kind` | redfish,os,esxi | O | O | O | O | e | O | O | O | O | OK |
| `meta.duration_ms` | redfish,os,esxi | O | O | O | O | O | O | O | O | O | OK |
| `diagnosis.failure_stage` | redfish,os,esxi | n | n | n | n | n | n | n | n | n | redfish:1,os:1,esxi:1 |
| `storage.physical_disks[].media_type` | redfish,os | O | O | e | O | e | O | O | O | O | OK |
| `storage.physical_disks[].protocol` | redfish | O | O | e | O | e | O | n | n | n | OK |
| `cpu.architecture` | os,esxi | n | n | O | n | n | n | O | O | O | OK |
| `system.hosting_type` | os | - | - | O | - | - | - | O | O | O | esxi:DRIFT-B? |
| `system.uptime_seconds` | os,esxi | - | - | O | - | - | - | O | O | O | OK |
| `firmware[].updateable` | redfish | O | O | - | O | e | O | - | - | - | OK |
| `cpu.summary` | redfish,os,esxi | O | O | O | O | O | O | O | O | O | OK |
| `memory.summary` | redfish,os,esxi | O | O | O | O | O | O | O | O | O | OK |
| `storage.summary` | redfish,os,esxi | O | O | O | O | O | O | O | O | O | OK |
| `network.summary` | redfish,os,esxi | O | O | O | O | O | O | O | O | O | OK |
| `network.adapters[]` | redfish,esxi | _ | _ | O | _ | e | _ | _ | _ | _ | redfish:1 |
| `network.ports[]` | redfish | _ | _ | _ | _ | e | _ | _ | _ | _ | redfish:1 |
| `network.virtual_switches[]` | esxi | _ | _ | O | _ | _ | _ | _ | _ | _ | OK |
| `network.driver_map[]` | os | _ | _ | _ | _ | _ | _ | _ | _ | _ | os:1 |
| `storage.hbas[]` | redfish,os,esxi | _ | _ | O | _ | e | _ | _ | _ | _ | redfish:1,os:1 |
| `storage.infiniband[]` | redfish,os,esxi | _ | _ | e | _ | e | _ | _ | _ | _ | redfish:1,os:1,esxi:1 |
| `system.runtime` | os,esxi | - | - | O | - | - | - | O | O | O | OK |
| `multi_node` | redfish | _ | _ | _ | _ | O | _ | _ | _ | _ | redfish:1 |
| `multi_node.enabled` | redfish | _ | _ | _ | _ | O | _ | _ | _ | _ | redfish:1 |
| `multi_node.layout` | redfish | _ | _ | _ | _ | O | _ | _ | _ | _ | redfish:1 |
| `multi_node.summary` | redfish | _ | _ | _ | _ | O | _ | _ | _ | _ | redfish:1 |
| `multi_node.partitions[]` | redfish | _ | _ | _ | _ | O | _ | _ | _ | _ | redfish:1 |
| `multi_node.managers[]` | redfish | _ | _ | _ | _ | O | _ | _ | _ | _ | redfish:1 |
| `multi_node.chassis[]` | redfish | _ | _ | _ | _ | O | _ | _ | _ | _ | redfish:1 |
| `diagnosis.details.multi_node_layout` | redfish | _ | _ | _ | _ | O | _ | _ | _ | _ | redfish:1 |
| `diagnosis.details.rmc_activation_check` | redfish | _ | _ | _ | _ | O | _ | _ | _ | _ | redfish:1 |

**범례**: O=present / n=null / e=empty / -=not_supported / _=missing

<!-- AUTO-GEN: FIELD_USAGE_MATRIX END -->

## Phase 1 의심 후보 (수동 식별)

Phase 1 탐색 (Explore agents) 에서 식별된 15 의심 후보. Phase 1 스크립트가 매트릭스로 확정.

### Redfish (6)
- `memory.visible_mb` — 1차: 분류 1 (Redfish spec 미정의)
- `memory.free_mb` — 1차: 분류 1 (필드 자체 없음)
- `hardware.bios_date` — 1차: 분류 2 (OEM 추출 코드 있으나 모든 baseline null)
- `storage.physical_disks[].locator` — 1차: 분류 2 (Redfish 표준 미보장)
- `storage.logical_volumes[].boot_volume` — 1차: 분류 2 (Dell OEM 만)
- `bmc.oem.ilo_version` — 1차: 분류 2 (HPE 만 + null)

### OS (5)
- `Windows memory.slots` — 1차: 분류 2 확정 (VM 환경 한정 — 코드 line 17-69 정상)
- `storage.physical_disks[].health` — 1차: 분류 1 (OS SMART 제한)
- `network.link_type` — 1차: 분류 1 (NIC 트랜시버 OS 미제공)
- `cpu.l2/l3_cache_kb` (raw fallback) — 1차: 분류 2
- `memory.slots[].speed_mhz / manufacturer` (raw fallback) — 1차: 분류 2

### ESXi (4)
- `memory.installed_mb` — 1차: 분류 2 (ansible_memtotal_mb 만)
- `storage.physical_disks[]` — 1차: 분류 1 (datastore 기반)
- `storage.controllers[]` — 1차: 분류 1 (RAID 미수집)
- `network.adapters[]` — 1차: 분류 2 (collect_network_extended 옵션)

## 관련

- rule: `13-output-schema-fields` R5/R7 (envelope shape 보존 + docs/20 동기화)
- rule: `28-empirical-verification-lifecycle` R1 #13 (측정 대상 신규)
- rule: `92-dependency-and-regression-gate` R5 (schema 변경 사용자 명시 승인)
- rule: `96-external-contract-integrity` R1 (외부 계약 origin 주석)
- skill: `add-new-vendor` (단계 11 — 필드 분류 검증 의무화 예정 — Phase 4)
- catalog: `SCHEMA_FIELDS.md` (field_dictionary 요약)
- script: `scripts/ai/measure_field_usage_matrix.py` (Phase 1 — 자동 측정)
- ADR: `docs/ai/decisions/ADR-2026-05-11-field-channel-declaration-refinement.md` (Phase 4)
- plan: `~/.claude/plans/tranquil-wandering-lampson.md`
