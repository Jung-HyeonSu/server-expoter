# GUIDE FOR AI — server-exporter

이 파일과 repo 코드를 함께 AI 에 업로드하면,
AI 가 이 repo 의 컨벤션에 맞게 새 gather 를 생성하거나 기존 gather 를 수정한다.

---

## 이 Repo 의 역할

서버의 하드웨어/OS 정보를 수집한다.
호출자 → Jenkins → Ansible → 표준 JSON 흐름으로 동작한다.

---

## 제약 (변경 불가)

| 제약 | 값 |
|------|-----|
| 입력 | `inventory_json = [{"ip":"10.x.x.1"}]` — ip 만 |
| 계정 관리 | vault 자동 로딩 (호출자가 계정 전달 안 함) |
| OUTPUT 태스크명 | `name: OUTPUT` — callback plugin 캡처 기준 |
| schema_version | `"1"` 고정 |

---

## Fragment 기반 수집 철학

각 gather_*.yml / normalize_*.yml 은 전체 JSON 을 만들지 않는다.
자기 역할에 해당하는 fragment 만 생성하고, merge_fragment 를 호출한다.
공통 builder 가 fragment 들을 병합해 최종 JSON 을 만든다.

```
raw collect → normalize → fragment 생성 → merge_fragment.yml → build_* (공통) → OUTPUT
```

**새 수집 항목 추가 방법:**
1. 새 `gather_xxx.yml` 또는 `normalize_xxx.yml` 작성
2. 해당 fragment 변수 생성
3. `merge_fragment.yml` 호출
4. `site.yml` 에 `include_tasks` 한 줄 추가

`site.yml`, `build_output.yml` 전체를 수정할 필요가 없다.

---

## Fragment 변수 규칙

### 생성 변수 (각 gather/normalize task 가 set_fact 해야 하는 것)

```yaml
_data_fragment:               {}   # data 기여분 (없으면 {})
_sections_supported_fragment: []   # 이 task 가 지원하는 섹션
_sections_collected_fragment: []   # 수집 성공한 섹션
_sections_failed_fragment:    []   # 수집 실패한 섹션
_errors_fragment:             []   # errors
```

### 누적 변수 (merge_fragment.yml 이 관리)

```
_merged_data       ← data 재귀 병합 결과
_all_sec_supported ← 지원 섹션 누적
_all_sec_collected ← 수집 성공 누적
_all_sec_failed    ← 수집 실패 누적
_all_errors        ← errors 누적
```

### 공통 builder 입력 변수

```
_out_target_type, _out_collection_method, _out_ip, _out_vendor
→ build_output.yml 호출 전 set_fact
```

### 실패 전용 변수

```
_fail_sec_supported   ← 이 gather 가 지원하는 섹션 목록
_fail_error_section   ← 에러 섹션명
_fail_error_message   ← 에러 메시지
→ build_failed_output.yml 호출 전 set_fact
```

---

## 변수 네이밍 컨벤션

```
_{채널}_{단계}_{의미}

채널: rf(Redfish) e(ESXi) l(Linux) w(Windows)
단계: raw(수집 직후) d(raw 하위 추출) norm(정규화) ok(bool)

예:
  _e_raw_facts          ESXi vmware_host_facts 직접 반환값
  _rf_raw_collect       Redfish 모듈 직접 반환값
  _rf_d_system          raw 에서 추출한 system 데이터
  _rf_norm_interfaces   Redfish 정규화된 인터페이스 목록
  _l_norm_filesystems   Linux 정규화된 파일시스템
  _w_norm_users_list    Windows 정규화된 사용자 목록
  _e_facts_ok           ESXi facts 수집 성공 여부
  _rf_vendor            최종 확정 벤더 (null 허용)
  _output               최종 OUTPUT 변수 — 이름 변경 금지
```

### 채널별 변수 사전

#### OS 수집 변수

| 변수 | 설명 |
|------|------|
| `_l_python` | Linux Python 실행 경로 (preflight) |
| `_l_has_lsblk`, `_l_has_dmi`, `_l_has_last` | 명령 존재 여부 (preflight) |
| `_l_fb` | Linux raw fallback 파싱 결과 |

#### Linux 2-Tier Gather 참고사항

- **Memory**: raw fallback 경로에서 dmidecode 접근이 성공하면 `physical_installed` (물리 장착 메모리)를 반환한다. Python 경로의 `ansible_memtotal_mb`는 커널 예약 후 `os_visible` 값이므로, raw 경로가 하드웨어 인벤토리 용도에 더 정밀하다.
- **SELinux**: `getenforce` 출력(`Enforcing`/`Permissive`/`Disabled`)은 Ansible 컨벤션에 맞게 `enabled`/`disabled`로 정규화된다.
- **Ubuntu SELinux**: Ubuntu에서는 `getenforce`가 미설치이므로 `selinux = null`이 정상이다 (Python 경로의 `disabled`와 다르지만 허용 범위).

#### Network 수집 정책

##### primary 판단 규칙

| 경로 | primary 판단 기준 |
|------|-------------------|
| Python 경로 | `ansible_default_ipv4.interface` = primary |
| Raw 경로 | `ip route show default \| head -1`의 `dev` 필드 = primary (lowest metric wins) |

양쪽 모두 **"IPv4 default route가 걸린 인터페이스 = primary"** 원칙이다.

- **bond master**에 default route가 걸리면 bond master가 primary
- **bridge**에 default route가 걸리면 bridge가 primary
- slave/port 인터페이스는 IP가 없으므로 primary 불가

##### default_gateways 추출

| 경로 | 추출 방식 |
|------|----------|
| Python 경로 | `ansible_default_ipv4.gateway` |
| Raw 경로 | `ip route show default \| head -1` → 3번째 필드 (gateway IP) |

- 다중 default route 존재 시: metric 순으로 정렬된 **첫 번째만** 사용
- IPv6 default gateway: 현재 미수집 (P3)

##### skip 패턴 (제외되는 가상 인터페이스)

아래 패턴에 매칭되는 인터페이스는 수집에서 제외된다:

| 패턴 | 대상 |
|------|------|
| `lo` | loopback |
| `docker*`, `br-*` | Docker bridge networks |
| `veth*` | container veth pairs |
| `virbr*`, `vir*` | libvirt virtual bridges |
| `cni*`, `flannel*`, `cali*` | Kubernetes CNI |
| `tunl*`, `dummy*` | tunnel, dummy interfaces |
| `kube-*` | Kubernetes internal |

**중요**: `br0`, `bond0`, `team0`, `eth0.100`(VLAN) 등 일반 네트워크 인터페이스는 제외 대상이 아니다. 이들은 IP가 할당된 정상 인터페이스이므로 수집된다.

- **bond slave / bridge port 자동 제외**: `/sys/class/net/$dev/master`가 존재하면서 자신이 bridge/bond master가 아닌 인터페이스는 수집 제외 (raw path). Python path에서는 IP 없는 인터페이스가 자동 제외됨

##### bond/team/bridge/VLAN 해석

| 유형 | 수집 여부 | 비고 |
|------|----------|------|
| bond master | IP 있으면 수집됨 | kind=os_nic, slave는 IP 없어 자동 제외 |
| bridge (br0) | IP 있으면 수집됨 | 하위 port는 IP 없어 자동 제외 |
| VLAN (eth0.100) | IP 있으면 수집됨 | — |

- **speed**: bond/bridge는 `/sys/class/net/*/speed`가 없거나 `-1` → `null`

##### speed/link_status 해석

| 필드 | 소스 | 비고 |
|------|------|------|
| `speed` | `/sys/class/net/*/speed` | 가상 NIC는 `-1` 또는 미보고 → `null` |
| `link_status` | `/sys/class/net/*/operstate` | `up`/`down`/`unknown` |

- bond master speed는 kernel이 보고 안 할 수 있음 → `null`

##### DNS 해석

- `/etc/resolv.conf`의 `nameserver` 행에서 추출
- `127.0.0.53` = systemd-resolved stub resolver (실제 upstream DNS가 아님)
- **운영 해석**: stub resolver가 보이면 `resolvectl status`로 실제 DNS 확인 필요

##### 현재 한계

- IPv6 주소/gateway 미수집
- policy routing (`ip rule`, `table`) 미반영
- 다중 default route 중 첫 번째만 사용

##### 배포판별 명령어 지원 매트릭스

실측 기준 (5대 서버 검증, SLES 15는 공식 문서 기준 예측):

| 명령/소스 | 패키지 | RHEL 8 | RHEL 9 | Rocky 9 | Ubuntu 24 | SLES 15 | gather 사용 | fallback |
|-----------|--------|--------|--------|---------|-----------|---------|------------|---------|
| `ip` | iproute | ✅ | ✅ | ✅ | ✅ | ✅ | 핵심 (addr/route/link) | 없음 — 필수 |
| `getent` | glibc-common | ✅ | ✅ | ✅ | ✅ | ✅ | users 수집 | 없음 — 필수 |
| `lsblk` | util-linux | ✅ | ✅ | ✅ | ✅ | ✅ | storage 물리디스크 | 빈 배열 반환 |
| `df` | coreutils | ✅ | ✅ | ✅ | ✅ | ✅ | storage 파일시스템 | 빈 배열 반환 |
| `getenforce` | libselinux-utils | ✅ | ✅ | ✅ | ❌ | ❌ | system.selinux | null |
| `lastlog` | shadow-utils/login | ✅ | ✅ | ✅ | ✅ | ✅ | users.last_access_time | last → utmpdump |
| `utmpdump` | util-linux | ✅ | ✅ | ✅ | ✅ | ✅ | users 3차 fallback | null |
| `systemd-detect-virt` | systemd | ✅ | ✅ | ✅ | ✅ | ✅ | system.hosting_type | unknown |
| `dmidecode` | dmidecode | ✅ | ✅ | ✅ | ✅ | ✅ | memory, serial/uuid | 권한 의존 |
| `resolvectl` | systemd-resolved | ✅(8) | ❌(9) | ❌ | ✅ | ❌ | 미사용 (참고용) | — |
| `nmcli` | NetworkManager | ✅ | ✅ | ✅ | ❌ | ❌ | 미사용 | — |
| `networkctl` | systemd | ❌ | ❌ | ❌ | ✅ | ❌ | 미사용 | — |
| `/sys/class/net/*` | kernel sysfs | ✅ | ✅ | ✅ | ✅ | ✅ | network 핵심 (mac/mtu/speed/state/master) | — |
| `/proc/cpuinfo` | kernel | ✅ | ✅ | ✅ | ✅ | ✅ | cpu 수집 | — |
| `/proc/meminfo` | kernel | ✅ | ✅ | ✅ | ✅ | ✅ | memory 수집 | — |
| `/etc/os-release` | filesystem | ✅ | ✅ | ✅ | ✅ | ✅ | system 수집 | — |
| `/etc/resolv.conf` | filesystem | ✅ | ✅ | ✅ | ✅ | ✅ | dns_servers | — |

- SLES 15 값은 공식 문서 기준 예측 (실증 미완)
- `ip`, `getent`, `/sys/class/net`, `/proc/*`, `/etc/os-release`는 모든 배포판에서 보장
- `nmcli`, `resolvectl`, `networkctl`은 배포판/네트워크 스택에 따라 상이하므로 gather 주 수집 소스로 사용하지 않음
- gather는 kernel sysfs + POSIX 명령 + /proc 의존 → 배포판 무관 동작 설계

##### Network raw fallback source 우선순위

| 데이터 | 1순위 | 2순위 | 3순위 | 미지원 시 |
|--------|-------|-------|-------|----------|
| IPv4 주소/프리픽스 | `ip -o -4 addr show` | — | — | 빈 addresses |
| IPv6 주소 | — | — | — | **미수집 (P3)** |
| default gateway | `ip route show default \| head -1` | — | — | 빈 default_gateways |
| primary 판정 | default route의 `dev` 필드 | — | — | 전체 is_primary=false |
| DNS | `/etc/resolv.conf` nameserver 행 | — | — | 빈 dns_servers |
| MAC | `/sys/class/net/*/address` | — | — | 인터페이스 제외 |
| MTU | `/sys/class/net/*/mtu` | — | — | null |
| speed | `/sys/class/net/*/speed` | — | — | null (-1 → null) |
| link state | `/sys/class/net/*/operstate` | — | — | unknown |
| slave/port 판정 | `/sys/class/net/*/master` sysfs | — | — | slave 미감지 → 수집 |
| bridge 판정 | `/sys/class/net/*/bridge/` dir | — | — | bridge 미감지 |
| bond 판정 | `/sys/class/net/*/bonding/` dir | — | — | bond 미감지 |

#### ESXi 수집 변수

| 변수 | 설명 |
|------|------|
| `_e_raw_facts` | vmware_host_facts 직접 반환값 |
| `_e_raw_config` | vmware_host_config_info 직접 반환값 |
| `_e_raw_ds` | vmware_datastore_info 직접 반환값 |
| `_e_facts_ok` | facts 수집 성공 여부 |
| `_e_config_ok` | config 수집 성공 여부 |
| `_e_ds_ok` | datastore 수집 성공 여부 |
| `_e_default_gw` | ESXi 기본 게이트웨이 |
| `_e_dns_servers` | ESXi DNS 서버 목록 |
| `_e_norm_interfaces` | 정규화된 인터페이스 |
| `_e_norm_datastores` | 정규화된 데이터스토어 |

#### Redfish 수집 변수

| 변수 | 설명 |
|------|------|
| `_rf_detected_vendor` | 1차 감지 벤더 ('unknown' 가능) |
| `_rf_vault_profile` | 실제 로딩된 vault 프로파일 |
| `_rf_raw_collect` | redfish_gather 모듈 전체 반환값 |
| `_rf_collect_ok` | 수집 성공 여부 |
| `_rf_vendor` | 최종 확정 벤더 (null 허용, "unknown" 금지) |
| `_rf_d_system` | 모듈 반환값에서 추출한 system raw |
| `_rf_d_bmc` | bmc raw |
| `_rf_d_procs` | processors raw |
| `_rf_d_memory` | memory raw |
| `_rf_d_storage` | storage raw |
| `_rf_d_network` | network raw |
| `_rf_norm_interfaces` | 정규화된 인터페이스 |
| `_rf_norm_gateways` | 집계된 default_gateways |
| `_rf_norm_controllers` | 정규화된 controllers |
| `_rf_norm_physical_disks` | controllers.drives 에서 추출 |
| `_rf_norm_logical_volumes` | Volumes 엔드포인트에서 수집한 RAID 논리 볼륨 |

#### 최종 변수

| 변수 | 설명 |
|------|------|
| `_output` | 최종 표준 JSON — **이름 변경 절대 금지** |

---

## Null / 빈값 정책 및 금지 패턴

| 케이스 | 값 |
|-------|-----|
| 단일 값 누락 | `null` |
| 배열 없음 | `[]` |
| 섹션 not_supported | `null` |
| 빈 문자열 | **사용 금지** |
| vendor 불명 | `null` (문자열 `"unknown"` 금지) |

**추가 금지 패턴:**
- `_f`, `_d` 등 너무 짧은 변수명 금지 — 채널+단계+의미를 포함해야 한다
- `_raw` prefix 없이 모듈 반환값을 직접 저장하지 않는다

---

## 실패 처리 패턴 (block/rescue/always)

```yaml
block:
  - include_tasks: common/tasks/normalize/init_fragments.yml
  - include_tasks: tasks/gather_*.yml  # 각자 fragment 생성
  - include_tasks: tasks/normalize_*.yml
  - include_tasks: common/tasks/normalize/build_sections.yml
  - include_tasks: common/tasks/normalize/build_status.yml
  - include_tasks: common/tasks/normalize/build_errors.yml
  - set_fact: _out_target_type/method/ip/vendor
  - include_tasks: common/tasks/normalize/build_output.yml
  - set_fact: _output="{{ _output | combine({'schema_version':'1'}) }}"

rescue:
  - set_fact:
      _out_target_type: "..."
      _out_collection_method: "..."
      _out_ip: "{{ _ip }}"
      _out_vendor: null
      _fail_sec_supported: [...]
      _fail_error_section: "gather_name"
      _fail_error_message: "{{ ansible_failed_result.msg | default('수집 예외') }}"
  - include_tasks: common/tasks/normalize/build_failed_output.yml
  - set_fact: _output="{{ _output | combine({'schema_version':'1'}) }}"

always:
  - name: OUTPUT
    debug: msg="{{ _output | to_json }}"
```

---

## 새 gather 추가 — site.yml 템플릿

```yaml
- name: "{gather}-gather"
  hosts: all
  gather_facts: no
  connection: local
  vars_files:
    - "{{ lookup('env','REPO_ROOT') }}/vault/{gather}.yml"
  vars:
    _ip: "{{ ansible_host | default(inventory_hostname) }}"
  tasks:
    - name: "{gather} | gather"
      block:
        - include_tasks: file="{{ REPO_ROOT }}/common/tasks/normalize/init_fragments.yml"
        - include_tasks: tasks/collect_standard.yml
        - include_tasks: tasks/normalize.yml
        - include_tasks: file="{{ REPO_ROOT }}/common/tasks/normalize/build_sections.yml"
        - include_tasks: file="{{ REPO_ROOT }}/common/tasks/normalize/build_status.yml"
        - include_tasks: file="{{ REPO_ROOT }}/common/tasks/normalize/build_errors.yml"
        - set_fact:
            _out_target_type: "{gather}"
            _out_collection_method: "{gather}_api"
            _out_ip: "{{ _ip }}"
            _out_vendor: null
        - include_tasks: file="{{ REPO_ROOT }}/common/tasks/normalize/build_output.yml"
        - set_fact: _output="{{ _output | combine({'schema_version':'1'}) }}"
      rescue:
        - set_fact:
            _out_target_type: "{gather}"
            _out_collection_method: "{gather}_api"
            _out_ip: "{{ _ip }}"
            _out_vendor: null
            _fail_sec_supported: ['hardware','cpu','memory']
            _fail_error_section: "{gather}_gather"
            _fail_error_message: "{{ ansible_failed_result.msg | default('수집 예외') }}"
        - include_tasks: file="{{ REPO_ROOT }}/common/tasks/normalize/build_failed_output.yml"
        - set_fact: _output="{{ _output | combine({'schema_version':'1'}) }}"
      always:
        - name: OUTPUT
          debug: msg="{{ _output | to_json }}"
```

---

## 참조 문서

| 주제 | 문서 |
|------|------|
| 스키마 / sections / status 규칙 | `docs/contract/02-output-envelope.md` |
| 아키텍처 / 정규화 흐름 | `docs/develop/01-gather-structure.md`, `docs/develop/02-normalize-flow.md` |
| Adapter 시스템 | `docs/develop/03-adapter-system.md` |
| Pre-check 진단 | `docs/contract/04-failure-and-diagnosis.md` |
| 필드 매핑 | `docs/develop/05-field-mapping.md` |
| Field Dictionary | `schema/field_dictionary.yml` |
