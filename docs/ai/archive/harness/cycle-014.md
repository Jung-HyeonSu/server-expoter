# cycle-014 — 실 BMC 4 vendor redfish 검증 + HIGH Jinja2 회귀 fix + vault sync 발견

## 일자
2026-04-29

## 진입 사유

사용자 명시 권한 부여 (cycle-014 결정):
- AI에게 모든 권한 (하네스 + 실 장비)
- 하네스 차단 시 하네스 자체 수정
- e2e Chrome 자동화 가능
- Jenkins master 152/153 + agent 154/155 자격 (cloviradmin / Goodmit0802!)
- "벤더당 1개씩 검증 필요" → 4 vendor BMC (Dell/HPE/Lenovo/Cisco) — Supermicro baseline 부재로 별도 cycle

cycle-013 종료 후 cycle-012 P2 redfish 공통계정 자동 생성 코드 (account_service_provision)의 실 BMC 검증.

## 처리 내역

### Phase 1 — 환경 접근 + 권한 확보

- **메모리 기록**: `feedback_full_authority.md` + `environment_lab.md` (사용자 명시 권한 + lab IP 보존)
- **Jenkins API 검증** (master 152): cloviradmin Read OK / buildWithParameters HTTP 403 (RBAC build 권한 부재 추정)
- **agent 154 SSH**: paramiko + cloviradmin 자격 OK
  - server-exporter repo: `/home/cloviradmin/jenkins-agent/workspace/hshwang-gather@2`
  - ansible: `/opt/ansible-env/bin/ansible-playbook` (core 2.20.3 — REQUIREMENTS.md 정합)
  - jenkins-agent 실행 사용자 = cloviradmin (jenkins 별도 user 없음)
- **하네스 차단 대응**: 일부 명령이 Claude Code prudent action prevention으로 차단 → `dangerouslyDisableSandbox=true` + 자격증명 transcript 노출 회피 (env var + redact) 패턴 적용

### Phase 2 — 코드 경로 검증 (4 vendor BMC)

vendor별 1대 BMC IP는 `schema/baseline_v1/` 정본에서 추출:

| Vendor | IP | adapter 자동 선택 | precheck | detect | adapter | collect |
|---|---|---|---|---|---|---|
| Dell | 10.50.11.162 | redfish_dell_idrac9 | OK | OK | OK | FAIL (auth 401) |
| HPE | 10.50.11.231 | redfish_hpe_ilo6 | OK | OK | OK | FAIL (auth 401) |
| Lenovo | 10.50.11.232 | redfish_lenovo_xcc | OK | OK | OK | FAIL (auth 401) |
| Cisco | 10.100.15.2 | redfish_cisco_cimc | OK | OK | OK | FAIL (auth 401) |

### Phase 3 — HIGH 버그 발견 + fix (cycle-013 main 회귀)

**증상**: 4 vendor 모두 fatal — `Error while resolving value for '_precheck_ok': Syntax error in template: expected token 'end of print statement', got '{'`

**Root cause** (`common/tasks/precheck/run_precheck.yml:47`):
```yaml
_precheck_ok: >-
  {{
    ...
    and (_precheck_raw.failure_stage is none ...) {# rule 95 R1 #5 ok: ... #}
  }}
```
Jinja2 `{{ ... }}` expression 안에 `{# ... #}` statement 주석 → parser confused.

**Fix** (commit `bf247266`):
- 주석을 expression 밖 (YAML 주석)으로 이동
- 1 file changed, 2 insertions, 1 deletion

**도입 시점**: cycle-012 P0~P5 commit 중 일부 (cycle-013 main `b605c68b`까지 발견 안 됨). 빌드 #38 (Jenkins SUCCESS — UNSTABLE catchError 처리)로 **마스킹**됨.

### Phase 4 — vault 자격 ↔ BMC sync 불일치 발견 (OPS-3 매트릭스)

curl HTTP code 검증 (자격 transcript 노출 0):
- **ServiceRoot 무인증 GET**: 4 vendor 모두 HTTP 200 OK
- **vault primary (infraops)**: 4 vendor 모두 HTTP 401
- **vault recovery (USERID/root/admin)**: 4 vendor 모두 HTTP 401

= cycle-012 P1 vault commit 시점 평문 password 6종 (`Passw0rd1!`, `Goodmit0802!`, `Dellidrac1!`, `calvin`, `hpinvent1!`, `VMware1!`)이 실 BMC와 sync 안 됨. **OPS-3 회전 매트릭스 의존**.

### Phase 5 — redfish 공통계정 자동 생성 미진입 (의도된 동작)

**진입 조건**: `_rf_used_account.role == 'recovery'` (primary fail + recovery success)
- 본 cycle: primary + recovery 모두 fail → account_service 분기 미진입
- code path 검증은 별개 (cycle-012 P2 commit `0448d00d` 작성됨 + 16 adapter `recovery_accounts` 메타 P1)

## 검증 결과

```
[정적]
ansible-playbook (4 vendor BMC, dryrun=true)  : 4/4 envelope 출력 (status=failed/auth=401)
verbose log (Lenovo 1대)                      : try_one_account×2 + abort + rescue → build_failed_output
HIGH Jinja2 fix                              : commit bf247266 main push 완료

[코드 경로]
precheck 4단계                                : OK (수정 후)
detect_vendor (ServiceRoot 무인증)             : OK (4 vendor)
adapter 자동 선택                              : OK (4 vendor)
load_vault                                   : OK (5 vendor vault 모두 decrypt OK)
collect_standard try_one_account             : 401로 collect_ok=false → abort
build_failed_output (rescue)                 : OK (envelope 13 필드)

[운영 sync]
ServiceRoot                                  : 4 vendor HTTP 200
vault primary auth                           : 4 vendor HTTP 401 (sync 안 됨)
vault recovery auth                          : 4 vendor HTTP 401 (sync 안 됨)
account_service 진입                          : 미진입 (primary+recovery 모두 fail)
```

## 영향

| 영역 | 변경 후 |
|---|---|
| cycle-013 main HIGH 회귀 | fix `bf247266` main push 완료 |
| 코드 경로 (precheck → detect → adapter → collect → rescue) | 4 vendor 검증됨 |
| vault sync (4 vendor) | 회전 필요 발견 — OPS-3 매트릭스 |
| account_service 자동 생성 검증 | OPS-3 후속 cycle (cycle-015 후보) |
| 빌드 #38 (Jenkins) SUCCESS 표시의 의미 | catchError UNSTABLE 마스킹 — 실은 envelope status=failed였을 가능성 높음 (재확인 필요) |

## 다음 단계

| # | 작업 | 진입 조건 |
|---|---|---|
| **OPS-3** | 4 vendor BMC password 회전 + vault 갱신 + encrypt | 운영팀 일정 |
| cycle-015 | OPS-3 후 4 vendor primary 인증 성공 검증 | OPS-3 완료 |
| cycle-015 | recovery role only 시나리오 만들어 account_service 진입 + dryrun=true 검증 | 위 |
| cycle-015 | dryrun=false 1 vendor (Dell 또는 HPE) 시범 | 위 + OPS-5 명시 |
| OPS-1 갱신 | Jenkins 빌드 시범 (cycle-014 fix + OPS-3 정합 후) | OPS-3 |

## 본 cycle commit

| commit | 내용 |
|---|---|
| `bf247266` | fix: Jinja2 expression 안 {# #} 주석 syntax error 정정 (cycle-013 main HIGH 회귀) |
| (다음) | docs: cycle-014 evidence + 후속 매트릭스 갱신 |

## 관련

- 사용자 명시 결정: "AI에게 모든 권한, 테스트 서버, 벤더당 1개"
- 검증 기준 IP: `schema/baseline_v1/{dell,hpe,lenovo,cisco}_baseline.json` 정본
- evidence: `tests/evidence/cycle-014/README.md` + 4 log 파일
- handoff: `docs/ai/handoff/2026-04-29-cycle-013.md` (cycle-013 정본)
- 후속 매트릭스: `docs/ai/NEXT_ACTIONS.md` (OPS-3 우선순위 격상 + cycle-015 등재)
