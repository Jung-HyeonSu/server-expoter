# SPEC — OS physical_disks serial / wwn 수집

> 확정일: 2026-06-22 (사용자 승인). 상태: [확정] 설계명세 → 구현 진행.
> 요구: OS(Linux/Windows) 개더링 시 디스크 WWN / serial 수집. 지원 전 OS 버전 커버.

## 1. 배경 / 웹 검증 결론 (rule 96 R1-A web sources)

- **Linux**: `lsblk` `SERIAL`·`WWN` 컬럼은 util-linux **2.23.2(RHEL7, 2013)부터 존재** → 지원 전 배포판(RHEL/Rocky 7~9, Ubuntu 18.04~24.04, Debian 10~12) 컬럼 인식. `unknown column` 실패 위험 없음. root 불필요(udev db 기반).
  - source: https://kernel.googlesource.com/pub/scm/utils/util-linux/util-linux/+/v2.23.2/misc-utils/lsblk.c (COL_SERIAL / COL_WWN)
  - 함정: virtio 가상디스크=값 빔 / Ubuntu 20.04 일부 모델 SERIAL↔WWN 혼동(Launchpad #1950793) / RAID 가상디스크 short vs full WWN 불일치(util-linux #321) → **udevadm 보강 2-tier 필요**.
- **Windows (Server 2012~2025, PS ≤5.1)**: `Win32_DiskDrive.SerialNumber`(2008+ 클래스) 전버전 가능하나 **hex/2글자 swap/공백 패딩 정규화 필요**. WWN은 표준 단일필드 없음 → `Get-PhysicalDisk.UniqueId` + `UniqueIdFormat ∈ {2 EUI64, 3 FCPHName, 8 SCSI Name String}`일 때만 해석. 로컬 SATA=null(best-effort). 2012/2012R2의 Get-PhysicalDisk 노출은 불명확 → Win32_DiskDrive serial fallback.
  - source: MS Learn Win32_DiskDrive / MSFT_PhysicalDisk(UniqueIdFormat 값맵) / Get-PhysicalDisk(2016~2025 moniker)
- **교차채널 발견**: redfish는 **이미 `physical_disks[].serial` emit**(dell baseline `S5CNNA0MC03697`) — 단 field_dictionary 미등록. 본 작업으로 문서화 동반. wwn은 어느 채널도 미emit(신규).

## 2. 확정 결정 (사용자 승인 2026-06-22)

| 항목 | 결정 |
|---|---|
| `physical_disks[].serial` | **Nice**, channel [redfish, os] (redfish 기존 emit 문서화 + os 신규) |
| `physical_disks[].wwn` | **Nice** (best-effort), channel [os] |
| schema_version | **"1" 유지** (Additive — 기존 path 불변, key 추가만) |
| Windows | **함께 구현** (단 baseline 값은 Windows 실측 환경 필요) |
| null 의미 | key 항상 존재, 값 null 허용(virtio/SATA 정상). diagnosis 경고 불필요 |

## 3. 필드 배치 / 정규화

- 배치: 기존 `model` 바로 뒤 (redfish serial 순서와 동일).
- Linux: lsblk truthy-null 정규화(model 패턴) → 빈값/의심 시 `udevadm info --query=property --name=/dev/<dev>` 의 `ID_WWN`/`ID_SERIAL_SHORT` 보강. python+raw **2경로 동일**.
- Windows serial: 공백 strip + 짝수 hex 감지 시 ASCII 디코딩 + 2글자 swap 보정(메모리 serial 패턴 재사용).
- Windows wwn: `UniqueIdFormat ∈ {2,3,8}`일 때만 `UniqueId` 채택, 그 외 null.

## 4. 변경 대상 (rule 13 R1 동반)

1. `schema/field_dictionary.yml` — +2 Nice entry (serial/wwn)
2. `os-gather/tasks/linux/gather_storage.yml` — lsblk `-o ...,SERIAL,WWN` + normalize(python+raw) + udevadm 보강
3. `os-gather/tasks/windows/gather_storage.yml` — serial/wwn 수집 + 정규화
4. `schema/baseline_v1/{ubuntu,rhel810_raw_fallback,windows}_baseline.json` — **실측 후** (ubuntu 현 baseline=virtio "Virtual disk" → serial/wwn null)
5. `docs/develop/05-field-mapping.md` + `docs/contract/03-fields.md`
6. `tests/evidence/2026-06-22-os-disk-serial-wwn.md` + 회귀 fixture
7. gather 주석 origin (web source URL, rule 96 R1-A)

## 5. 게이트 / 회귀

- Stage 3 (validate_field_dictionary): 신규 entry help_ko/en/priority/channel 충족 → PASS (미등록 출력필드는 검증기가 거부 안 함).
- Stage 4 (E2E): ubuntu/rhel810/windows baseline 갱신 후 회귀.
- 실측: Linux lab 161/165(live SSH) 검증 가능. Windows·virtio·RAID·NVMe 혼재는 사이트 실측 우선(rule 25 R7-A-1).

## 6. 미해결 / 후속

- Windows baseline 실값: Windows lab 가용성 미확인 → 사이트 실측 시점에 확정.
- 2012/2012R2 Get-PhysicalDisk 실노출, SATA/NVMe별 UniqueIdFormat 실문자열: 사이트 실측 필요.
- (선택) redfish `physical_disks[].wwn` 확장 — Drive.Identifiers 기반, 별도 cycle.
