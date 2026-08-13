#!/usr/bin/env python3
"""Secret Leak Gate — 저장소 tracked content 에 평문 자격증명이 남아 있는지 검사한다.

왜 (2026-08-12)
---------------
전수 조사 결과 tracked file 391 개에 실 자격증명 10 종이 평문으로 있었다. 정리한 뒤
**다시 들어오는 것**을 막을 자동 검사가 없어서 이 게이트를 만든다.

두 가지 모드를 함께 쓴다.

1) digest 모드 (기본, vault 비밀번호 불필요)
   `tests/secret_guard.py` 가 들고 있는 sha256 앞 8자리로 대조한다. 값이 없으므로
   이 스크립트도, 그 표도 자격증명이 아니다. 이미 회전돼 원문을 복원할 수 없는 과거
   세대까지 잡는 유일한 방법이다. 비용 때문에 **변경된 파일만** 훑는다(pre-commit 용).

2) literal 모드 (`--vault-password-file` 을 줄 때만)
   운영 Vault 를 복호화해 지금 살아 있는 자격증명 문자열을 얻고 tracked 전체를
   부분문자열로 검사한다. 빠르고 확정적이다. Jenkins 처럼 vault 비밀번호가 이미
   있는 환경에서 전수 검사용으로 쓴다.

무엇을 잡지 않는가
------------------
`admin` / `password` / `ADMIN` 같은 **벤더가 공개한 공장 기본값이자 사전 단어**는
대상이 아니다. 자격증명으로서의 정보가 없고, 넣으면 평범한 산문까지 걸려 게이트가
무력해진다 (이 저장소에서 각각 627 / 433 개 파일에 등장한다). 근거는
`docs/operate/05-vault.md` 의 벤더 기본값 표.

사용:
    python scripts/ai/verify_no_plaintext_secret.py                 # 변경분 digest 검사
    python scripts/ai/verify_no_plaintext_secret.py --all           # tracked 전체 digest 검사(느림)
    python scripts/ai/verify_no_plaintext_secret.py --vault-password-file <path>
종료 코드: 0 = 통과, 1 = 평문 자격증명 발견, 2 = 실행 오류
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tests"))

try:
    from secret_guard import KNOWN_SECRET_DIGESTS, _LENGTHS  # type: ignore
except Exception as exc:  # pragma: no cover - 설치 문제만 여기로 온다
    print(f"[FAIL] tests/secret_guard.py 를 읽지 못했습니다: {exc}")
    raise SystemExit(2)

MAX_FILE_BYTES = 4 * 1024 * 1024
_RUN = re.compile(r"[!-~]+")
_SKIP_DIRS = {".git", "__pycache__", "node_modules"}


def _git(*args: str) -> list[str]:
    out = subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True)
    if out.returncode != 0:
        return []
    return [line for line in out.stdout.splitlines() if line]


def _read(rel: str) -> str:
    path = REPO / rel
    try:
        if not path.is_file() or path.stat().st_size > MAX_FILE_BYTES:
            return ""
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _digest8(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:8]


def _candidate_starts(run: str) -> list[int]:
    """자격증명이 시작될 수 있는 위치만 고른다.

    모든 위치에서 모든 길이를 해싱하면 저장소 규모에서 끝나지 않는다(수천만 회).
    누출된 자격증명은 실제로는 토큰 경계에서 시작한다 — 토큰 전체이거나
    (`ansible_password=<값>`, `echo <값> | sudo -S`), 구분자 바로 뒤에서 시작한다.
    그래서 **토큰 시작 위치와 영숫자가 아닌 문자 다음 위치**만 후보로 본다.
    끝에 붙는 형태(`<값>Infra`)는 접미사 검사로 따로 잡는다.
    """
    starts = [0]
    for i in range(1, len(run)):
        if not run[i - 1].isalnum():
            starts.append(i)
    return starts


def scan_digest(rels: list[str]) -> dict[str, list[str]]:
    """알려진 digest 와 일치하는 부분문자열이 있는 파일을 찾는다."""
    hits: dict[str, list[str]] = {}
    for rel in rels:
        text = _read(rel)
        if not text:
            continue
        for run in _RUN.findall(text):
            size = len(run)
            starts = _candidate_starts(run)
            for length in _LENGTHS:
                if length > size:
                    continue
                for i in starts:
                    if i + length > size:
                        continue
                    d = _digest8(run[i:i + length])
                    if d in KNOWN_SECRET_DIGESTS:
                        hits.setdefault(d, [])
                        if rel not in hits[d]:
                            hits[d].append(rel)
                # 접미사 형태 (`<값>` 뒤에 문자열이 더 붙은 경우의 역방향)
                d = _digest8(run[size - length:])
                if d in KNOWN_SECRET_DIGESTS:
                    hits.setdefault(d, [])
                    if rel not in hits[d]:
                        hits[d].append(rel)
    return hits


def vault_literals(vault_password_file: str) -> list[str]:
    """운영 Vault 를 복호화해 살아 있는 자격증명 문자열을 모은다."""
    import glob

    import yaml
    from ansible.parsing.vault import VaultLib, VaultSecret

    secret = Path(vault_password_file).read_bytes().strip()
    lib = VaultLib([("default", VaultSecret(secret))])
    values: set[str] = set()
    for path in glob.glob(str(REPO / "vault" / "**" / "*.yml"), recursive=True):
        raw = Path(path).read_bytes()
        if raw.lstrip().startswith(b"$ANSIBLE_VAULT"):
            raw = lib.decrypt(raw)
        data = yaml.safe_load(raw) or {}
        for account in data.get("accounts") or []:
            pw = account.get("password")
            if isinstance(pw, str) and pw:
                values.add(pw)
        for key in ("ansible_password", "ansible_become_password"):
            pw = data.get(key)
            if isinstance(pw, str) and pw:
                values.add(pw)
    values.add(secret.decode("utf-8", "replace"))
    # 자명한 벤더 공장 기본값은 대상에서 뺀다 (위 docstring 참조).
    trivial = {_digest8(t) for t in
               ("admin", "ADMIN", "password", "Password", "root", "calvin",
                "Admin@9000", "USERID", "changeme", "superuser")}
    return [v for v in values if _digest8(v) not in trivial]


def scan_literal(rels: list[str], literals: list[str]) -> dict[str, list[str]]:
    hits: dict[str, list[str]] = {}
    for rel in rels:
        text = _read(rel)
        if not text:
            continue
        for lit in literals:
            if lit in text:
                hits.setdefault(_digest8(lit), []).append(rel)
    return hits


def _report(label: str, hits: dict[str, list[str]]) -> bool:
    if not hits:
        print(f"[PASS] {label} — 평문 자격증명 0건")
        return True
    print(f"[FAIL] {label} — 평문 자격증명 발견")
    for digest, files in sorted(hits.items(), key=lambda kv: -len(kv[1])):
        print(f"    sha256-8={digest}  files={len(files)}")
        for rel in files[:10]:
            print(f"        {rel}")
        if len(files) > 10:
            print(f"        ... 외 {len(files) - 10}건")
    print("    (값 자체는 출력하지 않습니다. 해당 파일에서 자격증명을 제거하세요.)")
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description="평문 자격증명 검사")
    ap.add_argument("--all", action="store_true",
                    help="tracked 전체를 digest 검사 (느림)")
    ap.add_argument("--base", default="HEAD",
                    help="변경분 비교 기준 (기본 HEAD)")
    ap.add_argument("--vault-password-file",
                    help="주면 Vault 를 복호화해 tracked 전체를 literal 검사")
    args = ap.parse_args()

    tracked = [r for r in _git("ls-files")
               if not any(part in _SKIP_DIRS for part in r.split("/"))]
    if not tracked:
        print("[FAIL] git ls-files 결과가 비었습니다 (저장소 안에서 실행하세요).")
        return 2

    ok = True
    if args.all:
        ok &= _report(f"digest 검사 (tracked {len(tracked)}건)", scan_digest(tracked))
    else:
        changed = sorted(set(_git("diff", "--name-only", args.base)
                             + _git("diff", "--name-only", "--cached", args.base)
                             + _git("ls-files", "--others", "--exclude-standard")))
        changed = [r for r in changed if r in set(tracked) or (REPO / r).is_file()]
        if changed:
            ok &= _report(f"digest 검사 (변경 {len(changed)}건)", scan_digest(changed))
        else:
            print("[SKIP] 변경된 파일이 없습니다 — digest 검사 생략")

    if args.vault_password_file:
        try:
            literals = vault_literals(args.vault_password_file)
        except Exception as exc:
            print(f"[FAIL] Vault 복호화 실패: {type(exc).__name__}")
            return 2
        ok &= _report(f"literal 검사 (운영 자격 {len(literals)}종 × tracked {len(tracked)}건)",
                      scan_literal(tracked, literals))
    else:
        print("[INFO] --vault-password-file 미지정 — 운영 자격 literal 전수 검사는 건너뜁니다.")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
