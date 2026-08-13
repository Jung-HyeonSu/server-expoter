# ADR-2026-05-06-rule13-r7-docs20-sync

## 상태
Accepted (2026-05-06)

## 컨텍스트 (Why)

cycle 2026-05-06 multi-session-compatibility 의 M-A 영역 (status 로직 사용자 의심) 분석 중 발견한 패턴:

### 사용자 의심 발생 사례

> "errors 에는 로그가 찍히는데 success로 빠지는경우가 있음 이것은 왜이런지 확인해줘 의도된건지" (사용자 명시 2026-05-06)

→ M-A1 분석 결과: **의도된 동작** (시나리오 B — errors[] warnings emit 시 status=success 정상). 단 **build_status.yml 의 의도 주석 부재** 로 사용자가 의심 발생.

### 호출자 계약 안정성 위험

envelope 13 필드 / sections 10 / field_dictionary 65 의 의미는 다음 4 정본에 분산:
1. `common/tasks/normalize/build_output.yml` (envelope 정본)
2. `schema/sections.yml` (sections 정의)
3. `schema/field_dictionary.yml` (Must/Nice/Skip 분류)
4. `common/tasks/normalize/build_status.yml` (status 판정 — M-A3 정본)

호출자 시스템 (Jenkins downstream / 모니터링 / 외부 통합) 은 정본 코드를 직접 읽지 않음. 통합 reference 부재로:
- envelope 키의 의미 / status 시나리오 모름 → 사용자 의심 발생
- 정본 변경 (예: cycle 2026-05-01 PowerSubsystem fallback) 시 호출자 측 파싱 영향 추적 불가
- M-F1 docs/contract/03-fields.md 신설 (625 라인) 로 통합 reference 확보

### M-G1 학습 (HARNESS-RETROSPECTIVE.md 학습 8)

> 정본 docs/20 신설의 호출자 계약 효과:
> "호출자 계약 안정성을 위해 envelope 의미 docs 가 critical. 정본 코드 변경 시 docs 동기화 필요."
> 보강 후보: rule 13 R9 (다음 추가): envelope 정본 변경 시 docs/20 갱신 의무

→ rule 본문에 추가 의무화 결정.

## 결정 (What)

### 1. rule 13 R7 신설 (M-G2 cycle 2026-05-06)

`.claude/rules/13-output-schema-fields.md` 에 R7 절 추가:

> **R7. envelope 정본 변경 시 docs/20 갱신 의무**
>
> - **Default**: 다음 정본 변경 시 `docs/contract/03-fields.md` 동기화 갱신 의무
>   - `common/tasks/normalize/build_output.yml` (envelope 13 필드 정본)
>   - `schema/sections.yml` (sections 10 정의)
>   - `schema/field_dictionary.yml` (Must/Nice/Skip 분류)
>   - `common/tasks/normalize/build_status.yml` (status 판정 규칙 — M-A3 정본)
> - **Allowed**: 변경이 cosmetic (주석 / 들여쓰기) 시 docs/20 갱신 skip 가능. 단 commit 메시지 명시
> - **Forbidden**: envelope 13 필드 / sections 10 / field_dictionary 65 의 의미 변경 + docs/20 갱신 누락

### 2. 금지 패턴 + 리뷰 포인트 추가

```
## 금지 패턴
- envelope 정본 변경 + docs/20 갱신 누락 — R7

## 리뷰 포인트
- [ ] envelope 정본 변경 시 docs/20 동기화 (R7)
```

### 3. 자동 검증 hook 후속 작업

- `pre_commit_docs20_sync_check.py` (신규 — M-G1 hook 후보 5건 중 1)
- 본 ADR 시점 advisory 권장. 안정화 후 blocking 격상 검토.

## 결과 (Impact)

### 즉시 영향

- `.claude/rules/13-output-schema-fields.md` 본문 변경 (R7 절 추가) — **rule 본문 의미 변경 (rule 70 R8 trigger 1)**
- 표면 카운트 변경 없음 (rules:28 유지)
- 보호 경로 정책 변경 없음

### 운영 영향

- envelope 정본 변경 PR 의 review 항목에 R7 추가 (4개 정본 변경 시 docs/20 동기화 검증)
- 호출자 시스템 통합 안정성 향상 — docs/20 가 정본 변경에 따라가도록 강제
- 다음 세션 / AI 가 envelope 의미 파악 시 docs/20 우선 참조 보장

### 리스크

- **(LOW)** rule 13 R7 위반 시 호출자 시스템 stale reference 사용 → 사용자 의심 재발 가능
- **(LOW)** docs/20 갱신 effort 추가 — cosmetic Allowed 영역으로 완화

### 표면 카운트 변경 없음

- rules: 28 (유지)
- skills: 48 (유지)
- agents: 59 (유지)
- policies: 10 (유지)

## 대안 비교 (Considered)

### 대안 1: 본 결정 — rule 13 R7 신설 (선택)

- **장점**: 정본 변경 시 docs/20 동기화 의무화 → 호출자 계약 안정성. M-A 사용자 의심 재발 차단
- **단점**: PR review 항목 1개 추가
- **선택 사유**: 호출자 신뢰성 > review effort. cycle 2026-05-06 M-G1 학습 직접 반영

### 대안 2: 자동 hook 만 도입 (rule 본문 추가 없이)

- **장점**: rule 본문 변경 없음 → ADR 의무 회피
- **단점**: hook 우회 시 검증 부재 (사용자가 hook bypass 시 정합 깨짐)
- **거절 사유**: rule 본문 + hook 이중 안전망 필요. 본 결정 1과 hook 후속 작업 양립

### 대안 3: docs/20 자동 생성 (정본 코드에서 추출)

- **장점**: 동기화 영구 보장
- **단점**: 자동 생성 도구 개발 비용 + 도구 자체 복잡성 증가. docs/20 의 채널별 비교 / 정규화 규칙 차이 같은 메타 의미 자동 추출 어려움
- **거절 사유**: 본 cycle 범위 외. 향후 별도 cycle 검토 (학습 후 도구화)

## 갱신 history

| 일시 | 변경 |
|---|---|
| 2026-05-06 | M-G2 — rule 13 R7 신설 + 본 ADR 신규 |
