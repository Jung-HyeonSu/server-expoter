# 05. inventory_json 필드 명세

포털이 Jenkins Job 트리거 시 전달하는 `inventory_json` 파라미터 명세.

---

## 형식

```json
[{"ip": "10.x.x.1"}, {"ip": "10.x.x.2"}]
```

## 전달 필드

| 필드 | 필수 | 설명 |
|------|------|------|
| `ip` | ✅ 전체 | Ansible 접속 IP |

hostname / username / password / vendor 는 전달하지 않는다.
계정은 vault 에서 자동 로딩하며, OS 타입/벤더는 gather 가 자동 감지한다.

---

## target_type 별 동작

### os

포트 감지로 Linux/Windows 자동 분기:
- SSH 22 열림 → Linux → `vault/linux.yml`
- WinRM 5986 또는 5985 열림 → Windows → `vault/windows.yml`
- 둘 다 닫힘 → `status: failed`

### esxi

단일 계정 로딩:
- `vault/esxi.yml`

### redfish

2단계 벤더 감지:
1. 빈 계정으로 Redfish ServiceRoot → `System.Manufacturer` 읽기
2. 감지된 벤더에 맞는 `vault/redfish/{dell|hpe|lenovo|supermicro}.yml` 로딩
3. 올바른 계정으로 전체 재수집

---

## Jenkins → inventory 스크립트 전달 흐름

### Jenkins 파라미터 → 환경변수 자동 전달

Jenkins Declarative Pipeline 의 `parameters` 블록에 정의한 파라미터는
빌드 실행 시 **자동으로 같은 이름의 환경변수로 내보내진다.**

```groovy
parameters {
    text(name: 'inventory_json', ...)   // → 환경변수 $inventory_json (소문자)
}
```

따라서 파라미터명이 `inventory_json` 이면 쉘·Python 에서
`$inventory_json` (소문자) 으로 바로 접근할 수 있다.

추가로 `environment` 블록에서 대문자 변수를 명시적으로 매핑하면
두 가지 이름 모두 사용 가능해진다:

```groovy
environment {
    INVENTORY_JSON = "${params.inventory_json}"   // 대문자 별칭
}
```

### inventory.sh 읽기 우선순위

각 gather 프로젝트의 `inventory.sh` 는 다음 순서로 인벤토리 JSON 을 탐색한다.

| 우선순위 | 소스 | 설명 |
|----------|------|------|
| 1순위 | 환경변수 `INVENTORY_JSON` (대문자) | `environment` 블록에서 명시 설정 |
| 2순위 | 환경변수 `inventory_json` (소문자) | Jenkins 파라미터 자동 전달 |
| 3순위 | `.inventory_input.json` 파일 | Jenkinsfile `writeFile` fallback |

세 가지 모두 비어 있거나 존재하지 않으면 에러로 종료한다.

> **참고** — 현재 Jenkinsfile v3 에서는 `environment` 블록에서 `INVENTORY_JSON` 을
> 명시 설정하므로, 실제 동작 시 1순위(대문자 환경변수) 로 전달된다.
> 2·3순위는 `environment` 블록 없이 파라미터만 정의하거나
> 수동 실행(writeFile) 시 fallback 으로 동작한다.

---

## inventory_hostname

모든 gather 에서 `inventory_hostname = ip` 로 통일한다.
포털 등록 전 서버이므로 hostname 을 알 수 없다.
OUTPUT JSON 의 `hostname` 필드도 ip 값으로 채워진다.

---

## Ansible 연결 파라미터 (vault 에서 로딩)

### vault/linux.yml
```yaml
ansible_user:     "..."
ansible_password: "..."
```

Ansible 연결 파라미터는 site.yml 의 `vars_files` 에서 자동 로딩:
```yaml
vars_files:
  - "{{ lookup('env', 'REPO_ROOT') }}/vault/linux.yml"
```

---

## 기존 문서와의 차이

이전 명세에서 변경된 사항:

| 항목 | 이전 | 현재 |
|------|------|------|
| inventory_json 필드 | ip, hostname, username, password | **ip 만** |
| 계정 전달 방식 | inventory_json 에 포함 | vault 자동 로딩 |
| hostname 처리 | 포털이 전달 | 없음 (ip 사용) |
| vendor 처리 | 포털이 전달 (선택) | 없음 (자동 감지) |
