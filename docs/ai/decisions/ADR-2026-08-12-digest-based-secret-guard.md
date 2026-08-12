# ADR-2026-08-12 — 누출 가드를 평문이 아니라 digest 로 한다

- 상태: Accepted
- 일자: 2026-08-12
- 결정 주체: 사용자 지시(§10~§13)에 따라 AI 가 설계·구현, 사용자 승인 대기 없이 진행
- 관련: rule 60 (security-and-secrets), rule 70 R8, rule 96 R4
- Evidence: `tests/evidence/2026-08-12-plaintext-secret-sanitization.md`

---

## 1. 컨텍스트 (Why)

저장소 전수 조사에서 **tracked file 391개에 실제 자격증명 10종이 평문으로** 남아 있었다.
그중 가장 아픈 것은 위치가 아니라 **정체**였다: 8개가 "비밀값이 결과에 새면 안 된다" 를
검사하는 **누출 방지 테스트 자신**이었다.

```python
SECRET_VALUE_PATTERNS = tuple(re.compile(p) for p in (
    r"<실제 비밀번호>",   # 이 값이 나오면 실패시키려고 적어 둔 것
    ...
))
```

검사 대상을 검사 코드가 평문으로 들고 있으니, 가드를 강화할수록 누출 표면이 커진다.
게다가 이 목록은 **회전을 따라가지 못했다** — 표준 계정 비밀번호가 3세대 회전하는 동안
가드는 gen1 만 알고 있었고, 그 시점의 **현행 값(gen3)은 목록에 없었다.** 즉 정작 지금
새면 안 되는 값은 검사되지 않고, 이미 죽은 값만 검사하고 있었다.

동시에 `tests/reference/os` 269개, `tests/reference/agent` 20개처럼 **운영 캡처 산출물**에
`echo <PW> | sudo -S`, `fact_caching_connection = host:6379:0:<PW>` 형태로 값이 그대로
들어가 있었다. 이들은 runtime 이 읽지 않는 증거 파일이므로 값이 있을 이유가 없다.

## 2. 결정 (What)

**자격증명 평문을 저장소에서 전부 제거하고, 가드는 sha256 앞 8자리로 대조한다.**

1. `tests/secret_guard.py` 신설 — `(digest8, length)` 표 + 합성 canary + 구조 패턴.
   `find_known_secrets(text)` 가 후보 부분문자열의 digest 를 표와 대조한다.
   digest 는 원문을 복원할 수 없으므로 저장소에 남아도 자격증명이 아니다.
2. **입력으로 쓰이던 실 자격증명은 합성 canary 로** 바꾼다. 테스트 의미는 그대로이고
   (입력한 자격이 출력에 새는가), 입력과 검사 대상이 같은 값이 되어 오히려 정확해진다.
3. **공개된 벤더 공장 기본값(`admin` / `password` / `ADMIN` / 벤더 문서에 실린 값)은
   가드 표에 넣지 않는다.**
4. `scripts/ai/verify_no_plaintext_secret.py` 신설 — vault 비밀번호 없이도 도는 digest
   게이트(변경분/전수) + vault 비밀번호가 있을 때의 literal 전수 게이트.

## 3. 결과 (Impact)

- tracked 17,982개 전수 검사에서 **평문 자격증명 0건** (digest·literal 양쪽).
- 회전되어 원문 복원이 불가능해진 4종은 저장소에서 더 이상 재구성되지 않는다.
- 가드가 **회전에 강해졌다**: 값이 바뀌어도 digest 한 줄만 갱신하면 되고, 갱신을 잊어도
  구조 패턴과 canary 가 남는다.
- 실패 메시지에 평문이 찍히지 않는다 — digest 만 보고된다.
- 길이(8~15)를 표에 남긴다. 성능 때문이다(모든 길이를 훑으면 저장소 규모에서 끝나지
  않는다). 공격자가 이미 가정하는 범위이고, 그 대가로 평문 10종을 제거했다.
- 게이트는 토큰 경계·구분자 다음·접미사만 후보로 본다. 전 위치 해싱은 수천만 회라
  현실적이지 않다. 실제 누출은 이 위치들에서 발생한다.

## 4. 대안 비교 (Considered)

| 대안 | 왜 택하지 않았나 |
|---|---|
| 평문 목록을 그대로 두고 파일만 `.gitignore` | 이미 tracked 다. ignore 해도 history 와 현재 HEAD 에 남는다. |
| 가드를 삭제 | 누출 검사 자체가 사라진다. 문제는 가드가 아니라 저장 방식이었다. |
| 런타임에 Vault 를 열어 실제 값으로 검사 | 테스트가 vault 비밀번호를 요구하게 되어 hermetic 이 깨진다(`tests/integration/conftest.py` 의 네트워크 차단 정신과 충돌). CI 도 복잡해진다. |
| 전체 위치 × 전체 길이 digest 스캔 | tracked 전수에서 수천만~수억 회 해싱. 게이트가 실용성을 잃는다. |
| 공개 기본값도 가드 표에 포함 | `admin` / `password` 는 627 / 433개 파일에 등장한다. 오탐으로 게이트가 무력해지고, 얻는 보안 이득은 0(벤더가 공개한 값). |
| Git history 재작성 | 사용자 지시 §13 이 명시적으로 금지. 별도 rotation 항목으로 분리. |

## 5. 남긴 것

- **Git history 의 평문은 그대로다.** 파일 내용과 commit 메시지(약 13개)에 남아 있다.
- **rotation 은 하지 않았다** (사용자 지시 §12 — 평문 제거와 rotation 분리).
  현재 유효한 6종의 rotation 필요성과 영향 범위는
  `tests/evidence/2026-08-12-plaintext-secret-sanitization.md` §6.2 와
  `docs/ai/NEXT_ACTIONS.md` 에 정리했다.
