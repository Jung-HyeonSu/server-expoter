---
name: verify-adapter-boundary
description: common / 3-channel 코드에 vendor 이름 하드코딩 검출 (rule 12 R1). 사용자가 "벤더 경계 검증", "이 변경 boundary 위반?", "verify boundary" 등 요청 시. - 코드 변경 후 / 새 vendor 추가 후 / PR 머지 전
---

# verify-adapter-boundary

## 목적

`scripts/ai/verify_vendor_boundary.py`를 사용해 common / 3-channel gather 코드에 vendor 이름 하드코딩 0건 검증. rule 12 R1 자동 검출.

## 입력

- (선택) 변경 파일 list 또는 전체 스캔
- 검사 디렉터리: common / os-gather / esxi-gather / redfish-gather

## 출력

```markdown
## Adapter 경계 검증

### 검사 대상 6 영역
- common/library/, common/tasks/, common/vars/
- os-gather/, esxi-gather/, redfish-gather/

### 결과: PASS (위반 0건)
또는

### 위반 N건

| 파일 | 라인 | 위반 vendor 이름 |
|---|---|---|
| redfish-gather/library/redfish_gather.py | 152 | "Dell" |
| common/library/precheck_bundle.py | 88 | "iDRAC" |

### 권고
- redfish_gather.py:152 — "Dell" 분기를 adapter capabilities로 이동
- precheck_bundle.py:88 — vendor-aliases.yml 정규화 메타로 대체
```

## 절차

1. **verify_vendor_boundary.py 실행**:
   ```bash
   python scripts/ai/verify_vendor_boundary.py
   ```
2. **결과 분류**:
   - 정상 분기 (vendor_aliases.yml 매핑 / adapter YAML metadata 참조) → 무시
   - 하드코딩 분기 → 위반
3. **각 위반에 대한 수정 방향**:
   - vendor 분기를 adapter YAML capabilities로 이동
   - vendor 이름 비교를 adapter score 기반 분기로 변경
4. **--strict 모드**: comment 안의 vendor 이름도 위반 (보통 advisory)

## 자동 호출 시점

- 코드 변경 후 (post_edit_hint.py 권고)
- (cycle-011: pre_commit_policy.py 제거됨 — verify_vendor_boundary 단독 호출)
- review-existing-code의 vendor_boundary 축

## 적용 rule / 관련

- **rule 12** (adapter-vendor-boundary) R1 정본
- rule 50 R5 (vendor 경계 정책)
- skill: `review-existing-code`, `vendor-change-impact`
- agent: `vendor-boundary-guardian`, `adapter-boundary-reviewer`
- script: `scripts/ai/verify_vendor_boundary.py`
