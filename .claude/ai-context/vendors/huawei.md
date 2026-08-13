# Huawei — 벤더 OEM 메모

> 2026-05-01 신규 (F44 사용자 명시 승인). lab 부재 — web sources only.

## 식별

- **Manufacturer (Redfish ServiceRoot)**: "Huawei", "Huawei Technologies Co., Ltd."
- **Aliases**: Huawei, HUAWEI, Huawei Technologies
- **BMC 이름**: iBMC (integrated Baseboard Management Controller)
- **vendor_aliases.yml** 정규화: `huawei`

## Adapter 매핑

| Adapter | priority | 대상 모델 / 펌웨어 |
|---|---|---|
| `adapters/redfish/huawei_ibmc.yml` | 80 | FusionServer Pro V5/V6 (lab 부재 — web sources) |
| `adapters/redfish/redfish_generic.yml` | 0 | unknown 펌웨어 fallback |

## OEM 특이사항

- **Manager URI 추정**: `/redfish/v1/Managers/iBMC` (사이트 검증 필요)
- **OEM namespace**: `Oem.Huawei`
- **표준 Redfish + IPMI 2.0 + SNMP + DCMI** 지원
- **대표 모델**:
  - FusionServer Pro 2288H V5 (2U, dual-socket Intel Xeon Cascade Lake)
  - FusionServer Pro 2288X V5 (2U, GPU 강화)
  - FusionServer Pro 2488H V5 (2U, 4-socket)
  - FusionServer Pro 1288H V6 (1U, V6 — Ice Lake/Sapphire Rapids 추정)

## Vault

- 위치: `vault/<loc>/redfish/huawei.yml` — **미생성 (사용자 명시 2026-05-01)**
- lab/사이트 도입 시: ansible-vault encrypt + username/password 등록
- 부재 시 동작: precheck auth 단계 status=failed (graceful degradation, rule 27 R4)
- 회전 절차: `rotate-vault` skill (vault 생성 후)

## 검증 이력

- 실장비 검증: **부재** (lab 없음)
- Baseline: 부재 (lab 도입 후 `schema/baseline_v1/<vendor>_baseline.json (huawei 는 lab 부재로 미생성)`)
- web sources 기반 회귀: redfish_generic vs huawei adapter 매칭 점수 차이만 검증

## 사이트 도입 시 절차 (rule 50 R2 잔여 단계)

1. `vault/<loc>/redfish/huawei.yml` 생성 (ansible-vault encrypt)
2. ServiceRoot 무인증 detect → vendor=huawei 확인
3. `tests/redfish-probe/probe_redfish.py --vendor huawei` 실행
4. `schema/baseline_v1/<vendor>_baseline.json (huawei 는 lab 부재로 미생성)` 생성
5. `tests/evidence/<날짜>-huawei.md` Round 검증 기록
6. `docs/reference/live-validation.md` Round 갱신
7. `capture-site-fixture` skill 으로 사이트 fixture 캡처

## Reference

- `docs/reference/decision-log.md` — 2026-05-01 신규 vendor 4종 도입 결정
- ticket F44 (cycle 2026-05-01 — git history) — 본 vendor cold-start ticket
- Huawei iBMC 공식 docs: support.huawei.com
- Huawei-iBMC-Cmdlets (vendor 공식 GitHub): https://github.com/Huawei/Huawei-iBMC-Cmdlets
