# Security Policy — server-exporter

> **[DEPRECATED]** cycle-011 (2026-04-28) 사용자 명시 결정으로 **rule 60 + 보안 정책 자체 해제**. 본 문서는 cycle-011 이전 정책의 역사 reference로 보존. 현재 보안은 cycle-012 vault encrypt + 운영자 권장 수준 (rule 60 의무 없음).
>
> 활성 정책: cycle-011 ADR (`docs/ai/decisions/ADR-2026-04-28-security-policy-removal.md`) + cycle-012 vault encrypt ADR (`docs/ai/decisions/ADR-2026-04-29-vault-encrypt-adoption.md`).

## 1. 비밀값 관리

### Vault 구조
- `vault/<loc>/os/{linux,windows}.yml + vault/<loc>/esxi.yml` — 채널별 자격증명
- `vault/<loc>/redfish/<vendor>.yml` — vendor별 BMC 자격증명

### 원칙
- 모든 vault 파일 ansible-vault encrypt 필수
- 평문 commit 금지 (pre_commit_policy.py 자동 차단)
- 회전: rotate-vault skill로만

## 2. Vault 2단계 로딩 (Redfish 특화)

1. `/redfish/v1/` 무인증 GET → Manufacturer 추출
2. vendor_aliases.yml로 vendor 정규화
3. `vault/<loc>/redfish/<vendor>.yml` 동적 로드
4. 인증으로 본 수집 재개

이 절차로 잘못된 vendor vault 로드 방지 (rule 27 R3).

## 3. Log redaction

`.claude/policy/security-redaction-policy.yaml` 패턴 적용:
- vault 변수 누설
- BMC password / iDRAC user / iLO password / XCC password / CIMC password
- Redfish basic auth header
- WinRM / SSH 자격증명
- 개인키 block
- 내부 IP 예시 (`10.x.x.x` 익명화)

## 4. HTTPS verify 정책

- Redfish: 자체 서명 인증서 일반 → `verify=False` 허용 + 코드 주석 명시
- vSphere: `validate_certs: false` (자체 서명 시) — community.vmware 공통 패턴
- WinRM: HTTPS (5986) + `server_cert_validation=ignore` (자체 서명)
- production: 정식 cert 권장 (운영자 결정)

## 5. callback URL 보안

- 형식: path/token (예: `/api/notify/<job_id>?token=<token>`)
- **금지**: `https://user:pass@host/...` (Jenkins console log 노출)
- 정규화: `url.strip().rstrip('/')` (rule 31 R1)

## 6. Bypass 금지

- `.claude/settings.json`의 `disableBypassPermissionsMode: "disable"` 강제
- CLI `--dangerously-skip-permissions` 사용 금지
- 전역 설정 (`~/.claude/settings.json`) 자율 수정 금지

## 7. Pre-commit 검사

- `pre_commit_policy.py` — 비밀값 파일 / 잔재 어휘 / 평문 password 의심 차단
- `pre_commit_skill_guard.py` — SKILL.md 형식
- `pre_commit_jenkinsfile_guard.py` — cron 변경 advisory
- `pre_commit_harness_drift.py` — surface-counts drift

## 8. 사고 대응

비밀값 노출 발견 시:
1. 즉시 vault rotate (rotate-vault skill)
2. Jenkins credentials 갱신
3. tests/evidence/ 사고 기록 (rule 70)
4. FAILURE_PATTERNS.md `vault-leak` 카테고리 append
5. 외부 시스템 (BMC) password 변경 의뢰

## 관련

- rule 60 (정본)
- rule 27 R3 (Vault 2단계)
- rule 31 (callback URL 무결성)
- policy: `.claude/policy/protected-paths.yaml`, `.claude/policy/security-redaction-policy.yaml`
- skill: rotate-vault, debug-precheck-failure
- agent: security-reviewer, vault-rotator
