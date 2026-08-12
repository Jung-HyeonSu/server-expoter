# ADR-2026-04-30-account-service-dryrun-off

> Status: Accepted (2026-04-30, 사용자 명시 승인)

## 컨텍스트 (Why)

server-exporter 명세서 (cycle-016 사용자 요구사항 #2 / #3 / #4):
- Redfish 공통계정 `infraops/__REDACTED__` 가 모든 BMC에 존재해야 함 (provision target)
- 없으면 만들기 (POST AccountService 또는 Dell PATCH empty slot)
- 있는데 사용 못 하면 (disabled / locked / password mismatch) → enable + 갱신

`account_service_provision` 함수는 이미 위 명세대로 구현됨 (line 1848~). 하지만 `redfish-gather/tasks/account_service.yml` 의 default `_rf_account_service_dryrun: true` 로 인해 **시뮬레이션만 동작** — method 결정 메타만 envelope에 노출되고 실제 PATCH/POST 미실행.

이전 cycle-014 결정 ("lab 잠금 위험 회피 위해 default true, 사용자 명시 승인 후 false 전환 — rule 92 R5 OPS-5 매트릭스") 의 단서 조건 = "사용자 명시 승인 후" 가 충족됨.

## 결정 (What)

`redfish-gather/tasks/account_service.yml` line 31:
- `_rf_account_service_dryrun | default(true)` → `_rf_account_service_dryrun | default(false)`
- 즉 default 동작이 시뮬레이션이 아닌 실 PATCH/POST.
- 시뮬레이션이 필요한 경우 외부 override `-e _rf_account_service_dryrun=true` 로 강제 가능.

## 결과 (Impact)

### 정상 흐름

1. recovery 자격으로 BMC 접속 → 1차 수집 succeed (`_rf_collect_ok=true`, `role=recovery`)
2. site.yml line 107 조건 충족 → `account_service.yml` 진입
3. recovery 자격으로 AccountService GET + 기존 infraops 검색
4. **(NEW) 실 PATCH/POST 실행**:
   - 기존 infraops 있음 → `PATCH {Password, Enabled: True, RoleId}` 실행. 이전 disabled 였으면 enable + password 갱신
   - 없음 → `POST /Accounts {UserName, Password, Enabled, RoleId}` (Dell은 빈 슬롯 PATCH)
5. recovered=true 면 primary 자격으로 rotate → `collect_standard.yml` 재실행 → infraops 로 정상 gather

### 영향 범위

- **vendor**: dell / hpe / lenovo / supermicro 4 vendor에 실 적용. Cisco는 AccountService 표준 미지원 (`not_supported` errors 기록 후 종료 — 변화 없음)
- **Cycle 영향**: 기존에 dryrun=true 시 infraops가 BMC에 영구 생성 안 됐던 시나리오가 정상 흐름에서 자동 생성됨
- **호출자 envelope**: `meta.account_service` 필드의 `dryrun` = false 표시. `recovered` = true 시 primary로 rotate

### 위험 / 완화

| 위험 | 완화 |
|---|---|
| BMC에 의도치 않은 infraops 갱신 (예: 운영자가 수동 변경한 password를 vault 값으로 덮어씀) | recovery 자격으로 진입 시에만 동작 — 정상 운영 (primary 자격 정상)에선 진입 안 함 |
| BMC PATCH 실패 시 errors 누적 | `failed_when: false` 로 빌드 fail 안 함. `meta.account_service.recovered=false` + errors 누적 |
| 잘못된 vault target_password 가 BMC password 덮어씀 | vault 갱신은 사용자 명시 승인 영역. 본 ADR 외 영역 |

## 대안 비교 (Considered)

### A. dryrun=true 유지 (이전 default)
- **장점**: lab 잠금 위험 0
- **단점**: 명세 (#2/#3/#4) 가 운영에서 미동작. infraops 생성 자체가 사용자 매번 명시 승인 (-e override) 해야 함
- **거부 사유**: 사용자가 명시 승인 — "동작하게 해야하는거 아님?"

### B. vendor별 dryrun (Cisco는 제외, 그 외만 false)
- **장점**: 미지원 vendor 자동 skip
- **단점**: 코드 복잡. 현재 Cisco는 이미 `not_supported` 분기로 errors만 기록 후 종료 (실 호출 없음) — vendor별 dryrun 불필요
- **거부 사유**: 단순 default 변경으로 충분

### C. dryrun=false default + Locked 보강 (채택)
- **장점**: 명세 "사용 못 하면 enable" 의 disabled + locked 둘 다 처리
- **단점**: PATCH body에 `Locked: False` 추가가 일부 BMC 펌웨어에서 PATCH 거부 가능 (read-only)
- **완화**: PATCH 응답이 400/405 일 때 Locked 빼고 1회 retry. retry 성공 시 errors[]에 advisory 기록
- **결정**: **채택** (사용자 추가 명시 승인 — "Locked 보강 진행 해라")

## 관련

- **이전 결정**: `docs/ai/archive/harness/cycle-014.md` — dryrun=true default 도입 사유 (lab 잠금 위험 회피)
- **명세 reference**: `docs/ai/harness/cycle-016.md` 사용자 요구사항 #2 / #3 / #4
- **rule**: rule 92 R5 (사용자 명시 결정 — OPS-5 매트릭스)
- **카탈로그**: `docs/ai/catalogs/VENDOR_ADAPTERS.md` dryrun 정책 절

## 승인 기록

| 일시 | 승인자 | 비고 |
|---|---|---|
| 2026-04-30 | hshwang1994 | "dryrun=true default 이게 무슨말?? 지금 동작안하는거임?? 동작하게 해야하는거아님??" — dryrun=false 명시 승인 |
| 2026-04-30 | hshwang1994 | "Locked 보강 진행 해라 그리고 default가 동작하게 해라 지금 써야하는 기능이다" — Locked 보강 + dryrun OFF 함께 명시 승인 |
