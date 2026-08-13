# 요구사항 분석 (Requirement Analysis)

> `analyze-new-requirement` skill 출력 템플릿.

## 요청

> {원문 사용자 요청 인용}

## 1. 의도 / 목표 (3가지)

(a) {사용자 flow}
(b) {핵심 결정사항}
(c) {기존 시스템 제약}

## 2. 영향 범위

| 영역 | 변경 / 영향 | 비고 |
|---|---|---|
| 채널 (os/esxi/redfish) | | |
| 어댑터 (vendor) | | |
| Schema (sections / field_dictionary / baseline) | | |
| Vault | | |
| Jenkinsfile (3종) | | |
| 외부 시스템 계약 (Redfish path 등) | | |
| 정본 문서 (CLAUDE / GUIDE / REQUIREMENTS / `docs/` 문서) | | |

## 3. 변경 대상 파일 (실측)

```
$ grep -rn "<keyword>" {channels/dirs}
{실측 결과}
```

## 4. 테스트 범위

- 단위: {pytest 파일 list}
- 통합: {ansible-playbook --syntax-check + redfish-probe}
- 회귀: {baseline_v1 / fixtures}
- 실장비: {Round 검증 필요 여부}

## 5. 리스크 top 3

1. **{리스크}** ({HIGH/MED/LOW}) — {근거}
2. ...
3. ...

## 6. 진행 확인 (사용자 선택지)

- (A) {옵션 A}
- (B) {옵션 B}
- (C) 취소
