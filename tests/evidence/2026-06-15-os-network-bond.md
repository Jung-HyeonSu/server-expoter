# OS 네트워크 본딩/티밍 수집 보강 — 실장비 검증 evidence

- 일시: 2026-06-15
- 작업: OS-gather 네트워크 수집에 Linux 본딩 + Windows 티밍 토폴로지 수집 추가 (Additive)
- 검증자: AI (Claude) + 사용자 제공 실장비
- 정본 코드:
  - `filter_plugins/network_topology.py` (신규 — bond/vlan/bridge/team 파서, stdlib only)
  - `os-gather/tasks/linux/gather_network.yml` (collector + python_ok/raw 두 경로)
  - `os-gather/tasks/windows/gather_network.yml` (LBFO/SET teaming)

## 1. 검증 환경 (실장비)

| 호스트 | IP | OS | Python | 수집 경로 | 비고 |
|---|---|---|---|---|---|
| rhel810 | 10.100.64.161 | RHEL 8.10 (Ootpa) | 3.6.8 | **raw fallback** (`python_incompatible`) | VMware VM, VMXNET3 |
| rhel96 | 10.100.64.165 | RHEL 9.6 (Plow) | 3.9.21 | **python_ok** | VMware VM, VMXNET3 |

두 호스트 모두 사용자가 동일 토폴로지로 사전 구성:
- bond1 = active-backup, slaves [ens161(active), ens193(backup)], miimon 100
- bond2 = active-backup, slaves [ens225(active), ens256(backup)], miimon 100
- 관리 NIC ens192(기본 라우트) + ens224 는 비본딩, 물리 slave 는 IP 없음, bond 에 IP.

## 2. 실 명령 원본 (ground truth) — rhel810

```
$ ip -d link show   (발췌)
9: bond1: <...MASTER...> ... bond mode active-backup active_slave ens161 miimon 100 ... xmit_hash_policy layer2 ...
5: ens256: <...SLAVE...> master bond2 ... bond_slave state BACKUP perm_hwaddr 00:50:56:84:38:a4
$ cat /sys/class/net/bond1/bonding/{mode,slaves,active_slave,miimon}
active-backup 1 / ens161 ens193 / ens161 / 100
$ cat /proc/net/bonding/bond1   (발췌)
Bonding Mode: fault-tolerance (active-backup); Currently Active Slave: ens161; MII Polling Interval (ms): 100
Slave Interface: ens161 ... Permanent HW addr: 00:50:56:84:57:81
Slave Interface: ens193 ... Permanent HW addr: 00:50:56:84:b6:f7
$ ip -br addr  (발췌)
ens192  UP  10.100.64.161/24 ;  bond1  UP  10.100.64.169/24 ;  bond2  UP  10.100.64.170/24
ens161/ens193/ens225/ens256  UP  (no IP)
```

전체 캡처: 세션 로컬 `.verify/net/rhel810_capture.txt`, `rhel96_capture.txt` (비커밋 — SSH 자격 포함 스크립트와 동일 폴더).
커밋된 fixture: `tests/fixtures/os/net/{rhel810_bond_topo.txt, rhel96_bond_topo.txt, rhel810_rawpath_stdout.txt}`.

## 3. 최종 JSON ↔ 원본 대조 결과

### rhel810 (raw fallback) — `tests/fixtures/os/net/rhel810_bond_network.expected.json`
실제 `gather_network.yml` raw 경로 템플릿 체인을 실장비 raw stdout 으로 렌더한 결과.

```
data.network.bonds[0] = {name:bond1, mode:active-backup, active_slave:ens161, miimon:100,
  lacp_rate:slow, xmit_hash_policy:layer2, primary:ens161, ad_select:stable,
  addresses:[10.100.64.169/24], slaves:[
    {name:ens161, state:active, perm_hwaddr:00:50:56:84:57:81, speed_mbps:10000, mtu:1500, link_status:up},
    {name:ens193, state:backup, perm_hwaddr:00:50:56:84:b6:f7, speed_mbps:10000, ...}]}
data.network.interfaces: bond1(master,IP) bond2(master,IP) ens192 ens224
  + ens161/ens193/ens225/ens256 (bond_role:slave, addresses:[], bond_master 지정)
data.network.bridges = [{name:virbr0, members:[]}]
```

| 항목 | 원본 명령 | 최종 JSON | 일치 |
|---|---|---|---|
| bond master | ip -br addr → bond1 10.100.64.169 | bonds[0].addresses=10.100.64.169 | [OK] |
| bonding mode | /sys .../bonding/mode = active-backup | bonds[0].mode=active-backup | [OK] |
| active slave | /sys .../active_slave = ens161 | bonds[0].active_slave=ens161 | [OK] |
| miimon | /sys .../miimon = 100 | bonds[0].miimon=100 | [OK] |
| slave 관계 | /sys .../slaves = ens161 ens193 | bonds[0].slaves 2개 + interfaces bond_master | [OK] |
| slave state | ip -d link bond_slave state | slaves[].state active/backup | [OK] |
| slave perm MAC | /proc Permanent HW addr | slaves[].perm_hwaddr | [OK] |
| 물리 NIC IP 없음 | ip -br addr (slave 공란) | slave interface addresses=[] | [OK] |

### rhel96 (python_ok) — `tests/fixtures/os/net/rhel96_bond_network.expected.json`
실 collector 출력 + ansible network fact 재구성(실 ip/sysfs 동일 소스)으로 python 경로 템플릿 렌더.
bond1=10.100.64.167, bond2=10.100.64.168. bond 메타/슬레이브 = rhel810 과 동일 구조 [OK].
→ **Ansible 모듈 경로와 raw 경로의 bond 수집 결과 동일** (collector+filter 경로 독립).

### 802.3ad 실커널 검증 (rhel810, dummy 인터페이스 — SSH NIC 미접촉, 검증 후 삭제)
```
/sys/class/net/bondtest/bonding/{mode,lacp_rate,xmit_hash_policy} = 802.3ad / fast / layer3+4
collector → BOND|bondtest|802.3ad||100|fast|layer3+4||stable|dmy0 dmy1
parsed → mode=802.3ad lacp_rate=fast xmit=layer3+4 (Speed Unknown → speed_mbps:None graceful)
cleanup → bondtest 삭제 확인
```

## 4. 검증 방법 (재현 절차)

1. SSH 로 두 호스트의 실 명령 캡처 (`ip -d link`, `/proc/net/bonding/*`, `/sys/class/net/*/bonding/*`).
2. collector(POSIX sh) 를 실 호스트에서 실행 → '|' 구분 라인 emit (실 출력).
3. raw 경로: 실제 YAML 의 raw 스크립트(+collector)를 호스트에서 실행 → stdout → 실제 set_fact 템플릿 체인 렌더 → 최종 data.network.
4. python 경로: 실 collector 출력 + 실 ip/sysfs 기반 ansible fact 재구성 → 실제 템플릿 렌더.
5. 결과를 원본 명령과 대조 (위 표).

회귀 고정: `tests/unit/test_os_network_render.py` 가 실제 YAML 템플릿을 커밋된 실장비 stdout fixture 로 렌더해 기대 JSON 과 정확히 일치하는지 검사 (SSH 없이 CI).

## 5. 알려진 한계

- **Windows**: 실 Windows 호스트 미제공 → LBFO/SET 수집은 코드 + 단위 테스트(realistic fixture)만 검증, 실장비 미검증. ⚠️ (후속: Windows Teaming 실장비 검증 필요)
- **python_ok 경로**: bond 부분(collector+filter)은 실 호스트 출력으로 검증. base interface 부분은 ansible setup fact 재구성으로 렌더(실 ip/sysfs 동일 소스). 전체 ansible-playbook 실행은 lab 의 호스트에 ansible 미설치로 미수행 → Jenkins 실 빌드 권장 (후속).
- 802.3ad 의 per-slave state 는 `ip -d link`(전 모드 권위) 우선. `ip -d` 미지원 구형 + 802.3ad 조합에서는 /proc 에 "Currently Active Slave" 부재로 state 부정확 가능(드문 graceful 강등).
