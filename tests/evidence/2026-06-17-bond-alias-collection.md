# 2026-06-17 — OS 네트워크 bond alias IP 수집

## 요청

OS 네트워크 개더링에 bond alias IP 수집을 추가. Linux 계열 전체 동작(RHEL 고정 금지).
테스트 대상: 10.100.64.161(RHEL 8.10), 10.100.64.165(RHEL 9.6) — bond alias 설정됨.

## 1. 현재(변경 전) 수집 방식

| 항목 | 방식 |
|---|---|
| `network.interfaces` / `bonds` / `bridges` / `teams` | `filter_plugins/network_topology.py` `build_linux_network()` 가 collector(`_l_net_collector`) 라인 + base interfaces 로 생성 |
| `network.driver_map` | 본 코드 경로엔 `driver_map` 미존재(질문 전제와 다름). NIC HW 는 `adapters[]`(lspci) |
| IP 주소 source | python_ok: `ansible_<iface>.ipv4.address`(primary only, secondaries/label 없음) · raw: `ip -o -4 addr show dev <dev> \| head -1`(primary only) |
| bond 상세 | `/sys/class/net/*/bonding` + `/proc/net/bonding/*` + `ip -d link` 를 collector 가 `BOND\|/BSLAVE\|/SLSTATE\|/SLMETA\|` 라인으로 emit → 필터 병합 |

→ **두 경로 모두 alias/secondary IP 누락** (primary 1개만). `build_linux_network()` 는 이미
bond master 인터페이스의 `addresses` 를 `bonds[].addresses` 로 mirror 하고 있었음.

## 2. 선택한 스키마 (Additive)

`interfaces[].addresses[]` / `bonds[].addresses[]` 각 주소 레코드에 기존 5 키
(`family`/`address`/`prefix_length`/`subnet_mask`/`gateway`) + 신규 5 키:

| 키 | 값 | 결정 |
|---|---|---|
| `label` | `ip addr` label (alias=`bond1:1`, 일반=ifname) | |
| `parent_interface` | 바인딩된 dev (alias 도 parent=bond) | bond1:1 을 신규 iface 로 만들지 않음 |
| `is_alias` | `label != parent_interface` | |
| `scope` | global/link/host | 기존 IPv6 scope 키 재사용 |
| `is_secondary` | 커널 secondary(같은 서브넷 2번째+ IPv4) | best-effort. 다른 서브넷 alias 는 false(정상) |

## 3. 수집 방식 (Linux 호환 다중 소스)

공유 collector `_l_net_collector` 에 주소 블록 추가(python_ok shell·raw 두 경로 공용):
`ip -j addr show`(1순위, JSON) → `ip -o addr show`(2순위) → `ifconfig -a`(3순위).
nmcli/ifcfg 비의존. 필터 `merge_linux_addresses()` 가 parse 후 parent `addresses[]` 에 병합
(기존 주소는 신규 키 enrich + 값 보존, alias 는 append). `build_linux_network()` 가 bond master
IP 를 `bonds[].addresses` 로 mirror → interfaces ↔ bonds 자동 일관.

## 4. 변경 파일

| 파일 | 변경 |
|---|---|
| `filter_plugins/network_topology.py` | `parse_linux_addresses` / `merge_linux_addresses` + 헬퍼 추가, FilterModule 등록. `build_linux_network` 불변 |
| `os-gather/tasks/linux/gather_network.yml` | `_l_net_collector` 주소 블록(ip -j/-o/ifconfig) + 양 경로 normalize 체인에 `merge_linux_addresses` 삽입 |
| `schema/field_dictionary.yml` | +10 entries (interfaces/bonds × addresses 5 키, `channel:[os]` nice) |
| `tests/unit/test_network_topology.py` | +13 테스트(parse 3-tier/merge/full-chain/back-compat/immutability), rhel96 alias 단언 |
| `tests/unit/test_os_network_render.py` | merge 필터 등록 + raw 렌더 alias 단언 |
| `tests/fixtures/os/net/` | `rhel810_addr.txt`·`rhel96_addr.txt` 신규(실 ip -j 캡처), `rhel810_rawpath_stdout.txt` ADDRJSON append, `rhel810/rhel96_bond_network.expected.json` 재생성 |
| `docs/develop/05-field-mapping.md`, `docs/contract/03-fields.md` | 주소 source 매핑 + 6.4.2 스키마 문서 |

## 5. 테스트 결과 (✅ 확인함)

- `pytest tests/unit tests/regression tests/e2e` → **1093 passed, 1 skipped, 9 xfailed, 0 failed**
- `tests/unit/test_network_topology.py tests/unit/test_os_network_render.py` → 62 passed
- `validate_field_dictionary.py` → PASS (0 failed) · `output_schema_drift_check.py` → exit 0 (sections=11, paths=160)
- `verify_vendor_boundary.py` → exit 0 · `verify_harness_consistency.py` → exit 0

## 6. 실장비 검증 (✅ 확인함 — live SSH)

업데이트된 `_l_net_collector` 를 161/165 에 SSH 로 직접 실행 → 실 stdout 을 실제 필터 파이프라인
(`merge_linux_addresses`→`build_linux_network`)에 투입한 결과:

| 서버 | bond1 addresses | bond2 addresses | bond meta |
|---|---|---|---|
| 161 (RHEL 8.10, py3.6) | 10.100.64.169 + **10.100.10.100 (bond1:1, is_alias)** | 10.100.64.170 + **10.100.10.101 (bond2:1)** | mode active-backup, active_slave ens161/ens225, slaves 4 유지 |
| 165 (RHEL 9.6, py3.9) | 10.100.64.167 + **10.100.10.102 (bond1:1)** | 10.100.64.168 + **10.100.10.103 (bond2:1)** | 동일 |

- alias 가 `interfaces[]` 와 `bonds[].addresses` 양쪽에 일관 반영. `label`/`parent_interface`/`is_alias`/`scope`/`is_secondary` 정확.
- `bond1:1` 등 alias 가 **별도 인터페이스로 생성되지 않음** 확인.
- slave NIC(ens161/193/225/256) 모두 IP 없음 유지. 기존 IP/active_slave/slaves 불변.
- 두 서버 모두 `ip -j` 사용 가능 → ADDRJSON(1순위) 경로 작동. 161=raw fallback 환경, 165=python_ok 환경 모두 동일 collector 로 검증.
- alias 없는 NIC(ens192/ens224): 주소 수·기존 값 불변, 신규 키만 Additive 추가 확인.

## 7. 남은 한계

- **alias 게이트웨이**: alias 주소의 per-route gateway 는 수집 안 함(`gateway:null`). 기본 GW 만 primary 에 주입(기존 동작 유지).
- **Windows/ESXi/Redfish**: 신규 5 키 미적용(요청 범위 Linux OS 전용, `channel:[os]`). 필요 시 별도 cycle.
- **schema/baseline_v1 ubuntu/rhel810_raw_fallback**: 다른 서버(alias 없음) 실측본이라 미수정. 구조 검증 테스트 green(신규 키 Additive). 차기 실측 recapture 시 자연 반영.
- **ansible-playbook --syntax-check**: 본 controller(Windows)에 ansible 미설치 → 미실행. YAML 은 PyYAML load + 실제 yml 템플릿 렌더 테스트(`test_os_network_render.py`)로 검증.
- **is_secondary**: 커널 secondary 플래그가 `ip` 출력에 있을 때만 true. 본 테스트 alias 는 다른 서브넷이라 false(정상).
