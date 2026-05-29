# ADR-2026-04-29 — 실장비 lab 접근 권한 부여 (Lab Access Grant)

## 상태

**Accepted** (2026-04-29 cycle-015, 사용자 명시 결정)

## 컨텍스트 (Why)

cycle-013 종료 시점 NEXT_ACTIONS 잔여:
- OPS-1 Jenkins 빌드 시범 (lab UI 클릭)
- OPS-3 평문 password 6종 회전 (실장비)
- OPS-4 P1 lab 회귀 (vendor 5종)
- 본 작업들 모두 사용자 1회 행위 의존 → AI 자동화 불가

cycle-015 진입 시 사용자 명시 결정 (2026-04-29 채팅):
> "해당 프로젝트는 ai에게 모든 권한을 준다 하네스에서 권한이 없다면 하네스를 수정하라 이 프로젝트는 ai에게 모든 권한을 주는것이다 실장비 권한도 하네스에게 주겠다 어짜피 테스트서버이다"
> "아래와같은 서버에도 모두 접속할수있도록한다 e2e 테스트도 크롬플러그인을 사용하던지 모두 수행할 수 있도록 해라"

→ cycle-011 보안 정책 해제의 **실장비 차원 확장**. AI에게 lab 자격증명 + 외부 시스템 접근 + Browser E2E 인프라 부여.

## 결정 (What)

| # | 영역 | 결정 |
|---|---|---|
| 1 | 자격증명 저장 | `vault/.lab-credentials.yml` 평문 + `.gitignore` (repo public 동안) |
| 2 | Inventory 위치 | `inventory/lab/*.json` (gitignored, INVENTORY_JSON 형식) |
| 3 | Catalog | `docs/ai/catalogs/LAB_INVENTORY.md` (sanitized — 카운트/zone만) |
| 4 | Browser E2E | `tests/e2e_browser/` (Playwright + Chromium) |
| 5 | Test 의존성 | `requirements-test.txt` (playwright/paramiko/pywinrm/pytest-playwright) |
| 6 | 정책 trigger | rule 70 R8 #2 (표면 카운트 변경 — catalogs +1 / 새 dir 2개) + rule 96 R1 (외부계약 origin) |

추가 결정 사항:
- **자격증명 회전 시기**: 사용자가 repo private 전환 시점에 ansible-vault encrypt 흡수 또는 gitignored 평문 영구 유지 결정 (NEXT_ACTIONS 추적)
- **Browser E2E 첫 시나리오**: Jenkins master dashboard 도달 (인증 시나리오는 Jenkins 사용자 정책 합의 후)
- **DRIFT 발견 처리**: 본 cycle 연결성 검증 중 **rule 96 외부계약 drift 2건** 발견 (DRIFT-011) — 사용자 라벨 vs Redfish Manufacturer 불일치

## 결과 (Impact)

| 영역 | 변경 |
|---|---|
| 신규 파일 (gitignored) | `vault/.lab-credentials.yml` + `inventory/lab/{os-linux,os-windows,redfish,esxi,jenkins}.json` + `inventory/lab/README.md` |
| 신규 파일 (committed) | `requirements-test.txt`, `tests/e2e_browser/{__init__.py,conftest.py,lab_loader.py,test_jenkins_master.py,test_grafana_ingest.py,README.md}`, `docs/ai/catalogs/LAB_INVENTORY.md`, `tests/evidence/cycle-015/connectivity-2026-04-29.md`, 본 ADR, `docs/ai/archive/harness/cycle-015.md` |
| 수정 파일 | `.gitignore` (lab credential / inventory 추가 차단), `docs/ai/catalogs/{CONVENTION_DRIFT,EXTERNAL_CONTRACTS,FAILURE_PATTERNS}.md`, `docs/ai/{CURRENT_STATE,NEXT_ACTIONS}.md` |
| 표면 카운트 | catalogs 8 → 9 (+LAB_INVENTORY) |
| 호스트 권한 부여 | 28대 (Jenkins master 2 / agent 2 / OS 8 / Redfish 11 / ESXi 3 / 주의: Win Server 2022는 firewall closed) |
| Network zone 도달 | 10.100.64.0/24 + 10.100.15.0/24 + 10.50.11.0/24 (모두 Windows 클라이언트에서 직접 도달) |

**리스크**:
- 평문 자격증명 로컬 잔존 — `.gitignore` 차단으로 commit 없으나, Windows 디스크 도난 시 노출. 사용자 lab 정책 수용 (MED).
- Win Server 2022 (10.100.64.132) 모든 포트 closed — 호스트 firewall / 서비스 down 추정. 자율 처리 한계. 사용자 host 콘솔 진입 또는 vCenter 경유 firewall 해제 필요 (LOW — 다른 호스트로 검증 가능).
- Cisco BMC 1, 3 일시 장애 (503/timeout) — 다음 일과시간 재확인 (LOW).
- **Dell 32 (GPU 호스트) BMC가 AMI Redfish Server** — 사용자 라벨 "dell"과 실 Manufacturer "AMI" 불일치 (DRIFT-011). 물리 호스트 식별 필요 (MED).
- **Cisco BMC 2 (10.100.15.2) Product=TA-UNODE-G1** — 표준 CIMC Product 형식 아님. UCS 외 제품 시리즈 가능 (DRIFT-011, MED).

→ 사용자 명시 결정 + 내부 lab + 테스트 서버 → 위 리스크 모두 수용.

## 대안 비교 (Considered)

| 옵션 | 설명 | 결정 | 사유 |
|---|---|---|---|
| **A. 평문 + gitignore** | `vault/.lab-credentials.yml` 평문, `.gitignore` 차단 | **채택** | 작업 속도 우선. private 전환 후 결정 보류 |
| B. 새 vault password로 암호화 | 기존 `vault/*.yml` 8개 재암호화 + 새 자격증명 흡수 | 거절 | 기존 baseline 회귀 의미 변동 + cycle-015 작업 정체 |
| C. 사용자 홈 외부 파일 | `~/.server-exporter-lab.yml` | 거절 | 저장소 외부에 두면 발견성 / 백업 정책 모호 |
| D. 자격증명 미저장 (매번 사용자 입력) | 환경변수 / prompt | 거절 | "AI에게 모든 권한" 결정 정신 위반 |

Browser E2E 도구 선택:

| 옵션 | 채택 |
|---|---|
| **Playwright** | **채택** — Python sync API, Chromium 단독, MS 공식 |
| Selenium | 거절 — 드라이버 매번 매칭 부담 |
| Puppeteer | 거절 — Node.js 의존 (저장소 Python only) |
| 사용자 Chrome 플러그인 | 보조 — 사용자가 원할 때 별도 |

## 후속 (Follow-up)

NEXT_ACTIONS.md 등재:
1. **OPS-9** repo private 전환 시 자격증명 정책 결정 (vault encrypt vs gitignored 영구)
2. **OPS-10** Win Server 2022 firewall 해제 (사용자 host 콘솔)
3. **OPS-11** Cisco BMC 1, 3 가용성 재확인 (다음 일과시간)
4. **OPS-12** Dell 32 (실제 AMI) 물리 호스트 식별 + inventory/lab vendor 라벨 정정
5. **OPS-13** Cisco BMC 2 TA-UNODE-G1 제품 시리즈 식별
6. **AI-12** 첫 lab Round (Dell × 5 정상 BMC) — Round 11 baseline 갱신
7. **AI-13** Linux raw fallback Round (RHEL 8.10) — Round 14
8. **AI-14** Browser E2E 활성 시나리오 (Jenkins 사용자 정책 결정 후)

## 관련

- 직전 ADR: `ADR-2026-04-28-security-policy-removal.md` (cycle-011) — 본 ADR이 정책 해제의 실장비 차원 확장
- 관련 ADR: `ADR-2026-04-29-vault-encrypt-adoption.md` (cycle-013) — vault encrypt 정책 (본 ADR과 별도, lab 자격증명은 평문 gitignored)
- rule: `00-core-repo` (보호 경로 분류 권장 — 본 cycle 실 적용 0건), `70-docs-and-evidence-policy` R8 (본 ADR이 R8 적용 세 번째 사례), `91-task-impact-gate` (cycle-015 진입 시 R3 5섹션 분석 수행), `96-external-contract-integrity` (Dell 32 / Cisco 2 DRIFT-011)
- evidence: `tests/evidence/cycle-015/connectivity-2026-04-29.md` (21 호스트 도달성 + Redfish ServiceRoot 무인증 응답)
- catalog: `docs/ai/catalogs/LAB_INVENTORY.md`, `EXTERNAL_CONTRACTS.md` (AMI 1.11.0 + TA-UNODE-G1 entry 추가)

## 작성 메타

- 결정 일자: 2026-04-29 (cycle-015)
- 결정자: hshwang1994 (사용자 명시 채팅 결정)
- 적용자: AI (Claude Opus 4.7)
- ADR trigger: rule 70 R8 #2 — 표면 카운트 변경 (catalogs 8→9 / 새 디렉터리 2개 (`inventory/lab/`, `tests/e2e_browser/`) / 새 파일 다수)
