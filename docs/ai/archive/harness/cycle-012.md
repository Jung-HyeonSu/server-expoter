# cycle-012 — 3-channel gather 대형 확장 P0~P5 + vault encrypt + Jenkins credential 등재

## 일자
2026-04-29

## 진입 사유

cycle-011 보안 정책 해제 후 운영 가동성 확보 작업. 6 Phase plan (`C:\Users\hshwa\.claude\plans\1-snazzy-haven.md`) 정본을 단일 cycle 안에 일괄 처리:

- **P0 Foundation** — Jenkinsfile×3 단일 ansible-playbook 진입점 통일 + bootstrap script
- **P1 vault accounts list** — Redfish/OS/ESXi 후보 순차 인증 + envelope `meta.auth.fallback_used` 노출
- **P2 Redfish AccountService dryrun** — 자동 복구 매핑 (dryrun 기본 ON, BMC 잠금 회피)
- **P3 group summary** — cpu/memory/storage/network.summary 4 필드 (Nice)
- **P4 NIC/HBA/IB 확장** — network.{adapters/ports/virtual_switches/driver_map}, storage.{hbas/infiniband} 6 필드 (Nice)
- **P5 runtime sub-phase a (Linux NTP+firewall+listening) + b (Windows runtime + ESXi vSwitch)** — system.runtime 1 필드 (Nice)

추가로 사용자 결정 옵션 A1 (평문 1회 노출 후 encrypt 분리) 채택 → vault 8개 ansible-vault encrypt + Jenkins credential `server-gather-vault-password` 등록.

## 처리 내역

### Phase 별 commit 시퀀스

| commit | Phase | 영향 파일 |
|---|---|---|
| `f0f621ce` | P0 Foundation | Jenkinsfile×3, .gitignore, scripts/bootstrap, docs/01, tests/e2e fixture |
| `fe0be36c` | P1 accounts list + 후보 순차 인증 | vault×8, redfish/load+collect+try, OS/ESXi try_credentials, adapters×16 |
| `0448d00d` | P2 dryrun + P4 Redfish AccountService | redfish_gather.py, account_service.yml |
| `fbb0f357` | P3 group summary + P4 normalize | normalize_standard.yml, gather_memory.yml (Linux) |
| `92b935c3` | P5 sub-phase a Linux runtime | gather_runtime.yml (Linux) |
| `b6d24fd3` | P4 OS/ESXi + P5 sub-phase b Windows runtime | gather_hba_ib.yml, windows/gather_storage+runtime, esxi/collect_network_extended |
| `8e536447` | schema 12 entries Nice + sections.yml empty_value | schema/sections.yml, field_dictionary.yml |
| `c37138ca` | docs cycle-012 진행 상황 | CURRENT_STATE.md, TEST_HISTORY.md |
| `29fee49a` | vault encrypt + credential ID 등록 | vault×8 (encrypt), Jenkinsfile×3, docs/01, scripts/bootstrap |
| `d8b3a0ed` | docs handoff + NEXT_ACTIONS 매트릭스 | docs/ai/handoff/2026-04-29-cycle-012.md, NEXT_ACTIONS.md |

총 9 commit feature 브랜치 push 완료 (cycle-013 후속 PROJECT_MAP fingerprint 갱신은 본 cycle 보고서 작성 commit에 포함될 예정).

### 표면 카운트 영향

```
rules: 28 (변경 없음)
skills: 43 (변경 없음)
agents: 49 (변경 없음)
policies: 9 (변경 없음)
hooks: 18 (변경 없음)
schema entries: 46 → 57 (+11 Nice)
adapter recovery_accounts 메타: 0 → 16 (Redfish 16 adapter 전부)
vault encrypt: 0/8 → 8/8 (linux/windows/esxi + redfish/{dell,hpe,lenovo,supermicro,cisco})
Jenkins credential: 0 → 1 (`server-gather-vault-password`, Secret File)
```

### 검증 결과

```
e2e (145건)                          → PASS (cycle-012 commit 시퀀스 전 단계 PASS 유지)
verify_harness_consistency.py        → PASS
verify_vendor_boundary.py            → PASS (벤더 하드코딩 0건)
field_dictionary.yml schema 정합     → PASS (Must 31 / Nice 20 / Skip 6 = 57 — 헤더 주석 1건 over count는 cycle-013 정정)
project_map_drift                    → 6 drift → 0 drift (cycle-013 --update 갱신)
ansible-vault decrypt 시나리오       → PASS (credential 파일로 decrypt 검증)
```

### 미완 / 사용자 행위 필요 (handoff 매트릭스)

자율 진행 가능 (다음 cycle AI):
- **AI-1** schema/examples 보강 (validate_field_dictionary 11 WARN 해소)
- **AI-2** PROJECT_MAP fingerprint 재계산 (cycle-013에서 수행)
- **AI-3** JENKINS_PIPELINES.md 갱신 — vault binding (cycle-013에서 수행)
- **AI-4** SCHEMA_FIELDS.md 갱신 — Must31/Nice20/Skip6 (cycle-013에서 수행)
- **AI-5** VENDOR_ADAPTERS.md 헤더 갱신 — recovery_accounts 메타 (cycle-013에서 수행)
- **AI-6** 본 cycle-012.md 작성 (cycle-013에서 수행)
- **AI-7** ADR vault-encrypt-adoption (rule 70 R8 trigger 검토 — cycle-013에서 수행)
- **AI-8** main pull → CURRENT_STATE.md 갱신 (PR 머지 후)

운영자 행위 필요 (OPS):
- **OPS-1** Jenkins 빌드 시범 1회 (target_type=redfish, 임의 BMC) — UI 클릭
- **OPS-2** PR 머지 결정 (squash 권장)
- **OPS-3** 평문 password 6종 회전 — Git history 잔존
- **OPS-4** P1 lab 회귀 — vendor 5종 1차/2차 fallback
- **OPS-5** P2 dryrun OFF 전환 — Dell + HPE 먼저, BMC 잠금 위험
- **OPS-6** baseline_v1/* 7개 실측 갱신 (rule 13 R4)
- **OPS-7** settings.local.json 직접 편집

사용자 결정 필요 (DEC):
- **DEC-1** OS/ESXi secondary 자격 사용 시 envelope `meta.auth.fallback_used` 노출 정책 — 노출 채택 (이미 P1 적용)
- **DEC-2** P5 sub-phase c (ESXi multipath / license) — 별도 cycle
- **DEC-3** Cisco AccountService 미지원 운영자 수동 복구 매뉴얼 작성 여부

## 영향

| 영역 | 변경 후 |
|---|---|
| 3-channel envelope | `meta.auth` 신규 (fallback_used / used_account / candidates_count) |
| vault 보안 | encrypted (8/8) — Git history 잔존 password는 OPS-3에서 회전 |
| Jenkins credential | `server-gather-vault-password` (Secret File) — 3 Jenkinsfile 모두 binding |
| Redfish auto-recovery | dryrun 기본 ON — 운영 안전. lab 검증 후 OPS-5 명시 OFF 전환 |
| schema 카탈로그 | 11 신 필드 (Nice) — baseline 영향 없음, OPS-6 실측 후 baseline 갱신 |
| Plan 정본 진행 | 6 Phase 모두 완료 (sub-phase c 제외) |

## 다음 단계

PR 머지 → main pull → cycle-013 시작 시 OPS-1 결과 (envelope `meta.auth.fallback_used` 값) 받아 회귀 fixture 추가 + baseline 갱신 (rule 13 R4 실측 evidence 기반).

## 관련

- plan: `C:\Users\hshwa\.claude\plans\1-snazzy-haven.md` (6 Phase 정본)
- handoff: `docs/ai/handoff/2026-04-29-cycle-012.md`
- 검토 trigger: rule 70 R8 (보호 경로 정책 변경 trigger 미해당 — cycle-011에서 이미 해제. 표면 카운트 변경 trigger 미해당. **rule 본문 의미 변경 trigger 미해당** → ADR 의무 없음. 단 cycle-012 vault encrypt 채택 자체는 governance 결정이므로 advisory ADR 후보 — AI-7에서 검토)
