# 04. Jenkins Job 등록

경로: Jenkins → New Item → Pipeline 선택

---

## Job 네이밍 규칙

RBAC Pattern 과 일치해야 권한이 자동 적용된다.

```
{프로젝트명}.{작업명}
```

**수집 파이프라인 예시:**

- `server-exporter.os-gather`
- `server-exporter.esxi-gather`
- `server-exporter.redfish-gather`

**인프라 자동화 예시:**

- `infra-automation.{작업명}.{타입}` (예: `infra-automation.load-test.linux`)

---

## Pipeline SCM 설정

경로: Job 설정 → Pipeline 섹션

| 항목 | 값 |
|------|----|
| Definition | Pipeline script from SCM |
| SCM | Git |
| Credentials | `gitlab-credentials` |
| Branch | `*/main` |

### 수집 파이프라인 Script Path

Jenkinsfile 은 루트에 1개만 존재한다. 3개 Job 모두 동일한 Script Path 를 사용하고
`target_type` 파라미터로 gather 종류를 구분한다.

| Job 이름 | Script Path | target_type 기본값 |
|----------|-------------|-------------------|
| `{프로젝트명}.os-gather` | `Jenkinsfile` | `os` |
| `{프로젝트명}.esxi-gather` | `Jenkinsfile` | `esxi` |
| `{프로젝트명}.redfish-gather` | `Jenkinsfile` | `redfish` |

> Script Path 는 모두 `Jenkinsfile` 이다. 각 gather 디렉토리에는 별도 Jenkinsfile 이 없다.

### 인프라 자동화 Script Path (참고)

| Script Path | 설명 |
|-------------|------|
| `load-test/Jenkinsfile` | 부하 테스트 |
| `day1/{작업명}/{타입}/Jenkinsfile` | Day-1 작업 |
| `day2/{작업명}/{타입}/Jenkinsfile` | Day-2 작업 |

> 인프라 자동화 프로젝트는 별도 저장소에서 관리한다.
