#!/bin/bash
# lab 개더링 러너 — WSL 제약 3가지 우회 포함
set -u
cd /mnt/c/github/server-exporter
export ANSIBLE_CONFIG=/mnt/c/github/server-exporter/ansible.cfg   # /mnt/c world-writable
export REPO_ROOT=/mnt/c/github/server-exporter
OUT="$1"; CH="$2"; KEY="$3"; shift 3
mkdir -p "$OUT"
VP=$(mktemp); cp "$REPO_ROOT/.vault_pass" "$VP"; chmod 600 "$VP"   # exec bit 회피
INV=$(mktemp); printf '#!/bin/sh\nexec python3 %s/%s-gather/inventory.sh "$@"\n' "$REPO_ROOT" "$CH" > "$INV"
chmod +x "$INV"                                                    # CRLF shebang 회피
for ip in "$@"; do
  f="$OUT/${CH}_${ip}.json"
  [ -s "$f" ] && { echo "[skip] $CH $ip (이미 있음)"; continue; }
  INVENTORY_JSON="[{\"$KEY\":\"$ip\"}]" timeout 600 \
    ansible-playbook -i "$INV" "$CH-gather/site.yml" \
      --vault-password-file "$VP" -e se_location=git > "$f" 2>"$OUT/${CH}_${ip}.err"
  rc=$?
  st=$(python3 -c "
import json,sys
try:
    d=json.load(open('$f'))
    d=d[0] if isinstance(d,list) else d
    print(d.get('status','?'), d.get('meta',{}).get('adapter_id','?'),
          (d.get('correlation') or {}).get('serial_number','-'))
except Exception as e: print('PARSE_FAIL', str(e)[:40])
" 2>/dev/null)
  echo "[$CH] $ip rc=$rc  $st"
done
rm -f "$VP" "$INV"
