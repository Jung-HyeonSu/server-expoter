---
name: capture-site-fixture
description: 사용자 사이트 사고 환경 (HPE Gen12 / Lenovo XCC3 / Dell iDRAC8 / Cisco CIMC 등) 의 fixture를 캡처해 회귀 회피. cycle 2026-05-01 학습 — 사이트 사고 fixture 부재로 다음 reverse regression 위험. 사이트 envelope / probe 결과 / 펌웨어 응답을 tests/fixtures/redfish/{vendor}_{firmware}/ 에 저장 + tests/evidence/<날짜>-<vendor>.md 작성. 사용자가 "사이트 fixture 캡처", "사고 재현 입력 저장" 요청 시.
---

# capture-site-fixture

## 목적

사용자 사이트에서 발생한 호환성 사고의 입력 (raw 응답 / envelope) 을 fixture로 보존. 다음 reverse regression 또는 같은 사고 재발 시 회귀 차단.

## 호출 시점

- 사용자 사이트에서 호환성 사고 발생 (envelope errors / 미지원 / 응답 형식 차이)
- hotfix 적용 후 본 fix 가 다른 사이트 회귀 안 일으키는지 검증 필요
- 신 펌웨어 / 신 모델 / 신 vendor 응답 발견

## 입력

- vendor (dell / hpe / lenovo / supermicro / cisco / huawei / ...)
- 펌웨어 버전 (예: "iLO6 1.55", "XCC3 1.17.0", "iDRAC9 5.10.x")
- 사고 envelope (사용자 console log 또는 callback 페이로드)
- 가능하면 raw probe 결과 (probe_redfish.py 출력)

## 출력

```
tests/fixtures/redfish/{vendor}_{firmware_id}/
├── service_root.json         # /redfish/v1/
├── chassis.json              # /redfish/v1/Chassis/{id}
├── system.json               # /redfish/v1/Systems/{id}
├── power.json                # /redfish/v1/Chassis/{id}/Power (또는 PowerSubsystem)
├── thermal.json              # 선택
├── storage_collection.json   # /Systems/{id}/Storage
├── env_metrics.json          # 선택 (PowerSubsystem 환경)
├── ServiceRoot.headers       # HTTP 응답 헤더 (Accept 협상 등)
└── README.md                 # 펌웨어 버전 / 사고 요약 / 사용자 동의 sanitize

tests/evidence/<YYYY-MM-DD>-<vendor>-<펌웨어>.md
```

## 절차

### 1. 사용자 동의 / sanitize

- 사용자에게 fixture commit 동의 받기 (운영 BMC IP / serial / asset_tag 노출 가능성)
- sanitize 항목:
  - IP: `10.50.11.232` → `192.0.2.10` (RFC 5737 documentation IP)
  - hostname: `prod-bmc-01` → `bmc-test-01`
  - serial: `CN747508KB` → `SAMPLE0001`
  - MAC: `00:11:22:...` → `02:00:00:...`

### 2. raw 응답 캡처

방법 A — 사용자가 probe_redfish.py 직접 실행:
```bash
python tests/redfish-probe/probe_redfish.py \
    --bmc-ip <site_ip> \
    --vendor <vendor> \
    --firmware <fw> \
    --output tests/fixtures/redfish/<vendor>_<fw_id>/
```

방법 B — 사용자가 envelope 첨부 → AI 가 응답 schema 추론 후 fixture 작성

### 3. fixture 디렉터리 작성

- 위 출력 형식 따름
- README.md 에 펌웨어 버전 / 사고 요약 / sanitize 적용 여부 / 사용자 동의 일자

### 4. evidence 작성

`tests/evidence/<YYYY-MM-DD>-<vendor>-<펌웨어>.md`:
```markdown
# <vendor> <펌웨어> 사이트 fixture — <YYYY-MM-DD>

## 사고 요약
- 환경: <vendor> <펌웨어> at <site>
- envelope errors: <요약>
- root cause: <분석>
- hotfix commit: <sha>

## fixture 출처
- 캡처 일시: YYYY-MM-DD
- sanitize 적용: yes/no
- 사용자 동의: <date>

## 회귀 추가
- pytest 위치: tests/unit/test_<vendor>_<fw>_regression.py
- 검증: <hotfix 적용 시 pass / 미적용 시 fail>
```

### 5. 회귀 테스트 추가

```python
# tests/unit/test_<vendor>_<fw>_regression.py
import pytest
from pathlib import Path

FIXTURE_DIR = Path("tests/fixtures/redfish/<vendor>_<fw_id>")

def test_<vendor>_<fw>_envelope_emit():
    """사이트 사고 환경에서 envelope 정상 emit (회귀 차단)."""
    # ... fixture 로드 + redfish_gather 실행 + 검증
```

### 6. 갱신

- `docs/ai/catalogs/EXTERNAL_CONTRACTS.md` — 펌웨어 / endpoint drift 추가
- `tests/evidence/` 의 카탈로그가 있으면 본 evidence 를 등재한다
- `.claude/ai-context/vendors/{vendor}.md` — 본 펌웨어 노트

### 7. cross-channel 회귀 테스트 자동 적용

신규 fixture / baseline 추가 시 `tests/regression/test_cross_channel_consistency.py` 가 자동으로 13 검증 그룹 적용 (T1~T10). 별도 테스트 작성 불필요:

- 새 baseline JSON 을 `schema/baseline_v1/{label}_baseline.json` 에 추가
- `tests/regression/conftest.py` 의 `BASELINE_REGISTRY` 에 entry 추가:
  ```python
  ("huawei_redfish", "redfish", "redfish_api", "huawei_baseline.json"),
  ```
- `pytest tests/regression/` 자동 적용 — envelope 13 필드 / vendor canonical / status enum / hostname fallback / diagnosis shape / errors list / schema_version / channel coverage 모두 검증

### 8. drift 발견 시 처리 (rule 13 R4 보호)

회귀 테스트가 baseline drift 검출 시:
1. **AI 임의 baseline 수정 금지** (rule 13 R4)
2. `pytest.xfail` 또는 `_HOSTNAME_FALLBACK_KNOWN_DRIFT` 같은 set 으로 known drift 마크
3. `docs/ai/NEXT_ACTIONS.md` 에 후속 실측 작업 등재
4. evidence (`tests/evidence/<날짜>-<주제>.md`) 에 root cause 후보 + 후속 절차 명시
5. 실측 / 사이트 fixture 캡처 후 baseline 갱신 + xfail 제거 (별도 cycle)

## 학습 (cycle 2026-05-01 + 2026-05-07)

- 사이트 사고 fixture 부재 → reverse regression 위험 (Lenovo XCC 1.17.0 사례)
- sanitize 안 된 fixture 는 commit 안 함 (보안 + 사용자 동의)
- evidence 가 fixture 의 "왜" 를 보존 — 단순 JSON 만으로는 다음 작업자 혼란
- (2026-05-07) cross-channel 회귀 테스트가 단일 vendor 회귀 만으로 발견 못한 drift 검출 — `cisco_baseline.json` hostname=null drift 사례

## 관련

- rule 13 R4 (실측 기반 baseline 갱신)
- rule 13 R5 (envelope 13 필드)
- rule 96 R1-A (web sources / 사이트 실측 우선)
- rule 25 R7-A-1 (사용자 실측 > spec)
- rule 21 R2 (fixture 출처 기록)
- rule 70 R3 (절대 날짜)
- agent: compatibility-detective (사고 발견 시)
- skill: probe-redfish-vendor (probe 절차)
- 회귀 정본: `tests/regression/test_cross_channel_consistency.py` (cycle 2026-05-07)
