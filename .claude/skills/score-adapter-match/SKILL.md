---
name: score-adapter-match
description: adapter_loader가 어떤 adapter를 어떤 점수로 선택했는지 디버깅. priority × 1000 + specificity × 10 + match_score 공식 분석. 사용자가 "왜 dell_idrac9 선택 안 됐어?", "adapter 점수 확인", "score-adapter-match" 등 요청 시. - adapter 추가 후 의도된 adapter가 매칭 안 되거나 / 다른 adapter가 우선되는 의심 / 새 펌웨어 시 분기 디버깅
---

# score-adapter-match

## 목적

server-exporter의 adapter_loader (lookup plugin)가 vendor + 펌웨어에 따라 어떤 adapter를 선택했는지 점수 계산을 추적. 의도와 다른 adapter가 선택되는 경우 원인 파악.

## 점수 공식 (rule 12 R2)

```
score = priority × 1000 + specificity × 10 + match_score
```

- **priority**: 0 (generic) / 10 (기본 vendor) / 50-100 (세대별)
- **specificity**: model_patterns 매칭 정확도
- **match_score**: 추가 조건 (firmware_pattern / capabilities)

높을수록 우선. 동률 시 정렬 결과 불확정 → 의심 패턴 (rule 95 R1 #4).

## 입력

- target_ip 또는 ServiceRoot 응답 (Manufacturer / Model / 펌웨어)
- 채널: redfish / os / esxi

## 출력

```markdown
## Adapter Match 점수표

대상: 10.x.x.1 (Dell PowerEdge R7525, iDRAC9 6.10.30.20)

| Adapter | priority | specificity | match | 합계 | 선택 |
|---|---|---|---|---|---|
| dell_idrac9.yml | 100 | 30 (model_patterns | 5 | 100305 | ★ |
| dell_idrac8.yml | 50 | 0 | 0 | 50000 | |
| dell_idrac.yml | 10 | 0 | 0 | 10000 | |
| redfish_generic.yml | 0 | 0 | 0 | 0 | |

선택: `dell_idrac9.yml` (100305)

근거:
- priority 100 (세대별 idrac9)
- model_patterns "PowerEdge R7*" 매치 → specificity 30
- firmware "6.10.30.20" 6.x 패턴 매치 → match 5
```

## 절차

1. **adapter_loader 호출** (수동 시뮬레이션):
   ```bash
   ansible-playbook redfish-gather/site.yml \
     -i redfish-gather/inventory.sh \
     -e "target_ip=10.x.x.1" -vvv 2>&1 | grep -i "adapter"
   ```
2. **각 adapter 점수 추출** (lookup plugin 디버그 출력)
3. **표 정리** + 선택된 adapter 강조
4. **의심 발견 시**:
   - priority 충돌 (rule 12 R2 위반)
   - model_patterns이 너무 광범위 / 좁음
   - firmware_pattern 누락
5. **수정 방향 제안**:
   - priority 조정
   - match.model_patterns 정밀화
   - generic fallback 우선순위 확인

## server-exporter 도메인 적용

- 영향 채널: 주로 redfish (벤더 분기 가장 많음)
- 영향 vendor: 디버깅 대상
- 영향 schema: 없음 (선택만)

## 실패 / 오탐 처리

- adapter_loader가 fallback 없이 매치 0건 → generic adapter 부재 (rule 12 R5)
- 점수 동률 → adapter YAML에 specificity 추가 권장
- 의도와 다른 adapter 선택 → priority 또는 match 조정 PR

## 적용 rule / 관련

- **rule 12** (adapter-vendor-boundary) — 점수 공식 정본
- rule 95 R1 #4 (점수 동률 의심 패턴)
- skill: `add-new-vendor`, `vendor-change-impact`
- agent: `adapter-author`, `adapter-boundary-reviewer`
- 정본 reference: `docs/develop/03-adapter-system.md`, `module_utils/adapter_common.py`

## 디버깅 명령

```bash
# 전체 vvv 디버그
ansible-playbook redfish-gather/site.yml -i ... -e "target_ip=..." -vvv 2>&1 | tee /tmp/adapter.log
grep -E "adapter_loader|score|priority|specificity" /tmp/adapter.log

# 특정 adapter만 체크
python -c "
import yaml
a = yaml.safe_load(open('adapters/redfish/dell_idrac9.yml'))
print('priority:', a.get('priority'))
print('match:', a.get('match'))
"
```
