# ESXi 4건 수정 + Linux 검증 (Jenkins 검수 루프, 실장비)

- 일시: 2026-06-30
- 대상: ESXi 10.100.64.2(esxi02, Cisco TA-UNODE-G1, ESXi 7.0.3) / Linux 10.100.64.161(RHEL 8.10) / 10.100.64.165(RHEL 9.6)
- 경로: Jenkins master 10.100.64.152 job `hshwang-gather` 실 4-Stage 파이프라인 (#160~#163) + SSH(paramiko) 실측 대조

## ESXi 수정 4건 (build #162 발견 → #163 검증)

| # | 버그 | 수정 | #162→#163 |
|---|---|---|---|
| B | network.summary 가 vmk(speed=none)로 계산돼 `null qty=1` 누출 + null 가드 부재 | pnic(`_e_ext_adapters` 실 speed) 기준 산출(collect_network_extended) + null/0 가드(normalize_network) | `null q1` → `1000 q1 + 10000 q2` |
| A | cpu 최상위 `manufacturer` 누락 (summary.groups 엔 존재) | normalize_system cpu 최상위에 manufacturer 추가 (Win/Linux parity) | `(없음)` → `Intel` |
| C | bios_date 풀타임스탬프 — field_dictionary 계약(YYYY-MM-DD) 위반 | `(raw).split('T')[0]` truncate | `2021-02-02T09:00:00+09:00` → `2021-02-02` |

검증(#163): 호스트 pnic 실속도(vmnic0=1000 up / vmnic3·4=10000 up / vmnic1·2·5 down)와 summary 일치.
연관 회귀 0 — adapters=6/disks=2/hbas=2/controllers=5/datastores=2, cpu 44/88, mem 1048464 전부 불변, 전 섹션 status 동일.

### ESXi 비-버그 (의도된 설계 — 수정 안 함)
- storage.summary `groups=[]` + grand_total_gb=datastore 합계: normalize_storage line 76 주석 "physical disk
  grouping 은 OS/Redfish 채널" — 의도된 채널 차이 (rule 92 R2 — 정상 동작 설계 임의 변경 금지).
- physical_disks protocol/health=null, hbas vendor=null, runtime listening_ports=[]/swap=null: vSphere API
  미제공 영역의 정직한 null (날조 아님).

## Linux 검증 (build #160/#161 — 버그 0건)

전수 스캔(heuristic) clean: 캐시 실값(null→0 없음) / float 노이즈 0 / selinux 정규화 / 본드·주소(is_secondary/is_alias) 정상 / summary null 누출 없음.

### 10.100.64.161 (RHEL 8.10) SSH 실측 대조 — 전부 일치
| 값 | 호스트(SSH) | envelope |
|---|---|---|
| CPU sockets/cores/threads | 4 / 1×4 / 1 | 4/4/4 |
| L2/L3 캐시 | 256K / 56320K | 256 / 56320 |
| selinux | Enforcing | enabled |
| bonds | bond1,bond2 | 2 |

### hostname=localhost 확인 (버그 아님)
두 호스트 SSH `hostname` → `localhost.localdomain` (161 설정됨 / 165 /etc/hostname unset → 런타임 기본값).
게더가 실 OS 값을 충실 반영. (#160 fqdn 이 `localhost` 로 약간 truncate 되나 localhost 라 무의미.)

## 결론
ESXi 채널 4 버그 수정·검증 완료. Linux 채널 버그 0(실측 대조 완료). 3 대상 모두 status=success / errors=0.
