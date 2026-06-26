# Windows OS gather 네트워크/스토리지 3건 버그 수정 (site 10.100.64.120 실측)

- 일시: 2026-06-26
- 대상: site 10.100.64.120 (WIN-TP7D9J9QKCB, Windows Server 2022, cloviradmin)
- 수집 경로: WinRM 5986 (HTTPS) 직접 Invoke-Command 실측
- 환경: LBFO 팀 2개 (LabTeam1/LabTeam2) + LabTeam1 위 VLAN tNIC(VlanID 100), vmxnet3 NIC, IB 미존재

## 배경

사용자 캡처 envelope 에서 다음 3건 이상 발견:
1. `data.storage.infiniband[]` 에 IB 가 없는 VM 인데 3건이 Mellanox 로 보고됨
2. `data.network.driver_map` 가 `[]` (Up 어댑터 다수 존재함에도)
3. 팀 위 VLAN(`LabTeam1 - VLAN 100`) 이 팀과 끊긴 맨 NIC 로 떨어지고 vlan_id 없음

## 실측 근본 원인 (전부 site 실행으로 확인)

### 1. InfiniBand 오탐 — `gather_storage.yml`
- FALLBACK `Get-PnpDevice -Class Net | Where Service -match '^(mlx|ibal|nd)'` 의 `nd` 가
  LBFO 팀 멀티플렉서 service `NdisImPlatformMp` 를 매칭 (HWID `COMPOSITEBUS\MS_IMPLAT_MP`, VEN_15B3 아님).
- PRIMARY (Get-NetAdapter PhysicalMediaType/NdisPhysicalMedium=11) 는 정상적으로 0건.
- 수정: PRIMARY 에 `InterfaceDescription -notmatch 'Multiplexor'` + FALLBACK 을
  `VEN_15B3` 또는 특정 Mellanox/IB service(`mlx|mlnx|ibbus|ibal`) 로 한정 + `MS_IMPLAT` 제외.
- 검증: 수정 쿼리 PRIMARY count=0 / FALLBACK count=0 → `infiniband: []` (올바름).

### 2. driver_map 통째 `[]` — `gather_network.yml`
- `$_.DriverDate` 가 이 환경에서 `[string]`("2006-06-21") 으로 옴.
- `String.ToString('yyyy-MM-dd')` 오버로드 없음 → .NET 터미네이팅 예외 → ForEach 전체 중단 → `[]`.
- LBFO 멀티플렉서 어댑터(2006-06-21)가 트리거 → 팀 있는 모든 Windows 호스트에서 재현.
- 수정: `-is [datetime]` 분기 + string 은 `[datetime]` 캐스트 후 포맷, 실패 시 null.
- 검증: 수정본 9개 어댑터 전부 정상 emit.

### 3. 팀 위 VLAN 미연결 — `gather_network.yml` + `network_topology.py`
- 기존 코드가 `Get-NetLbfoTeamNic` 미수집 → 팀 VLAN tNIC 의 VlanID/부모팀 손실.
- `enrich_windows_interfaces` 는 이름 정확 일치라 `LabTeam1 - VLAN 100` ≠ `LabTeam1` → master 안 됨.
- 수정: teaming win_shell 에 `LBFOTEAMNIC` emit 추가 + 필터에 `parse_windows_team_nics` /
  enrich 에서 VLAN tNIC 에 `vlan_id`/`vlan_parent` 주입 (Linux bond0.100 와 동일 키, Additive).
- 검증(E2E): site 실 emit 라인 → 필터 → `LabTeam1 - VLAN 100`:`vlan_id=100, vlan_parent=LabTeam1`.

## 검증 요약

| 항목 | 방법 | 결과 |
|---|---|---|
| IB 수정 | site WinRM 수정 쿼리 실행 | [PASS] PRIMARY/FALLBACK 둘 다 count=0 |
| driver_map 수정 | site WinRM 수정 emit 실행 | [PASS] 9 어댑터 전부 emit |
| 팀 VLAN | site 실 emit → Python 필터 E2E | [PASS] vlan_id=100/parent=LabTeam1 |
| 단위 테스트 | `pytest tests/unit` | [PASS] 781 passed, 1 skipped (회귀 0, 신규 3) |
| YAML | `yaml.safe_load` | [PASS] |

## Jenkins 검수 루프 (실 파이프라인 end-to-end)

Jenkins master 10.100.64.152 / job `hshwang-gather` (loc=git, target_type=os,
inventory_json=[{service_ip:10.100.64.120}]) 로 실 4-Stage 파이프라인 반복 검증.

| build | 변경 | ib | driver_map | 팀VLAN | result |
|---|---|---|---|---|---|
| #154 | 수정 전(baseline) | 3 | 0 | (없음) | SUCCESS (버그 잠복) |
| #155 | IB/driver_map/팀VLAN 3건 | 0 | 9 | 100/LabTeam1 | SUCCESS |
| #156 | CPU 캐시 null + driver_date 제거 | 0 | 9 | 100/LabTeam1 | SUCCESS |
| #157 | filesystems float 반올림 | 0 | 9 | 100/LabTeam1 | SUCCESS |

추가 발견·수정 (라운드 2~3, 전부 site 실측):
- **CPU L2 캐시 null→0 날조** (`gather_cpu.yml`): `[int]$null=0` → 존재 시에만 cast (L2=null 유지, L3=0 충실).
- **driver_map driver_date 미사용 수집 제거** (`gather_network.yml`): parse 폐기 필드 + string ToString
  예외가 driver_map 통째 [] 유발 → canonical(name/driver/vlan_id/bond_master) 외라 제거.
- **filesystems used_mb float 노이즈** (`gather_storage.yml`): `round(1) total - round(1) free` 뺄셈이
  `95.80000000000291` 재생성 → 파생값 round(1) (→ 95.8).

수렴: #157 envelope 전수 스캔 — float 노이즈 0(타임스탬프/버전 substring 오탐만), errors 0,
모든 섹션 success/not_supported(VM os 채널 정상). 3 라운드 결과 일관 (non-flaky).

검증 안 된 것(=호스트가 실제로 그렇게 보고): disk media_type=HDD (Get-PhysicalDisk 가 HDD 반환),
L3 cache=0 (WMI 가 0 반환) — 둘 다 OS 값 충실 반영이라 수정 대상 아님.

## 미확인 / 후속

- 실 ansible os-gather 전체 파이프라인(Jenkins Stage 1~4) 미실행 — 컨트롤러(Linux agent) 필요.
  본 검증은 PowerShell 수집부 + Python 정규화부 분리 검증 + 단위 회귀로 대체.
- Windows baseline JSON(`schema/baseline_v1/windows_*`) 갱신 여부는 실 파이프라인 재캡처 후 판단 (Additive 라 Must 필드 불변).
