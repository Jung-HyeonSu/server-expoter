# Harness Feedback Loop — server-exporter

> 사용자 피드백 → rule / skill / agent / policy 갱신 흐름.

## 피드백 진입 경로

| 출처 | 처리 |
|---|---|
| 사용자 chat 피드백 ("이렇게 해줘", "이건 그만") | docs/ai/tickets/<날짜>-<주제>.md 기록 → cycle 일환으로 정리 |
| FAILURE_PATTERNS.md append (사고 후) | rule 95 R1 의심 패턴 추가 검토 |
| CONVENTION_DRIFT.md (drift 발견) | 마이그레이션 계획 (rule 92 R2) |
| Round 검증 결과 (tests/evidence/) | adapter origin 주석 / baseline 갱신 (rule 96 R1) |
| post_merge_incoming_review 보고 | docs/ai/incoming-review/<날짜>-<sha>.md 후속 PR |
| harness-cycle observer 결과 | architect 명세 → 정식 cycle |

## 피드백 변환 (Tier 분류)

| 피드백 | Tier |
|---|---|
| 어휘 치환 (예: "고객사" → "벤더") | 1 (자동) |
| catalogs 갱신 (VENDOR_ADAPTERS / SCHEMA_FIELDS / EXTERNAL_CONTRACTS) | 1 |
| rule 어휘 치환 / 풀이 보강 | 2 (governor 심사) |
| skill / agent 신규 추가 | 2 |
| 새 정책 분류 (Tier 3 후보) | 3 (사용자만) |

## 사고 → rule 추가 (예시)

```
1. 사고 발생 (예: 잘못된 baseline 회귀)
2. FAILURE_PATTERNS.md append (해당 카테고리)
3. observer가 다음 cycle에 검출
4. architect가 관련 rule 보강 명세 (예: rule 13 / 22 / 92)
5. reviewer / governor 심사
6. updater 적용 → 해당 rule에 새 R 추가
7. verifier 검증
8. cycle 로그 기록
```

(cycle-011: 본 예시는 rule 60 vault 누설을 예로 들었으나 rule 60 자체 해제됨. 도메인별 rule로 일반화)

## 정기 cycle 주기

운영 정책 결정 필요. 후보:
- 매주 정기 (현재 미설정)
- 사고 대응 (즉시)
- 사용자 명시 요청 (수동)

## 관련

- rule 28 (empirical-verification-lifecycle)
- rule 70 (docs-and-evidence-policy)
- skill: harness-cycle, measure-reality-snapshot
- catalog: FAILURE_PATTERNS.md, CONVENTION_DRIFT.md
