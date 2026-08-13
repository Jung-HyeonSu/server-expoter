# LAB_INVENTORY — 실장비 토폴로지

> 2026-08-13 전면 재작성. 종전 문서는 cycle-015 / cycle-016 / 2026-08-12 정정이 겹겹이
> 쌓이면서 서로 어긋나 있었다 (§2는 `15.34 ↔ 64.96`, §4는 `15.33 ↔ 64.96`이라 적었다).
> 사용자가 제공한 장비 목록을 기준으로 다시 쓰고, 도달성은 직접 측정한 값을 적는다.

자격증명은 여기 없다. 세 곳으로 나뉜다.

| 내용 | 위치 |
|---|---|
| 계정·비밀번호 | `vault/.lab-credentials.yml` (gitignored) |
| IP·모델·짝 정보 | `inventory/lab/*.json` (gitignored) |
| sanitized 토폴로지 | 이 파일 |

수집 실행에 쓰는 자격증명은 또 다르다. `vault/<loc>/…` 의 ansible-vault 파일이며
`vault/.lab-credentials.yml` 과는 별개다. 후자는 브라우저 E2E(`tests/e2e_browser/lab_loader.py`)가 읽는다.

## 1. 권한

사용자 명시 (2026-04-29):

> 이 프로젝트는 ai에게 모든 권한을 준다 … 실장비 권한도 하네스에게 주겠다 어짜피 테스트서버이다

근거 ADR: `docs/ai/decisions/ADR-2026-04-28-security-policy-removal.md`,
`docs/ai/decisions/ADR-2026-04-29-lab-access-grant.md`

## 2. 베어메탈 9대 — BMC와 OS가 같은 기계

이 9쌍이 이 lab의 핵심 자산이다. 같은 물리 서버를 BMC 경로와 OS/ESXi 경로 양쪽에서
수집할 수 있어서, 채널 간 `correlation.serial_number` 일치 여부를 실증할 수 있다.

| # | 모델 | BMC | 얹힌 것 | OS/ESXi IP |
|---|---|---|---|---|
| esxi01 | Cisco-TA-UNODE-G1 | 10.100.15.1 | ESXi 7.0.3 | 10.100.64.1 |
| esxi02 | Cisco-TA-UNODE-G1 | 10.100.15.2 | ESXi 7.0.3 | 10.100.64.2 |
| esxi03 | Cisco-TA-UNODE-G1 | 10.100.15.3 | ESXi 7.0.3 | 10.100.64.3 |
| svr01 | Dell-PowerEdge R760 | 10.100.15.27 | ESXi 9.0.0 | 10.100.64.91 |
| svr02 | Dell-PowerEdge R760 | 10.100.15.28 | ESXi 9.0.0 | 10.100.64.92 |
| svr03 | Dell-PowerEdge R760 | 10.100.15.31 | ESXi 9.0.0 | 10.100.64.93 |
| svr04 | Dell-PowerEdge R760 | 10.100.15.32 | ESXi 9.0.0 | 10.100.64.94 |
| svr05 | Dell-PowerEdge R760 | 10.100.15.33 | ESXi 9.0.0 | 10.100.64.95 |
| svr06 | Dell-PowerEdge R760 | 10.100.15.34 | Ubuntu 24.04 | 10.100.64.96 |

**시리얼 대조가 자명하지 않은 이유.** `common/tasks/normalize/build_correlation.yml:18-39`을
보면 채널마다 읽는 원본이 다르다. Redfish는 BMC가 보고하는 `ComputerSystem.SerialNumber`,
ESXi는 하이퍼바이저가 본 SMBIOS(`ansible_product_serial`), Linux는 DMI `product_serial`이다.
게다가 Linux는 `data.hardware` 섹션 자체가 없어 `data.system.serial_number` 분기로 떨어진다.
그래서 이 9쌍 대조는 "같은지 확인"이 아니라 **채널 간 시리얼 계약을 확정하는 작업**이다.

## 3. BMC 외 대상

| 구분 | IP | 비고 |
|---|---|---|
| HPE iLO6 | 10.50.11.231 | ProLiant DL380 Gen11 |
| Lenovo XCC | 10.50.11.232 | |
| Windows | 10.100.64.120 | |
| Linux VM | 10.100.64.156 / .161 / .165 | .161은 Python 3.6 — raw fallback 검증 대상 |
| Jenkins master | 10.100.64.152 / .153 | |
| Jenkins agent | 10.100.64.154 / .155 | agent는 `ich/chj/yi/git` 4 label을 모두 갖는다 |

미확인으로 남긴 것: `10.100.64.135`(2026-08-12 실측에서 Windows가 아니라 RHEL 계열이었다),
`10.100.64.163` / `.167` / `.169`(사용자 제공 목록에 없다).

## 4. 도달성 실측 (2026-08-13)

인증 없이 TCP 연결만 확인했다. BMC/ESXi는 443, Linux는 22, Windows는 5985·5986.

**23/25 도달.** 이 결과가 이전 기록 몇 개를 뒤집는다.

| 대상 | 이전 기록 | 실측 |
|---|---|---|
| 10.100.15.1 | cycle-016 "lab 부재 / non-Redfish" | [OK] 443 OPEN |
| 10.100.15.32 | cycle-015 "사내에 없는 장비" | [OK] 443 OPEN |
| 10.100.64.120 | cycle-015 "사내 부재" | [OK] 5985·5986 OPEN |
| 10.50.11.231 | 2026-08-12 정정본 "종전 timeout 기록은 stale" | [OK] 443 OPEN — 정정본이 맞다 |
| 10.100.15.3 | cycle-016 "ping fail 부재" | [WARN] 443/80/22/623/5000 전부 timeout |
| 10.100.64.94 | 기록 없음 | [WARN] 443/80/22/902/5989 전부 timeout |

닿지 않은 둘은 RST가 한 번도 오지 않았고, 각각의 짝(`10.100.64.3`, `10.100.15.32`)은
열려 있으니 라우팅 문제는 아니다. 다만 이 관측만으로 방화벽 drop인지 전원 off인지는
가려낼 수 없다. `CLAUDE.md` §7이 금지하는 "timeout만 보고 IP 미사용 단정"을 하지 않고
관측 사실로만 남긴다.

## 5. 네트워크 구간

| 구간 | 용도 |
|---|---|
| 10.100.64.0/24 | Jenkins + OS/ESXi 수집 대상 |
| 10.100.15.0/24 | Dell + Cisco BMC |
| 10.50.11.0/24 | HPE + Lenovo BMC |

Jenkins agent(10.100.64.0/24)에서 세 구간 모두 닿는다.

## 6. 알려진 공백

**ESXi 9.0.0에 맞는 어댑터가 없다.** `adapters/esxi/*.yml`의 `version_patterns`는
`^6\.` / `^7\.` / `^8\.` 셋뿐이라 9.0.0 다섯 대는 `esxi_generic`으로 떨어진다.
다만 `esxi_7x` / `esxi_8x` / `esxi_generic`의 `sections_supported`가 완전히 같아서
수집 항목이 줄지는 않는다. `meta.adapter_id`가 `esxi_generic`으로 찍히는 관측 정확도 문제다.
`REQUIREMENTS.md` 지원 표에는 9.x가 아예 없다.

**ESXi 9.0.0 5대의 접속 자격증명이 제공되지 않았다.** BMC 자격증명만 받았다.
`vault/.lab-credentials.yml`에는 `credentials_provided: false`로 표시해 두었고,
수집 실행은 `vault/<loc>/esxi.yml`을 쓰므로 그쪽에 값이 있으면 동작한다.

## 7. 갱신 시점

호스트가 늘거나 줄 때, 벤더가 추가될 때, 도달성이 바뀔 때 이 문서를 고친다.
자격증명은 여기 적지 않는다 — `scripts/ai/verify_no_plaintext_secret.py`가 막는다.
