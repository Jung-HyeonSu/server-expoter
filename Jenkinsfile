// =============================================================================
// server-exporter / Jenkinsfile  v3
//
// 포털 → Jenkins → Ansible gather → 결과 stdout JSON → 포털
//
// 지원 gather 종류 (target_type):
//   os      → os-gather/site.yml     (Linux/Windows 자동 감지)
//   esxi    → esxi-gather/site.yml
//   redfish → redfish-gather/site.yml
//
// 파라미터:
//   loc             : 슬레이브 로케이션 Labels (ich|chj|yi)
//   target_type     : 수집 대상 종류 (os|esxi|redfish)
//   inventory_json  : 포털이 조립한 호스트 배열 JSON
//
// 출력:
//   표준 JSON schema v1 (stdout) — json_only callback 필터
//   BUILD_RESULT artifact (results.json) — 포털 재취득 가능
//
// 실패 처리:
//   Validate 단계 실패 → 즉시 종료
//   Ansible 실패 → partial result JSON 포함하여 계속
// =============================================================================

pipeline {

    agent { label "${params.loc}" }

    parameters {
        // 포털이 전달하는 값 — defaultValue 는 포털 jspreadsheet 컬럼 정의로 사용
        string(
            name        : 'loc',
            defaultValue: '',
            description : '슬레이브 로케이션 Labels (ich | chj | yi)'
        )
        choice(
            name        : 'target_type',
            choices     : ['os', 'esxi', 'redfish'],
            description : '수집 대상 종류'
        )
        text(
            name        : 'inventory_json',
            defaultValue: '''[
  {
    "ip": ""
  }
]''',
            description : '포털이 조립한 타겟 호스트 JSON 배열'
        )
    }

    environment {
        INVENTORY_JSON = "${params.inventory_json}"
        REPO_ROOT      = "${WORKSPACE}"
        ANSIBLE_CONFIG = "${WORKSPACE}/ansible.cfg"
    }

    options {
        timeout(time: 30, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '100'))
        ansiColor('xterm')
    }

    stages {

        // ── 1. 파라미터 검증 ──────────────────────────────────────────────────
        stage('Validate') {
            steps {
                script {

                    // loc 필수
                    if (!params.loc?.trim()) {
                        error "[Validate] 필수 파라미터 누락: loc"
                    }

                    // target_type 범위 검증
                    def allowed = ['os', 'esxi', 'redfish']
                    if (!allowed.contains(params.target_type?.trim())) {
                        error "[Validate] target_type 값 오류: '${params.target_type}' — 허용값: ${allowed}"
                    }

                    // inventory_json 파싱 검증
                    if (!params.inventory_json?.trim()) {
                        error "[Validate] inventory_json 이 비어있습니다"
                    }

                    def hosts
                    try {
                        hosts = readJSON text: params.inventory_json
                    } catch (groovy.json.JsonException e) {
                        error "[Validate] inventory_json JSON 파싱 실패: ${e.message}"
                    }

                    if (!hosts || hosts.size() == 0) {
                        error "[Validate] inventory_json 배열이 비어있습니다"
                    }

                    // 각 호스트 ip 필드 검증
                    hosts.eachWithIndex { host, idx ->
                        if (!host.ip?.trim()) {
                            error "[Validate] inventory_json[${idx}] ip 필드 누락: ${host}"
                        }
                    }

                    // redfish 는 vendor 필드 권장 (없어도 진행)
                    if (params.target_type == 'redfish') {
                        def missing = hosts.findAll { !it.vendor?.trim() }
                        if (missing) {
                            echo "[Validate] WARNING: redfish 항목 중 vendor 필드 미지정 (${missing.size()}개) — 자동 감지 시도"
                        }
                    }

                    echo "[Validate] OK — target_type=${params.target_type}, hosts=${hosts.size()}개, loc=${params.loc}"
                }
            }
        }

        // ── 2. Ansible 실행 ───────────────────────────────────────────────────
        stage('Gather') {
            steps {
                script {
                    // target_type 별 playbook 경로 결정
                    def playbookMap = [
                        'os'     : "${WORKSPACE}/os-gather/site.yml",
                        'esxi'   : "${WORKSPACE}/esxi-gather/site.yml",
                        'redfish': "${WORKSPACE}/redfish-gather/site.yml",
                    ]
                    def inventoryMap = [
                        'os'     : "${WORKSPACE}/os-gather/inventory.sh",
                        'esxi'   : "${WORKSPACE}/esxi-gather/inventory.sh",
                        'redfish': "${WORKSPACE}/redfish-gather/inventory.sh",
                    ]

                    def playbook  = playbookMap[params.target_type]
                    def inventory = inventoryMap[params.target_type]

                    echo "[Gather] playbook=${playbook}"

                    // Ansible 실패 시 unstable 처리 (partial result JSON 포함)
                    // catchError 로 감싸서 post 단계까지 진행
                    catchError(buildResult: 'UNSTABLE', stageResult: 'UNSTABLE') {
                        ansiblePlaybook(
                            playbook    : playbook,
                            inventory   : inventory,
                            installation: 'ansible',
                            colorized   : true,
                        )
                    }
                }
            }
        }

        // ── 3. Schema Validator ─────────────────────────────────────────────────
        // field_dictionary.yml 정합성 검증
        // 1단계: 실패 시 UNSTABLE (품질 게이트 부드럽게 도입)
        // 2단계: 운영 안정화 후 FAIL 상향 검토
        stage('Validate Schema') {
            steps {
                catchError(buildResult: 'UNSTABLE', stageResult: 'UNSTABLE') {
                    sh '''
                        cd "${WORKSPACE}"
                        . /opt/ansible-env/bin/activate
                        python3 tests/validate_field_dictionary.py
                    '''
                }
            }
        }

        // ── 4. E2E Regression ─────────────────────────────────────────────────
        // baseline/fixture 기반 핵심 필드 회귀 검증
        // 실패 시 UNSTABLE (Phase 2에서 FAIL 상향 검토)
        stage('E2E Regression') {
            steps {
                catchError(buildResult: 'UNSTABLE', stageResult: 'UNSTABLE') {
                    sh '''
                        cd "${WORKSPACE}"
                        . /opt/ansible-env/bin/activate
                        python3 -m pytest tests/e2e/ -v --tb=short
                    '''
                }
            }
        }
    }

    // ── post 처리 ─────────────────────────────────────────────────────────────
    post {
        always {
            script {
                def result = currentBuild.currentResult
                echo "[Post] 빌드 결과: ${result}"
                // json_only callback 이 stdout 에 JSON 을 출력하므로
                // 포털은 Jenkins console log 에서 JSON 라인을 파싱한다.
                // 또는 archiveArtifacts 로 결과 파일 보존 가능.
            }
        }
        success {
            echo "[Post] gather 완료 — 포털로 결과 반환"
        }
        failure {
            echo "[Post] gather 실패 — 포털로 에러 상태 반환 (partial result 포함 가능)"
        }
    }
}
