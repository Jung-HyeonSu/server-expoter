# 2026-05-11 — HPE iLO 6 Gen11 (FW 1.73) Adapter 선택 실패

## 환경

| 항목 | 값 |
|---|---|
| Jenkins | 10.100.64.152 (`hshwang-gather` build #133) |
| Branch | main (HEAD = `1387b505` fix: hpe_ilo7 Gen12 2-part firmware version 매치 보강) |
| 대상 BMC | 10.50.11.231 |
| 자격증명 | admin / __REDACTED__ |
| Product | HPE ProLiant DL380 Gen11 |
| Manager.Model | iLO 6 |
| Manager.FirmwareVersion | `iLO 6 v1.73` (literal string) |
| Manager.ManagerType | BMC |
| BIOS | U54 v2.16 (03/01/2024) |
| Redfish | 1.20.0 |
| System.Manufacturer | HPE |

## 증상

```json
{
  "target_type": "redfish",
  "ip": "10.50.11.231",
  "vendor": "hpe",
  "status": "failed",
  "sections": { "system": "failed", "...": "failed (all 10)" },
  "diagnosis": {
    "reachable": true,
    "port_open": true,
    "protocol_supported": true,
    "auth_success": null,
    "failure_stage": null,
    "details": {
      "channel": "redfish",
      "adapter_candidate": null,
      "redfish_version": "1.20.0",
      "product": "ProLiant DL380 Gen11"
    }
  },
  "errors": [
    {
      "section": "redfish_gather",
      "message": "Task failed: Conditional result (False) was derived from value of type 'NoneType' at '<unknown>'. Conditionals must have a boolean result."
    }
  ]
}
```

- 4단계 precheck 모두 PASS (reach / port / protocol)
- Vendor detection PASS (`vendor: "hpe"`)
- **`adapter_candidate: null`** — adapter_loader가 어느 hpe adapter도 선택 못 함
- `auth_success: null` — auth 단계 진입 전 abort
- Ansible Jinja2 conditional이 NoneType에서 False 도출 → strict mode FAIL

## 근본 원인 가설

**facts.firmware = `"iLO 6 v1.73"` 가 모든 hpe_* adapter의 `firmware_patterns` regex와 불일치**

`module_utils/adapter_common.py` L258-267 disqualify 로직:
```python
if firmware_patterns and facts.get("firmware"):
    if not pattern_match_any(firmware_patterns, facts["firmware"]):
        return -9999  # disqualify
```

| adapter | priority | firmware_patterns | "iLO 6 v1.73" 매치? |
|---|---|---|---|
| `hpe_ilo7` | 120 | `iLO.*7`, `^\d+\.\d+\.\d+`, `^1\.1[0-9]` | NO (모두 불일치) |
| **`hpe_ilo6`** | **100** | `iLO.*6`, `^1\.[5-9]` | **`iLO.*6` 매치 → OK** ※ |
| `hpe_ilo5` | (TBD) | (TBD) | NO |
| `hpe_ilo4` | (TBD) | (TBD) | NO |
| `hpe_ilo` (generic) | (낮음) | (TBD) | (TBD) |

※ **그러나** envelope이 `adapter_candidate: null` — 어떤 adapter도 선택되지 못함. 가설 검증 추가 필요.

## 의심 단서

1. **commit `1387b505`** (`fix: hpe_ilo7 Gen12 2-part firmware version 매치 보강`) 가 hpe_ilo7에 `^1\.1[0-9]` 추가. 만약 facts.firmware가 `"1.73"` 같은 short form일 경우:
   - `^1\.1[0-9]` 는 "1.73" 매치 X (1.10-1.19만)
   - `^1\.[5-9]` 는 "1.73" 매치 O — hpe_ilo6 정상 선택
   - 그러면 fail 안 함
2. **그러나** Manager.FirmwareVersion 원본은 `"iLO 6 v1.73"` (string, prefix "iLO 6 v"). facts.firmware 추출 path가 어떻게 정규화하는지 확인 필요.
3. NoneType conditional의 `<unknown>` 위치 — `strategy: free` + `no_log: true` (L70) 로 정확한 task 식별 불가. `-vvv` 빌드 필요.

## 후속 조사 항목

1. `detect_vendor.yml` 의 `_rf_probe_facts.firmware` 추출 path 확인 — Manager.FirmwareVersion raw vs parsed
2. `redfish-gather/site.yml` L77 (load_vault), L82 (collect_standard) 의 conditional traversal — `_selected_adapter` None 가드 검토
3. -vvv 빌드로 정확한 NoneType conditional 위치 식별
4. `git log --since='2026-04-25' -- adapters/redfish/hpe_*.yml module_utils/adapter_common.py lookup_plugins/adapter_loader.py` 회귀 영역 검토

## 캡처된 fixture

- `tests/fixtures/redfish/hpe_ilo6_v1_73/01_service_root.json` — `/redfish/v1/`
- `tests/fixtures/redfish/hpe_ilo6_v1_73/02_manager_1.json` — `/redfish/v1/Managers/1`
- `tests/fixtures/redfish/hpe_ilo6_v1_73/03_system_1.json` — `/redfish/v1/Systems/1`

## 다른 채널 결과 (회귀 비교용)

### OS 채널 (#132) — 7/7 SUCCESS
- 10.100.64.161 (RHEL 8.10) — raw fallback 자동 (Python 3.6.8) ✓
- 10.100.64.163/165/167/169/96 — python_ok ✓
- 10.100.64.135 (Win 2022) — 7/10 sections ✓

### Redfish 채널 (#133) — 7/10 SUCCESS
- Dell idrac10 × 5대 (10.100.15.27/28/31/33/34) ✓
- Lenovo XCC3 × 1대 (10.50.11.232) ✓
- Cisco UCS X-series × 1대 (10.100.15.2) ✓
- HPE iLO 6 × 1대 (10.50.11.231) — **본 issue**
- Cisco 10.100.15.1 — auth_failed (vault 자격 불일치 의심)
- Cisco 10.100.15.3 — reachable failed (host down)

### ESXi 채널 (#134) — 3/3 SUCCESS
- 10.100.64.1/2/3 — esxi_generic adapter ✓ (vendor=cisco DMI 정상 식별)

## 영향 평가

- **rule 95 (production-critical-review)**: HPE iLO 6 회귀 검증 누락 발견 — 다음 cycle 명시 회귀 대상
- **rule 96 (external-contract-integrity)**: Manager.FirmwareVersion 형식이 vendor 펌웨어별로 다름 (`"iLO 6 v1.73"` vs `"1.73"` vs `"1.12.00"`) — facts.firmware 추출 정규화 검토 필요
- **rule 50 R2**: lab 보유 vendor에서도 실 환경 회귀 누락 가능 — `pre_commit_hpe_ilo6_regression_check.py` 권장

---

## [RESOLVED] 근본 원인 + Fix (2026-05-11 cycle)

### 진짜 원인 (가설 정정)

가설 (facts.firmware regex 매치) 은 **부분적 진실 — 진짜 원인 아님**.

**진짜 원인**: `redfish-gather/tasks/vendors/hpe/collect_oem.yml` L82 + `normalize_oem.yml` L39/L45 의 `when` 절:
```yaml
when:
  - "(_rf_detected_model | default('')) | regex_search('(?i)Superdome|Flex|Compute Scale-up|CSUS')"
```

`regex_search`가 미매치 시 **None** 반환 → Ansible strict mode 의 conditional fail (`Conditional result (False) was derived from value of type 'NoneType'`). DL380 Gen11 model은 Superdome 패턴 미매치 → None → 전체 block fail → rescue → status=failed.

### 식별 방법

`redfish-gather/site.yml` rescue 의 `_fail_error_message` 에 `ansible_failed_task.name` prefix 추가 (commit `7906fe85`) → 빌드 #137 envelope errors[].message에 정확한 task 이름 노출 → 1턴에 원인 식별.

### Fix commits

| commit | 변경 | 효과 |
|---|---|---|
| `1065bb79` | detect_vendor.yml — `\| default({}, true)` None 가드 강화 | defensive (회귀 0) |
| `7906fe85` | site.yml rescue — task name prefix in error msg | debugging visibility |
| `5d6cf72c` | collect_oem.yml — regex_search `is not none` 명시 | **main fix** |
| `a972acc4` | normalize_oem.yml — 동일 패턴 2곳 | **main fix** |

### Round 2 검증 (build #139)

| IP | vendor | adapter | sections | status |
|---|---|---|---|---|
| 10.50.11.232 | lenovo | redfish_lenovo_xcc3 | 8/10 | success |
| **10.50.11.231** | **hpe** | **redfish_hpe_ilo7** | **8/10** | **success** ✓ |
| 10.100.15.27 | dell | redfish_dell_idrac10 | 8/10 | success |
| 10.100.15.2 | cisco | redfish_cisco_ucs_xseries | 8/10 | success |

### Round 3 검증 (T-01 fix 후, cycle 2026-05-11)

#### build #140 (HPE 단일 host)

| IP | vendor | adapter | sections | status | 비고 |
|---|---|---|---|---|---|
| **10.50.11.231** | **hpe** | **redfish_hpe_ilo6** | **8/10** | **success** | **T-01 fix 검증 — Gen11/iLO 6 정확 매칭 ✓** (#139 의 hpe_ilo7 오선택 해소) |

#### build #141 (전 vendor 회귀 — HPE + Lenovo + Dell × 2 + Cisco)

| IP | vendor | adapter | sections | status | 비고 |
|---|---|---|---|---|---|
| 10.50.11.231 | hpe | redfish_hpe_ilo6 | 8/10 | success | T-01 fix 확인 |
| 10.50.11.232 | lenovo | redfish_lenovo_xcc3 | 8/10 | success | 회귀 0 |
| 10.100.15.27 | dell | redfish_dell_idrac10 | 8/10 | success | 회귀 0 |
| 10.100.15.28 | dell | redfish_dell_idrac10 | 8/10 | success | 회귀 0 |
| 10.100.15.2 | cisco | redfish_cisco_ucs_xseries | 8/10 | success | 회귀 0 |

- 5/5 host SUCCESS — Dell / Lenovo / Cisco 영향 0 확인 (사용자 명시 "다른 세대장비 다른 장비 문제 발생되지않도록")
- adapter selection 정확도: HPE Gen11 → hpe_ilo7 (Gen12 adapter) → **hpe_ilo6 (Gen11 정확 adapter)** 로 정정. 타 vendor 변화 없음.
- sections collected: hardware / bmc / cpu / memory / storage / network / firmware / power (8/10)
- sections not_supported: system / users (이전 build #139 와 동일 — adapter capabilities 정합)

### 잔여 후속 작업 (다음 cycle)

1. ~~**adapter 오선택 (LOW)**: DL380 Gen11 (iLO 6) 가 `redfish_hpe_ilo7` (Gen12 adapter) 로 매칭됨~~ — **[RESOLVED] cycle 2026-05-11 T-01 fix + Jenkins build #140 실 검증 통과**: `redfish_gather.py` `_extract_probe_facts(root, vendor)` 신규 함수 + `detect_vendor()` 가 ServiceRoot 응답 함께 반환 + `main()` 이 `probe_facts` top-level field 노출 (Additive — envelope shape 신 키 추가는 probe 응답 한정). `detect_vendor.yml` 이 `data.bmc.firmware_version` / `data.system.model` 가 비었을 때 `probe_facts.model_hint` (= ServiceRoot.Product) / `probe_facts.firmware_hint` (= Oem.Hpe.Manager[0].ManagerFirmwareVersion) / `probe_facts.manager_type` 로 fallback. 회귀: pytest 608/608 + 9건 adapter 선택 시뮬레이션 + 9건 _extract_probe_facts 단위 — DL380 Gen11 → hpe_ilo6 정확 선택 확인, Gen12 → hpe_ilo7 유지, 타 vendor (Dell/Lenovo/Cisco/Supermicro/Huawei/Inspur/Fujitsu/Quanta) 영향 0.
2. **Cisco 10.100.15.1 운영 점검**: TCP/443 OK + HTTP 503 → Redfish 서비스 down/busy (운영 영역 — AI 작업 외)
3. **Cisco 10.100.15.3 운영 점검**: ICMP/TCP timeout → host down or firewall (운영 영역 — AI 작업 외)
4. ~~**rule 95 hook**: `is not none` 패턴 lint~~ — **[RESOLVED] cycle 2026-05-11 T-02 fix**: `scripts/ai/hooks/pre_commit_regex_search_conditional_check.py` 신규 hook (advisory) + rule 95 R1 #12 추가 + `install-git-hooks.sh` 등록 + `surface-counts.yaml` hooks 29 갱신. POST-regex_* 가드 위치 정밀화 (`| default('')` 가 regex_search **앞** 에 있으면 INPUT 만 가드 — 5d6cf72c 사고 사례 정확 차단). self-test 10/10 + 전체 codebase 0 false positive. 1주 안정 후 BLOCKING 격상 검토.

