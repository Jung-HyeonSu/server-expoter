# cycle-014 evidence — redfish 공통계정 검증 + HIGH 버그 fix

## 일자
2026-04-29

## 진입 사유
사용자 명시: "AI에게 모든 권한 (하네스 + 실 장비). 테스트 서버이므로 안전. 벤더당 1대씩 검증 필요"

## 환경

| 항목 | 값 |
|---|---|
| Jenkins Master | 10.100.64.152 / 10.100.64.153 |
| Jenkins Agent (검증 기준) | 10.100.64.154 (jenkins-agent-ops, Ubuntu 6.8) |
| ansible | /opt/ansible-env/bin/ansible-playbook (core 2.20.3 — REQUIREMENTS.md 정합) |
| Jenkins workspace | /home/cloviradmin/jenkins-agent/workspace/hshwang-gather@2 |
| 사용자 | cloviradmin (jenkins-agent 실행) |
| main commit (검증 시점) | bf247266 (cycle-014 fix 후) |

## 4 vendor BMC 검증 (baseline_v1 정본 IP)

| Vendor | BMC IP | Source | adapter (자동 선택) |
|---|---|---|---|
| Dell | 10.50.11.162 | dell_baseline.json | redfish_dell_idrac9 |
| HPE | 10.50.11.231 | hpe_baseline.json | redfish_hpe_ilo6 |
| Lenovo | 10.50.11.232 | lenovo_baseline.json | redfish_lenovo_xcc |
| Cisco | 10.100.15.2 | cisco_baseline.json | redfish_cisco_cimc |

**Supermicro**: baseline_v1 부재 → 본 cycle 검증 제외 (별도 cycle).

## 결과

### [PASS] 코드 경로 검증 (cycle-013 main + cycle-014 fix 후)

4 vendor 모두 다음 단계 정상 동작:
1. **precheck 4단계**: reachable + port_open(443) + protocol_supported 모두 OK (수정 후)
2. **detect_vendor**: ServiceRoot 무인증 GET 성공 → Manufacturer 추출 → vendor 자동 매핑
   - dell / hpe / lenovo / cisco 모두 정확
3. **adapter 자동 선택**: priority 점수 기반 매칭
   - dell_idrac9 (priority=100) / hpe_ilo6 (100) / lenovo_xcc (100) / cisco_cimc (100)
4. **load_vault**: vendor별 vault 동적 로드 + accounts list 추출
5. **collect_standard try_one_account**: 2 자격 (primary + recovery) 순차 시도
6. **build_failed_output (rescue)**: 13 필드 envelope 정상 출력 (rule 13 R5 정합)

### [HIGH FIX] Jinja2 syntax error 정정 (cycle-013 main 회귀)

**증상**: 4 vendor 모두 fatal — `Error while resolving value for '_precheck_ok': Syntax error in template: expected token 'end of print statement', got '{'`

**Root cause** (`common/tasks/precheck/run_precheck.yml:47`):
```yaml
_precheck_ok: >-
  {{
    ...
    and (_precheck_raw.failure_stage is none ...) {# rule 95 R1 #5 ok: ... #}
  }}
```
`{{ ... }}` Jinja2 expression **안**에 `{# ... #}` 주석 → parser가 `{{ }}` 종료 못 함.

**Fix** (commit `bf247266`):
- 주석을 expression 밖으로 이동 (YAML 주석 `#` 또는 task 위 별도 주석)

**도입 시점 (확정)**: commit `87624231` (cycle-004 silence 작업, 2026-04-27)
```
$ git log --oneline -- common/tasks/precheck/run_precheck.yml
bf247266 fix: Jinja2 expression 안 {# #} 주석 syntax error 정정 (cycle-014)
87624231 fix: redfish_gather _safe_int + 변수 분기 의도 silence  ← 도입
2f998c90 feat: initial commit
```
`87624231` diff: 본 라인에 `{# rule 95 R1 #5 ok: 진단 통과 = failure_stage 부재 #}` 주석 추가.

**Jenkins 빌드 마스킹 영향 (cycle-014에서 검증)**:
- 18 빌드 분석 (`hshwang-gather` #34~#38 + `extended-fields-test` × 4 + `multi-stage-single-playbook` × 5 + `single-stage-single-playbook` × 5)
- Jenkins SUCCESS + envelope=failed + Jinja2 error 발견 = **0 빌드**
- 빌드 #38 envelope status=success 였음 (cycle-012 PR 머지 직후 시점)
- → cycle-014 시점 ansible 환경 (agent 154 ansible-core 2.20.3 + Jinja2 3.1.6)에서 strict해진 듯
- → 본 cycle-014 fix는 모든 환경에서 안전 (Jinja2 expression 안 statement 주석은 표준 비호환)

**영향**: cycle-013 main commit 시점 모든 redfish gather가 precheck 단계 후 envelope `_output 미생성` (block/rescue 모두 실패) 또는 fatal로 빌드 실패. 실 BMC 빌드 시범 (OPS-1)이 어떤 빌드든 모두 affected.

### [WARN] vault 자격 ↔ BMC sync 불일치

| Vendor | Primary user (vault) | HTTP code | Recovery user (vault) | HTTP code |
|---|---|---|---|---|
| Lenovo | infraops | **401** | USERID | **401** |
| Dell | infraops | **401** | root | **401** |
| HPE | infraops | **401** | admin | **401** |
| Cisco | infraops | **401** | (truncated) | — |

ServiceRoot 무인증 GET = 4 vendor 모두 **HTTP 200 OK** (Redfish 서비스 정상). 인증 자격만 wrong.

**해석**: cycle-012 P1 vault accounts list 도입 시 commit된 password들 (cycle-012 NEXT_ACTIONS OPS-3: __REDACTED__/__REDACTED__/__REDACTED__/calvin/__REDACTED__/__REDACTED__)이 실 BMC와 sync 안 됨. OPS-3 회전 작업 의존.

### [INFO] redfish 공통계정 자동 생성 (P2 account_service) 진입 안 함

**진입 조건** (account_service.yml + site.yml:91): `_rf_used_account.role == 'recovery'`
- = primary 자격 fail + recovery 자격 success 시점에만 진입
- 본 cycle은 **primary + recovery 모두 fail** → account_service 분기 미진입
- 코드 path 검증은 별개 (cycle-012 P2 commit `0448d00d` 작성 + 16 redfish adapter `recovery_accounts:` 메타 cycle-012 P1 commit `fe0be36c`)

## 후속 작업 (운영자 의존)

| # | 작업 | 의존 |
|---|---|---|
| **OPS-3** | 4 vendor BMC password 회전 + vault 갱신 | 운영팀 일정 + 실 장비 |
| OPS-3 후 | cycle-014 재검증 — vault 자격 정합 후 4 vendor primary 인증 성공 | OPS-3 |
| OPS-3 후 | recovery role 자격으로만 인증 가능한 시나리오 만들어 account_service 진입 검증 | 위와 동시 |
| OPS-5 | dryrun OFF 전환 (Dell + HPE 우선) | OPS-3 + lab 검증 |
| OPS-1 | Jenkins 빌드 시범 (cycle-014 fix bf247266 + vault 정합 후) | OPS-3 |

## 첨부 파일

- `dryrun-true-4vendor.log` — fix 전 (Jinja2 syntax error)
- `dryrun-true-4vendor-after-fix.log` — fix 후 (4 envelope JSON, 모두 status=failed/auth=401)
- `verbose-lenovo.log` — Lenovo 단일 verbose 추적 (try_one_account 2회 호출 후 abort)
- `build-38-console.redacted.txt` — Jenkins 빌드 #38 console (cycle-012 PR 머지 직후 reference)

## 본 cycle commit

| commit | 내용 |
|---|---|
| `bf247266` | fix: Jinja2 expression 안 {# #} 주석 syntax error 정정 (HIGH 회귀 수정) |
| (다음) | docs: cycle-014 evidence + 후속 매트릭스 갱신 |

## 검증 명령 재현

```bash
# agent 154 (cloviradmin) 에서:
WS=/home/cloviradmin/jenkins-agent/workspace/hshwang-gather@2
cd $WS && git fetch origin main && git reset --hard origin/main
echo -n '__REDACTED__' > /tmp/.vault_pass_se && chmod 600 /tmp/.vault_pass_se

export INVENTORY_JSON='[{"ip":"10.50.11.162"},{"ip":"10.50.11.231"},{"ip":"10.50.11.232"},{"ip":"10.100.15.2"}]'
export REPO_ROOT=$WS
export ANSIBLE_CONFIG=$WS/ansible.cfg

/opt/ansible-env/bin/ansible-playbook redfish-gather/site.yml \
    -i redfish-gather/inventory.sh \
    --vault-password-file /tmp/.vault_pass_se
```
