---
name: review-adapter-change
description: adapters/{redfish,os,esxi}/*.yml 변경을 점수 / metadata / OEM 분기 / 영향 vendor 4축으로 리뷰. 사용자가 "adapter 리뷰", "이 YAML 변경 봐줘", "adapter score 검토" 등 요청 시. - adapter YAML 추가/수정 후 / 새 vendor 추가 / OEM tasks 변경
---

# review-adapter-change

## 목적

adapter YAML 변경 전문 리뷰. server-exporter의 adapter는 vendor 분기 메타 정본 (점수 / capabilities / collect / normalize 4 키).

## 검증 항목

1. **점수 공식 일관성** (rule 12 R2):
   - priority가 같은 vendor 다른 generation과 역전 없음
   - specificity가 model_patterns 정확도 반영
   - generic fallback (priority=0) 별도 존재

2. **metadata origin 주석** (rule 96 R1):
   - vendor / firmware / tested_against / oem_path 명시
   - 마지막 동기화 일자

3. **match 조건**:
   - manufacturer + model_patterns + (선택) firmware_patterns
   - 너무 광범위 (다른 vendor 매치) / 너무 좁음 (실 host 미매치) 검토

4. **capabilities**:
   - 펌웨어/모델별 endpoint 지원 여부 명시
   - server-exporter 표준 + OEM 분기

5. **collect / normalize 경로**:
   - standard / standard+oem / oem_only 중 하나
   - oem_tasks 경로가 실제 존재

6. **새 OEM tasks** (선택):
   - rule 11 (gather-output-boundary) — fragment 침범 없음
   - rule 22 (fragment-philosophy) 준수

## 입력

- 변경 adapter YAML 파일 list

## 출력

```markdown
## Adapter 리뷰 — adapters/redfish/dell_idrac9.yml

### 점수 일관성: PASS
- priority 100 > dell_idrac8.yml 50 > dell_idrac.yml 10 (역전 없음)

### metadata 주석: WARN
- tested_against: "5.x, 6.x" — 7.x 미반영 (probe 권장)

### match 조건: PASS
- manufacturer ["Dell Inc.", "Dell EMC"]
- model_patterns ["PowerEdge R7*", "PowerEdge R6*"]

### capabilities: PASS

### collect / normalize: PASS
- strategy: standard+oem
- oem_tasks: redfish-gather/tasks/vendors/dell/collect_oem.yml ✓

### 권고
- probe-redfish-vendor로 7.x 검증 + tested_against 갱신 (rule 96 R1)
```

## 적용 rule / 관련

- **rule 12** (adapter-vendor-boundary) 정본
- rule 96 R1 (origin 주석)
- rule 11 (gather-output-boundary, OEM tasks)
- skill: `score-adapter-match`, `probe-redfish-vendor`, `update-vendor-baseline`
- agent: `adapter-author`, `adapter-boundary-reviewer`, `schema-mapping-reviewer`
- 정본: `docs/develop/03-adapter-system.md`
