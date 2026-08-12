#!/usr/bin/env python3
"""[DEPRECATED 2026-08-12] 평문 자격증명을 담고 있어 환경변수 기반으로 바꿨다.
   대상 경로(vault/redfish/*.yml)는 flat vault 제거(adc99570) 로 더는 존재하지 않는다.
   실행 전 SE_LAB_RECOVERY_PASS 를 설정해야 한다.

cycle-016 후속 — 모든 redfish vault + linux/windows/esxi vault 에 lab recovery 추가.

기존 add_lab_recovery_to_dell_vault.py 의 일반화. vault/.lab-credentials.yml
에 정의된 lab 자격증명을 각 vault 의 accounts[] 에 recovery role 로 주입.

agent 154 SSH → ansible-vault decrypt → accounts list 끝에 새 entry append → encrypt → SCP back.

Idempotent: lab_* label 이 있으면 skip.
"""
from __future__ import annotations
import os
import sys
import paramiko

AGENT_HOST = '10.100.64.154'
AGENT_USER = 'cloviradmin'
AGENT_PASS = '__REDACTED__'
WS = '/home/cloviradmin/jenkins-agent/workspace/hshwang-gather'

# 각 vault 에 추가할 lab recovery 자격
TARGETS: list[tuple[str, list[dict]]] = [
    ('vault/redfish/hpe.yml', [
        {'username': 'admin', 'password': os.environ.get('SE_LAB_RECOVERY_PASS', ''), 'label': 'lab_hpe_admin', 'role': 'recovery'},
    ]),
    ('vault/redfish/lenovo.yml', [
        {'username': 'USERID', 'password': os.environ.get('SE_LAB_RECOVERY_PASS', ''), 'label': 'lab_lenovo_userid', 'role': 'recovery'},
    ]),
    ('vault/redfish/cisco.yml', [
        {'username': 'admin', 'password': os.environ.get('SE_LAB_RECOVERY_PASS', ''), 'label': 'lab_cisco_admin', 'role': 'recovery'},
    ]),
]


def run(ssh: paramiko.SSHClient, cmd: str, expect_exit: int | None = 0) -> str:
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=60)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    rc = stdout.channel.recv_exit_status()
    if expect_exit is not None and rc != expect_exit:
        raise RuntimeError(f'cmd={cmd!r} rc={rc}\nstdout={out}\nstderr={err}')
    return out


def add_recovery(ssh: paramiko.SSHClient, vault_path: str, recoveries: list[dict]) -> bool:
    decrypted = run(ssh, f'cd {WS} && /opt/ansible-env/bin/ansible-vault view --vault-password-file=/tmp/.vault_pass {vault_path}')
    # idempotent check
    skipped = []
    todo = []
    for r in recoveries:
        if f"label: {r['label']}" in decrypted or f"label: \"{r['label']}\"" in decrypted:
            skipped.append(r['label'])
        else:
            todo.append(r)
    if not todo:
        print(f'[SKIP] {vault_path}: all labels already present {skipped}')
        return False

    # accounts list 끝에 추가
    lines = decrypted.rstrip('\n').split('\n')
    in_accounts = False
    last_account_idx = -1
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('accounts:'):
            in_accounts = True
            continue
        if in_accounts:
            if line.lstrip().startswith('-'):
                last_account_idx = i
            elif line.strip() and not line.startswith(' '):
                in_accounts = False

    if last_account_idx < 0:
        print(f'[ERR] {vault_path}: accounts list not found')
        return False

    indent = len(lines[last_account_idx]) - len(lines[last_account_idx].lstrip())
    prefix = ' ' * indent
    insert_idx = last_account_idx + 1
    while insert_idx < len(lines) and (lines[insert_idx].startswith(' ' * (indent + 2)) or not lines[insert_idx].strip()):
        insert_idx += 1

    new_blocks: list[str] = []
    for r in todo:
        new_blocks.extend([
            f'{prefix}- username: {r["username"]}',
            f'{prefix}  password: {r["password"]}',
            f'{prefix}  label: {r["label"]}',
            f'{prefix}  role: {r["role"]}',
        ])
    new_lines = lines[:insert_idx] + new_blocks + lines[insert_idx:]
    new_yaml = '\n'.join(new_lines) + '\n'

    import base64
    b64 = base64.b64encode(new_yaml.encode('utf-8')).decode('ascii')
    run(ssh, f'echo "{b64}" | base64 -d > /tmp/vault-new.yml')
    run(ssh, f'/opt/ansible-env/bin/ansible-vault encrypt --vault-password-file=/tmp/.vault_pass /tmp/vault-new.yml')
    run(ssh, f'cp {WS}/{vault_path} {WS}/{vault_path}.cycle016.bak')
    run(ssh, f'cp /tmp/vault-new.yml {WS}/{vault_path}')
    print(f'[CHG] {vault_path}: added {[r["label"] for r in todo]}')
    return True


def main() -> int:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(AGENT_HOST, username=AGENT_USER, password=AGENT_PASS, timeout=30, allow_agent=False, look_for_keys=False)
    try:
        run(ssh, "echo '__REDACTED__' > /tmp/.vault_pass && chmod 600 /tmp/.vault_pass")
        changed: list[str] = []
        for vault_path, recoveries in TARGETS:
            if add_recovery(ssh, vault_path, recoveries):
                changed.append(vault_path)
        if changed:
            # SCP back to local
            sftp = ssh.open_sftp()
            for vp in changed:
                local = f'C:/github/server-exporter/{vp}'
                sftp.get(f'{WS}/{vp}', local)
                print(f'  downloaded → {local}')
            sftp.close()
        run(ssh, 'rm -f /tmp/.vault_pass /tmp/vault-new.yml')
        return 0
    finally:
        ssh.close()


if __name__ == '__main__':
    sys.exit(main())
