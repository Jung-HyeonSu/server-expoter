# 04. Jenkins 플러그인 설치

경로: Jenkins → Manage Jenkins → Plugins → Available plugins

---

## 필수 플러그인

> 03_jenkins-install.md 초기 설정에서 **Install suggested plugins** 를 선택하면
> Pipeline, Credentials, Git 등 기본 플러그인은 자동 설치된다.
> 아래 표에서 ★ 표시가 없는 항목만 별도 설치하면 된다.

| 플러그인 | 용도 | suggested 포함 |
|----------|------|:--------------:|
| **Ansible** | `ansiblePlaybook()` 스텝 | |
| **GitLab** | GitLab SCM 연동 | |
| **Role-based Authorization Strategy** | Job 단위 권한 분리 | |
| **Credentials** | GitLab 계정 중앙 관리 | ★ |
| **Pipeline** | Declarative Pipeline 실행 | ★ |
| **Pipeline Utility Steps** | `readJSON` 스텝 (Jenkinsfile 파라미터 파싱) | |
| **AnsiColor** | `ansiColor('xterm')` 옵션 — Ansible 컬러 출력 | |
| **Git** | SCM checkout | ★ |

## 권장 플러그인

| 플러그인 | 용도 |
|----------|------|
| **Pipeline: Stage View** | Stage 별 실행 결과 시각화 |
| **Blue Ocean** | 파이프라인 흐름 UI |
| **Timestamper** | 콘솔 로그 타임스탬프 |
| **Workspace Cleanup** | 빌드 후 workspace 자동 정리 |

---

## Ansible 플러그인 경로 설정

경로: Jenkins → Manage Jenkins → Tools → Ansible installations

| 항목 | 값 |
|------|----|
| Name | `ansible` |
| Path to ansible executables directory | `/opt/ansible-env/bin` |

> 이 경로는 08_agent-setup.md § 3 에서 Agent 에 가상환경을 생성한 뒤 실제로 동작한다.
> 마스터에서는 경로만 미리 등록해두면 된다.
