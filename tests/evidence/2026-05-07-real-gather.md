# 2026-05-07 실 장비 개더링 — JSON 출력 예시 갱신

## 1. 목적

사용자 명시 (2026-05-07): 실 장비 개더링 결과로 `schema/output_examples/` 신설 + 한글 주석본 갱신. `schema/baseline_v1/*_annotated.jsonc` 8개 삭제 (cycle 2026-05-06 b65e162e 산출물 — baseline_v1 가 회귀 기준선이지 출력 예시가 아니므로 위치 부적합).

## 2. 실행 환경

| 항목 | 값 |
|---|---|
| 실행 일시 | 2026-05-07 KST (08:46~08:54 UTC) |
| Jenkins 에이전트 | 10.100.64.155 (cloviradmin) — Ubuntu 6.8 / Java 21 / Ansible 2.20.3 / Python 3.12 venv `/opt/ansible-env/` |
| 코드 배포 | rsync 로 로컬 main 코드를 `~/se-realtest-2026-05-07/` 로 push |
| 자격증명 | vault/<loc>/os/{linux,windows}.yml + vault/<loc>/esxi.yml + vault/<loc>/redfish/<vendor>.yml (5 vendor 통일 — primary `infraops/__REDACTED__Infra` + recovery list, cycle 2026-04-29~2026-05-06) |
| vault 비밀번호 | `__REDACTED__` (사용자 통일) |

## 3. 대상 장비 (사용자 제공)

### OS 채널 (7대)
| IP | OS | hosting_type | 결과 |
|---|---|---|---|
| 10.100.64.161 | RHEL 8.10 | virtual | success / sections 6/10 / **raw fallback (Python 3.6)** |
| 10.100.64.163 | RHEL 9.20 | virtual | success / sections 6/10 |
| 10.100.64.165 | RHEL 9.60 | virtual | success / sections 6/10 |
| 10.100.64.167 | Ubuntu 24.04 | virtual | success / sections 6/10 |
| 10.100.64.169 | Rocky 9.60 | virtual | success / sections 6/10 |
| 10.100.64.135 | Windows Server 2022 | virtual | success / sections 7/10 |
| 10.100.64.96  | RHEL 베어메탈 (Dell R760) | baremetal | success / sections 6/10 / **vendor=dell DMI 감지** |

### Redfish 채널 (10대 시도, 5대 성공)
| IP | vendor | adapter | 결과 |
|---|---|---|---|
| 10.50.11.231 | hpe | redfish_hpe_ilo7 | success 8/10 (PSU1 Critical) |
| 10.50.11.232 | lenovo | redfish_lenovo_xcc3 | success 8/10 (PSU1 Critical) |
| 10.100.15.1 | (probe 실패) | redfish_generic | **failed** — root 503 |
| 10.100.15.2 | cisco | redfish_cisco_ucs_xseries | success 8/10 (270초) |
| 10.100.15.3 | (대기) | — | 사용 안 함 (15.2 로 대표) |
| 10.100.15.27 | dell | redfish_dell_idrac10 | success 8/10 (62초) |
| 10.100.15.28 | dell | redfish_dell_idrac10 | success — 사용 안 함 (15.27 로 대표) |
| 10.100.15.31 | dell | redfish_dell_idrac10 | success — 사용 안 함 |
| 10.100.15.33 | dell | redfish_dell_idrac10 | success — 베어메탈 OS (10.100.64.96) 와 연계 |
| 10.100.15.34 | dell | redfish_dell_idrac10 | success — 사용 안 함 |

### ESXi 채널 (3대)
| IP | vendor (hosting hardware) | ESXi | 결과 |
|---|---|---|---|
| 10.100.64.1 | cisco | 7.0.3 | success / sections 6/10 |
| 10.100.64.2 | cisco | 7.0.3 | success — 사용 안 함 (64.1 로 대표) |
| 10.100.64.3 | cisco | 7.0.3 | success — 사용 안 함 |

## 4. 실행 절차

```bash
# Step 1: 에이전트 SSH 확인
sshpass -p '__REDACTED__' ssh cloviradmin@10.100.64.155 'hostname; ansible-playbook --version'

# Step 2: 로컬 코드 rsync
cd C:/github/server-exporter
rsync -az --exclude='.git/' --exclude='*.pyc' --exclude='docs/ai/incoming-review/' \
  ./ cloviradmin@10.100.64.155:~/se-realtest-2026-05-07/

# Step 3: vault 비밀번호 파일 (1회)
echo '__REDACTED__' > ~/.vault_pass_se_test
chmod 600 ~/.vault_pass_se_test

# Step 4: 채널별 ansible-playbook (병렬)
cd ~/se-realtest-2026-05-07
export REPO_ROOT=$(pwd)
export ANSIBLE_CONFIG=$(pwd)/ansible.cfg

INVENTORY_JSON='[{"service_ip":"10.100.64.161"}]' \
  ansible-playbook -i os-gather/inventory.sh os-gather/site.yml \
  -e loc=ich -e target_type=os \
  --vault-password-file=~/.vault_pass_se_test \
  > _outputs/os_rhel810.json

# Redfish:
INVENTORY_JSON='[{"bmc_ip":"10.100.15.27"}]' \
  ansible-playbook -i redfish-gather/inventory.sh redfish-gather/site.yml \
  -e loc=ich -e target_type=redfish \
  --vault-password-file=~/.vault_pass_se_test \
  > _outputs/redfish_dell_15_27.json

# ESXi:
INVENTORY_JSON='[{"service_ip":"10.100.64.1"}]' \
  ansible-playbook -i esxi-gather/inventory.sh esxi-gather/site.yml \
  -e loc=ich -e target_type=esxi \
  --vault-password-file=~/.vault_pass_se_test \
  > _outputs/esxi_64_1.json

# Step 5: 결과 회수
rsync -az cloviradmin@10.100.64.155:~/se-realtest-2026-05-07/_outputs/ ./_temp_outputs/
```

## 5. 발견 사항 / 특이점

### 5-A. Cisco 10.100.15.1 BMC 503

```json
"diagnosis.details": {
  "root_status_code": 503,
  "requires_auth_at_root": false,
  "header_negotiation_issue": false
}
```

→ ServiceRoot (`/redfish/v1/`) 가 503 응답. Cisco CIMC 자체 재기동 필요 (사용자 운영 영역). 호환성 fix 대상 아님 (rule 96 R1-A — 외부 시스템 일시 장애).

본 케이스를 `redfish_failed.jsonc` 예시로 보존 — 호출자가 status=failed 처리 reference 로 사용.

### 5-B. Cisco 10.100.15.2 duration 270초

| vendor | duration_ms |
|---|---|
| Dell iDRAC10 | 62,802 ms (1분) |
| Lenovo XCC3 | 69,958 ms (1.2분) |
| HPE iLO 6 | 129,615 ms (2.2분) |
| Cisco CIMC 4.1(2g) | 270,089 ms (4.5분) |

→ Cisco BMC 가 가장 느림. 향후 timeout / parallelism 영향 — 본 cycle 에서는 정보로만 기록.

### 5-C. PSU 장애 사례

- HPE 10.50.11.231: power_supplies[0].health = "Critical", state = "UnavailableOffline" → power.summary.health_rollup = "Critical"
- Lenovo 10.50.11.232: power_supplies[0].health = "Critical" → 동일

→ status 는 success (수집 성공). 호출자가 `data.power.summary.health_rollup` 으로 별도 분기 (rule 13 R8 시나리오 D).

### 5-D. Linux raw fallback (RHEL 8.10)

```json
"diagnosis.details.gather_mode": "python_incompatible",
"diagnosis.details.python_version": "3.6.8"
```

→ Python 3.9 미만 → setup 모듈 미동작 → raw 모듈로 모든 정보 수집. JSON envelope schema 호환성 100% 유지 확인.

## 6. 산출물

### 6-A. 신설 (10 jsonc + 1 README)

```
schema/output_examples/
├── README.md
├── os_linux_rhel810_raw_fallback.jsonc
├── os_linux_ubuntu2404.jsonc
├── os_linux_baremetal_dell.jsonc
├── os_windows2022.jsonc
├── esxi_vmware.jsonc
├── redfish_dell_idrac9.jsonc
├── redfish_hpe_ilo6.jsonc
├── redfish_lenovo_xcc.jsonc
├── redfish_cisco_cimc.jsonc
└── redfish_failed.jsonc
```

### 6-B. 삭제 (사용자 명시)

```
schema/baseline_v1/cisco_baseline_annotated.jsonc           — DEL
schema/baseline_v1/dell_baseline_annotated.jsonc            — DEL
schema/baseline_v1/esxi_baseline_annotated.jsonc            — DEL
schema/baseline_v1/hpe_baseline_annotated.jsonc             — DEL
schema/baseline_v1/lenovo_baseline_annotated.jsonc          — DEL
schema/baseline_v1/rhel810_raw_fallback_baseline_annotated.jsonc — DEL
schema/baseline_v1/ubuntu_baseline_annotated.jsonc          — DEL
schema/baseline_v1/windows_baseline_annotated.jsonc         — DEL
```

→ baseline_v1 디렉터리는 회귀 기준선 (8개 *.json) 만 보존. 한글 주석본은 `schema/output_examples/` 로 분리.

### 6-C. 보존 (변경 안 함)

```
schema/baseline_v1/*_baseline.json                          — 8 회귀 기준선 그대로
schema/examples/{os_partial,redfish_failed,redfish_not_supported,redfish_success}.json — 4 시나리오 예시 그대로
schema/sections.yml                                          — 섹션 정의 그대로
schema/field_dictionary.yml                                  — 65 entries 그대로
```

## 7. 검증 결과

| 검증 | 결과 |
|---|---|
| JSONC valid (10 파일) | [PASS] 모두 13 필드 (target_type ... schema_version) |
| `verify_harness_consistency.py` | [PASS] rules 28 / skills 51 / agents 60 / policies 10 |
| `verify_vendor_boundary.py` | [PASS] vendor 하드코딩 0건 |
| `check_project_map_drift.py --update` | [INFO] schema fingerprint 갱신 (521534b09b45 → a15de0936932 — output_examples/ 추가 + baseline_v1 _annotated.jsonc 삭제 반영) |
| `pytest tests/` | [PASS] 335/335 |

## 8. 호출자 영향

- `schema/baseline_v1/*_baseline.json` 8개 → 변경 없음 (Jenkins Stage 4 회귀 입력 그대로)
- `schema/examples/*.json` 4개 → 변경 없음 (시나리오 reference 그대로)
- envelope 13 필드 / sections 10 / field_dictionary 65 → 변경 없음
- 호출자 시스템 파싱 변경 0 (rule 13 R5 / rule 96 R1-B Additive only 준수)

## 9. 사용자 명시 결정 기록

| 결정 항목 | 사용자 입장 | 진행 |
|---|---|---|
| 디렉터리 | 신규 (baseline_v1 != 출력 예시) | `schema/output_examples/` 신설 |
| baseline_v1 annotated 8개 | 삭제 | 8개 모두 삭제 |
| 자격증명 | 평문 노출 OK / vault 사용 OK | vault 그대로 사용, 평문 그대로 commit |
| 실행 위치 | 권장 (Jenkins 에이전트 SSH) | 10.100.64.155 SSH 직접 실행 |

## 10. 관련

- 정본: rule 13 (`13-output-schema-fields`), rule 22 (`22-fragment-philosophy`), rule 24 R5 (commit + push), rule 70 R1 (evidence 갱신)
- 카탈로그: `docs/ai/CURRENT_STATE.md`, `docs/ai/catalogs/TEST_HISTORY.md`, `docs/reference/decision-log.md`
