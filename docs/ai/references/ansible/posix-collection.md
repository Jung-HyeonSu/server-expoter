# ansible.posix Collection — 핵심 reference

> Source: https://docs.ansible.com/ansible/latest/collections/ansible/posix/index.html
> Fetched: 2026-04-27
> Version: ansible.posix 2.1.0
> 사용 위치 (server-exporter): os-gather Linux Play2 (간접 — synchronize / authorized_key 등 운영 보조)

## 주요 모듈

| Module | 용도 | server-exporter 활용 |
|---|---|---|
| `synchronize` | rsync wrapper (양방향) | (직접 사용 없음, 운영 보조 가능) |
| `mount` | filesystem mount 관리 | (수집 전용이라 직접 사용 안 함) |
| `sysctl` | 커널 파라미터 | (수집 시 read-only) |
| `firewalld` | firewalld port/service | precheck 디버깅 시 운영자 보조 |
| `selinux` | SELinux 정책 / 상태 | os-gather Linux의 SELinux 섹션 (raw fallback에서 직접 활용) |
| `seboolean` | SELinux boolean | (필요 시) |
| `authorized_key` | SSH key 추가/제거 | Vault 회전 시 운영자 보조 |
| `at` | one-time 작업 스케줄 | (직접 사용 없음) |
| `patch` | GNU patch 적용 | (직접 사용 없음) |

## SELinux (server-exporter Linux gather 활용)

raw fallback 모드 (rule 10 R4 + rule 22 (fragment-philosophy) "Linux 2-Tier")에서:

```yaml
- name: SELinux 상태 (Python ok 모드)
  selinux:
    state: enforcing
  check_mode: true   # 변경 안 함, 상태만
  register: _selinux_state

- name: SELinux 상태 (raw 모드 — Python 미설치)
  raw: getenforce
  register: _selinux_raw

- set_fact:
    _selinux_status: "{{ _selinux_raw.stdout | trim | lower }}"  # enabled / disabled
```

Round 2 수정에서 `getenforce` 출력을 `enabled` / `disabled`로 정규화.

## 요구사항

- ansible-core 2.15.0+
- server-exporter 검증 기준: ansible.posix 2.1.0

## 적용 rule / 관련

- rule 10 R4 (Linux 2-tier raw fallback)
- rule 30 (integration-redfish-vmware-os) — SSH 채널
- 정본: rule 22 (fragment-philosophy) "Linux 2-Tier Gather"
- reference: `docs/ai/references/ansible/builtin-modules.md`
