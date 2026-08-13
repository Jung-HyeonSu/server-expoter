# JENKINS_PIPELINES — server-exporter

> Jenkins multi-pipeline 2종 카탈로그. rule 28 #4-5 측정 대상 (TTL 7-14일).
> 실측 (`grep stage Jenkinsfile*`) — 2026-04-29 (cycle-015 — `grafana 파이프라인(제거됨)` 제거됨).

## 2종 Pipeline 4-Stage 매트릭스 (실측)

| Pipeline | Stage 1 | Stage 2 | Stage 3 | Stage 4 |
|---|---|---|---|---|
| `Jenkinsfile` | Validate | Gather | Validate Schema | **E2E Regression** |
| `Jenkinsfile_portal` | Validate | Gather | Validate Schema | **Callback** (호출자 통보) |

> **cycle-015 변경**: `grafana 파이프라인(제거됨)` 삭제 (사용자 명시 결정 — Grafana 적재 미사용).

**[INFO]** Plan/design 문서에서 "4-Stage = Validate/Gather/Validate Schema/**E2E Regression**" 으로 일반화 표기했으나, 실측 결과 **Stage 4가 Jenkinsfile별로 다름**.

## Stage별 책임

| Stage | 공통 (모든 2종) | Stage 4 차이 |
|---|---|---|
| 1. Validate | 입력 형식 (target_type / loc / inventory_json) | — |
| 2. Gather | ansible-playbook 실행 (해당 채널) | — |
| 3. Validate Schema | field_dictionary 정합 | — |
| 4. (pipeline별) | — | Jenkinsfile: pytest baseline 회귀(tests/e2e) + HPE 에뮬레이터 오프라인 회귀(tests/integration -m "not live", 2026-06-08) — 별도 호출 |
| | — | Jenkinsfile_portal: 호출자 callback (Callback) |

## agent-master 망 분리 (이전 commit 8bd80c1 / 8b2f128 참조)

| Stage | Jenkinsfile | Jenkinsfile_portal |
|---|---|---|
| Validate | master | master |
| Gather | agent (loc) | agent |
| Validate Schema | master | master |
| Stage 4 | master (pytest) | **master (Callback)** |

`Callback`(Portal)은 망 분리 정책에 따라 **master에서 실행**.

## vault binding (cycle-012 / 2026-06-18 갱신)

Jenkins credential `server-gather-vault-password` (type: **Secret text**) 사용 — 메인 `Jenkinsfile` 과
`Jenkinsfile_portal` **둘 다 동일** credential. `withCredentials` 가 `$VAULT_PASSWORD` 를 주입(콘솔 마스킹),
Pipeline 이 런타임 임시파일(chmod 600)에 써서 `--vault-password-file` 로 ansible-playbook 에 넘기고 종료 시 삭제.

| 항목 | 값 |
|---|---|
| credential ID | `server-gather-vault-password` |
| credential type | Secret text |
| 패턴 | `withCredentials([string(credentialsId: 'server-gather-vault-password', variable: 'VAULT_PASSWORD')]) { ... }` |
| ansible-playbook 인자 | `--vault-password-file=<임시파일>` (VAULT_PASSWORD → mktemp/chmod 600 → 종료 시 삭제) |
| 적용 stage | Stage 2 (Gather) — 2종 Jenkinsfile 모두 |

**위치 실측 (2026-06-18)**:
- `Jenkinsfile:157-184` (Stage 2 Gather — ansiblePlaybook step, extras 로 `--vault-password-file`)
- `Jenkinsfile_portal:152-177` (Stage 2 Gather — sh ansible-playbook, `withCredentials` 래핑)

> **2026-06-18 변경**: `Jenkinsfile_portal` 의 임시 하드코딩 패스워드(`24677f57`)를 제거하고 메인 `Jenkinsfile`
> 과 동일 Secret text credential 로 통일. 이전 catalog 의 "Secret File / `file()`" 표기는 stale 였음(실제는
> Secret text / `string()`).

**vault encrypt 상태 (cycle-012)**: 8 vault 파일 (linux/windows/esxi + redfish/{dell,hpe,lenovo,supermicro,cisco}) 모두 ansible-vault AES256 encrypt 완료. 평문 password 더 이상 commit 안 됨.

**참조**: `docs/operate/01-jenkins-master.md` (credential 등록 절차).

## cron 인벤토리 (rule 28 #5)

각 Jenkinsfile의 `triggers` 블록 — 실 환경 (Jenkins controller)에서 측정. 본 catalog에 갱신 시 사용자 명시 승인 (rule 80 + 92 R5).

## callback URL (rule 31)

Jenkinsfile_portal의 Stage 4 Callback이 호출자에게 결과 통지:
- 전송: **HTTP Request 플러그인 `httpRequest()` 스텝** (curl/셸 미사용 — 2026-06-22 전환). `validResponseCodes:'100:599'` 로 비-2xx 에도 예외 미발생 → status 직접 판정 (graceful, rule 31 R2). `ignoreSslErrors` 미설정 → SSL 검증 유지.
- 정규화: `url.strip().rstrip('/')` (commit 4ccc1d7 fix)
- Method: POST (`Content-Type: application/json`)
- Body: `{loc, deploymentEnvironmentId, gatherInfoJson:[...]}` — gatherInfoJson 은 callback_plugins/json_only.py JSON envelope (rule 20) 라인 배열
- 재시도: 3회 + backoff(attempt*10s), 최종 실패 시 unstable (빌드 fail 아님 — rule 31 R2)
- 보안 권장: URL에 user:pass 형식 금지 (path/token만 — cycle-011 rule 60 해제 후 운영 권장 수준)

## 갱신 trigger (rule 28 #4 / #5)

- TTL 7-14일
- Jenkinsfile* 수정
- cron 표현식 변경 (사용자 명시 승인 필수)
- 새 Jenkinsfile 추가

## 측정 명령

```bash
grep -E "stage\s*\(" Jenkinsfile Jenkinsfile_portal
grep -E "callback_url|triggers|cron" Jenkinsfile*
```

## 정본 reference

- `Jenkinsfile`, `Jenkinsfile_portal` (정본)
- `docs/operate/01-jenkins-master.md`, `docs/operate/03-job-registration.md`, `docs/operate/04-pipeline-runtime.md`
- `.claude/ai-context/infra/convention.md`
- `docs/ai/references/jenkins/pipeline-syntax.md`

## 후속 작업 (사용자 결정)

- [x] rule 80 R1-A에 pipeline별 Stage 4 차이 명시 (cycle-006) — closed 2026-04-28 full-sweep
- [x] vault encrypt + credential `server-gather-vault-password` 등록 (cycle-012)
- [x] **grafana 파이프라인(제거됨) 제거** (cycle-015, 사용자 명시 결정)
- [ ] Jenkins console에서 cron 표현식 실측 + 본 catalog 갱신
- [ ] OPS-1 빌드 시범 1회 후 envelope `meta.auth.fallback_used` 값 추가 검증
