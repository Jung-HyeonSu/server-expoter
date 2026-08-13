---
name: probe-redfish-vendor
description: 새 벤더 / 새 펌웨어 / 의심 응답에 대해 deep_probe_redfish.py로 Redfish API 응답을 전수 프로파일링한다. ServiceRoot부터 Chassis/Systems/Storage/Volumes/Drives/Managers/UpdateService/AccountService 모두 dump 후 vendor adapter 작성을 위한 baseline 자료 생성. 사용자가 "Dell iDRAC 7.x 프로파일", "새 펌웨어 응답 봐줘", "deep probe", "벤더 추가 전 검증" 등 요청 시. - 새 vendor 추가 전 / 펌웨어 업그레이드 후 응답 변경 의심 / 외부 계약 drift 발견 (rule 96)
---

# probe-redfish-vendor

## 목적

`tests/redfish-probe/deep_probe_redfish.py`를 사용해 새 벤더/펌웨어의 Redfish API 응답 전수 수집. 결과로 adapter YAML 작성 (`add-new-vendor` skill) + baseline JSON 생성 (`update-vendor-baseline`)에 활용.

## 입력

- target_ip (BMC IP)
- 자격증명 (vault 또는 인터랙티브)
- 결과 저장 경로 (기본: `tests/evidence/<날짜>-<vendor>-<펌웨어>/`)

## 출력

```markdown
## Deep Probe 결과 — Dell iDRAC 7.x

### ServiceRoot 응답
- Manufacturer: "Dell Inc."
- Model: "PowerEdge R7525"
- Firmware: 7.10.30.20

### 발견 endpoint
- /redfish/v1/Chassis (1 item)
- /redfish/v1/Systems (1 item)
- /redfish/v1/Systems/System.Embedded.1/Storage (3 controllers)
- /redfish/v1/Managers/iDRAC.Embedded.1
- /redfish/v1/UpdateService/FirmwareInventory (15 items)
- /redfish/v1/AccountService/Accounts (8 accounts)

### Path 변경 발견 (vs 5.x baseline)
- [NEW] /redfish/v1/Systems/.../Storage/Volumes (이전엔 OEM only)
- [MOD] /redfish/v1/Chassis/.../Power.PowerSupplies (sensor 필드 추가)
- [DEL] (없음)

### OEM 분기
- /redfish/v1/Dell/Managers/iDRAC.Embedded.1 (Dell-specific)

### 다음 단계
- adapter dell_idrac9.yml의 firmware_patterns에 "7.x" 추가 (priority 100 유지)
- schema/baseline_v1/dell_baseline.json 회귀 검토
- rule 96 origin 주석 갱신 (마지막 동기화 = 오늘)
```

## 절차

1. **자격증명 확보** — vault/<loc>/redfish/<vendor>.yml 또는 인터랙티브 (probe 시점)
2. **deep_probe 실행**:
   ```bash
   python tests/redfish-probe/deep_probe_redfish.py \
     --ip 10.x.x.1 \
     --user "$VAULT_USER" \
     --password "$VAULT_PASS" \
     --output tests/evidence/<날짜>-<vendor>-<펌웨어>/
   ```
3. **응답 dump 분석**:
   - ServiceRoot → vendor 식별
   - Chassis / Systems / Storage / Volumes / Drives / Managers / UpdateService / AccountService 모두 GET
   - OEM endpoint 재귀 탐색
4. **기존 baseline / fixtures와 diff**:
   - `schema/baseline_v1/<vendor>_baseline.json`
   - `tests/fixtures/<vendor>_*.json`
5. **변경 path / 필드 list 작성** — rule 96 origin 주석 갱신용
6. **결과를 evidence/ 에 저장**:
   - 원본 JSON dump
   - diff 보고서
   - 권고 (adapter / baseline 변경 list)
7. **다음 skill 안내** — `update-vendor-baseline` 또는 `add-new-vendor`

## server-exporter 도메인 적용

- 영향 채널: redfish 전용 (os / esxi probe는 별도 도구)
- 영향 vendor: 검증 대상 1개
- 영향 schema: baseline_v1 갱신 가능

## 보안 (운영 권장 — cycle-011: rule 60 정책 해제)

- probe 결과 dump에 BMC password 누설 안 되도록 운영자 확인 (security-redaction-policy.yaml 제거됨)
- 자격증명을 명령행으로 전달 → Jenkins console log 노출 위험. probe는 사용자 환경에서만 실행

## 실패 / 오탐 처리

- 일부 endpoint가 인증 후에도 403 → BMC 권한 부족 (vault 사용자 권한 격상 필요)
- 펌웨어가 Redfish 미지원 → IPMI fallback 검토 (현재 server-exporter 미지원)
- 응답이 비표준 (스키마 위반) → vendor에 문의 + rule 96 R4 drift 기록

## 적용 rule / 관련

- **rule 96** (external-contract-integrity) — origin 주석 정본
- (cycle-011: rule 60 해제 — probe 시 비밀값 redaction은 운영자 권장 수준)
- rule 40 (qa-pytest-baseline) — Round 검증 일환
- skill: `add-new-vendor`, `update-vendor-baseline`, `debug-external-integrated-feature`
- agent: `adapter-author`, `vendor-onboarding-worker`
- 정본: `docs/reference/live-validation.md`, `tests/redfish-probe/deep_probe_redfish.py`
- reference: 외부 API 공식 문서
