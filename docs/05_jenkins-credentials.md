# 05. Jenkins Credentials 등록

경로: Jenkins → Manage Jenkins → Credentials → System → Global credentials → Add Credentials

---

## gitlab-credentials

GitLab 레포지토리 checkout 에 사용하는 계정.

| 항목 | 값 |
|------|----|
| Kind | Username with password |
| Username | GitLab 계정 아이디 |
| Password | GitLab Access Token (api 권한) — 비밀번호가 아닌 토큰 입력 |
| ID | `gitlab-credentials` |

**GitLab Access Token 발급**
1. GitLab → Preferences → Access Tokens
2. Scopes: `api` 체크
3. Create → 발급된 토큰을 Password 에 입력

---

> vault-password Credentials 는 등록하지 않는다.
> vault 파일은 plain text 로 repo 에 포함되며 GitLab 접근 권한으로 보안을 통제한다.
