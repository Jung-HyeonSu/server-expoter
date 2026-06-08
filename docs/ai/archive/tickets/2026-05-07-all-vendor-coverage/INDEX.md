# All-Vendor Coverage Cycle — 2026-05-07

> **사용자 명시 (2026-05-07)**:
> "server-exporter는 본질적으로 모든 vendor / 모든 generation / 모든 host 지원 프로젝트. 사이트 검증 불가하더라도 코드 path는 모두 깔려야 함. lab 한계는 web sources로 보완. 한번에 모두 수행."

본 cycle 은 **메인 오케스트레이터 세션 (Session-0)** 이 ticket 만 작성.
실 작업은 **5 worker 세션** 에서 병렬 진행. 동기화는 본 INDEX + SESSION-HANDOFF + DEPENDENCIES 로.

---

## 사이트 검증 baseline (2026-05-07 cycle 시작 시점)

오늘 사이트 검증 결과 (commit `ec6dc7ff`):

| vendor | generation | 사이트 BMC | 검증 결과 |
|---|---|---|---|
| Dell | iDRAC10 | 5대 (10.100.15.27/28/31/33/34) | [PASS] |
| HPE | iLO7 | 1대 (10.50.11.231) | [PASS] |
| Lenovo | XCC3 | 1대 (10.50.11.232) | [PASS] |
| Cisco | UCS X-series | 1대 (10.100.15.2) | [PASS] |

→ **사이트 검증된 vendor × generation: 4개**. 나머지는 lab 부재 — web sources (rule 96 R1-A) 로 보강.

---

## 목적

server-exporter 가 **모든 vendor × 모든 generation × 모든 host** 지원하도록 코드 path 전수 보강. 9 vendor + 1 special (Superdome Flex) × N generation × 10 sections 매트릭스.

| # | 영역 | ticket | 책임 worker |
|---|---|---|---|
| **A** | Vault 임시 정책 (vendor 공장 기본 자격 추가) | M-A1~A6 (6) | W1 |
| **B** | Supermicro 6 generation 보강 | M-B1~B4 (4) | W1 |
| **C** | Huawei iBMC 보강 | M-C1~C3 (3) | W2 |
| **D** | Inspur ISBMC 보강 | M-D1~D2 (2) | W2 |
| **E** | Fujitsu iRMC 보강 | M-E1~E3 (3) | W3 |
| **F** | Quanta QCT 보강 | M-F1~F2 (2) | W3 |
| **G** | HPE Superdome Flex 보강 | M-G1~G2 (2) | W3 |
| **H** | 기존 4 vendor 미검증 generation 점검 | M-H1~H4 (4) | W4 |
| **I** | gather 10 sections × all vendor 변형 | M-I1~I5 (5) | W4 (~I3) + W5 (I4~I5) |
| **J** | OEM namespace 매핑 매트릭스 + Cisco vendor task 신설 | M-J1 (1) | W5 |
| **K** | adapter origin 주석 + EXTERNAL_CONTRACTS | M-K1~K2 (2) | W5 |
| **L** | catalog 갱신 (NEXT_ACTIONS / VENDOR_ADAPTERS / COMPATIBILITY / docs/13) | M-L1~L4 (4) | W5 |

총 **38 ticket** (M-A1 ~ M-L4).

---

## 사용자 confirm 답변 (2026-05-07)

| Q | 질문 | 답변 |
|---|---|---|
| Q1 | IBM/Oracle/NEC/Dell XR/Inspur Yitian in-scope | **모두 제외** — 9 vendor + Superdome Flex만 |
| Q2 | Supermicro 사이트 BMC 보유 | **0대** — lab 부재 처리 |
| Q3 | Huawei/Inspur/Fujitsu/Quanta lab 도입 timeline | **장기 (미정)** — NEXT_ACTIONS 우선순위는 코드 path 보장 우선 |
| Q4 | vault 임시 자격 정책 | **vendor 공장 기본 자격 추가** (Dell root/calvin / HPE admin/admin / Lenovo USERID/PASSW0RD / Supermicro ADMIN/ADMIN / Cisco admin/password / Huawei Administrator/Admin@9000 / Inspur admin/admin / Fujitsu admin/admin / Quanta admin/admin) |
| Q5 | worker 수 | **5 worker 권장** |
| Q6 | 우선순위 | **권장 순서 (A → B → C~G → H → I → J → K → L) + 사용자 승인 없이 한번에 모두 수행** |
| Q7 | schema 변경 발생 시 처리 | **schema 변경 0 (발생 시 즉시 사용자 confirm)** — 본 cycle Additive only 영역만 |

---

## 현재 상태

| 단계 | 상태 |
|---|---|
| Session-0 ticket 작성 | [DONE] (2026-05-07) |
| Session-1 ~ 5 worker 진행 | [DONE] (39/39 ticket — M-A1~A7 + M-B~L + A7-followup 모두 [DONE] 2026-05-11) |
| 통합 검증 (pytest / verify_*) | [DONE] (pytest 587/587 PASS / verify_harness_consistency PASS / verify_vendor_boundary PASS) |
| cycle 종료 (HARNESS-RETROSPECTIVE) | [DONE] (cycle 정식 종료 기록은 `docs/ai/NEXT_ACTIONS.md` "2026-05-11 cycle 2026-05-07-all-vendor-coverage Session-1" 절) |

> **cycle 종료**: 2026-05-11 — 39 ticket 모두 [DONE]. HARNESS-RETROSPECTIVE 별도 미작성 — 학습은 NEXT_ACTIONS + ADR/decision-log 에 흡수. 후속 작업은 lab 도입 의존 (NEXT_ACTIONS "lab 도입 후 별도 cycle 권장" 절).

- 마지막 commit (cycle 시작 시점): `ec6dc7ff` — schema/output_examples/ 신설 (실 장비 개더링 한글 주석본 10개)
- adapter: **28** (Supermicro X10 신설 시 +1 = 29 예상)
- vendor 정규화: **9** (Dell/HPE/Lenovo/Supermicro/Cisco/Huawei/Inspur/Fujitsu/Quanta) + Superdome Flex special
- vault: **5 vendor** (huawei/inspur/fujitsu/quanta 신설 시 +4 = 9)
- vendor OEM tasks: **4 vendor** (Cisco/Huawei/Inspur/Fujitsu/Quanta 신설 시 +5 = 9)

---

## 운영 모드

**5 worker 병렬 진행 + 자율 진행 권한 + 한번에 모두 수행 (사용자 명시 2026-05-07)**

→ 본 cycle 의 모든 worker 세션은 사용자 승인 없이 부가 작업 자율 진행 (rule 24 6 체크리스트 통과 후 [DONE]).

---

## cold-start 가이드 (worker 세션 처음 읽을 순서)

1. **본 INDEX.md** — cycle 전체 그림
2. **SESSION-HANDOFF.md** — 직전 세션 종료 시점 + 다음 세션 첫 지시
3. **DEPENDENCIES.md** — ticket 간 의존성
4. **SESSION-PROMPTS.md** — worker별 cold-start 진입 프롬프트
5. **COMPATIBILITY-MATRIX.md** — 9 vendor × N generation × 10 sections 매트릭스
6. **fixes/INDEX.md** — 38 ticket 분류 + 진행 상태
7. **fixes/M-X##.md** — 작업 spec 정본 (cold-start 6 절 형식)

---

## 티켓 구조

```
docs/ai/tickets/2026-05-07-all-vendor-coverage/
├── INDEX.md                    # 본 파일 — 진입점
├── SESSION-HANDOFF.md          # 세션 종료 시점 + 다음 세션 첫 지시
├── DEPENDENCIES.md             # 의존 그래프 + 진행 가능 ticket 식별
├── SESSION-PROMPTS.md          # 5 worker 세션별 cold-start 프롬프트
├── COMPATIBILITY-MATRIX.md     # 9 vendor × N generation × 10 sections (cycle 진입 baseline)
├── HARNESS-RETROSPECTIVE.md    # (cycle 종료 시 — 학습 추출)
└── fixes/
    ├── INDEX.md                # 38 ticket 분류 + 진행 상태
    ├── M-A1.md ~ M-A6.md       # Vault (6)
    ├── M-B1.md ~ M-B4.md       # Supermicro (4)
    ├── M-C1.md ~ M-C3.md       # Huawei (3)
    ├── M-D1.md ~ M-D2.md       # Inspur (2)
    ├── M-E1.md ~ M-E3.md       # Fujitsu (3)
    ├── M-F1.md ~ M-F2.md       # Quanta (2)
    ├── M-G1.md ~ M-G2.md       # Superdome Flex (2)
    ├── M-H1.md ~ M-H4.md       # 기존 4 vendor 미검증 (4)
    ├── M-I1.md ~ M-I5.md       # gather sections 변형 (5)
    ├── M-J1.md                 # OEM mapping (1)
    ├── M-K1.md ~ M-K2.md       # origin + EXTERNAL_CONTRACTS (2)
    └── M-L1.md ~ M-L4.md       # catalog 갱신 (4)
```

총 **38 ticket** (fixes/M-*.md).

---

## 결정 의존

### 본 cycle 사용자 confirm 답변에서 결정 완료

- vault 임시 자격 → vendor 공장 기본 자격 (Q4)
- in-scope vendor → 9 vendor + Superdome Flex (Q1)
- worker 수 / 우선순위 → 권장값 (Q5/Q6)
- schema 변경 → 0건 (Q7) — 발생 시 즉시 사용자 confirm

### 외부 의존 (lab 도입 시까지 보류)

- 모든 lab 부재 vendor 의 실 검증 (mock fixture + 정적 검증으로 본 cycle 종료)
- Round 검증 / docs/13_redfish-live-validation.md 갱신 (사이트 검증 4 vendor 만 [PASS] 표시)
- vault primary `infraops` 실 회전 검증 (mock 시뮬만 — 실 BMC 도입 후 별도 cycle)
- baseline_v1/{vendor}_baseline.json — lab 부재 vendor 는 SKIP (rule 13 R4)

---

## 사용자 명시 원칙 (본 cycle)

1. **Additive only** (rule 92 R2) — 사이트 검증 4 vendor × 1 generation 코드 path **변경 금지**. 신규 분기 추가만
2. **lab 한계 보완** — lab 부재 영역은 web sources (rule 96 R1-A 의무) 로 보강. vendor 공식 docs / DMTF spec / GitHub issue / 사용자 사이트 실측 4종 sources 중 1개 이상
3. **다른 worker 세션 작업** — 본 세션은 ticket 만. 실 코드 변경은 worker 세션 5개에서 진행
4. **상세 티켓화** — cold-start 가능 (다음 worker 컨텍스트 0 진입)
5. **누락 0** — 38 ticket 모두 cold-start 6 절 형식 (배경/현재/목표/영향/구현/검증)
6. **자율 진행** — 사용자 승인 없이 한번에 모두 수행 (Q6 명시)
7. **schema 변경 0** — Must/Nice/Skip 재분류 발생 시 즉시 사용자 confirm (rule 92 R5)

---

## Out of scope (본 cycle 변경 금지 — rule 92 R2)

- **사이트 PASS 4 vendor × 1 generation 코드 path** (Dell iDRAC10 / HPE iLO7 / Lenovo XCC3 / Cisco UCS X-series) — Additive only
- `schema/baseline_v1/{사이트_검증_vendor}_baseline.json` — rule 13 R4 (실장비 검증만 변경 가능)
- `schema/sections.yml` 또는 `schema/field_dictionary.yml` 버전 — rule 92 R5 (사용자 승인 필요)
- `Jenkinsfile*` cron 변경 — rule 80 R2
- `vault/redfish/{사이트_검증_vendor}.yml` 의 primary `infraops` 변경 — cycle 2026-05-06 F50 통일 유지
- `redfish-gather/library/redfish_gather.py` 의 사이트 검증된 path — Additive (신규 분기만 추가)

---

## 세션 간 동기화 프로토콜

### Worker 세션 진입 시 (cold-start)

```
1. INDEX.md 읽기 (본 파일)
2. SESSION-HANDOFF.md 읽기 — 직전 세션 종료 시점 확인
3. DEPENDENCIES.md 읽기 — 진행 가능 ticket 식별
4. fixes/INDEX.md 에서 [PENDING] + 의존성 통과 ticket 선택 (worker 컬럼 본인 본인 일치 확인)
5. 해당 ticket M-X##.md 읽고 작업 시작
6. ticket 상단 status 갱신: [PENDING] → [IN-PROGRESS]
7. SESSION-HANDOFF.md "현재 진행 중" 갱신
```

### Worker 세션 종료 시

```
1. ticket M-X##.md status 갱신: [IN-PROGRESS] → [DONE / BLOCKED:사유]
2. fixes/INDEX.md 진행 상태 표 갱신
3. SESSION-HANDOFF.md "마지막 commit / 시점 / 다음 세션 첫 지시" 갱신
4. commit 메시지 마커: `<type>: [M-X## DONE] <요약>` (rule 26 R7 / rule 90)
5. push (rule 93 R1+R4 — 본 cycle 자율 push)
```

### 충돌 방지 (rule 26 R3+R4)

- `git add .` / `git commit -a` **금지** — pathspec 만
- 공용 파일 동시 편집 금지 (다음 표 참조):

| 공용 파일 | 단독 worker |
|---|---|
| `common/vars/vendor_aliases.yml` | (변경 없음 — 9 vendor 모두 등록됨) |
| `redfish-gather/library/redfish_gather.py` | W5 (M-J1) |
| `schema/sections.yml`, `schema/field_dictionary.yml` | (본 cycle 변경 0 — Q7) |
| `vault/redfish/{vendor}.yml` | W1 (M-A1~A6) |
| `docs/ai/catalogs/EXTERNAL_CONTRACTS.md` | W5 (M-K2) |
| `docs/ai/catalogs/VENDOR_ADAPTERS.md` | W5 (M-L2) |
| `docs/ai/catalogs/COMPATIBILITY-MATRIX.md` | W5 (M-L3) |
| `docs/ai/NEXT_ACTIONS.md` | W5 (M-L1) |
| `docs/13_redfish-live-validation.md` | W5 (M-L4) |
| `adapters/redfish/{vendor}_*.yml` | vendor 영역 worker (W1=Supermicro / W2=Huawei,Inspur / W3=Fujitsu,Quanta,Superdome / W4=기존 4 vendor) |
| `redfish-gather/tasks/vendors/{vendor}/` | vendor 영역 worker (위와 동일 분배) |
| `tests/fixtures/redfish/{vendor}_*/` | vendor 영역 worker |

---

## 갱신 history

| 일시 | 누가 | 변경 |
|---|---|---|
| 2026-05-07 Session-0 | AI (cycle 시작) | 본 cycle ticket 38건 작성 + INDEX/SESSION-HANDOFF/DEPENDENCIES/SESSION-PROMPTS/COMPATIBILITY-MATRIX 초안 |

---

## 관련

- rule 13 R5 (envelope 13 필드 — 본 cycle 변경 0)
- rule 22 (Fragment 철학)
- rule 25 R7-A1 (사용자 실측 > spec — 사이트 검증 4 vendor 우선)
- rule 26 R10 (다중 worker 4 정본)
- rule 50 R2 (vendor 추가 9단계 + 단계 10 lab 부재)
- rule 60 (vault encrypt 의무 — 본 cycle 신설 4 vault encrypt)
- rule 80 R1-A (Jenkins 4-Stage)
- rule 91 R1 (task-impact-preview)
- rule 92 R2 (Additive only)
- rule 92 R5 (schema 변경 사용자 명시)
- rule 93 R1+R4+R7 (자율 push + github/gitlab 동시)
- rule 96 R1+R1-A+R1-B+R1-C (외부 계약 origin / web sources / envelope shape / NEXT_ACTIONS 자동 등재)
- skill: write-cold-start-ticket / cycle-orchestrator / add-vendor-no-lab
- skill: handoff-driven-implementation (worker 세션 진입 메타)
