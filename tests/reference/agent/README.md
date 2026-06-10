# tests/reference/agent/ — Jenkins Agent + Master 환경 reference

## 수집 도구

`tests/reference/scripts/gather_agent_env.py` — paramiko SSH 기반.

## 수집 항목 (~40개)

- **OS / Kernel**: hostnamectl, uname, /etc/os-release, uptime
- **Java**: java -version, update-alternatives --display java
- **Python**: 다중 버전 (`python` ~ `python3.12`, `/opt/ansible-env/bin/python`), pip freeze (default + ansible_env)
- **Ansible**: --version, ansible-config dump --only-changed, collection list, role list
- **Jenkins**: systemctl status jenkins, /var/lib/jenkins/, id jenkins, /var/lib/jenkins/jobs/
- **Network**: ip addr/route, /etc/resolv.conf, /etc/hosts, ss -tlnp, firewall (firewall-cmd / iptables)
- **Filesystem**: lsblk, df, mount
- **Project**: server-exporter 위치 탐색 (/home/cloviradmin, /opt), ansible.cfg 위치
- **Vault**: find vault.yml 위치
- **수집 도구**: smartctl, ipmitool, nvme, racadm, storcli 버전
- **Redis**: status, redis-cli ping/info
- **Time**: timedatectl, chrony, ntp
- **Process**: ps -eo
- **Logs**: journalctl -p err 최근

## 디렉터리 컨벤션

```text
tests/reference/agent/
├── agent/<ip>/             ← Jenkins Agent
└── jenkins_master/<ip>/    ← Jenkins Master
    └── cmd_<name>.txt
```

## 수집 대상 (2026-04-28)

| Role | IP | 비고 |
|---|---|---|
| Master | 10.100.64.152 | Jenkins UI 호스트 |
| Master | 10.100.64.153 | Jenkins UI 호스트 (HA?) |
| Agent | 10.100.64.154 | ansible 실행 (REQUIREMENTS.md 검증 기준) |
| Agent | 10.100.64.155 | ansible 실행 |

## 활용

1. **REQUIREMENTS.md 검증**: ansible/python/collection/Java 버전 ↔ 문서 명시 버전 정합 (rule 96 외부 계약)
2. **agent 동질성 확인**: 154 vs 155의 환경 diff
3. **vault 위치 / 자격 처리 패턴 확인**

## 재실행

```bash
wsl python3 tests/reference/scripts/gather_agent_env.py --skip-existing
wsl python3 tests/reference/scripts/gather_agent_env.py --role agent
wsl python3 tests/reference/scripts/gather_agent_env.py --target agent-10.100.64.154
```
