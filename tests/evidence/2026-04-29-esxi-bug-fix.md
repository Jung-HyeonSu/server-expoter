# ESXi Channel BUG #1 / #2 / #4 fix — Round 12 검증

> 일시: 2026-04-29
> 검증자: AI (Claude Opus 4.7) + 사용자 hshwang1994
> 환경: Jenkins agent 10.100.64.154 (jenkins-agent-ops, Ubuntu 24.04)
> ansible-core 2.20.3 / community.vmware 6.2.0 / Python 3.12.3

---

## 1. 배경 — 사용자 보고

ESXi 채널 출력 JSON 검증 중 다음 이상 관찰:

1. `hostname` 이 IP 와 동일 (`10.100.64.1`)
2. `vendor` 가 raw 값 그대로 (`"Cisco Systems Inc"` — 정규화 실패)
3. `network.adapters` / `virtual_switches` / `storage.hbas` 모두 빈 배열 (실 호스트는 NIC 6, vSwitch 1, HBA 다수 보유)
4. `default_gateways` / `dns_servers` 빈 배열 (실 라우팅 존재)

---

## 2. 진단 결과 (raw facts 캡처)

진단 playbook: `tests/scripts/diag_esxi_raw.yml` (1회성 진단 자산, rule 21 R4 보존).

캡처된 raw 응답 핵심 (10.100.64.1):

| 필드 | 값 |
|---|---|
| `_facts.ansible_facts.ansible_hostname` | `"esxi01"` |
| `_facts.ansible_facts.ansible_fqdn` | `__MISSING__` (vmware_host_facts 미반환) |
| `_facts.ansible_facts.ansible_default_ipv4` | `__MISSING__` |
| `_facts.ansible_facts.ansible_machine` / `_processor_mhz` | `__MISSING__` |
| `_vmnic.hosts_vmnics_info` top-level keys | `["esxi01"]` (← hostname, IP 아님) |
| `_vmnic.hosts_vmnics_info["esxi01"]["all"]` | `["vmnic0", ..., "vmnic5"]` (string list — 이름만) |
| `_vmnic.hosts_vmnics_info["esxi01"]["vmnic_details"]` | dict list (실 매핑 대상) |
| `_vmhba.hosts_vmhbas_info["esxi01"]["vmhba_details"]` | dict list |
| `_vswitch.hosts_vswitch_info["esxi01"]` | `{"vSwitch0": {pnics, mtu, num_ports}}` (dict-of-dict) |
| `_cfg.hosts_config_info` | `{}` (빈 응답 — DNS 추출 자체 불가) |

### 외부 계약 (rule 96 R1) 매핑 정정

| 모듈 | 기존 코드 | 실제 키 |
|---|---|---|
| `vmware_host_vmnic_info` | `[ip]["all"]` (string list) | `[hostname]["vmnic_details"]` (dict list) |
| vmnic dict | `n.pci` | `n.location` |
| `vmware_host_vmhba_info` | `[ip]["all"]` | `[hostname]["vmhba_details"]` |
| vmhba dict | `h.adapter_type` / `h.pci_slot` / `h.node_world_wide_name` | `h.type` / `h.location` / `h.node_wwn` |
| vmhba dict (FC) | `h.port_world_wide_name` | `h.port_wwn` |
| `vmware_vswitch_info` | `[ip]` (list 가정) | `[hostname]` (dict-of-dict, key=vSwitch name) |
| vswitch portgroups | `v.portgroups` (vswitch_info 에 없음) | `vmware_portgroup_info` 결과를 vswitch 별 group |

---

## 3. 코드 fix

### BUG #1 — `hostname` = IP

원인:
- `esxi-gather/tasks/normalize_system.yml`: `system.fqdn = "{{ _e_ip }}"` (`ansible_hostname` 미사용, `system.hostname` 키 자체 누락)
- `common/tasks/normalize/build_output.yml`: `hostname` 폴백 chain `system.hostname → system.fqdn → _out_ip` 에서 앞 둘이 비어 IP 폴백

Fix:
- `esxi-gather/site.yml`: `collect_facts` 직후 `_e_hostname` 변수 도입 (ansible_hostname 우선, IP 폴백)
- `normalize_system.yml`: `system.hostname` / `system.fqdn` 모두 `_e_hostname` 사용

### BUG #2 — vendor 정규화 실패

원인: Jinja2 loop scoping. `{% set canonical = canon %}` 이 inner loop block 안에서만 영향 → outer 변수 갱신 안 됨. cycle-016 "9 파일 namespace pattern fix" 잔류분.

Fix: `esxi-gather/site.yml` 의 vendor 정규화 블록을 `namespace(canonical=none)` 으로 wrapping.

### BUG #4 — extended modules lookup key 잘못 + 매핑 키 mismatch

원인: 위 2절 raw 진단 표 참조.

Fix: `esxi-gather/tasks/collect_network_extended.yml`
- lookup key `_e_ip` → `_e_hostname` (first-key 폴백)
- vmnic: `.get('all', [])` → `.get('vmnic_details', [])`
- vmnic 매핑: `pci` → `location`, `adapter` 키 추가
- vmhba: `.get('all', [])` → `.get('vmhba_details', [])`
- vmhba 매핑: `type` / `location` / `port_wwn` / `node_wwn` / `bus`
- vswitch: dict-of-dict iteration (key=vswitch name)
- vswitch.portgroups: `vmware_portgroup_info` 결과를 vswitch 별 group 후 join

---

## 4. 실 ESXi 검증 (10.100.64.1 + 10.100.64.2)

agent 10.100.64.154 에서 본 `esxi-gather/site.yml` 실행 후 단일 JSON envelope (json_only callback) 캡처.

| 필드 | 10.100.64.1 (esxi01) | 10.100.64.2 (esxi02) |
|---|---|---|
| status | success | success |
| hostname | `esxi01` | `esxi02` |
| vendor | `cisco` | `cisco` |
| auth_success | true | true |
| network.adapters | 6 NIC (Intel I350 ×2 + Cisco VIC ×4) | 6 NIC (동일 패턴) |
| virtual_switches | vSwitch0 (mtu=9000, pnics=[vmnic3,4], portgroups=4) | 동일 |
| portgroups | 4 (10.100.64.0/24 + Trunk + VM Network + Management Network) | 4 |
| storage.hbas | 4 (AHCI×2 + SAS RAID + iSCSI) | 5 (AHCI×2 + SAS RAID + FC×2 nfnic Cisco UCS VIC Fnic) |
| storage.hbas wwpn / wwnn (FC) | N/A | esxi02 vmhba2/3 wwpn `20:00:00:27:E3:6C:A6:6E/F`, wwnn `10:00:00:27:E3:6C:A6:6E/F` 정확 추출 |
| storage.datastores | 2 (Local-RAID5 / RAID0) | 2 (동일 패턴) |

### 잔류 미세 이슈 (별도 cycle 권장)

- `network.default_gateways = []` — `vmware_host_facts.ansible_default_ipv4` 자체가 미반환
- `network.dns_servers = []` — `vmware_host_config_info` 빈 응답. `community.vmware.vmware_host_dns_info` 별도 모듈 필요
- `network.adapters[].speed_mbps` — Connected 시 int (10000), Disconnected 시 string ("N/A") 혼재. 호출자 측 일관성 정책 결정 필요
- `cpu.architecture` / `system.architecture` / `cpu.max_speed_mhz` — vmware_host_facts 미반환 (model 파싱 폴백 가능, 우선순위 낮음)
- `interfaces[].link_status = "unknown"` — `ansible_vmk0.active` 필드 폴백 부족

---

## 5. 변경 파일

```
esxi-gather/site.yml                              (+11 lines)
esxi-gather/tasks/normalize_system.yml            (+3 lines)
esxi-gather/tasks/collect_network_extended.yml    (+30 lines)
schema/baseline_v1/esxi_baseline.json             (231 +, 47 -) — 10.100.64.2 (esxi02) 실측 갱신
tests/scripts/diag_esxi_raw.yml                   (NEW, 1회성 진단 자산)
tests/evidence/esxi01_2026-04-29.json             (NEW, raw 캡처)
tests/evidence/2026-04-29-esxi-bug-fix.md         (NEW, 본 문서)
```

---

## 6. 후속 추적 (rule 70)

- `docs/ai/CURRENT_STATE.md` — production-audit cycle 후속 entry
- `docs/reference/decision-log.md` — Round 12 등재
- `docs/ai/catalogs/EXTERNAL_CONTRACTS.md` — community.vmware 6.2.0 vmnic / vmhba / vswitch 키 매핑 정본

---

## 7. ADR 트리거 (rule 70 R8) 평가

| Trigger | 해당? |
|---|---|
| rule 본문 의미 변경 | NO |
| 표면 카운트 변경 | NO (.claude 미변경) |
| 보호 경로 정책 변경 | NO |

→ ADR 작성 불필요. 본 evidence + commit log 로 충분.
