# NEXT_ACTIONS 역사 — 2026-04 ~ 2026-05 (archive)

> **archive 일자**: 2026-05-21
> **이유**: rule 70 R6 archive 진입 기준 — "왜 지금 이 모습인지" 설명 가치 + 일부는 정기 추적 항목.
> **정본 본문**: `docs/ai/NEXT_ACTIONS.md` 현행 압축본 + `docs/ai/catalogs/LAB_PENDING_MATRIX.md`.
> **삭제하지 않은 이유**: 본 항목들은 외부 의존 (lab / 운영팀 / 사용자 결정) 의 trigger 가 오면 진입 가능한 작업 또는 보안/운영 추적 기록. git log 만으로는 trigger 발생 시 무엇을 해야 하는지 복원 불가.

---

## 2026-04-30 OPS-RESIDUAL (residual-sweep 후속)

| 항목 | 분류 | 차단 사유 |
|---|---|---|
| **OPS-RESIDUAL-1** Win10 (10.100.64.120) WinRM HTTPS 활성화 후 라이브 검증 | 운영 작업 (lab) | WinRM HTTPS off / NTLM MD4 미지원 — 16건 코드 fix 적용됨 (raw PowerShell). 실 검증 lab 한계 |
| **OPS-RESIDUAL-2** Dell 10.50.11.162 BMC 응답 실패 재확인 | 외부 의존 (BMC) | residual-sweep 시 status=failed — 일시적 lab condition 추정. 다음 운영 검증 시 재확인 |
| **OPS-RESIDUAL-3** ESXi vsphere config.network routeConfig path 펌웨어 검증 | LOW | 현재 config.network 단계로 fallback. 펌웨어 7.0.3 확인됨. 다른 펌웨어 (8.0u3) 시 추가 path 등록 가능 |

---

## 2026-04-29 OPS-AS (account-fallback-validation 후속)

| 항목 | 분류 | 차단 사유 |
|---|---|---|
| **OPS-AS-DELL-1** Dell iDRAC9 AccountService `find_empty_slot` None 반환 진단 | HIGH | `redfish_gather.py` 1413-1448 `account_service_get` errors 가시성 부족. 빈 슬롯 14개 raw probe 확인되었으나 코드 검색 None. `_rf_account_service_meta` 에 `errors[]` 노출 + ansible -vv debug 필요. evidence: `tests/evidence/2026-04-29-account-fallback-validation.md` G1 |
| **OPS-AS-CISCO-1** Cisco CIMC 다른 펌웨어/모델 multi-slot 노출 검증 | LOW | lab CIMC 1대 (10.100.15.2) `Members@odata.count = 1` (admin 1슬롯만). 다른 모델/펌웨어가 multi-slot 노출하면 `not_supported` 분기 재검토. 외부 의존 |
| **OPS-AS-SMC-1** Supermicro 실 BMC lab 확보 + AccountService 검증 | MED | 외부 의존 — `.lab-credentials.yml` 에 Supermicro BMC 미정의 |
| **OPS-AS-LAB-CLEANUP** lab Lenovo (slot 4) + HPE (slot 3) 의 infraops 정리 | LOW | lab BMC 에 영속 생성 (idempotent OK). production 배포 후 lab 회수 시 cleanup 또는 유지 — 사용자 결정 |

---

## 2026-04-29 OPS-AUDIT (production-audit 후속)

| 항목 | 분류 | 차단 사유 |
|---|---|---|
| **OPS-AUDIT-1** Goodmit0802! 자격증명 회전 | 사용자 결정 (보안) | 자격증명이 git history 잔존 — 회전 후 filter-branch / repo rewrite 결정 필요 |
| **OPS-AUDIT-2** Supermicro 실장비 fixture 확보 | 외부 의존 | 3 adapter 정의 (`supermicro_bmc/x9/x11.yml`) 에 0 fixture / 0 baseline → `LAB_PENDING_MATRIX.md` Supermicro 행 참조 |
| **OPS-AUDIT-3** ESXi 8.0u3 baseline 생성 | 외부 의존 | tests/reference/esxi/ 3종 모두 ESXi 7.0.3. 8.0u3 reference 미존재 |
| **OPS-AUDIT-5** Cisco UCS C-series (cisco_bmc) 실장비 검증 | 외부 의존 | cisco_bmc.yml fallback adapter — TA-UNODE-G1 외 일반 CIMC 검증 필요 |
| **OPS-AUDIT-6** RAID6/10/50/60 fixture 추가 | 외부 의존 | 현재 RAID0/1/5 만 baseline. 8+ drive RAID6 검증 필요 |
| **OPS-AUDIT-7** HPE iLO4 / iLO6 / Dell iDRAC8 / Lenovo IMM2 baseline | 외부 의존 | adapter 정의 있으나 baseline 없음 → `LAB_PENDING_MATRIX.md` 매트릭스 참조 |

---

## 2026-04-29 OPS-HPE-REVIEW / OPS-CISCO-REVIEW / OPS-DELL-VAULT / OPS-LENOVO

| 항목 | 분류 | 차단 사유 |
|---|---|---|
| **OPS-HPE-REVIEW-1** HPE iLO 6 baseline 재수집 (10.50.11.231) | 운영 작업 | hpe-critical-review fix 5건 적용 후. 현재 baseline cycle-016 Phase M/N 이전 stale — 재수집 시 fix 효과 (bios_date / ilo_version / cpu.architecture / hostname / is_primary / 빈 문자열 정규화) 반영. evidence: `tests/evidence/2026-04-29-hpe-redfish-critical-review.md` |
| **OPS-HPE-REVIEW-2** Dell baseline 재검토 | 운영 작업 | `_hoist_oem_extras` 적용으로 Dell `hardware.bios_date` 채워짐. 실 Dell 검증 후 baseline 갱신 |
| **OPS-CISCO-REVIEW-1** Cisco baseline 재수집 (10.100.15.2) | 운영 작업 | cisco-critical-review fix 5건 적용 후. dynamic 필드 (`power_consumed_watts/avg/max`, `bmc.datetime`) 정책 결정 (nullify vs realtime) 후 재캡처. evidence: `tests/evidence/2026-04-29-cisco-redfish-critical-review.md` |
| **OPS-CISCO-REVIEW-2** Cisco baseline `data.bmc` Phase M/N 신규 8 필드 보강 | 운영 작업 | `cisco_baseline.json` `data.bmc` cycle-016 Phase M/N 이전 stale. 코드 fix 후 재수집 시 자연 반영 — OPS-CISCO-REVIEW-1 묶음 |
| **OPS-DELL-VAULT-1** Dell BMC vault 자격증명 회전 (10.50.11.162) | 운영 작업 (보안) | vault `dell.yml` (root/GoodskInfra1!) BMC 인증 시 HTTP 401. ServiceRoot 무인증 GET 정상. BMC 자격증명 만료/잠금/변경 추정. `rotate-vault` skill |
| **OPS-LENOVO-PSU1** Lenovo 10.50.11.232 PSU1 hardware 점검 | 운영 작업 (실 hardware) | 회귀 검사에서 PSU1 `Health=Critical`, `InputRanges[0].OutputWattage=null`. 실 PSU 고장 또는 커넥터 분리. PSU 교체 또는 커넥터 점검 필요 |

---

## cycle-016 잔여 (2026-04-29 종료 시점)

| 항목 | 차단 사유 |
|---|---|
| **OPS-3** 운영팀 vault credential 회전 timing | AccountService 실 호출 권한 부여 (현재 dryrun toggle 만 검증) |
| **OPS-9** repo private 전환 | 사용자 결정 |
| **OPS-11 partial** Cisco BMC 10.100.15.3 ping fail | lab 부재 — 1번 (10.100.15.1) 은 회복됐으나 Redfish 미지원 |
| **AI-22 reopen** Win Server 2022 (10.100.64.135) WinRM probe 간헐 실패 | lab firewall/WinRM 서비스 안정성 OPS 조사 |
| **AI-25 후속** dell_baseline.json 정본 갱신 | baseline IP (10.50.11.162) vs lab 실 IP 불일치. lab 실 IP 정본 채택 시 정합성 검토 후 갱신 |

---

## cycle-013 잔여 (사용자 개입 필요)

| 항목 | 차단 사유 |
|---|---|
| **OPS-1** Jenkins 빌드 시범 1회 (target_type=redfish, 임의 BMC) | UI 클릭 + lab 환경 |
| **OPS-4** P1 lab 회귀 — vendor 5종 1차 / 2차 fallback 시나리오 | 실 BMC + lab cycle. 결과 받으면 evidence + baseline 갱신 |
| **OPS-5** P2 dryrun OFF 전환 (Dell + HPE 먼저) | rule 92 R5 + BMC 잠금 위험. 결정 시 `_rf_account_service_dryrun: false` 토글 + lab 검증 |
| **OPS-6** baseline_v1/* 7개 실측 갱신 (P3/P4 신 필드 정합) | rule 13 R4 — 실측 기반만. probe_redfish.py 결과 받으면 baseline 갱신 + Stage 4 회귀 |
| **OPS-7** settings.local.json 편집 — AI self-modification 차단 (cycle-011 잔여) | settings.json 만으로 풀림 확인됨. 운영자 직접 편집 |
| **OPS-8** main 에 cycle-013 commit 정리 (PR 또는 직접) | rule 93 R2 머지 사용자 명시 승인 |

> **참고**: cycle-013 의 ~~OPS-2~~ / ~~OPS-10~~ / ~~OPS-12~~ / ~~OPS-13~~ / ~~OPS-14~~ / ~~OPS-15~~ 는 모두 closed (cycle-015 / cycle-016 에서 처리).

---

## archive 진입 후 복원 절차

위 항목 중 trigger 가 발생하면:

1. 본 archive 에서 항목 식별
2. 해당 vendor / 작업 영역의 `LAB_PENDING_MATRIX.md` 또는 active `NEXT_ACTIONS.md` 로 이동
3. trigger 충족 evidence 첨부 (rule 70 R1 매핑)
4. 후속 cycle 진입

---

## 관련

- 정본: `docs/ai/NEXT_ACTIONS.md` (현행 active 만)
- 매트릭스: `docs/ai/catalogs/LAB_PENDING_MATRIX.md`
- rule: `70-docs-and-evidence-policy` R5 (보존 판정) / R6 (archive 진입 기준)
