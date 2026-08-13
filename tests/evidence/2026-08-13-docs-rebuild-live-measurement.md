# 실장비 실측 — 문서 재작성 근거 (2026-08-13)

문서를 코드와 실장비 기준으로 다시 쓰기 위해 3채널을 실제로 돌렸다. 기존 문서는 근거로
쓰지 않았다.

## 실행 방법

WSL Ubuntu, `ansible-core 2.20.7`, `se_location=git`.
**Redfish 는 `-e _rf_account_service_dryrun=true` 로 계정 쓰기를 강제 차단**했다.
문서 작업이 BMC 계정을 건드리면 안 되기 때문이다.

```bash
INVENTORY_JSON='[{"bmc_ip":"<ip>"}]' \
  ansible-playbook -i <inventory.sh> redfish-gather/site.yml \
    --vault-password-file <tmp> -e se_location=git -e _rf_account_service_dryrun=true
```

로컬 실행 시 걸린 것 세 가지 (Jenkins agent 에서는 해당 없음):
`/mnt/c` 가 world-writable 이라 `ansible.cfg` 자동 탐색이 무시된다 → `ANSIBLE_CONFIG` 명시.
`.vault_pass` 에 exec bit 이 붙어 스크립트로 오인된다 → mktemp 사본 + `chmod 600`.
`inventory.sh` 가 CRLF 라 shebang 이 깨진다 → `python3 inventory.sh` 래퍼.

## 결과

| 대상 | 채널 | status | vendor | adapter | 성공 섹션 | serial |
|---|---|---|---|---|---|---|
| 10.100.15.34 | redfish | success | dell | `redfish_dell_idrac10` | 9 | `GSBPK54` |
| 10.100.64.96 | os | success | dell | `os_linux_ubuntu` | 6 | `GSBPK54` |
| 10.50.11.231 | redfish | success | **hp** | `redfish_hpe_ilo6` | 9 | `SGH504HNZK` |
| 10.50.11.232 | redfish | success | lenovo | `redfish_lenovo_xcc3` | 9 | `J30AF7LC` |
| 10.100.15.2 | redfish | success | cisco | `redfish_cisco_ucs_xseries` | 9 | `FCH2116V1V0` |
| 10.100.15.27 | redfish | failed | dell | `redfish_dell_idrac10` | 0 | — |
| 10.100.15.1 | redfish | failed | — | — | 0 | — |
| 10.100.64.1 | esxi | success | cisco | `esxi_7x` | 6 | `FCH2117V12M` |
| 10.100.64.91 | esxi | success | dell | **`esxi_generic`** | 6 | `64CXJ54` |
| 10.100.64.120 | os | success | vmware | `os_windows_2022` | 7 | `VMware-42 04 …` |

## 확인된 계약

**BMC 와 OS 의 시리얼이 같다.** `10.100.15.34`(BMC)와 `10.100.64.96`(같은 기계의 Ubuntu)이
둘 다 `GSBPK54` 를 보고했다. 다만 두 값은 **다른 원본에서 온다** —
Redfish 는 `ComputerSystem.SerialNumber`, Linux 는 DMI `product_serial` 이고,
Linux 는 `data.hardware` 섹션이 없어 `data.system.serial_number` 분기를 탄다
(`common/tasks/normalize/build_correlation.yml:18-39`). 값이 같은 것은 두 경로가 같은
SMBIOS 를 읽기 때문이지, 코드가 일치를 보장해서가 아니다.

**Redfish 성공 경로는 9섹션이다.** `hardware, bmc, cpu, memory, storage, network,
firmware, power, thermal`. `system` 과 `users` 는 `not_supported` 로 나온다.
그런데 `data.system` 에는 8개 키가 들어 있다 — 내용을 채우면서 지원 선언은 하지 않는다
(`redfish-gather/tasks/normalize_standard.yml:470-478`, `:580-581`).

**vendor 표시 매핑이 동작한다.** HPE 장비의 envelope `vendor` 가 `hp` 로 나왔다
(`common/vars/vendor_aliases.yml` 의 `vendor_output_display`).

**OS/Linux 는 6섹션, OS/Windows 는 7섹션이다.** Windows 만 `hardware` 를 더 올린다
(`os-gather/tasks/windows/gather_hardware.yml:102`). 그런데 `schema/sections.yml` 은
`hardware` 를 `[esxi, redfish]` 전용으로 선언한다 — 스키마와 코드가 어긋나 있고,
실장비 envelope 가 그걸 그대로 보여준다.

**ESXi 9.0.0 은 버전 어댑터가 없어 `esxi_generic` 으로 떨어진다.** 7.0.3 은 `esxi_7x`,
9.0.0 은 `esxi_generic` 이 선택됐다. 다만 두 어댑터의 `sections_supported` 가 같아서
**수집 섹션은 6개로 동일**했다. 즉 데이터 손실은 없고 `meta.adapter_id` 만 사실과 다르다.

**시리얼 일치가 두 번째 쌍에서도 확인된다.** ESXi `10.100.64.91` 이 `64CXJ54` 를 보고했고,
같은 기계의 BMC `10.100.15.27` 에서 뜬 저장 예시(`schema/output_examples/redfish_dell_idrac9.jsonc`)도
`64CXJ54` 다.

## 발견 — adapter 오선택이 실장비에서 재현된다

두 장비가 실제 세대와 다른 adapter 를 골랐다.

| 장비 | 실제 | 고른 adapter |
|---|---|---|
| 10.100.15.34 / .27 | PowerEdge R760 = 16G = iDRAC9 (FW 7.10.70.00) | `redfish_dell_idrac10` |
| 10.100.15.2 | TA-UNODE-G1 (CIMC) | `redfish_cisco_ucs_xseries` |

점수를 직접 계산해 원인을 좁혔다 (`module_utils/adapter_common.adapter_score`).

| facts | 1위 |
|---|---|
| `{cisco, model=TA-UNODE-G1}` | `redfish_cisco_cimc` (100545) |
| `{cisco, model=''}` | `redfish_cisco_ucs_xseries` (110320) |
| `{dell, model=PowerEdge R760, fw=7.10.70.00}` | `redfish_dell_idrac9` (100345) |
| `{dell, model=Integrated Dell Remote Access Controller}` | `redfish_dell_idrac9` (100320) |

**model 이 채워지면 올바른 adapter 가 이긴다.** 실제 실행이 상위 priority adapter 를
골랐다는 건 선택 시점에 `_rf_probe_facts` 의 `model` / `firmware` 가 비어 있었다는 뜻이다.
`detect_vendor.yml:62-80` 이 `probe_facts.model_hint` / `firmware_hint` 로 채우게 돼 있으니,
그 hint 가 선택 시점까지 오지 않는 셈이다.

빈 값이 실격 사유가 아닌 것 자체는 설계 의도다 (`adapter_match_score` — 사실을 모르면
후보에서 빼지 않는다). 문제는 hint 전달이다. 이미 `NEXT_ACTIONS` 의 PWC-4 로 열려 있는
과제이며, 이번 작업은 문서 범위라 **보고만 한다.**

수집 결과에 미치는 영향은 제한적이다 — 두 경우 모두 9섹션을 정상 수집했다. 다만
`meta.adapter_id` 가 사실과 다르고, 계정 쓰기 Family 판정이 adapter hint 를 참고하므로
쓰기 경로에서는 영향이 있을 수 있다 (그래서 이번 실행은 dryrun 을 강제했다).

## 도달했지만 수집이 안 되는 장비

`10.100.15.1` — TCP 443 은 열려 있는데 `failure_stage=protocol`,
`PROTOCOL_CHECK_FAILED`. 즉 장비는 있고 443 도 응답하지만 Redfish ServiceRoot 를
제대로 주지 않는다. `LAB_INVENTORY` 가 cycle-016 에 "lab 부재 / non-Redfish" 라 적었던
것 중 **"non-Redfish" 는 맞고 "부재" 는 틀렸다.**

`10.100.15.27` — 표준 계정 인증 거부(401). 2026-08-12 비밀번호 회전이 이 BMC 까지
수렴하지 않았다. dryrun 강제 덕분에 계정 쓰기는 0건이었고, 조정 경로는
`method=patch_existing` 까지만 진입했다.

## 도달성 (인증 없이 TCP 만, 3초)

23/25. 저장소 기록을 뒤집은 것 — `10.100.15.1`, `10.100.15.32`, `10.100.64.120` 은
"사내 부재" 로 기록돼 있었지만 모두 열려 있다. 닿지 않은 둘(`10.100.15.3`,
`10.100.64.94`)은 5개 포트 전부 무응답이고 RST 도 없다. 방화벽 drop 인지 전원 off 인지는
이 관측만으로 구분되지 않는다.

## 하지 않은 것

`schema/baseline_v1/*.json` 은 건드리지 않았다. 회귀 기준선이라 갱신하면 테스트 판정이
바뀐다 (rule 13 R4 / rule 21 R1). 계정 쓰기도 하지 않았다.
