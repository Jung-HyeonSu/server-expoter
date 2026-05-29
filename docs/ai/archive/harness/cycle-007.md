# cycle-007 — 4축 자동 검수 + HIGH 4 일괄 정합

## 일자
2026-04-28

## 진입 사유
사용자 명시 ("github에 넣고 남아있는 작업 모두 자동수행 + 프로젝트 코드 모두 검수") — 4축 (구조 / 품질 / 보안 / 벤더경계) 자동 검수 결과 HIGH 6건 발견. 사용자 후속 지시:
- "보안은 모두 무시" (memory feedback 등재) → 4축 → 3축으로 축소
- "A 진행" — HIGH 4건 (보안 제외) 일괄 처리

## 처리 내역

### #1 — rule 22 R7 텍스트 ↔ 코드 drift 정합

- **문제**: rule 22 R7은 `_sections_<name>_supported_fragment` (예: `_sections_cpu_collected_fragment`) 명명을 명시했으나, 실제 코드는 `_sections_supported_fragment` / `_sections_collected_fragment` / `_sections_failed_fragment` 3 공통 변수 + `_data_fragment` + `_errors_fragment` = **5 공통 변수** 사용 (각 gather가 변수 이름은 동일하게, 값으로 자기 섹션을 채우는 패턴)
- **갱신 8 파일**:
  - `.claude/rules/22-fragment-philosophy.md` R1, R7, R8 + Bad/Good 예시
  - `.claude/rules/11-gather-output-boundary.md` 현재 관찰
  - `.claude/agents/fragment-engineer.md`
  - `.claude/ai-context/common/coding-glossary-ko.md` Fragment 정의
  - `.claude/ai-context/common/project-map.md` Fragment 변수 패턴
  - `.claude/ai-context/gather/convention.md` Fragment 철학 + 명명 + 새 gather 템플릿
  - `.claude/role/gather/README.md` Critical 섹션
  - `.claude/skills/validate-fragment-philosophy/SKILL.md` 검사 항목 + 절차
  - `CLAUDE.md` Fragment 추가 체크리스트 + Critical 예시
- **확인**: drift 5건 (historical plans 제외) → 0건

### #2 — redfish_gather.py `gather_storage()` 190줄 분리

- **문제**: rule 10 R3 (함수 50줄) 위반 — gather_storage 1개 함수가 SimpleStorage fallback + Standard Storage controllers + drives + volumes 모두 처리
- **분리 5 함수**:
  - `_gather_simple_storage(...)` — SimpleStorage 경로 (~30줄)
  - `_gather_standard_storage(...)` — Storage 정규경로 dispatcher (~25줄)
  - `_extract_storage_controller_info(...)` — StorageControllers 인라인 / Controllers 서브링크 분기 (~32줄)
  - `_extract_storage_drives(...)` — Empty Bay 필터 + 정규화 (~38줄)
  - `_extract_storage_volumes(...)` — RAID 정규화 + JBOD 필터 (~50줄)
  - `gather_storage(...)` — Storage → SimpleStorage fallback dispatcher (~30줄)
- **logic 변경 없음** (signature 동일, 외부 호출 동일)

### #3 — precheck_bundle.py + adapter_loader.py 함수 분리

`common/library/precheck_bundle.py`:
- `run_module()` 181줄 → 6 함수 분리:
  - `_init_result(channel, ports)` — result dict 초기화
  - `_check_ports(host, ports, timeout_port)` — Stage 1+2 포트 순회
  - `_detect_os_from_port(open_port)` — OS 채널 포트 기반 OS 판별
  - `_probe_protocol(channel, ...)` — Stage 3 dispatcher
  - `_try_redfish_auth(...)` — Stage 4 Redfish 인증
  - `run_module()` — orchestrator (~60줄)

`lookup_plugins/adapter_loader.py`:
- `LookupModule.run()` 115줄 → 5 함수 분리:
  - `_resolve_repo_root(kwargs, variables)` — REPO_ROOT 결정
  - `_import_adapter_common(repo_root)` — module_utils import
  - `_scan_adapters(adapter_dir)` — YAML 스캔
  - `_match_and_score(adapters, facts, aliases, ...)` — match 평가 + 점수
  - `_pick_generic_fallback(adapters)` — generic fallback 검색
  - `LookupModule.run()` — orchestrator (~30줄)

### #4 — precheck_bundle.py `requests` 의존 제거

- **문제**: `HAS_REQUESTS` 분기 — requests 라이브러리 선택적 import + 양 분기 (urllib / requests) 동작 미세 차이 (에러 메시지 형식 등)
- **변경**:
  - `try: import requests` 제거 → urllib stdlib 단일 경로
  - `_build_ssl_context(verify)` + `_basic_auth_header(auth)` 헬퍼 추출
  - 에러 분류 강화: HTTPError / socket.timeout / urllib.error.URLError / ssl.SSLError / OSError
- **rule 10 R2 정합**: redfish_gather.py와 동일하게 stdlib only

## 검증 결과

| 검증 | 결과 |
|---|---|
| pytest tests/ | **95/95 PASS** |
| ansible-playbook --syntax-check (3 채널) | OK |
| python -m ast (3 변경 파일) | AST OK |
| verify_harness_consistency.py | rules 29 / skills 43 / agents 51 / policies 10 정합 |
| verify_vendor_boundary.py | 0건 |
| scan_suspicious_patterns.py | 11 패턴 0건 |
| output_schema_drift_check.py | sections=10 / fd_paths=46 정합 |
| validate_claude_structure.py | OK |

## 영향 범위

- **영향 채널**: redfish-gather (gather_storage 분리), os/esxi/redfish (precheck 공통), 모든 채널 (adapter_loader)
- **영향 vendor**: 5 vendor 전체 (storage 수집 경로 공통 코드)
- **logic 변경 없음**: 모든 외부 호출 signature + 동작 동일. 함수 분리 + helper 추출만.
- **회귀 위험**: LOW — pytest 95/95 통과, signature 동일

## 변경 파일 12개

- `.claude/agents/fragment-engineer.md`
- `.claude/ai-context/common/coding-glossary-ko.md`
- `.claude/ai-context/common/project-map.md`
- `.claude/ai-context/gather/convention.md`
- `.claude/role/gather/README.md`
- `.claude/rules/11-gather-output-boundary.md`
- `.claude/rules/22-fragment-philosophy.md`
- `.claude/skills/validate-fragment-philosophy/SKILL.md`
- `CLAUDE.md`
- `common/library/precheck_bundle.py`
- `lookup_plugins/adapter_loader.py`
- `redfish-gather/library/redfish_gather.py`
- 본 cycle-007 보고서 + CURRENT_STATE / NEXT_ACTIONS 갱신

## 미진행 (다음 cycle 후속)

| 영역 | 항목 | 우선 |
|---|---|---|
| 구조 | redfish_gather.py `gather_system()` 100줄 / `detect_vendor()` 64줄 / `main()` 67줄 분리 | MED |
| 구조 | os-gather/tasks/linux/gather_system.yml 346줄 → identifier_diagnostics 분리 | MED |
| 구조 | adapters/redfish/hpe_ilo5.yml + hpe_ilo6.yml priority 동률 → 차등 (90/100) | MED |
| 품질 | callback_plugins/json_only.py `_emit()` 빈 `pass` → stderr 경고 | MED |
| 품질 | adapter_loader score 동률 시 정렬 결정성 (Python sort stable + glob 알파벳) 문서화 | MED |
| 품질 | redfish_gather.py:757 `int(vcap_int / 1048576)` 패턴 통일 | LOW |
| 품질 | redfish_gather.py docstring `(Dell/HPE/Lenovo/Supermicro)` Cisco 누락 | LOW |
| 벤더 | adapters/redfish/lenovo_imm2.yml `tested_against` 펌웨어 명시 | LOW |
| 벤더 | Cisco OEM gather_system 분기 누락 (silent oem={}) — 의도 vs 미구현 확인 | MED |
| 벤더 | adapters/redfish/cisco_cimc.yml 단일 priority — 세대(M4/M5/M6) 미준비 | LOW |

## 결정 (사용자 명시)

- 보안 axis 검수 결과 무시 (memory feedback 등재 — 2026-04-28)
- HIGH 4건 일괄 처리 ((A) 옵션 선택)

## 보존 판정

본 cycle-007 보고서는 **결정의 reasoning + 구체적 변경 매핑**을 포함 → **보존** (rule 70 보존 판정 1번 해당).
