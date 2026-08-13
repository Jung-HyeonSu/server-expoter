---
name: verify-json-output
description: callback_plugins/json_only.py가 출력하는 JSON envelope 13 필드 정합 검증. server-exporter는 UI 없음 -> 호출자 시스템은 stdout JSON 파싱. 사용자가 "envelope 검증", "callback 출력 형식 맞아?", "JSON 출력 확인" 등 요청 시 또는 callback_plugins / build_*.yml 변경 후. - callback_plugins/json_only.py 수정 / build_output.yml 수정 / envelope 형식 변경 의심 / 호출자 시스템 호환성 확인
---

# verify-json-output

## 목적

server-exporter 출력 envelope의 호출자 호환성 검증. UI 없음 — JSON envelope이 호출자 계약면.

## 입력

- 검증 대상: callback_plugins/json_only.py / build_output.yml / 또는 실제 ansible 실행 결과
- (선택) 호출자 시스템 contract spec

## 검증 항목

1. **envelope 13 필드 존재** (rule 20 R1):
   - status: "success" | "partial" | "failed"
   - sections: list of strings (section 이름)
   - data: dict (섹션별 데이터)
   - errors: list of error dicts
   - meta: dict (loc / target_type / vendor / host_id / run_id)
   - diagnosis: dict (precheck / gather_mode / details)

2. **OUTPUT 태스크 prefix** (rule 20 R3): task name이 "OUTPUT"으로 시작

3. **Jinja2 정합성**: build_output.yml의 모든 변수가 정의됨

4. **status 일관성**:
   - 모든 섹션 성공 → "success"
   - 일부 실패 / 일부 미수집 → "partial"
   - precheck 실패 / 인증 실패 → "failed"

5. **errors 형식**:
   ```json
   {"section": "cpu", "stage": "collect", "message": "...", "details": {...}}
   ```

6. **meta 필수 필드**: loc / target_type / vendor / host_id

## 절차

1. **callback_plugins/json_only.py Read** + parse 로직 확인
2. **build_output.yml Read** + envelope 조립 변수 확인
3. **모든 build_*.yml 호출 순서** (init_fragments → merge_fragment → build_sections → build_status → build_errors → build_meta → build_correlation → build_output)
4. **dry-run** (가능 시):
   ```bash
   ansible-playbook redfish-gather/site.yml -i ... -e "target_ip=..." 2>&1 | tail -50
   ```
5. **결과 envelope JSON parse** + 6 필드 검증
6. **호출자 contract 비교** (선택): 호출자가 알려준 spec과 envelope 일치
7. **결과 보고**

## 출력

```markdown
## JSON 출력 검증 결과

### envelope 13 필드: PASS
- status / sections / data / errors / meta / diagnosis 모두 존재

### Jinja2 정합성: PASS
- build_output.yml 변수 누락 0건

### 의심 발견
- meta.run_id 필드가 callback에서 누락 (build_meta.yml:42 변수 정의 필요)

### 권고
- build_meta.yml 수정 후 재검증
- 호출자 시스템 contract 영향 확인 (rule 96)
```

## 적용 rule / 관련

- **rule 20** (output-json-callback) 정본
- rule 13 R5 (envelope 13 필드)
- rule 31 (callback URL 무결성)
- skill: `update-output-schema-evidence`, `task-impact-preview`
- agent: `output-schema-reviewer`
- script: `scripts/ai/hooks/post_edit_jinja_check.py`
