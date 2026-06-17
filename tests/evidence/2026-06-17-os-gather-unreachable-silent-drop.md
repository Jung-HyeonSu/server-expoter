# OS gather — SSH unreachable silent host-drop (빌드 #29 진단)

- 일시: 2026-06-17
- 채널: os (Linux)
- 대상: Jenkins `portal/gather/gatherOS` #27~#29 (FAILURE)
- 증상: "OS 정보 개더링이 안됨" — gather_output.json 비어있음 → Callback `error` → 빌드 FAILURE

## 증거 (Jenkins API, read-only)

| build | commit | result | gather 출력 |
|---|---|---|---|
| 25/26 | (이전, 다른 host 202-254) | UNSTABLE | 있음 (53 host 중 26 envelope, Stashed 1) |
| 27/28 | 0c66b993 (redfish OEM) | FAILURE | 없음 (Stashed 0) |
| 29 | 443d4a68 (workspace) | FAILURE | 없음 (Stashed 0) |

- build #29 params: target_type=os, hosts=`10.100.64.161`,`10.100.64.165`, loc=git, verbosity=0
- build #29 console: ansible-playbook 호출 후 `[WARNING] Could not match supplied host pattern, ignoring: _os_failed` +
  `[WARNING] reset_connection ... when conditional` 2줄 뒤 `FATAL: ... Ansible playbook execution failed` → **그 외 출력 0**.
- build #26: hosts=53 인데 OUTPUT envelope **26개만** (전부 `status:"failed"`) → **27개 host 가 envelope 없이 증발**.

## 근본 원인

1. **코드 결함 (silent total failure):** `os-gather/tasks/try_one_credential.yml` 의 SSH/WinRM probe 가
   `failed_when:false` 만 있고 `ignore_unreachable:true` 누락. SSH 인증 실패는 ansible 에서 `failed` 가 아닌
   **`unreachable`** 로 분류됨 → `failed_when:false` 가 못 잡음 → host 가 block/rescue/always(OUTPUT) 를
   우회하고 play 에서 제거 → envelope 0 + exit 비정상. (build #26 의 27 host 증발, build #29 의 161/165 0 envelope 가 동일 메커니즘.)
2. **관측 결함:** `callback_plugins/json_only.py` 가 `v2_runner_on_unreachable`/`v2_runner_on_failed` 를
   OUTPUT task 외에는 전부 suppress → 콘솔에 실패 사유가 전혀 안 남음.
3. **운영 원인 (데이터 미수집의 실제 사유):** 161/165 는 port 22 probe 는 통과(linux 분류, `_os_failed` 빈
   group 1줄만 경고)했으나 SSH transport/auth 단계에서 실패 → unreachable. 즉 **SSH 인증/handshake 실패**
   (vault 자격 불일치 또는 host sshd 설정). 데이터를 받으려면 161/165 자격/접속 확인 필요 (사용자 도메인).

## 조치

- `try_one_credential.yml` linux/windows probe 2종에 `ignore_unreachable: true` 추가.
  → unreachable host 보존 → evaluate=false → 후보 소진 → site.yml `abort if all credentials failed` fail →
  rescue → `build_failed_output` → **정상 `status:"failed"` envelope** (diagnosis 포함). 빌드 FAILURE→UNSTABLE.
- (잔여 edge case) vault `accounts` 가 비어 있으면 `abort if all credentials failed` 가 skip 되어 본 gather
  task 에서 unreachable 재발 가능 — 현 incident 범위 밖, 후속 검토.

## 검증

- `python -c yaml.safe_load_all` PASS (probe 2종 ignore_unreachable=True 확인). ansible syntax-check 는
  Windows 환경 미설치로 미실행 (env 제약).
- 실 동작 검증(re-run #30)은 사용자 승인 후 — 기대값: 161/165 각 `status:"failed"` envelope, 빌드 UNSTABLE.

## FAILURE_PATTERNS

- `ansible-unreachable-escapes-rescue`: SSH/WinRM 인증 실패가 unreachable 로 분류되어 `failed_when:false`/
  block-rescue 를 우회. probe·연결 task 에는 `ignore_unreachable:true` 필수.
