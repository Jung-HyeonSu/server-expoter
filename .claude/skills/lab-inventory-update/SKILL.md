---
name: lab-inventory-update
description: lab 보유 / 부재 영역 (vendor / 펌웨어 / OS / 환경) 을 자동 측정해서 LAB_INVENTORY 갱신. cycle 2026-05-01 학습 — lab 한계가 본질적 제약. 사용자가 "lab 인벤토리 갱신", "현재 lab 상태", "부재 영역 list" 요청 시.
---

# lab-inventory-update

## 목적

server-exporter lab 의 현재 보유 / 부재 영역을 측정해 `docs/ai/tickets/<active-cycle>/LAB_INVENTORY.md` 또는 `docs/ai/catalogs/LAB_INVENTORY.md` 갱신. 다음 cycle 의 호환성 작업이 어디까지 사이트 실측 가능 / 어디부터 web sources 의존 인지 명확히 한다.

## 호출 시점

- 새 cycle 진입 시 (현재 lab 상태 파악)
- 사용자 사이트 사고 후 "이 환경 lab 보유?" 의문
- 신 vendor / 신 펌웨어 추가 의뢰 시 lab 가용성 점검
- 정기 (격주 / 월간)

## 측정 대상

### Redfish vendor / 펌웨어
- Dell iDRAC9 (5.x / 6.x)
- HPE iLO 5 / iLO 6 (펌웨어 별)
- Lenovo XCC2 / XCC3 (펌웨어 별)
- Supermicro X9 / X10 / X11 / X12 / X13 / X14
- Cisco CIMC (M4 / M5 / M6 generations)
- 부재 vendor: Huawei iBMC / Inspur / NEC

### OS
- RHEL 8.x / 9.x / 10
- Rocky 8.x / 9.x
- Ubuntu 20.04 / 22.04 / 24.04
- Windows Server 2019 / 2022 / 2025
- Windows 10 / 11 (raw fallback 검증)

### ESXi
- 6.x / 7.0.3 / 8.0.x

### 외부 환경
- InfiniBand fabric (현재 부재 — DMTF + Mellanox spec 의존)
- TPM 2.0
- BMC TLS 1.0/1.1 구 펌웨어

## 자동 측정 절차

### 1. lab credentials 로드

```bash
test -f .lab-credentials.yml && echo "credentials available"
```

또는 `tests/scripts/lab_inventory.py` (있을 시) — sanitized 버전만 commit.

### 2. ICMP / TCP 도달성 + Redfish ServiceRoot

```python
# tests/scripts/lab_inventory.py (예시)
import json
from pathlib import Path

REDFISH_HOSTS = ...  # .lab-credentials.yml 에서 로드 (gitignored)

def probe_host(ip: str) -> dict:
    # ping → port 443 → /redfish/v1/ → Manufacturer / FirmwareVersion 추출
    ...
```

### 3. OS / ESXi 도달성

- SSH 22 / WinRM 5986 / vSphere 443

### 4. 결과 sanitize

- IP / hostname / serial / asset_tag → 가명
- vendor / 펌웨어 / OS 만 보존

### 5. LAB_INVENTORY.md 갱신

```markdown
# LAB_INVENTORY — 측정 일자 YYYY-MM-DD

## 보유 (sanitized)

### Redfish
| vendor | 펌웨어 | 도달 | Manufacturer 확인 |
|---|---|---|---|
| dell | iDRAC9 6.10 | OK | Dell Inc. |
| hpe | iLO 6 1.55 | OK | HPE |
| lenovo | XCC3 1.17.0 | OK | Lenovo |
| supermicro | (부재) | - | - |
| cisco | CIMC M4 | partial | Cisco Systems |

### OS
| distro | version | 도달 |
|---|---|---|
| RHEL | 8.10 | OK |
| RHEL | 9.6 | OK |
| Ubuntu | 24.04 | OK |
| Rocky | 9.6 | OK |
| Windows Server | 2022 | UNSTABLE |

### ESXi
| version | 도달 |
|---|---|
| 7.0.3 | OK |
| 8.0u3 | 부재 |

## 부재 (sources 의존)

| 영역 | 의존 | 다음 cycle 결정 |
|---|---|---|
| Huawei iBMC | web sources (support.huawei.com) | (사용자 결정) |
| Inspur | web sources | (사용자 결정) |
| InfiniBand | DMTF + Mellanox spec | OPS 결정 |
| RHEL 10 | release notes | 신 distro 시점 |
| iDRAC 7/8 | vendor docs | EOL 영역 |

## 갱신 history
- YYYY-MM-DD: ...
```

## sanitize 규칙

- IP: `10.50.11.232` → `192.0.2.10` (RFC 5737)
- hostname: 운영 명 → `bmc-test-NN`
- serial: 실 serial → `SAMPLE-NNN`
- credential: 절대 commit 안 함

## 자율 vs 사용자 결정

- **AI 자율**: 측정 + sanitize + LAB_INVENTORY.md 갱신
- **사용자 결정**: 신 lab 환경 추가 / 부재 vendor 의 lab 환경 의뢰 / EOL 영역 정리

## 관련

- rule 96 R1-A (web sources 의무 — lab 부재 영역)
- rule 25 R7-A-1 (사용자 실측 > spec)
- agent: lab-tracker (자동 측정 위임)
- skill: capture-site-fixture (사이트 사고 fixture)
- catalog: docs/ai/catalogs/LAB_INVENTORY.md (있을 시)
