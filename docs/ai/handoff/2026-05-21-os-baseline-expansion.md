# Handoff — OS baseline expansion (rhel920 / rhel960 / rocky960)

> 직전 NEXT_ACTIONS.md F6 의 별도 cycle 권장 — cold-start 6 절 형식 (rule 26 R6 / write-cold-start-ticket skill).
> 사용자 access 제공된 진짜 즉시 가능 작업 (lab access 만 필요, BMC fixture 부재 아님).

---

## 1. 컨텍스트 (이전 세션 종료 시점)

- **종료 commit**: `e5ddc85a` (CSUS 3200 mock baseline 깊이 보강)
- **trigger 출처**: cycle 2026-05-11 `field-channel-refinement` F6 (NEXT_ACTIONS 등재 → 본 handoff 로 분리)
- **사용자 명시 (2026-05-11)**: OS access IP 3대 제공
  - `10.100.64.163` — RHEL 9.2 VM (`rhel920`)
  - `10.100.64.165` — RHEL 9.6 VM (`rhel960`)
  - `10.100.64.169` — Rocky 9.6 VM (`rocky960`)
- **선행 의존**: F5 (`system.runtime` 9 필드 Linux/Windows 빌더) **[DONE 2026-05-11]** — 본 cycle 에서 신규 빌더 실측 검증 포함

---

## 2. 다음 첫 지시 (cold-start prompt)

```
OS baseline expansion cycle 진입 — rhel920 / rhel960 / rocky960 신규 baseline 3건.

진입 정보:
- 3 IP: 10.100.64.163 (rhel920) / 10.100.64.165 (rhel960) / 10.100.64.169 (rocky960)
- 실행 환경: Jenkins Agent (ansible-playbook + vault/<loc>/os/linux.yml 자동 로드)
- 선행 cycle: F5 (system.runtime 9 필드 Linux/Windows 빌더 정착 후)

각 baseline 추가 절차 (rule 13 R4):
1. ansible-playbook os-gather/site.yml -e target_ip=<IP> 실 수집
   → Jenkins Agent 환경 / loc=<적절>
2. 출력 envelope → schema/baseline_v1/{name}_baseline.json 저장
3. tests/evidence/2026-MM-DD-{name}.md evidence 기록
   - 수집 일자, ansible/python 버전, target OS 버전 명시
   - F5 신규 system.runtime 9 필드 정상 채워짐 검증
4. update-vendor-baseline skill 절차 follow (실측 vs 기존 ubuntu/rhel810 비교)
5. F5 system.runtime 빌더 안정성 — 신규 baseline 3건에서 9 필드 모두 채워지면 빌더 검증 완료
6. pytest tests/ 회귀 PASS
7. docs/reference/decision-log.md entry + docs/ai/CURRENT_STATE.md 갱신
8. commit + push (rule 93 R1 자율 — github + gitlab 동시)
9. NEXT_ACTIONS.md F6 [PENDING] → [DONE] 갱신

진입 전 read 권장:
- docs/develop/05-field-mapping.md (Linux/Windows 필드 매핑)
- schema/baseline_v1/ubuntu_baseline.json + rhel810_raw_fallback_baseline.json
  (기존 OS baseline 형식 비교)
- os-gather/tasks/linux/gather_system.yml (F5 system.runtime 9 필드 정본)
- skill: update-vendor-baseline
```

---

## 3. 의존성 / 전제 조건

| # | 조건 | 상태 |
|---|---|---|
| 1 | 3 IP access (사용자 제공) | [OK] (2026-05-11 명시) |
| 2 | F5 system.runtime 9 필드 빌더 적용 | [DONE 2026-05-11] |
| 3 | Jenkins Agent + vault/<loc>/os/linux.yml | [OK] (운영 환경) |
| 4 | ansible-playbook + Python 3.12 + Linux ansible.posix | [OK] (운영 Agent) |

---

## 4. 작업 범위 (rule 13 / rule 22 / rule 26 R10)

- 단일 worker (N=1) — rule 26 R10 4 정본 의무 X
- 본 handoff 1 파일 만으로 충분
- envelope shape 변경 0 (rule 13 R5 / R7) — baseline 추가만
- F5 system.runtime 빌더는 이미 적용 — 본 cycle 은 실측 검증

---

## 5. 검증 기준 (rule 24 6 체크)

- [ ] 정적 검증 (pytest / yamllint / verify_harness_consistency)
- [ ] 발견 버그 0건 또는 수정 commit (F5 빌더 9 필드 검증 — 신규 baseline 3건 모두에서 채워지면 PASS)
- [ ] 문서 갱신:
  - `docs/ai/CURRENT_STATE.md` — OS baseline 3건 추가 명시
  - `docs/ai/catalogs/TEST_HISTORY.md` — 실 수집 + evidence
  - `schema/baseline_v1/{name}_baseline.json` × 3
  - `tests/evidence/2026-MM-DD-{name}.md` × 3
  - `docs/reference/decision-log.md` — Round entry
  - `docs/ai/NEXT_ACTIONS.md` F6 [DONE] 표기
- [ ] NEXT_ACTIONS 갱신
- [ ] (선택) git 태그 `v-os-baseline-2026-MM-DD`
- [ ] 회귀 PASS (기존 baseline 7건 영향 0)

---

## 6. 에스컬레이션

| 발생 시 | 책임 |
|---|---|
| 3 IP 중 1대 이상 접속 불가 (방화벽 / vault 자격 불일치) | OPS 보고 + 사용자 확인. 가능한 IP 만 진행 (graceful degradation) |
| F5 system.runtime 9 필드 일부 누락 (실측) | F5 빌더 회귀 — `gather_system.yml` Linux 영역 fix 필요 (별도 ticket) |
| envelope shape 변경 발견 (rule 13 R5 / R7 / rule 96 R1-B) | 즉시 abort + 사용자 보고. baseline 추가 cycle 에서 envelope 변경 금지 |
| 기존 baseline (ubuntu / rhel810) 회귀 발생 | 즉시 사용자 보고 + rule 25 R7-A-1 (사용자 실측 우선) |

---

## 7. 산출 예상

| 항목 | 형식 |
|---|---|
| 신규 baseline JSON | `schema/baseline_v1/{rhel920,rhel960,rocky960}_baseline.json` (3 파일) |
| evidence | `tests/evidence/2026-MM-DD-{rhel920,rhel960,rocky960}.md` (3 파일) |
| 회귀 추가 (선택) | `tests/regression/test_os_baseline_consistency.py` 에 3 baseline 추가 |
| 문서 갱신 | CURRENT_STATE + TEST_HISTORY + decision-log + NEXT_ACTIONS |
| commit | 1~3건 (baseline 별 분리 또는 통합 선택) |

---

## 관련

- rule: `13-output-schema-fields` R4 (baseline 실측 기반), `22-fragment-philosophy`, `92-dependency-and-regression-gate`
- skill: `update-vendor-baseline`, `prepare-regression-check`
- 정본: `docs/develop/05-field-mapping.md`, `os-gather/tasks/linux/gather_system.yml` (F5 system.runtime 9 필드)
- baseline 기존: `schema/baseline_v1/{ubuntu,rhel810_raw_fallback,windows}_baseline.json`
