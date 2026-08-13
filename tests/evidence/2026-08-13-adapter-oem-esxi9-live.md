# 실장비 검증 — adapter 재선택 / OEM task 제거 / ESXi 9.x (2026-08-13)

제품 코드 결함 3건을 고치고 lab 24대를 **수정 전·후 2회** 돌려 대조했다.
계정 쓰기는 차단하지 않았다 (사용자 결정) — dryrun override 없이 실행했다.

WSL Ubuntu, `ansible-core 2.20.7`, `se_location=git`. 로컬 실행 제약 3가지는
`2026-08-13-docs-rebuild-live-measurement.md` 와 같다 (`/mnt/c` world-writable →
`ANSIBLE_CONFIG` 명시, `.vault_pass` exec bit → mktemp 사본, `inventory.sh` CRLF →
`python3` 래퍼).

## 한 줄 결론

**바뀐 것은 `meta.adapter_id` 10건뿐이다.** status·`data` 키 수·섹션 구성·시리얼은
24대 전부 불변이었다.

## 대조표

`adapter` 열의 `A → **B**` 는 수정으로 바뀐 것이다.

| 채널 | 대상 | status | adapter | 성공 섹션 | serial / 실패 |
|---|---|---|---|---|---|
| esxi | 10.100.64.1 | success | esxi_7x | 6 | FCH2117V12M |
| esxi | 10.100.64.2 | success | esxi_7x | 6 | FCH2116V1V0 |
| esxi | 10.100.64.3 | success | esxi_7x | 6 | FCH2116V1UZ |
| esxi | 10.100.64.91 | success | esxi_generic → **esxi_9x** | 6 | 64CXJ54 |
| esxi | 10.100.64.92 | success | esxi_generic → **esxi_9x** | 6 | 29N1K54 |
| esxi | 10.100.64.93 | success | esxi_generic → **esxi_9x** | 6 | 4BP2K54 |
| esxi | 10.100.64.94 | failed | — | 0 | reachable / TCP_CONNECT_FAILED |
| esxi | 10.100.64.95 | failed | — | 0 | protocol / PROTOCOL_CHECK_FAILED |
| os | 10.100.64.96 | success | os_linux_ubuntu | 6 | GSBPK54 |
| os | 10.100.64.120 | success | os_windows_2022 | 7 | VMware-42 04 a2 40 … |
| os | 10.100.64.156 | success | os_linux_ubuntu | 6 | VMware-42 04 ad 78 … |
| os | 10.100.64.161 | success | os_linux_rhel | 6 | VMware-42 04 c1 6d … |
| os | 10.100.64.165 | success | os_linux_rhel | 6 | VMware-42 04 78 0c … |
| redfish | 10.100.15.1 | failed | — | 0 | protocol / PROTOCOL_CHECK_FAILED |
| redfish | 10.100.15.2 | success | redfish_cisco_ucs_xseries → **redfish_cisco_cimc** | 9 | FCH2116V1V0 |
| redfish | 10.100.15.3 | failed | — | 0 | reachable / TCP_CONNECT_FAILED |
| redfish | 10.100.15.27 | success | redfish_dell_idrac10 → **redfish_dell_idrac9** | 9 | 64CXJ54 |
| redfish | 10.100.15.28 | success | redfish_dell_idrac10 → **redfish_dell_idrac9** | 9 | 29N1K54 |
| redfish | 10.100.15.31 | success | redfish_dell_idrac10 → **redfish_dell_idrac9** | 9 | 4BP2K54 |
| redfish | 10.100.15.32 | failed | redfish_generic | 0 | auth / AUTH_PROBE_FAILED |
| redfish | 10.100.15.33 | success | redfish_dell_idrac10 → **redfish_dell_idrac9** | 9 | C3BXJ54 |
| redfish | 10.100.15.34 | success | redfish_dell_idrac10 → **redfish_dell_idrac9** | 9 | GSBPK54 |
| redfish | 10.50.11.231 | success | redfish_hpe_ilo6 | 9 | SGH504HNZK |
| redfish | 10.50.11.232 | success | redfish_lenovo_xcc3 → **redfish_lenovo_xcc** | 9 | J30AF7LC |

`data` 키 개수도 전·후가 같다 — Dell 137, HPE 136, Lenovo 132, Cisco 127,
ESXi 77, Windows 91, Linux 76, 실패 33.

## adapter 재선택

Dell 5대가 `idrac10` → `idrac9`, Cisco 1대가 `ucs_xseries` → `cimc`,
Lenovo 1대가 `xcc3` → `xcc` 로 바뀌었다. 전부 **장비 실제 세대와 맞는 쪽**이다
(R760 은 FW 7.10.70.00 = iDRAC9, TA-UNODE-G1 은 CIMC, XCC 는 AFBT58B).

HPE `10.50.11.231` 은 1차부터 맞았다 — `_extract_probe_facts()` 가 HPE 분기만
갖고 있어 이 vendor 는 무인증에서도 model/firmware hint 를 얻기 때문이다.
그래서 `diagnosis.details.adapter_first_pass` 가 `None` 으로 나온다. 재선택이
값을 바꾼 경우에만 그 필드에 종전 값이 남는다.

수집 결과에는 영향이 없었다. 오선택 쌍끼리 `sections_supported` 가 같아서다
(Supermicro X9/X10 만 6섹션이라 다른데, 그 세대는 lab 에 없다).

## OEM task 제거

`data` 키가 한 개도 늘거나 줄지 않았다. 제거 전 envelope 에도 vendor task 가
쓴다던 `data.bmc.oem_<vendor>` 키는 8대 전부 0개였고, 라이브러리가 채우는
`data.bmc.oem` 은 8대 전부 있었다. 예상대로 기여가 0이었다.

## ESXi 9.x

9.0.0 세 대가 `esxi_generic` → `esxi_9x`. 7.0.3 세 대는 `esxi_7x` 유지.
수집 섹션은 양쪽 다 6개로 전·후 동일하다 — 네 adapter 의 `sections_supported`
가 같기 때문이고, 그래서 이 결함은 처음부터 데이터 손실이 아니라 관측
정확도 문제였다.

## 계정 쓰기 — 실제로 일어났고 검증까지 통과했다

**수정 전 실행**에서 Dell 4대의 표준 계정이 실제로 복구됐다.

| 대상 | family | method | action | verification | HTTP |
|---|---|---|---|---|---|
| 10.100.15.27 | `dell_slot_patch` | `patch_existing` | `password_sync` | verified | 200 |
| 10.100.15.28 | `dell_slot_patch` | `patch_existing` | `password_sync` | verified | 200 |
| 10.100.15.31 | `dell_slot_patch` | `patch_existing` | `password_sync` | verified | 200 |
| 10.100.15.33 | `dell_slot_patch` | `patch_existing` | `password_sync` | verified | 200 |

**수정 후 실행에서는 쓰기가 0건**이다. 표준 계정이 이미 맞아서 진입 조건
(표준 수집 실패 AND 표준 자격 401 AND 복구 후보 존재)이 성립하지 않았다.
게이트가 의도대로 닫혔다.

### 가장 중요한 관찰

수정 전 실행에서 `adapter_id` 는 `redfish_dell_idrac10`(오선택)이었는데
**Family 는 `dell_slot_patch`(iDRAC9, 정답)로 잡혔다.** `resolve_account_family`
가 2026-08-12 에 firmware major 우선으로 고쳐졌기 때문이다 — adapter hint 는
마지막 순위다. 이번 adapter 수정이 계정 계약을 깨뜨릴 수 없다는 근거가
실측으로 확인됐다. 수정 후에도 Family 판정 로직은 같은 답을 낸다.

## 시리얼 대조 — 베어메탈 9쌍

| # | BMC | BMC serial | 짝 | 짝 serial | 판정 |
|---|---|---|---|---|---|
| esxi01 | 10.100.15.1 | — | 10.100.64.1 | FCH2117V12M | 대조 불가 (BMC 실패) |
| esxi02 | 10.100.15.2 | FCH2116V1V0 | 10.100.64.2 | FCH2116V1V0 | **일치** |
| esxi03 | 10.100.15.3 | — | 10.100.64.3 | FCH2116V1UZ | 대조 불가 (BMC 실패) |
| svr01 | 10.100.15.27 | 64CXJ54 | 10.100.64.91 | 64CXJ54 | **일치** |
| svr02 | 10.100.15.28 | 29N1K54 | 10.100.64.92 | 29N1K54 | **일치** |
| svr03 | 10.100.15.31 | 4BP2K54 | 10.100.64.93 | 4BP2K54 | **일치** |
| svr04 | 10.100.15.32 | — | 10.100.64.94 | — | 대조 불가 (양쪽 실패) |
| svr05 | 10.100.15.33 | C3BXJ54 | 10.100.64.95 | — | 대조 불가 (ESXi 실패) |
| svr06 | 10.100.15.34 | GSBPK54 | 10.100.64.96 | GSBPK54 | **일치** |

**대조 성립 5쌍, 5쌍 모두 일치.**

### 값이 같은 이유 — 원본은 다르다

`build_correlation.yml` 은 `data.hardware` 가 mapping 이면 `hardware.serial`,
아니면 `system.serial_number` 로 떨어진다. 실제로 탄 분기를 확인했다.

| 쌍 | Redfish 쪽 | 짝 쪽 |
|---|---|---|
| esxi02 / svr01~03 | `hardware.serial` | `hardware.serial` (ESXi) |
| **svr06** | `hardware.serial` | **`system.serial_number`** (Linux) |

`svr06` 만 짝이 Linux 라 다른 분기를 탄다. Linux 에는 `gather_hardware.yml`
자체가 없어 `data.hardware` 가 null 이기 때문이다. **다른 분기, 다른 원본,
같은 값**이 나온 것이다.

원본을 채널별로 적으면 이렇다.

| 채널 | 원본 |
|---|---|
| Redfish (Dell) | `ServiceRoot.Oem.Dell.ServiceTag` — `ComputerSystem.SerialNumber` 를 덮어쓴다 |
| Redfish (그 외) | `ComputerSystem.SerialNumber` |
| ESXi | 하이퍼바이저가 읽은 SMBIOS `ansible_product_serial` |
| Linux | DMI `product_serial` (setup fact → `/sys/class/dmi/id/product_serial` → null) |

즉 Dell 6대는 **BMC 가 Service Tag 를, OS/ESXi 가 SMBIOS 를** 보고하는데 값이
같다. 이번 검증의 핵심 관찰 지점이었고, 결과는 Dell 이 두 곳에 같은 문자열을
넣는다는 것이다. **코드가 일치를 보장하는 게 아니라 장비가 그렇게 준다.**
`docs/ai/contracts/serial-number.md` 가 "시리얼에는 폴백이 없다" 고 적어 둔 것과
같은 맥락이다 — 값이 어긋나는 장비가 나오면 그때는 어느 쪽이 맞는지 따로
판단해야 한다.

## 수집이 안 되는 5대 — 전·후 동일

| 대상 | 실패 | 확인한 것 |
|---|---|---|
| 10.100.15.1 | protocol / PROTOCOL_CHECK_FAILED | TCP 443 은 열려 있는데 ServiceRoot 를 제대로 주지 않는다 |
| 10.100.15.3 | reachable / TCP_CONNECT_FAILED | 전 포트 무응답. 방화벽 drop 인지 전원 off 인지는 이 관측만으로 안 갈린다 |
| 10.100.15.32 | auth / AUTH_PROBE_FAILED | ServiceRoot 가 벤더를 식별시키지 못한다(`vendor_unresolved`). 표준 계정은 전역이라 시도됐고 거부됐다. 복구 세트는 vendor 축이라 못 열었다 — 설계대로다 |
| 10.100.64.94 | reachable / TCP_CONNECT_FAILED | 짝인 BMC 10.100.15.32 도 실패. 같은 기계가 양쪽 다 안 된다 |
| 10.100.64.95 | protocol / PROTOCOL_CHECK_FAILED | 이번에 처음 확인. 443 응답은 있으나 vSphere 응답이 아니다 |

`10.100.64.95` 는 직전 실측(2026-08-13 문서 작업)에서는 대상이 아니었다.
`10.100.64.94` 의 전 포트 무응답은 그때와 같다.

## 하지 않은 것

- `schema/baseline_v1/*.json` 은 건드리지 않았다. 회귀 기준선이고
  `schema/baseline_v1/README.md` 가 수정을 금지한다 (rule 13 R4 / 21 R1)
- adapter priority 를 재배치하지 않았다. 정상 경로에서 신세대가 구세대에 지는
  역전을 만든다
- `_extract_probe_facts` 를 non-HPE 로 넓히지 않았다. Dell `ServiceRoot.Product`
  는 BMC 이름이라 넣으면 model_patterns 미스매치로 Dell adapter 가 전부 실격되고
  generic 으로 떨어진다 — 그건 진짜 데이터 손실이다
