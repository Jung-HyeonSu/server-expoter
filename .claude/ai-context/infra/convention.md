# Infra Convention — server-exporter

> Jenkins / Agent / Vault / Redis / ansible.cfg 작업 컨벤션.
> 정본: `docs/` 문서, `docs/operate/04-pipeline-runtime.md`, `docs/operate/08-ansible-config.md`.

## 1. Jenkins 파이프라인 3종

| Jenkinsfile | 용도 | 호출자 |
|---|---|---|
| `Jenkinsfile` | 메인 (3-channel 통합) | 일반 호출자 |
| `Jenkinsfile_portal` | Portal 호출 (agent-master 망 분리: Callback은 master) | Portal |

각 파이프라인 4-Stage:
1. **Validate** — 입력값 (loc / target_type / inventory_json) 검증
2. **Gather** — ansible-playbook 실행
3. **Validate Schema** — field_dictionary 정합 (FAIL 게이트)
4. **E2E Regression** — pytest baseline (FAIL 게이트)
5. **Post** — json_only callback → JSON 출력

## 2. Agent 노드 (`docs/operate/02-agent-node.md`)

운영 토폴로지:
- master (10.100.64.154) — Jenkins controller, 검증 기준 Agent
- agent (loc 별 label — 정본은 `common/vars/locations.yml`) — gather 실행
- 망 분리: Ingest / Callback 단계는 master에서, gather는 agent에서

Agent 요구사항:
- ansible-core 2.20.3
- Python 3.12.3 venv (`/opt/ansible-env/`)
- pip: pywinrm / pyvmomi / redis / jmespath / netaddr / lxml
- collections: ansible.windows / community.vmware / ansible.posix / community.general / community.windows / ansible.utils

## 3. Vault 구조

```
vault/
├── linux.yml              # SSH 사용자/비밀번호 (Linux gather)
├── windows.yml            # WinRM 사용자/비밀번호 (Windows gather)
├── esxi.yml               # vSphere 사용자/비밀번호 (ESXi gather)
└── redfish/
    ├── dell.yml           # iDRAC 사용자/비밀번호
    ├── hpe.yml            # iLO 사용자/비밀번호
    ├── lenovo.yml         # XCC 사용자/비밀번호
    ├── supermicro.yml     # BMC 사용자/비밀번호
    ├── cisco.yml          # CIMC 사용자/비밀번호
    └── generic.yml        # 알 수 없는 vendor fallback
```

모든 vault 파일은 ansible-vault encrypt 운영 권장 (cycle-011: rule 60 해제 + cycle-012: 8 vault encrypt 채택).

회전: `rotate-vault` skill 절차 — 운영자 직접 실행 (cycle-011: vault-rotator agent 제거).

## 4. Redis fact cache

ansible.cfg `fact_caching = redis`로 Ansible fact를 Redis에 캐시. 같은 host 재수집 시 일부 fact 재사용 → 시간 단축. 만료 정책은 ansible.cfg `fact_caching_timeout`.

설정 정본: `docs/operate/02-agent-node.md`.

## 5. ansible.cfg 핵심

- `callback_plugins = callback_plugins` (json_only 활성)
- `stdout_callback = json_only`
- `fact_caching = redis`
- `roles_path`, `collections_paths`, `library` 경로
- `host_key_checking = False` (Agent ↔ target 신뢰)

정본: `docs/operate/08-ansible-config.md`.

## 6. callback URL 무결성 (rule 31)

호출자에게 결과 통지하는 callback URL은 공백 / 후행 슬래시 방어 필수 (이전 commit `4ccc1d7` fix).

```python
url = url.strip().rstrip('/')
```

## 7. agent-master 망 분리

- `Jenkinsfile_portal` 의 `Resolve Location` 과 `Callback` → master(`built-in`) 에서 실행
- Callback (Portal 호출 등) → master에서 실행 (`Jenkinsfile_portal`)
- gather는 agent에서 실행

이유: 보안 / 네트워크 정책 / 권한 분리.

## 8. 자주 호출하는 Skill / Agent

- `task-impact-preview` — Jenkinsfile / ansible.cfg 변경 전
- `scheduler-change-playbook` — Jenkins cron 변경
- `investigate-ci-failure` — Jenkins 실패 분석
- `rotate-vault` — Vault 회전
- agent: `jenkins-refactor-worker`, `jenkinsfile-engineer`, `deploy-orchestrator`, `release-manager`, `ansible-perf-investigator` (cycle-011: vault-rotator 제거)
