# Jenkins Pipeline Syntax — declarative

> Source: https://www.jenkins.io/doc/book/pipeline/syntax/
> Fetched: 2026-04-27
> 사용 위치 (server-exporter): `Jenkinsfile`, `grafana 파이프라인(제거됨)`, `Jenkinsfile_portal`

## Pipeline 기본 구조

```groovy
pipeline {
    agent any
    stages {
        stage('Validate') {
            steps {
                sh 'ansible-playbook --syntax-check ...'
            }
        }
    }
}
```

## Agent 종류

- `agent any` — 아무 agent
- `agent none` — top-level 없음, stage별 지정
- `agent { label 'master' }` — 특정 라벨 (server-exporter agent-master 망 분리)
- `agent { label 'ich' }` — loc별 agent
- `agent { docker 'image:tag' }` — Docker

server-exporter 패턴:
```groovy
pipeline {
    agent none

    stages {
        stage('Validate') {
            agent { label 'master' }       // 입력 검증은 master
            steps { ... }
        }
        stage('Gather') {
            agent { label "${params.LOC}" } // ich/chj/yi
            steps { ... }
        }
        stage('Validate Schema') {
            agent { label 'master' }
            steps { ... }
        }
        stage('E2E Regression') {
            agent { label 'master' }       // baseline 비교
            steps { ... }
        }
    }
}
```

## Parameters

```groovy
parameters {
    choice(name: 'TARGET_TYPE', choices: ['os', 'esxi', 'redfish'])
    choice(name: 'LOC', choices: ['ich', 'chj', 'yi'])
    string(name: 'INVENTORY_JSON', defaultValue: '[]', description: 'JSON list')
    string(name: 'CALLBACK_URL', defaultValue: '', description: '결과 통보 URL')
}
```

## Environment + credentials

```groovy
environment {
    ANSIBLE_HOST_KEY_CHECKING = 'False'
    VAULT_PASS = credentials('ansible-vault-password')
    BMC_VAULT = credentials('redfish-bmc-creds-prod')
}
```

`credentials()` helper는 Jenkins Credentials Store에서 안전하게 주입.

## Conditional with `when`

```groovy
stage('E2E Regression') {
    when {
        expression { return params.TARGET_TYPE == 'redfish' }
    }
    steps { ... }
}
```

## Post actions

```groovy
post {
    always {
        archiveArtifacts artifacts: 'output/*.json'
    }
    success {
        sh """
            curl -X POST "${CALLBACK_URL}" \\
                 -H "Content-Type: application/json" \\
                 -d @output/envelope.json
        """
    }
    failure {
        // 에러도 callback으로 통보
    }
    cleanup {
        deleteDir()
    }
}
```

## Triggers

```groovy
triggers {
    cron('H H(9-16)/2 * * 1-5')  // 평일 09-16 hash 기반
    pollSCM('H/15 * * * *')
}
```

server-exporter cron 변경은 사용자 명시 승인 필수 (rule 80 + 92 R5). `pre_commit_jenkinsfile_guard.py` advisory 검출.

## Parallel (Stage 4 회귀 — 다중 vendor)

```groovy
stage('E2E Regression') {
    parallel {
        stage('Dell') {
            steps { sh 'pytest --vendor dell' }
        }
        stage('HPE') {
            steps { sh 'pytest --vendor hpe' }
        }
        stage('Lenovo') {
            steps { sh 'pytest --vendor lenovo' }
        }
    }
}
```

## server-exporter 4-Stage 템플릿

```groovy
pipeline {
    agent none
    parameters {
        choice(name: 'TARGET_TYPE', choices: ['os', 'esxi', 'redfish'])
        choice(name: 'LOC', choices: ['ich', 'chj', 'yi'])
        text(name: 'INVENTORY_JSON', defaultValue: '[]')
        string(name: 'CALLBACK_URL', defaultValue: '')
    }
    environment {
        ANSIBLE_HOST_KEY_CHECKING = 'False'
        VAULT_PASS = credentials('ansible-vault-password')
    }
    options {
        timeout(time: 30, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '50'))
        timestamps()
    }
    stages {
        stage('Stage 1 — Validate') {
            agent { label 'master' }
            steps { sh '...' }
        }
        stage('Stage 2 — Gather') {
            agent { label "${params.LOC}" }
            steps { sh 'ansible-playbook ...' }
        }
        stage('Stage 3 — Validate Schema') {
            agent { label 'master' }
            steps { sh 'python scripts/ai/hooks/output_schema_drift_check.py' }
        }
        stage('Stage 4 — E2E Regression') {
            agent { label 'master' }
            steps { sh 'pytest tests/redfish-probe/ 의 baseline 테스트 ...' }
        }
    }
    post {
        success {
            sh '''
                URL="$(echo "${CALLBACK_URL}" | sed 's:/*$::')"  # rule 31 R1: 후행 슬래시 제거
                curl -X POST -d @output/envelope.json "${URL}"
            '''
        }
    }
}
```

## 적용 rule

- rule 80 (ci-jenkins-policy)
- rule 31 (callback URL 무결성)
- rule 92 R5 (cron 변경 사용자 확인)
- script: `scripts/ai/hooks/pre_commit_jenkinsfile_guard.py`
