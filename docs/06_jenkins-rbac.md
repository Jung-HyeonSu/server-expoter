# 06. Jenkins RBAC 권한 설정

Role Strategy Plugin 으로 Job 단위 접근 권한을 제어한다.
Job 이름이 Pattern 과 일치하면 권한이 자동 적용되므로 신규 Job 추가 시 별도 권한 설정 불필요.

---

## Global Roles

경로: Jenkins → Manage Jenkins → Manage and Assign Roles → Manage Roles → Global roles

| Role | Overall 권한 | 설명 |
|------|-------------|------|
| `admin` | Administer | 시스템 전체 관리자 |
| `portal` | Read | 포털 서비스 계정 |
| `engineer` | Read | 인프라 엔지니어 |

---

## Item Roles

| Role | Pattern | 부여 권한 |
|------|---------|----------|
| `portal` | `clovirone-portal.*` | Job Build, Read |
| `engineer` | `skhynix-infraops.*` | Job Build, Create, Configure, Read |

---

## 동작 확인

- `engineer` 계정 로그인 시 `clovirone-portal.*` Job 이 보이지 않아야 함
- `portal` 계정 로그인 시 `skhynix-infraops.*` Job 이 보이지 않아야 함
