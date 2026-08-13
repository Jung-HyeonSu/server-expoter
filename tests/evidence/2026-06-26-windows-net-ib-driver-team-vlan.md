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

## 라운드 4 — Windows 주소 5키 parity (is_secondary 등, build #158)

배경: `addresses[]` 5키(scope/label/parent_interface/is_alias/is_secondary)가 `channel:[os]` 로
field_dictionary 에 등록(2026-06-17 커밋 70eb541a)됐으나 **Linux 만 구현**되고 Windows 는 미구현이었음
(같은 커밋에 windows 파일 없음 — 암묵적 parity 갭). 사용자 질의("2 IP 면 Windows 도 맞추자")로 완성.

설계: is_alias 로 다중 IP 를 표현하면 (a) field_dictionary 정의(label 기반) 위반 + (b) 같은 상황에서
Linux 는 is_alias=false/is_secondary=true 라 **Linux 와 값이 정반대** → 목적 자체 깨짐. 정답은 is_secondary.

구현(`filter_plugins/network_topology.py` `enrich_windows_addresses`):
- is_secondary = 같은 인터페이스+같은 서브넷 2번째+ IPv4 → true (Linux 커널 동작 controller-side 모사, best-effort)
- is_alias = 항상 false (Windows 라벨 개념 부재 — 날조 금지)
- label/parent_interface = 인터페이스명, scope = best-effort(fe80→link/127.→host/그외 global)

검증(build #158, 전 스테이지 SUCCESS):
- Ethernet4 (192.168.50.40 + .41, 같은 /24): 한 주소 is_secondary=true, 다른 하나 false (정확히 1 primary)
- 전 주소 6개 5키 보유, is_secondary 누락 0, is_alias=true 0 (날조 0)
- 단위 787 passed (신규 6), field_dictionary + `docs/contract/03-fields.md` §6.4.2 Windows 반영 동기화

한계(문서화됨): "어느 IP 가 primary 인가"는 수집 순서 기반(best-effort) — Windows 는 커널 primary 플래그
API 가 없어 first-in-collection 을 primary 로. "같은 서브넷에 정확히 1 primary" 불변식은 보장.

## 라운드 5 — diagnosis selected_port 타입 + network.summary 이중카운트 (build #159)

전체 envelope 전수 스캔(사용자 지시: 일부만 보지 말 것)에서 추가 2건:
- **selected_port 타입**: Windows 경로(`site.yml`)가 `"{{ ansible_port | default(5986) }}"` → 문자열 `"5986"`.
  checked_ports(`[5985,5986]` 정수) / Linux SSH 경로(`22` 정수) / precheck 모듈(int) 과 불일치 → `| int`.
  검증: #159 `selected_port=5986` (Int64).
- **network.summary 이중카운트**: 팀 VLAN tNIC(`LabTeam1 - VLAN 100`, 20G)을 부모 팀(`LabTeam1`, 20G)과
  별도 NIC 로 세서 같은 물리 대역 이중 카운트(site 실측: 둘 다 같은 팀 LabTeam1/2×10G). field_dictionary
  정의 = "NIC 그룹" → enriched 기준 + VLAN tNIC(vlan_id)/team member 제외. summary 태스크를 teaming 정규화
  이후로 이동. 검증: #159 `20000 qty=3→2`, `10000 qty=2` (LabTeam1+LabTeam2 + Ethernet0+4).

연관 회귀 점검(#158 대비): ib=0 / driver_map=9 / Ethernet4 is_secondary=1 / l2=null / teams=2 / errors=0 유지,
전 섹션 status 동일 → **연쇄 문제 0**. system.runtime 호스트 대조(tz Asia/Seoul 정규화, swap 1280/515,
방화벽 3 active) 일치.

## 수렴 — 비-버그 관찰 (코드 수정 아님, 운영 참고)
- `diagnosis.auth.fallback_used=true / used_role=secondary`: 매 빌드 primary Windows vault 자격증명이
  실패하고 secondary(cloviradmin)로 fallback. **gather 코드 버그 아님 — vault 설정 점검 필요(운영)**.
- `system.runtime.ntp_last_sync=null` / `meta.adapter_version=null`: 미수집(정직한 null, 날조 아님).

## 미확인 / 후속

- 실 ansible os-gather 전체 파이프라인(Jenkins Stage 1~4) 미실행 — 컨트롤러(Linux agent) 필요.
  본 검증은 PowerShell 수집부 + Python 정규화부 분리 검증 + 단위 회귀로 대체.
- Windows baseline JSON(`schema/baseline_v1/windows_*`) 갱신 여부는 실 파이프라인 재캡처 후 판단 (Additive 라 Must 필드 불변).
