# Human Docs Overhaul Cycle — 2026-05-06

> **사용자 명시 (2026-05-06)**:
> "ai가 읽지않는 문서는 사람이 읽기 편하고, 이해하기 쉽게 만들어주세요. 그리고 루트밑에 파일들도 업데이트해주세요. (예를들어 스키파 폴더내의 파일) 모든 파일 진행해주세요. 먼저 계획하고. 한세션 내에서 모두 진행하세요."
>
> **사용자 후속 (2026-05-06)**:
> "아니다 모두 업데이트되지않았다 더 딥하게 티켓으로만들어서 모두 변경해라"

본 cycle은 **단일 세션 (Session-0)** 이 ticket 작성 + 실행 모두 수행하는 모드.
사람용 문서 32종을 표면 도입부 추가가 아닌 **본문 전반 재구성** 으로 개편.

---

## 목적

server-exporter 의 사람용 문서 (호출자 / 운영자 / 개발자 / 검증 담당) 가 다음 기준을 모두 만족하도록 본문을 재작성:

1. **첫 문단 도입부** — 누가 / 언제 / 왜 보는지 명확
2. **본문 구조** — "무엇을 / 어떻게 / 왜 / 예시 / 트러블슈팅 / 다음 단계" 의 일관 흐름
3. **약어 풀어쓰기** — BMC / iDRAC / iLO / XCC / WinRM / WMI / DMI 등 첫 등장 시 풀이
4. **내부 jargon 제거** — cycle / Round / P0 / M-A / commit hash 같은 작업 흔적은 본문에서 제거 (필요 시 "이력" 푸터로)
5. **표 / 다이어그램 / 예시** — 의미 모호한 표는 컬럼 의미 보강, 코드 예시 한 줄 설명 추가
6. **상태 태그** — 이모지 대신 ASCII (`[PASS]/[FAIL]/[INFO]/[WARN]/[CRIT]`)
7. **Cross-reference** — 다른 문서로 보낼 때 정확한 절 번호까지 명시

| # | 분류 | 작업 |
|---|---|---|
| H-A | 루트 2종 | README, REQUIREMENTS 딥 리라이트 |
| H-B | 운영 가이드 5종 | docs/01~05 |
| H-C | 아키텍처 가이드 7종 | docs/06~12 |
| H-D | 검증·결정·스키마 9종 | docs/13~22 |
| H-E | schema YAML 6종 | sections.yml, field_dictionary.yml, fields/*.yml |
| H-F | 서브 README 5종 | schema/baseline_v1/, tests/fixtures/, tests/inventory/, tests/reference/, tests/e2e_browser/ |

총 34 파일 (32 docs + 2 schema yaml header만).

---

## 제외 (AI 전용)

| 영역 | 제외 사유 |
|---|---|
| `CLAUDE.md` | AI 진입점 — 본 cycle 범위 외 |
| `GUIDE_FOR_AI.md` | AI 가이드 — 본 cycle 범위 외 |
| `.claude/**` | AI rules / skills / agents / policy |
| `docs/ai/**` | AI 카탈로그 / cycle 자료 |

---

## 운영 모드

**단일 세션 + 즉시 실행**: ticket 작성 → 즉시 본문 재작성 → 다음 ticket.
사용자 명시 "한 세션 내에서 모두 진행".

---

## cold-start 가이드

다음 세션이 본 cycle 을 이어받을 때 읽을 순서:

1. 본 INDEX.md
2. SESSION-HANDOFF.md (직전 세션 종료 시점)
3. fixes/INDEX.md (티켓 분류 + 진행 상태)
4. 착수할 ticket 본문 (fixes/H-X#.md)

---

## 티켓 구조

각 ticket 파일은 다음 6 절을 갖습니다.

| 절 | 내용 |
|---|---|
| 사용자 의도 | 본 cycle 사용자 명시 인용 |
| 작업 범위 | 영향 파일 / 영향 독자 / 함께 바뀌는 것 |
| 변경 항목 | 본문 재작성 요구사항 list |
| 검증 | YAML syntax / link 깨짐 / 약어 풀이 일관성 |
| 의존성 | 다른 ticket 과의 선후 |
| 진행 상태 | [DONE] / [WIP] / [PENDING] |

---

## 진행 상태

| 분류 | 티켓 수 | 상태 |
|---|---|---|
| H-A | 2 | [DONE] |
| H-B | 5 | [DONE] |
| H-C | 7 | [DONE] |
| H-D | 9 | [DONE] |
| H-E | 6 | [DONE] |
| H-F | 5 | [DONE] |
| **합계** | **34** | **[DONE]** |

cycle 회고는 `HARNESS-RETROSPECTIVE.md` 참조.
