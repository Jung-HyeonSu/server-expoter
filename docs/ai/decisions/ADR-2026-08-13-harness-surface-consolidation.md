# ADR 2026-08-13 — 하네스 표면 통합과 rule 70 보존 기준 변경

- 상태: Accepted
- 결정: 사용자 (2026-08-13 대화)
- 작성: AI (Claude Code)
- 관련 rule: 70 R5 / R6 / R8, 00 (표면 카운트), 13, 40, 41

## 컨텍스트 (Why)

전수 감사에서 하네스가 스스로 부풀었다는 게 드러났다. 세 가지가 겹쳤다.

같은 일을 하는 표면이 이름만 다르게 여러 벌 있었다. schema 리뷰어 3편은
전부 rule 13 을 근거로 삼고 envelope 필드와 빌더 패턴을 중복 검사하면서 서로를
"자가 검수 금지" 대상으로 순환 지목했다. A 는 B 에게, B 는 C 에게,
C 는 A 에게 위임하라고 적혀 있으니 어느 쪽을 불러도 검수가 닫히지 않는다.
refactor worker 4편은 절차가 글자까지 같고 대상 디렉터리만 달랐다. mermaid 는
스킬 4편이 전부 rule 41 을 옮겨 적은 것이었다.

표면이 나뉘어 있으니 한 곳을 고쳐도 나머지가 낡은 채 남았다. 중복이 오류를
숨겼다. 실제로 세 곳을 찾았다.

| 표면 | 낡은 내용 | 사실 |
|---|---|---|
| `output-schema-reviewer` | "OUTPUT 태스크 **prefix** 식별" | callback 은 **완전일치** 비교다 (`json_only.py:108`). prefix 로 알고 검수하면 `OUTPUT: 결과 출력` 같은 이름을 통과시킨다. 그러면 호출자가 빈 응답을 받는다 |
| `jenkins-refactor-worker` | "Jenkinsfile **3종**" | cycle-015 에서 `Jenkinsfile_grafana` 가 제거돼 2종이다 |
| mermaid 스킬 | `Precheck (TCP 도달 → 프로토콜 → 인증 (ICMP 미사용))` | 1차 치환이 만든 중첩 괄호. 읽히지 않는다 |

**rule 70 R5 가 "남긴다"고 지정한 유형이 실제로는 안 읽혔다.**
R5 는 "다음 작업에서 AI 가 참조하면 도움이 되는가"를 기준으로 제시한다.
정작 그 표에 `실행 패턴 사례`·`Round 검증 결과` 같은 유형을 통째로 "남김"에
넣어 두어 기준이 아니라 면제 목록처럼 작동했다.

## 결정 (What)

### 1. agent 10편을 5편으로 흡수

| 없앤 것 | 간 곳 |
|---|---|
| `schema-mapping-reviewer`, `output-schema-reviewer` | `schema-reviewer` (분류 / 정합 / 형식 3축) |
| `gather-refactor-worker`, `jenkins-refactor-worker`, `output-schema-refactor-worker`, `nonfunctional-refactor-worker` | `refactor-worker` (4 레인 표) |
| `baseline-validation-worker`, `regression-planner` | `qa-regression-worker` (선정 → 실행 → baseline 검증) |
| `feature-flowchart-designer` | `flow-visualizer` |
| `impact-brief-writer` | `change-impact-analyst` (분석이 브리핑까지 낸다) |

56편 → 47편. 흡수한 쪽 본문에 각 축·레인의 고유 규칙을 그대로 옮겼다. 합치면서
버린 검증 항목은 없다. 위에 적은 낡은 내용 3건은 옮기면서 고쳤다.

### 2. skill 3편을 1편으로 흡수

`write-feature-flowchart`, `visualize-flow`, `update-flowchart-after-change`
→ `mermaid-visualization` (상황 1/2/3 절). 50편 → 47편.

### 3. rule 70 R5 / R6 을 기준으로 되돌린다

유형 표를 면제 목록으로 쓰지 않는다. 유형은 판정을 도우는 예시이고 판정은
언제나 "지금 코드 기준으로 다음 작업에 쓰이는가" 하나다. 그 결과
이번에 archive 39편, 완료된 ticket 8편, 조사 전용 contract 4편,
upstream 문서 사본 9편, 에이전트 프로세스 기록 12편을 지웠다. 종전 R5 표라면
"실행 패턴 사례"·"Round 검증 결과"로 분류돼 남았을 것들이다.

### 4. 표면 카운트 갱신

`rules 28 / skills 47 / agents 47 / policies 7`. rule 70 R8 trigger 2 에 해당해
이 ADR 을 쓴다.

## 결과 (Impact)

- 하네스 마크다운 180편 → 168편, 그중 죽은 표면 0
- 이름으로 도달 불가한 skill·agent 0 (종전 skill 5 / agent 9 가 고아였다)
- 모든 참조 갱신 46 + 15 = 61개 파일. `verify_harness_consistency.py` 확장판이
  맨 이름 참조까지 보므로 남은 죽은 이름은 CI 에서 잡힌다
- 검수 순환 해소 — 합친 에이전트는 축이 다른 에이전트에게만 위임한다

## 대안 비교 (Considered)

**(A) 그대로 둔다.** 이름이 많으면 고르기 쉽다는 논리다. 실제로는 반대였다.
같은 일을 하는 이름이 3개면 어느 걸 부를지 판단 비용이 생기고 셋 중 하나만
고쳐지면서 낡은 둘이 남는다. 위 표의 오류 3건이 그 결과다. 기각한다.

**(B) 별칭만 만든다.** 한 파일을 정본으로 두고 나머지는 "여기를 보라"로 축약.
기각. 표면 수는 그대로라 카운트·검증기·선택 비용이 줄지 않는다. 껍데기가
남으면 다음 작업자가 또 채운다.

**(C) 더 크게 합친다 (리뷰어 전체를 1편으로).** 기각 — 리뷰어는 축이 다르면
보는 파일이 다르다. `vendor-boundary-guardian` 과 `schema-reviewer` 를 합치면
한 번 호출에 관련 없는 검사를 다 돌게 된다. 축이 같은 것만 합쳤다.
