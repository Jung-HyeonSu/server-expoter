# 2026-04-29 Output Quality Bug Tickets

> 출처: 2026-04-29 lab full-sweep (Jenkins #114 Redfish + #115 OS + #116 ESXi).
> 분석: deep dive 4 round → 99 finding → ticket 영속화.
> 브랜치: `fix/output-quality-99bugs-2026-04-29`.

## 처리 절차 (rule 28 R1 + rule 95 R1)

각 티켓은 다음 게이트를 모두 통과해야 closed:

1. **VERIFY** — Jenkins agent (10.100.64.154)에서 실제 raw 외부 API 응답 capture → 증상 재현 확인
2. **PLAN** — 영향 모듈 / vendor / 채널 / fix 위치 명시
3. **TEST** — pytest fixture (raw 기반) + 회귀 테스트 추가 (RED)
4. **FIX** — 코드 수정 (GREEN)
5. **CHECK** — pytest + verify_harness_consistency + verify_vendor_boundary + lab re-run
6. **CONSISTENCY** — 같은 host 3회 반복 실행 — 누락/중복/drift 0건 확인
7. **CLOSE** — evidence 첨부, 티켓 closed 마크

## 카테고리

| ID | 제목 | 채널 | Vendor | 비고 |
|---|---|---|---|---|
| B01 | GPU(Tesla T4)가 CPU 섹션에 합쳐짐 | redfish | dell | ProcessorType 필터 누락 |
| B02 | DNS unspecified IP(`0.0.0.0`/`::`) 그대로 노출 | redfish | dell/hpe/lenovo | 정규화 부재 |
| B03 | failed envelope 6필드 정합성 깨짐 (None vs {}) | redfish | dell | rule 13 R6 |
| B04 | Ubuntu DNS=`127.0.0.53` (systemd-resolved stub) | os | linux | resolvectl 미사용 |
| B05 | RHEL 8.10 raw_fallback cpu.summary.groups=[] | os | linux | raw build_cpu 누락 |
| B06 | ESXi network.summary.groups buggy | esxi | vmware | quantity=1 (실제 6) |
| B07 | Redfish system.* 모두 None인데 sections.system="success" | redfish | all | rule 22 status_rules |
| B08 | BMC.product/mac/hostname 모두 None | redfish | all | 필드 추출 누락 |
| B09 | memory.slots[*].locator 모두 None | redfish | all | DIMM 위치 추출 누락 |
| B10 | physical_disks[*].capacity_gb 모두 None | redfish | all | Drive.CapacityBytes 누락 |
| B11 | GPU group total_cores=0 (B1 부산물) | redfish | dell | B1 fix되면 자연 해결 |
| B12 | firmware.component vendor마다 ID 형식 다름 | redfish | all | cross-vendor 매칭 어려움 |
| B13 | network.interfaces.link_status 표기 비일관 | redfish | all | linkup/linkdown vs none |
| B14 | network.interfaces.name 의미 vendor마다 다름 | redfish | all | 정규화 필요 |
| B15 | data.users=[] but sections.users="not_supported" | redfish | all | 정책 결정 |
| B16 | bios_date 형식 vendor마다 다름 | redfish/esxi | all | ISO 8601 통일 필요 |
| B17 | Linux users.username 모두 None | os | linux | getent 추출 누락 |
| B18 | system.hostname=None (fqdn만 채워짐) | os | linux | gather_system 누락 |
| B19 | r760-6 baremetal hardware 미수집 | os | linux baremetal | dmidecode 미분기 |
| B20 | VM CPU sockets=4 cores=4 threads=4 | os | linux VM | lscpu Socket(s) 미사용 (관찰) |
| B21 | RHEL 8.10 raw fallback summary.groups 누락 (B5 동일) | os | linux | duplicate of B5 |
| B22 | VM cpu.max_speed_mhz=None | os | linux VM | setup module 누락 |
| B23 | r760-6 memory.mfg=`00AD063200AD` raw hex JEDEC | os | linux | 정규화 매핑 부재 |
| B24 | r760-6 memory.speed Redfish 4400 vs OS 5600 drift | redfish vs os | dell | 의미 정의 부재 |
| B25 | Linux storage.physical_disks.capacity_gb=None | os | linux | /sys/block size 미사용 |
| B26 | Linux storage.filesystems.fstype=None | os | linux | df -T 미사용 |
| B27 | RHEL VM tz=America/New_York (관찰) | os | linux | 환경 |
| B28 | r760-6 baremetal hardware not_supported (B19 동일) | os | linux | duplicate of B19 |
| B29 | Linux disk media_type 부정확 (RAID 가상 디스크) | os | linux | rotational 한계 |
| B30 | esxi03 vmnic1 누락 | esxi | vmware | 실 hw vs 누락 검증 필요 |
| B31 | ESXi runtime tz/ntp/firewall_state 모두 None | esxi | vmware | esxcli 미사용 |
| B32 | ESXi network.default_gateways=[] | esxi | vmware | routing 미수집 |
| B33 | ESXi network.summary.groups buggy (B6 동일) | esxi | vmware | duplicate of B6 |
| B34 | ESXi physical_disks=[] | esxi | vmware | scsiLun 미사용 |
| B35 | ESXi storage.controllers=[] | esxi | vmware | 정책 결정 |
| B36 | ESXi HBA 개수가 host별 다름 (관찰) | esxi | vmware | 환경 |
| B37 | ESXi auth.attempted_count=2 fallback_used=false | esxi | vmware | 의미 모호 |
| B38 | ESXi memory.installed_mb=null (한계) | esxi | vmware | 관찰 |
| B39 | ESXi sections.users=not_supported (정책) | esxi | vmware | 정책 결정 |
| B40 | Ansible reserved variable 'name' warning | global | all | cleanup |
| B41 | Dell PSU=1 (실제 redundant 2개일 수도) | redfish | dell | 검증 필요 |
| B42 | Dell PowerControl 6개 (의미 불명) | redfish | dell | 관찰 |
| B43 | Lenovo firmware version=None 2건 (Pending) | redfish | lenovo | pending 분리 |
| B44 | Lenovo firmware component naming vendor-specific | redfish | lenovo | 일관성 |
| B45 | Dell PSU 1개 — PS2 누락 의심 | redfish | dell | 사용자 검증 |
| B46 | power.power_control = list of strings (builder bug) | redfish | all | dict.keys() 누락 |
| B47 | esxi03 vmnic1 누락 (B30 동일) | esxi | vmware | duplicate of B30 |
| B48 | Cisco logical_volume.name="" 빈 문자열 | redfish | cisco | fallback 필요 |
| B49 | Dell BOSS volumes boot_volume=false | redfish | dell | boot marker 매핑 |
| B50 | duration_ms 1초 단위 절삭 | global | all | builder 정밀도 |
| B51 | Memory total/slots 합계 일치 (OK) | redfish | all | 검증 통과 |
| B52 | storage.grand_total_gb 의미 비일관 (raw vs usable) | redfish | all | 정의 명시 필요 |
| B53 | correlation.bmc_ip == host_ip (의도된?) | redfish | all | 정책 |
| B54 | Dell UUID prefix 4c4c4544 (정상 - 관찰) | redfish | dell | 관찰 |
| B55 | failed envelope diagnosis.details 키 누락 | redfish | dell | 일관성 |
| B56 | failed envelope auth_success=null (false여야) | redfish | all | 의미 정의 |
| B57 | iface[*].mac ≠ adapter[*].mac (의미 정의 부재) | redfish | all | 정의 명시 |
| B58 | PSU Critical 알람이 summary에 노출 안 됨 | redfish | hpe/lenovo | 운영 알람 |
| B59 | Lenovo PSU total_capacity_w=750 (PSU#1 null+PSU#2 750) | redfish | lenovo | None 합산 버그 |
| B60 | storage.grand_total_gb 의미 비일관 (B52 동일) | redfish | all | duplicate of B52 |
| B61 | hardware.oem coverage 비대칭 | redfish | lenovo/cisco | OEM 추출 부족 |
| B62 | ESXi diagnosis.details에 esxi_version 없음 | esxi | vmware | trace 보강 |
| B63 | OS diagnosis.auth 일관성 (OK) | os | linux | 검증 통과 |
| B64 | OS filesystem.used_mb 부동소수점 오차 | os | linux | int() 미적용 |
| B65 | OS filesystem.free_mb=None 모든 fs | os | linux | 추출 누락 |
| B66 | OS filesystem.read_only=None 모든 fs | os | linux | 추출 누락 |
| B67 | OS filesystem.fstype=None (B26 동일) | os | linux | duplicate of B26 |
| B68 | OS network IPv6 address 0개 | os | linux | 추출 누락 |
| B69 | ESXi network IPv6 0개 | esxi | vmware | 환경 의존 |
| B70 | r760-6 Redfish adapter.name="Network Adapter View" | redfish | dell | 의미 없는 라벨 |
| B71 | r760-6 memory.mfg drift (Redfish vs OS) | cross | dell | 정규화 |
| B72 | r760-6 memory.speed drift (4400 vs 5600) | cross | dell | 의미 정의 |
| B73 | OS hostname/fqdn drift | os | linux | builder 누락 |
| B74 | swap_used 분포 (OK 관찰) | os | linux | 관찰 |
| B75 | OS memory.visible_mb < total_mb (kernel reserved) | os | linux | 필드명 명확화 |
| B76 | OS network.adapters=[] 모두 | os | linux | hardware NIC 미수집 |
| B77 | correlation 필드 일관성 | global | all | 정책 |
| B78 | OS VM serial_number raw VMware 형식 | os | linux VM | 정규화 |
| B79 | OS correlation.bmc_ip=None (정책) | os | linux | 정책 |
| B80 | OS envelope.vendor=None (베어메탈도) | os | linux | 분기 부재 |
| B81 | target_type별 envelope.vendor 정책 다름 | global | all | 정책 통일 |
| B82 | RHEL VM hostname=localhost (관찰) | os | linux | 환경 |
| B83 | ESXi hostname=esxi01 short name | esxi | vmware | 환경 |
| B84 | ESXi datastore precision (OK 검증) | esxi | vmware | 검증 통과 |
| B85 | RHEL tz=America/New_York (B27 동일) | os | linux | duplicate of B27 |
| B86 | RHEL hostname misconfig (B82 동일) | os | linux | duplicate of B82 |
| B87 | OS sys.hostname=None (B18 동일) | os | linux | duplicate of B18 |
| B88 | ESXi correlation.bmc_ip=None (정책) | esxi | vmware | 정책 |
| B89 | r760-1 memory Samsung+Hynix 혼합 (관찰) | redfish | dell | 운영 critical 후보 |
| B90 | Cisco memory.mfg=`0xCE00` raw JEDEC | redfish | cisco | 정규화 |
| B91 | RHEL 8.10 raw fallback memory.mfg=None | os | linux | raw builder 누락 |
| B92 | HPE iface.name 숫자만 (`9`,`10`,...) | redfish | hpe | 정규화 |
| B93 | HPE adapter.mac/link 모두 None | redfish | hpe | ports 미통합 |
| B94 | HPE iface.addresses 0개 (관찰) | redfish | hpe | 환경 |
| B95 | Lenovo PSU#1 health=Critical 알람 부재 (B58 동일) | redfish | lenovo | duplicate of B58 |
| B96 | ESXi collection_method=vsphere_api (OK) | esxi | vmware | OK |
| B97 | OS collection_method='agent' 모호 | os | linux | 명확화 |
| B98 | bios_date 형식 vendor 간 비일관 (B16 동일) | global | all | duplicate of B16 |
| B99 | listening_ports = list of int (proto/family 부재) | os | linux | 구조화 |

**dedup 후 unique 티켓: ~80건** (B11=B1 부산물, B21=B5, B28=B19, B33=B6, B47=B30, B60=B52, B67=B26, B85=B27, B86=B82, B87=B18, B95=B58, B98=B16).

## 진행 트래커

각 티켓 파일은 다음 상태 enum 사용:
- `proposed` (생성됨, 검증 전)
- `verified` (raw API로 증상 재현 확인)
- `wip` (fix 진행 중)
- `tested` (pytest GREEN, lab re-run OK)
- `closed` (consistency 3회 통과, evidence 첨부)
- `rejected` (실측 결과 not-a-bug)
- `dup` (다른 ticket의 중복)

상태는 ticket file 본문 첫 줄 `Status: <state>` 로 명시.
