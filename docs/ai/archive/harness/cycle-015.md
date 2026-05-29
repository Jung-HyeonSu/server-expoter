# cycle-015 — 실장비 lab 전체 권한 확장 + Browser E2E 도입

## 일자
2026-04-29

## 진입 사유

cycle-014가 4 vendor BMC code path 검증 + HIGH Jinja2 fix 완료 직후, 사용자가 cycle-015 시작 시 lab 전체 (28 호스트) 권한 + Browser E2E 인프라 명시 결정:

> "해당 프로젝트는 ai에게 모든 권한을 준다 ... 실장비 권한도 하네스에게 주겠다 어짜피 테스트서버이다"
> "아래와같은 서버에도 모두 접속할수있도록한다 e2e 테스트도 크롬플러그인을 사용하던지 모두 수행할 수 있도록 해라"

cycle-014가 4 vendor BMC만 다뤘다면, cycle-015는 **lab 전체**:
- Jenkins master 2 + agent 2
- Linux VM 5 (RHEL 8.10 / 9.2 / 9.6 / Rocky 9.6 / Ubuntu 24.04) + baremetal 1
- Windows VM 2 (Win10 / Server 2022)
- BMC 11 (Dell × 6 / HPE 1 / Lenovo 1 / Cisco × 3)
- ESXi 3

→ 총 **28 호스트** lab 권한 정책 정착 + Browser E2E 인프라.

## 처리 내역

### Phase A — 자격증명 + 인벤토리 구조

| 작업 | 결과 |
|---|---|
| `.gitignore` 강화 | `vault/.lab-credentials.yml` + `inventory/lab/**` 차단 (commit 안전) |
| `vault/.lab-credentials.yml` 신규 (gitignored) | 5 그룹 (jenkins_masters/agents/os_linux/os_windows/redfish/esxi), 28 호스트 |
| `inventory/lab/{os-linux,os-windows,redfish,esxi,jenkins}.json` (gitignored) | INVENTORY_JSON 형식 |
| `inventory/lab/README.md` (gitignored) | 사용법 + 자격증명 위치 |

### Phase B — LAB_INVENTORY catalog (sanitized)

`docs/ai/catalogs/LAB_INVENTORY.md` 신규 (8 섹션):
1. 권한 정책 (cycle-011 + cycle-015 ADR reference)
2. 호스트 카운트 (28대)
3. 네트워크 zone (3 zone — service/Dell-Cisco BMC/HPE-Lenovo BMC)
4. 특이 호스트 (RHEL 8.10 Py3.6 / Dell baremetal correlation / Dell GPU / Win 2022 / Cisco × 3)
5. 검증 라운드 매핑 (Round 11~16 + Browser E2E)
6. 자격증명 정책 (gitignored 평문 → private 전환 후 결정)
7. 참고 파일
8. 갱신 trigger

> sanitized = IP / 자격증명 제외, 카운트 / zone / 특이사항만.

### Phase C — 실장비 연결성 검증 (Windows 클라이언트 직접)

| 검증 | 결과 |
|---|---|
| ICMP 도달성 (21 호스트 sample) | 21/21 PASS |
| TCP protocol 포트 | Linux SSH 22 / Redfish HTTPS 443 / ESXi HTTPS 443 / Win10 WinRM 5985 / Jenkins HTTP 8080 모두 OPEN |
| Redfish ServiceRoot 무인증 응답 (rule 27 R3 1단계) | Dell × 5 정상 iDRAC + HPE iLO ProLiant DL380 Gen11 + Lenovo XCC 1.15 정상 |
| **rule 96 DRIFT-011 검출** | Dell 32 (사용자 라벨) → 실 `Vendor='AMI'` / Cisco 2 (사용자 라벨) → 실 `Product='TA-UNODE-G1'` |
| Win Server 2022 (10.100.64.132) | **모든 포트 closed** — 호스트 firewall (OPS-10) |
| Cisco BMC 1, 3 일시 장애 | 503 / timeout — 다음 일과시간 재확인 (OPS-11) |

evidence: `tests/evidence/cycle-015/connectivity-2026-04-29.md`

### Phase D — Playwright Browser E2E 스켈레톤

| 파일 | 내용 |
|---|---|
| `requirements-test.txt` | playwright 1.58 + pytest-playwright 0.7.2 + paramiko 4.0 + pywinrm 0.5.0 + pyyaml + requests |
| `tests/e2e_browser/__init__.py` | (empty) |
| `tests/e2e_browser/lab_loader.py` | `vault/.lab-credentials.yml` 로더 + `LabCreds` dataclass |
| `tests/e2e_browser/conftest.py` | `lab` / `jenkins` / `grafana` / `slow` marker + 미존재 시 auto-skip |
| `tests/e2e_browser/test_jenkins_master.py` | dashboard 도달 (active) + login flow (skip — 사용자 정책 결정 후) |
| `tests/e2e_browser/test_grafana_ingest.py` | placeholder (skip — Grafana endpoint 합의 후) |
| `tests/e2e_browser/README.md` | 실행 방법 + Marker 정의 |
| Chromium 1208 다운로드 | `~/.cache/ms-playwright/chromium-1208` 설치 완료 |

**smoke test**: `test_master_dashboard_reachable[chromium]` PASSED (2.42s, 10.100.64.152:8080).

### Phase E — Catalog + ADR

| 파일 | 변경 |
|---|---|
| `docs/ai/catalogs/CONVENTION_DRIFT.md` | DRIFT-011 entry (open) — user-label vs Redfish Manufacturer |
| `docs/ai/catalogs/EXTERNAL_CONTRACTS.md` | "실 lab 발견 — 비표준 BMC" 절 (AMI 1.11.0 + TA-UNODE-G1 + Cisco 일시 장애) |
| `docs/ai/catalogs/FAILURE_PATTERNS.md` | `user-label-vs-redfish-manufacturer-drift` 첫 실 사례 |
| `docs/ai/catalogs/LAB_INVENTORY.md` | 신규 (Phase B) |
| `docs/ai/decisions/ADR-2026-04-29-lab-access-grant.md` | 신규 (rule 70 R8 #2 trigger — catalogs 카운트 변경 + 신규 디렉터리 2개) |
| `docs/ai/CURRENT_STATE.md` | cycle-015 단락 |
| `docs/ai/NEXT_ACTIONS.md` | cycle-015 closed + OPS-9~15 + AI-12~15 등재 |

## 표면 카운트 영향

```
rules: 28 (변경 없음)
skills: 43 (변경 없음)
agents: 49 (변경 없음)
policies: 9 (변경 없음)
hooks: 18 (변경 없음)
schema entries: 57 (변경 없음)
catalogs: 8 → 9 (+LAB_INVENTORY)
decisions: 4 → 5 (+lab-access-grant)
신규 디렉터리: 2 (`inventory/lab/` gitignored, `tests/e2e_browser/`)
신규 의존성 파일: 1 (`requirements-test.txt`)
신규 evidence 디렉터리: 1 (`tests/evidence/cycle-015/`)
```

## 검증 결과 (cycle-015 후반 자율 매트릭스 일괄 실행 후)

| 검증 | 결과 |
|---|---|
| harness consistency | PASS (28/43/49/9) |
| vendor boundary | PASS |
| project_map_drift | PASS (fingerprint 갱신) |
| validate_field_dictionary | PASS (10/10) |
| pytest tests/e2e (기존) | 145 passed |
| pytest tests/e2e_browser smoke | dashboard 도달 PASS |
| **pytest tests/e2e_browser login** | **dashboard + login 2/2 PASS** (cloviradmin 활성) |

## 자율 매트릭스 일괄 실행 결과 (Phase F — cycle-015 후반)

사용자 명시 ("남아있는 작업 모두수행해라" + cleanup 결정) 후 다음 추가 작업:

### Phase F-1 — Cleanup (사용자 명시)

| 작업 | 결과 |
|---|---|
| `Jenkinsfile_grafana` 삭제 | done — 모든 docs/rule/policy 참조 정리 (rule 80/13/31/00 + JENKINS_PIPELINES + CLAUDE.md + LAB_INVENTORY + ai-context + test-selection-map + measurement-targets + pre_commit_jenkinsfile_guard) |
| `tests/e2e_browser/test_grafana_ingest.py` 삭제 | done |
| 10.100.15.32 (Dell GPU — 실 AMI) 제거 | done — DRIFT-011 resolved |
| 10.100.15.2 (Cisco — 실 TA-UNODE) 제거 | done — DRIFT-011 resolved |
| 10.100.64.120 (Windows 10) 제거 | done — 사내 부재 |
| Win Server 2022 IP 정정 132 → **10.100.64.135** | done |

### Phase F-2 — 자율 매트릭스 (5건)

| # | 작업 | 결과 | evidence |
|---|---|---|---|
| OPS-3 partial | Dell × 5 + HPE + Lenovo lab credentials → 실 BMC primary auth | **7/9 PASS** (200 OK ServiceRoot+Systems+Managers) | `bmc-auth-probe-2026-04-29.{py,json}` |
| OPS-11 | Cisco BMC 1, 3 재확인 | 1: 503/Bad Gateway, 3: timeout (open 잔존) | 동일 |
| AI-13 | Linux raw fallback (rule 10 R4) | **6/6 SSH PASS + RHEL 8.10 Py 3.6.8 → python_incompatible 실증** | `linux-probe-2026-04-29.{py,json}` |
| AI-14 | Browser E2E Jenkins login 활성 | 2/2 PASS (test_master_dashboard_reachable + test_master_login_then_dashboard) | pytest tests/e2e_browser |
| AI-12 | Dell × 5 Round 11 endpoint coverage | 5/5 PowerEdge R760 BIOS 2.3.5 + Systems/Storage/NIC/FW/Accounts 모두 응답 | `dell-round11-endpoint-coverage.{py,json}` |
| WinRM | Win 2022 (정정된 IP) | PASS — administrator/NTLM, OS build 20348, PS 5.1, Xeon Silver 4510 8GB | `winrm-probe-2026-04-29.{py,json}` |

## 미완 / 사용자 행위 필요 (cycle-015 종료 시점)

| # | 작업 | 상태 | 차단 사유 |
|---|---|---|---|
| OPS-9 | repo private 전환 시 자격증명 정책 결정 | open | private 전환 시점 |
| OPS-3 (잔여) | vault에 lab credentials 흡수 + ansible-vault encrypt | partially possible | 운영팀 timing |
| OPS-11 (잔여) | Cisco BMC 1, 3 가용성 재확인 | open | 일시 장애 — lab 운영자 |
| OPS-14 | Jenkins API token 정책 | partially obviated | cloviradmin이 Jenkins 사용자 = E2E PASS |

## closed (cycle-015 본 세션)

| OPS / AI | 결과 |
|---|---|
| OPS-10 (Win 2022 firewall) | resolved (사용자 직접 + IP 정정 132→135) |
| OPS-12 (Dell 32 라벨) | resolved (호스트 제거) |
| OPS-13 (Cisco 2 식별) | resolved (호스트 제거) |
| OPS-15 (Grafana endpoint) | closed (Jenkinsfile_grafana 제거) |
| AI-13 (Linux raw fallback Round) | DONE |
| AI-14 (Browser E2E login 활성) | DONE |
| AI-15 (deep_probe AMI/TA-UNODE) | obviated (호스트 제거) |

## 자율 진행 closed (cycle-015 — Phase A~F)

| Phase | 결과 |
|---|---|
| A | lab 자격증명 + inventory 6 파일 (gitignored) |
| B | LAB_INVENTORY catalog 신규 + 8 섹션 |
| C | 21 호스트 ICMP + TCP protocol 검증 + DRIFT-011 발견 |
| D | Playwright + Chromium 설치 + Browser E2E smoke 1/1 PASS |
| E | catalog 4종 갱신 + ADR + cycle-015 log + CURRENT_STATE + NEXT_ACTIONS |
| F-1 | Cleanup (Grafana 제거 / 호스트 3대 제거 / Win2022 IP 정정) |
| F-2 | 자율 매트릭스 5건 (BMC auth + Linux raw + WinRM + Dell Round 11 + Jenkins login E2E) |

## 자율 진행 잔여 (다음 세션 AI)

| # | 작업 | 전제 |
|---|---|---|
| AI-12 | 첫 lab Round (Dell × 5 정상 BMC) — Round 11 baseline 갱신 | 사용자 OPS-12 (32번 라벨) 결정 후 (그러나 Dell × 5는 즉시 가능) |
| AI-13 | Linux raw fallback Round (RHEL 8.10) — Round 14 | 즉시 가능 (OPS-3와 무관) |
| AI-14 | Browser E2E 활성 시나리오 (Jenkins login + Grafana) | OPS-14 / OPS-15 결정 후 |
| AI-15 | deep_probe_redfish.py — Dell 32 (AMI) + Cisco 2 (TA-UNODE) | 즉시 가능 (BMC 자격 시도 후 unauthenticated 추가 path 확인) |
| AI-16 | Browser E2E — Cisco CIMC / iDRAC Web UI 추가 시나리오 | 자격증명 정책 결정 후 |

## 본 cycle commit (예정)

| 영역 | 내용 |
|---|---|
| docs | cycle-015.md + ADR + LAB_INVENTORY 신규 |
| catalogs | DRIFT-011 / EXTERNAL_CONTRACTS / FAILURE_PATTERNS / NEXT_ACTIONS / CURRENT_STATE |
| infra | requirements-test.txt + tests/e2e_browser/ + .gitignore |
| evidence | tests/evidence/cycle-015/connectivity-2026-04-29.md |

## 관련

- 직전: cycle-014 (4 vendor BMC code path + Jinja2 fix `bf247266`)
- ADR: `ADR-2026-04-29-lab-access-grant.md` (cycle-015 governance)
- 직전 ADR (대조): `ADR-2026-04-28-security-policy-removal.md` (cycle-011 — 본 ADR이 정책 해제의 실장비 차원 확장)
- evidence: `tests/evidence/cycle-015/connectivity-2026-04-29.md`
- catalog: `LAB_INVENTORY.md` 신규 / DRIFT-011 / EXTERNAL_CONTRACTS lab 발견 절 / FAILURE_PATTERNS 첫 실 사례
- rule trigger: rule 27 R3 (Vault 2단계 1단계 검출) / rule 96 R1, R4 (외부 계약 origin + drift 기록) / rule 70 R8 #2 (ADR trigger) / rule 91 R3 (cycle 진입 시 5섹션 분석 수행)
