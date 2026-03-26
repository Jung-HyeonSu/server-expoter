# 04. Jenkins Job 등록

경로: Jenkins → New Item → Pipeline 선택

---

## Job 네이밍 규칙

RBAC Pattern 과 일치해야 권한이 자동 적용된다.

| 레포 | Job 이름 형식 |
|------|-------------|
| skhynix-infraops | `skhynix-infraops.{작업명}.{타입}` |
| clovirone-portal | `clovirone-portal.{gather명}` |

예시:
- `skhynix-infraops.load-test.linux`
- `clovirone-portal.os-gather`
- `clovirone-portal.esxi-gather`
- `clovirone-portal.redfish-gather`

---

## Pipeline SCM 설정

경로: Job 설정 → Pipeline 섹션

| 항목 | 값 |
|------|----|
| Definition | Pipeline script from SCM |
| SCM | Git |
| Credentials | `gitlab-credentials` |
| Branch | `*/main` |

### skhynix-infraops Script Path 예시

| Script Path | 설명 |
|-------------|------|
| `load-test/Jenkinsfile` | 부하 테스트 |
| `day1/{작업명}/{타입}/Jenkinsfile` | Day-1 작업 |
| `day2/{작업명}/{타입}/Jenkinsfile` | Day-2 작업 |

### clovirone-portal Script Path

Jenkinsfile 은 루트에 1개만 존재한다. 3개 Job 모두 동일한 Script Path 를 사용하고
`target_type` 파라미터로 gather 종류를 구분한다.

| Job 이름 | Script Path | target_type 기본값 |
|----------|-------------|-------------------|
| `clovirone-portal.os-gather` | `Jenkinsfile` | `os` |
| `clovirone-portal.esxi-gather` | `Jenkinsfile` | `esxi` |
| `clovirone-portal.redfish-gather` | `Jenkinsfile` | `redfish` |

> Script Path 는 모두 `Jenkinsfile` 이다. 각 gather 디렉토리에는 별도 Jenkinsfile 이 없다.
