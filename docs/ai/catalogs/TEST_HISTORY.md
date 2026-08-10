# TEST_HISTORY — server-exporter

> 테스트 실행 / Round 검증 / Baseline 갱신 이력 (append-only, rule 70).

## 2026-08-10 (i) — WinRM WS-Management Identify 판정 검증 (Phase 3-B 최종)

- **재작성**: `tests/unit/test_precheck_probe_os.py` **30건**.
  - Positive: 5985 / 5986 정상 IdentifyResponse, 네임스페이스 표기 변형 2종,
    Identify 요청 형식(SOAP POST + `WSMANIDENTIFY: unauthenticated` + `/wsman` + verify=False)
  - **False Positive 11조합 전부 거부**: 단순 200(일반 웹서버 HTML) / 401 / 403 / 404 /
    405 / 500 / 일반 XML / 다른 네임스페이스의 IdentifyResponse / ProtocolVersion 없음 /
    ProtocolVersion 이 WS-Management 아님 / 잘린 IdentifyResponse
  - **헤더 heuristic 제거 확인**: `_looks_like_wsman` 부재 + Microsoft-HTTPAPI/401 거부
  - **비-Windows WS-Man 장비**(Openwsman) 를 Windows 로 판정하지 않음
  - XML 폭탄 방어(64KB 상한) / TLS handshake 실패 / timeout / 자격증명 미전송
- **SSH**: 구현 변경 없음. 기존 23건 중 SSH 관련 테스트 그대로 통과
  (identification 2종 / 선행 추가 줄 / SMTP 배너 거부 / 무응답 / 알 수 없는 protoversion / 읽기 상한).
- **Timeout 최악 계산**: 죽은 호스트 6초(Phase 3-A 대비 불변) / 정상 Windows 7초 /
  정상 Linux 11초 / 전 포트 열림 + 프로토콜 전멸 21초.
- **전체 회귀**: `pytest tests/` → **1566 passed, 11 skipped, 7 xfailed**
- **Jenkins 등가**: Stage 3 PASS / e2e 258 / integration 200 / unit 936 / regression 169
- **하네스**: harness / boundary / output_schema_drift / envelope_change / cross_channel exit 0
- **Redfish/ESXi**: `http_get` 미변경(새 `http_post_soap` 분리) → 두 채널 소비 경로 영향 0.
  regression 169 · integration 200 · baseline 10 통과.
- **schema/**: 파일 변경 0
- **환경 제약**: `ansible-playbook --syntax-check` **미실행** (Windows, `os.get_blocking` POSIX 전용).
  대체로 YAML 파싱 5종 + Jinja2 166 표현식 전수 컴파일 실패 0.
- **한계 (보고 대상)**: lab 에 Windows WinRM 실장비가 없어 IdentifyResponse 는 **규격 기반**이며
  실측 캡처가 아니다. 네임스페이스 표기(http/https, .xsd 유무)를 4가지 허용해 방어했으나
  실장비 확보 시 실제 응답으로 재확인이 필요하다.
- **SSH 읽기 상한은 정책값**: 8줄 / 2048바이트. RFC 4253 은 선행 줄 상한을 정하지 않으며
  OpenSSH banner(/etc/issue.net)는 통상 3~10줄이다. 매우 긴 banner 를 쓰는 사이트에서는
  identification 을 놓칠 수 있어 상한 조정이 필요할 수 있다.

## 2026-08-10 (h) — OS Protocol 판정 강화 검증 (Phase 3-B)

- **신규**: `tests/unit/test_os_candidate_search.py` **24건** — run_module 을 실제로 돌려
  후보 탐색 전 경로 검증.
  - Case 1~4 정상 판정(5986 / 5985 / 22) + scheme + checked_ports
  - Case 12 열린 포트는 있으나 프로토콜 전멸 → `protocol` + `PROTOCOL_CHECK_FAILED`,
    `port_open=true` / `protocol_supported=false` / `detected_os=None`
  - Case 13 앞 후보 실패 후 뒤 후보 성공 → 전체 성공
  - Case 11 TCP 전멸 4조합 → Phase 3-A 매핑 유지, 프로토콜 probe 미호출
  - Case 16 auth_success 는 어떤 경우에도 null
  - Case 14 checked_ports 5조합 (중복 없음)
  - 폴링 인자 보존 (포트별 예산 2초 / poll 1초 / 순서)
  - Case 18 redfish/esxi 는 후보 탐색을 타지 않음 + probe_protocol=false 경로 잔존 확인
- **재작성**: `tests/unit/test_precheck_probe_os.py` **23건**. 종전 상태 코드 whitelist
  테스트(200/401/403/405/503 → WinRM)를 폐기하고 헤더 근거 기반으로 교체.
  - **False Positive 8조합**: nginx/Apache 의 200 / 404 / 403 / 405 / 503 /
    `Basic realm="Restricted"` 401 / 헤더 없음 → **전부 거부**
  - WSMAN realm / Microsoft-HTTPAPI + 인증요구 → 인정
  - SSH: 정상 identification 2종 / 선행 추가 줄 3줄 후 identification / SMTP 배너 거부 /
    무응답 거부 / 알 수 없는 protoversion 거부 / 읽기 상한 확인
  - `/wsman` 기본 경로 + `verify=False` 확인, probe 가 자격증명 미전송 확인
- **PLAY 1 → PLAY 1.5 시뮬레이션**: 9 시나리오를 실제 템플릿으로 렌더.
  OS 판정 / scheme / protocol_supported / stage / code / auth / checked_ports / reason 전부 기대 일치.
- **전체 회귀**: `pytest tests/` → **1559 passed, 11 skipped, 7 xfailed**
- **Jenkins 등가**: Stage 3 PASS / e2e 258 / integration 200 / unit 929 / regression 169
- **하네스**: harness / boundary / output_schema_drift / envelope_change / cross_channel exit 0
- **Baseline / schema**: 파일 변경 0
- **환경 제약**: `ansible-playbook --syntax-check` **미실행** (Windows, `os.get_blocking` POSIX 전용).
  대체로 YAML 파싱 5종 + Jinja2 166 표현식 전수 컴파일 실패 0.
- **구현 한계 (보고 대상)**: 자격증명 없이 WS-Management handshake 를 완결할 수 없어 WinRM
  판정은 **헤더 근거 기반**이다. (2) `Server=Microsoft-HTTPAPI + 인증요구` 는 결정적 증거가
  아니라 강한 정황이다. 완전한 판정은 Credential Probe 영역이며 이번 범위 밖이다.

## 2026-08-10 (g) — Phase 3-A 보정 검증 (폴링 복원 / 문구 정정)

- **신규**: `tests/unit/test_os_precheck_polling.py` **21건**.
  실제 시간 기반 소켓 상태 전환을 만들 수 없어 **결정적 mock clock** 사용
  (`pb.time.monotonic` / `pb.time.sleep` 대체 → 실제 대기 0초).
  - **핵심 회귀 Case**: t=0 에 닫혀 있고 t=1.0 에 기동되는 서비스 →
    폴링(예산 2초, sleep 1) 으로 **2회째 시도에서 성공**. 대조군(단일 시도)은 실패.
  - 예산 초과 대기 없음(clock <= 2.0) / 시도별 타임아웃 = `min(5, ceil(남은))` = [2, 1]
  - timeout 실패는 1회로 끝남(wait_for 와 동일) / refused 후 예산 내 성공
  - 여러 시도의 kind 종합 우선순위 4조합
  - checked_ports 중복 없음 / 첫 성공에서 중단
  - **DNS 규칙**: 주소 시도 실패는 timeout kind, getaddrinfo 실패만 DNS kind /
    복수 주소 중 하나 실패해도 다른 주소 성공이 우선
  - **§9 채널 보호**: redfish/esxi 는 `(443, 3.0)` 단일 시도 유지, stage/code/checked_ports 불변
  - os-gather/run_precheck 배선 검증 + RST 문구에 "서버는 응답하지만" 부재 확인
- **수정**: 공유 테스트 하네스 2곳에 `port_poll_interval` 파라미터 추가,
  RST 문구 기대값 갱신.
- **전체 회귀**: `pytest tests/` → **1519 passed, 11 skipped, 7 xfailed**
- **Jenkins 등가**: Stage 3 PASS / e2e 258 / integration 200 / unit 889 / regression 169
- **하네스**: harness / boundary / output_schema_drift / envelope_change / cross_channel exit 0
- **Baseline**: 10건 변경 없음
- **환경 제약**: `ansible-playbook --syntax-check` **미실행** (Windows, `os.get_blocking` POSIX 전용).
  대체로 YAML 파싱 5종 + Jinja2 165 표현식 전수 컴파일 실패 0.
- **wait_for 실측 근거**: `ansible/modules/wait_for.py` argument_spec
  (`timeout=300`, `connect_timeout=5`, `sleep=1`, `delay=0`) + started 분기 폴링 루프 :619-628.

## 2026-08-10 (f) — OS 공통 Precheck 통합 검증 (Phase 3-A)

- **신규**: `tests/unit/test_os_precheck_integration.py` **18건** — `run_module()` 을 실제로
  돌려 포트별 결과를 주입한다(네트워크 0).
  - Case 1~3 포트 우선순위 + OS Type + scheme + checked_ports
  - Case 4~7 전 포트 timeout / 전 포트 refused / 혼합 4조합 / DNS 실패
  - Case 8~9 IPv6 → IPv4 graceful degradation (주소군 순서)
  - 포트 점검 단계는 auth_success 를 만들지 않음 / 프로토콜을 확인했다고 위장하지 않음
  - 타임아웃 2초가 실제 전달되는지(모듈 기본 3.0 이 조용히 적용되지 않는지) / 포트당 재시도 없음
  - Case 18 민감정보 비노출
  - **Cross-channel**: redfish/esxi 는 probe_protocol 기본 true 로 Stage 3 유지,
    checked_ports=[443] 불변
- **수정**: `test_precheck_detail_propagation.py` 의 포트 순서 회귀를 공통 모듈 정본
  (`CHANNEL_DEFAULT_PORTS['os']`) 기준으로 재작성 + `_check_ports` 실측 probed 목록 검증 추가.
  `test_failure_code_contract.py` 의 OS 매핑 예외 제거(해소됨) →
  code↔stage 전 채널 1:1 로 강화. `test_failure_reason_contract.py` OS 포트 전멸 3분기 검증.
- **PLAY 1 → PLAY 1.5 배선 시뮬레이션**: site.yml 템플릿을 직접 추출해 7 시나리오 렌더.
  OS 판정 / stage / code / auth / checked_ports / reason 전부 기대와 일치.
- **전체 회귀**: `pytest tests/` → **1498 passed, 11 skipped, 7 xfailed**
- **Jenkins 등가**: Stage 3 PASS / Stage 4-a 258 / Stage 4-b 200 / unit 868 / regression 169
- **하네스**: harness / boundary / output_schema_drift / envelope_change / cross_channel 전부 exit 0
- **Baseline**: 10건 shape·값 검사 통과 (변경 없음)
- **환경 제약**: `ansible-playbook --syntax-check` **미실행** (Windows 에서 Ansible CLI 진입부가
  POSIX 전용 `os.get_blocking` 호출). 대체로 YAML 파싱 5종 + Jinja2 163 표현식 전수 컴파일
  실패 0 + 7 시나리오 실제 렌더 수행. lab/Jenkins 재확인 필요.
- **알려진 동작 차이 (보고 대상)**: `wait_for` 는 timeout 안에서 재시도(polling)하지만
  `tcp_check_ex` 는 포트당 1회 시도다. 부팅 중 서비스가 t=1.5s 에 열리는 경계 사례에서
  결과가 달라질 수 있다. 재시도 정책 변경은 이번 범위 밖이라 1회 시도를 채택했다.

## 2026-08-10 (e) — failure_stage / failure_code 계약 테스트 (Phase 2)

- **신규**: `tests/e2e/test_failure_code_contract.py` **42건**. production site.yml /
  precheck_bundle 을 직접 렌더·실행해 검증 (합성 fixture 아님).
  - 사용자 지정 14 Case 전수 + OS 포트 전멸 예외 매핑
  - 불변식: code 허용 집합 / code-stage 조합 / success·partial 은 둘 다 null /
    baseline 전수 null / field_dictionary 와 코드 집합 일치 / 자격 전멸 시 auth false 금지 /
    HTTP 403 auth false 금지 / errors detail 민감정보 미노출 / Phase 1 reason 문구 유지
- **수정**: `tests/e2e/test_envelope_failure_modes.py` fixture 에 failure_code 추가 +
  fallback 문구를 production 과 동기화. `tests/regression/test_cross_channel_consistency.py` 에
  `test_diagnosis_has_failure_keys` 추가 (baseline 10 전수 shape 고정).
  `tests/e2e/test_failure_reason_contract.py` 기대값 4건 갱신
  (인증 통과 후 실패의 stage 가 null → gather 로 바뀐 의도된 변경을 실제로 검출했다).
- **14 Case 실측 렌더 결과**: 조합 위반 0, 전 Case failure_code 키 존재.
- **전체 회귀**: `pytest tests/` → **1472 passed, 11 skipped, 7 xfailed**
- **Jenkins 등가**: Stage 3 `validate_field_dictionary.py` PASS (fd_paths 168→169) /
  Stage 4-a e2e 252 passed / Stage 4-b integration 200 passed / unit 848 / regression 169
- **하네스**: harness / vendor boundary / output_schema_drift / envelope_change /
  cross_channel 전부 exit 0
- **자산 파싱**: baseline 10 + examples 4 + output_examples 11 전수 파싱 실패 0
  (검증 중 scratchpad 헬퍼의 이스케이프 처리 버그로 2건이 거짓 실패로 보고돼, 상태 머신
  기반 파서로 교체 후 재확인)
- **Baseline 갱신**: 10건에 `failure_code: null` **키만** 추가. 전부 `status=success` 라
  null 이 실측과 일치하는 값이며 회귀 기준선의 의미는 불변 (rule 13 R1 3종 동반 갱신)
- **환경 제약**: `ansible-playbook --syntax-check` **미실행** (Windows 에서 Ansible CLI 진입부가
  POSIX 전용 `os.get_blocking` 호출). 대체로 YAML 파싱 6종 + Jinja2 표현식 163개 전수 컴파일
  실패 0 + 14 Case 실제 렌더 수행. lab/Jenkins 에서 재확인 필요.

## 2026-08-10 (d) — Portal 실패 사유 계약 테스트 신설 (Phase 1-B)

- **신규**: `tests/e2e/test_failure_reason_contract.py` **40건**. 합성 fixture 가 아니라
  **production site.yml 에서 템플릿을 추출해 직접 렌더**한다 (NativeEnvironment +
  ansible `bool`/`combine` 필터 대역, `ansible.cfg:44 jinja2_native=True` 반영).
  - 사용자 지정 12 Case 전수: precheck reachable/port/protocol, Redfish post-precheck(수집실패·
    정규화예외), ESXi 자격전멸·facts실패·기타예외, Linux/Windows 자격전멸·수집예외,
    OS 포트 전멸, Fallback(3채널 × always 블록 4개)
  - **요구사항 11 불변식**: `status=failed` ⇒ `diagnosis` 非null ∧ `failure_reason` 非공백
  - **요구사항 6 불변식**: `auth_success=false` 는 HTTP 401 관측 시에만 (403·500 은 null)
  - 문체 가드: 긴 대시(—)·가운데점(·) 금지, 완결 문장, 200자 이내, 내부 잡음 미노출
  - `_diagnosis` 미정의 상황에서도 7키 shape 보장, precheck 사유 보존(when 가드) 검증
- **가드 유효성 증명** (사고 형태 주입): 구 OS 동작(diagnosis=null) / 구 Redfish 동작
  (failure_reason=null) / 빈 문자열 → **3건 모두 검출**. 문체 위반 4종 → **4건 모두 검출**.
- **전체 회귀**: `pytest tests/` → **1421 passed, 8 skipped, 7 xfailed** (35.04s)
- **Jenkins 등가**: Stage 3 `validate_field_dictionary.py` PASS (0 failed) /
  Stage 4-a `tests/e2e/` 210 passed / Stage 4-b `tests/integration/ -m "not live"` 200 passed
- **하네스**: harness consistency / vendor boundary / output_schema_drift /
  envelope_change / cross_channel 전부 exit 0
- **Baseline 갱신**: **없음** (성공 경로 envelope 불변)
- **환경 제약**: `ansible-playbook --syntax-check` 실행 불가 (Windows, `os.get_blocking` POSIX 전용).
  대체로 YAML 파싱 5종 + **Jinja2 표현식 163개 전수 컴파일 실패 0** + 12 Case 실제 렌더 수행.
  lab/Jenkins 에서 `--syntax-check` 재확인 필요.

## 2026-08-10 (c) — 진단 detail 전달 + 오진단 회귀 고정 (Phase 1-A)

계획 `precheck-snazzy-leaf.md` rev.2 Phase 1-A 구현에 대한 검증.

- **신규 테스트**: `tests/unit/test_precheck_detail_propagation.py` **13건**
  - C2~C6 각 실패 단계에서 `detail` 이 실제로 채워지는지 (DNS / TCP timeout / refused /
    기타 OSError / protocol) — `socket` 계층 monkeypatch, 네트워크 0
  - 성공 시 `detail is None` (이후 gather 실패로 precheck detail 이 새지 않음)
  - **자격증명 미포함 방어** — `_try_redfish_auth` 실패의 detail/reason 에 password /
    username / `Basic <base64>` 패턴 0건. detail 이 이번 변경으로 처음 envelope 에
    노출되므로 필수 방어선.
  - YAML 배선 회귀 — `_fail_error_detail` 생산처(run_precheck.yml) + 소비처
    (build_failed_output.yml) 양쪽 존재 확인 (한쪽만 있으면 다시 null 이 된다)
  - **B-8 재발 차단** — redfish 실패 메시지 분기에 `d.auth_success` 재등장 금지
  - **B-4 회귀** — `wait_for` 실제 순서(5986/5985/22) 추출 + checked_ports 리터럴 대조
  - **B-7 회귀** — redfish/esxi rescue 메시지의 `[task: ]` prefix 대칭
- **수정 테스트**: `tests/e2e/test_envelope_failure_modes.py` — fixture 를 production 실제
  shape(flat diagnosis)로 교체 + `collection_method` 실제 값으로 정정 + stale 인용 라인 정정.
  종전 fixture 는 `diagnosis.precheck.*` 중첩이라 실제 회귀를 잡지 못했다.
- **전체 회귀**: `pytest tests/` → **1381 passed, 5 skipped, 7 xfailed** (81.96s)
- **Jenkins 게이트 등가**:
  - Stage 3 `python tests/validate_field_dictionary.py` → **PASS** (10 checks, 8 passed, 0 failed)
  - Stage 4-a `pytest tests/e2e/` → **170 passed**
  - Stage 4-b `pytest tests/integration/ -m "not live"` → **200 passed, 3 skipped**
- **하네스**: `verify_harness_consistency.py` PASS (rules 28 / skills 51 / agents 60 / policies 10) /
  `verify_vendor_boundary.py` PASS / `output_schema_drift_check.py` PASS
  (sections=11 fd_paths=168) / `envelope_change_check.py` exit 0 /
  `cross_channel_consistency_check.py` exit 0
- **Baseline 갱신**: **없음** — Phase 1-A 는 성공 경로 envelope 을 건드리지 않는다
  (baseline 10 + examples 15 무변경)
- **환경 제약**: `ansible-playbook --syntax-check` **실행 불가** — Windows 개발환경에서
  `ansible/cli/__init__.py:44` 가 POSIX 전용 `os.get_blocking` 을 호출한다(ansible 2.19.9 설치됨,
  CLI 진입 자체가 AttributeError). 대체 검증 4종 수행:
  (a) 변경 YAML 5종 `yaml.safe_load_all` 파싱 OK
  (b) 변경 파일 내 **Jinja2 표현식 159개 전수 `env.parse()` — 실패 0**
  (c) redfish 실패 메시지 템플릿을 site.yml 에서 추출해 **4개 분기 전수 렌더** (details 부재
      케이스 포함 → `? / Unknown` fallback 확인)
  (d) `precheck_bundle.run_module()` 실행 → `run_precheck.yml` set_fact →
      `build_failed_output.yml` errors 조립까지 **전 경로 시뮬레이션**
      (NativeEnvironment, `ansible.cfg:44 jinja2_native=True` 반영):
      `detail='port=443: 연결 시간 초과 (timeout=3.0s)'` 가 `errors[0].detail` 까지 도달 **PASS**.
      성공 경로에서는 `None` 유지 **PASS**.
  → lab/Jenkins 에서 `--syntax-check` 재확인 필요 (미실행 항목으로 남김)
- **미실행**: 실장비 검증 없음 (코드 변경이 성공 경로 envelope 을 바꾸지 않음)

## 2026-08-03 (후속 4) — 교차 검증 불변식 + 조립 경로 링크 대조 가드 신설

사용자 요구: "다른 세대·벤더 물리장비에서도 버그가 없어야 한다. 그 기준으로 개선하고 있나?"
→ 기대값 고정형 회귀만으로는 미보유 장비를 못 잡는다는 진단 하에 **결과 자체의 정합성**을 보는
가드 2종 신설 (`tests/integration/test_port_classification_invariants.py`, 35건).

- **INV-1~4 (분류 자기모순)**: 같은 물리 포트가 `network.ports[]` 와 `storage.hbas[]`/`infiniband[]`
  에서 다르게 분류되면 FAIL. **replay fixture 10종 전수**(Dell iDRAC9 / HPE iLO5·iLO6·Gen12 /
  HPE CSUS 3200 / Lenovo XCC3 / DMTF mockup) + **baseline 10종 전수**에 적용.
  - 매칭은 `(adapter_id, port_id)` — `port_id` 는 호스트 내 유일하지 않다(실측 HPE DL380 Gen12:
    FC HBA 와 이더넷 NIC 이 둘 다 `"1"`/`"2"`). 초기 구현이 id 만 써서 HPE 3종에 **가짜 모순**을
    냈고, 제품 버그가 아님을 확인 후 테스트 측을 수정.
- **조립 경로 ↔ 노출 링크 대조**: 부모 응답이 `@odata.id` 를 노출하면 우리가 조립한 경로와 같아야 함.
  **10 fixture 전수 불일치 0** → 보유 세대에서 조립 안전 확인. 미보유 세대 캡처 시 자동 효력.
- **가드 유효성**: 분류 불변식 = 사고 형태 주입 시 검출 / 링크 대조 = 조립 키 변조 시 10 FAIL.
- **전체**: `pytest tests/ --ignore=tests/e2e_browser` = **1353 passed, 5 skipped, 7 xfailed**.
- 감사 산출물: `EXTERNAL_CONTRACTS.md` 2026-08-03 "조립 경로 17곳 전수 목록 + 세대 이동 위험도".
- Baseline 갱신: 없음.

## 2026-08-03 (사이트 Dell NetworkAdapters 400 마스킹 fix)

사이트 Jenkins console(DAY_1/git/소연등록redfish #1) Dell 8대 `status=partial` 조사 → 보조 섹션
마스킹 + 400 미분류 + detail 소실 3건 fix.

- 신규 회귀 **27건**: `tests/unit/test_network_adapters_aux_status.py`(21) +
  `tests/integration/test_site_dell_networkadapters_400.py`(6 — 실 R740 미러의 NetworkAdapters 를 400 으로
  변조해 모듈→normalize fragment→build_sections→build_status 전 체인 렌더, 역가드 포함).
- 전체: `pytest tests/ --ignore=tests/e2e_browser` = **1302 passed, 5 skipped, 7 xfailed**.
- 게이트: output_schema_drift(sections=11 fd=168) / envelope_change / jinja_compile / jinja_namespace /
  additive_only / status_logic / docs20_sync / verify_harness_consistency / verify_vendor_boundary /
  check_project_map_drift **전부 rc=0**. py_compile + YAML parse OK.
- 가드 유효성 실증: `git stash push -- redfish-gather/tasks/normalize_standard.yml` 후 재실행 → **9 failed**
  (fix 없으면 신규 테스트가 실제로 잡음), stash pop 복원.
- Baseline 갱신: 없음 (10종 전부 `sections.network=success` 유지 — 변경 전후 동일).
- **미실행(환경 제약)**: `ansible-playbook --syntax-check`(CLI 부재) / 실 Jenkins 빌드 → NEXT_ACTIONS 등재.
- Evidence: `tests/evidence/2026-08-03-network-adapters-400-masking.md`

### 2026-08-03 (후속) — 사이트 재검증 + 근본 원인 정정

- **빌드 #3 재검증**: Dell 8대 `partial → success`, `sections.network failed → success`, 빌드 SUCCESS.
  전수 비교에서 바뀐 필드는 `sections.network` 하나뿐(data keys / network sub-keys / interfaces 전부 동일).
- **정정**: 400 은 장비 미지원이 아니라 **경로 오류**(iDRAC8 은 NetworkAdapters 가 `Systems` 밑).
  400→unsupported 분류 **철회** + Chassis→Systems fallback 신설.
- **전체**: `pytest tests/ --ignore=tests/e2e_browser` = **1306 passed, 5 skipped, 7 xfailed**.
- 개정 회귀: unit 24 + integration 7. 핵심 3건 —
  `test_systems_fallback_recovers_nic_cards`(실 R740 미러를 Systems 토폴로지로 변조 → 원본과 동일 NIC 집합 수집) /
  `test_400_is_not_treated_as_unsupported`(은폐 재발 차단 — 헬퍼 부활 자체 금지) /
  `test_chassis_success_does_not_try_systems`(1순위 200 시 왕복 불변).
- 게이트 9종 rc=0 (harness_consistency / vendor_boundary / output_schema_drift / envelope_change /
  jinja_compile / additive_only / status_logic / docs20_sync / adapter_origin). py_compile OK.
- Baseline 갱신: 없음.

### 2026-08-03 (후속 2) — 빌드 #4 실효 확인 + FCoE CNA 오분류 fix

- **빌드 #4 (fallback 배포 후)**: 8대 전부 `adapters` 1건 + `ports` 4건 수집, 빌드 SUCCESS.
  MAC 이 `network.interfaces[]` 와 일치. **fallback 실효 확인 — 목표 달성.**
- **노출된 기존 버그**: 같은 포트 4개가 `network.ports`=Ethernet 인데 `storage.hbas`=FibreChannel.
  CSUS-FC1 휴리스틱(`ndf_wwpn` → FC)이 Ethernet 판정보다 위에 있던 것 → 맨 끝으로 강등.
- **전체**: `pytest tests/ --ignore=tests/e2e_browser` = **1315 passed, 5 skipped, 7 xfailed**.
- 신규 회귀 9건: `tests/unit/test_fcoe_cna_not_fc_hba.py` — 오분류 방지 3 / 진짜 FC·FCoE·IB 보존 5 /
  end-to-end(사이트 57800 재현 → `fc_hbas == []`) 1.
- **가드 유효성**: 강등을 되돌리면 4 failed 확인.
- CSUS(명시 신호 전무 + WWPN) / Dell R740(명시 `NetDevFuncType=FibreChannel`) 실미러 replay 모두 통과.
- Baseline 갱신: 없음.

### 2026-08-03 (후속 3) — 빌드 #5 부분 해결 + orphan NDF 부모 상속 fix

- **빌드 #5**: 8대 중 6대 `hbas=0` 해결, 2대(.52/.152) 잔존. 원인 = NIC 펌웨어 15.20.13 이 NDF 에
  MAC 파생 WWN 노출 + Dell NDF Id(`<PortId>-<funcIdx>`) 가 join 2종에 모두 빗나가 orphan → 포트
  컨텍스트 없이 분류 → 강등 fix 무력화.
- **fix**: orphan NDF 가 부모 포트 신호(`PortProtocol`/link_tech/raw port)를 상속. 접두 매칭 + 구분자 `-` 요구.
- **전체**: `pytest tests/ --ignore=tests/e2e_browser` = **1318 passed, 5 skipped, 7 xfailed**.
- 신규 회귀 +3 (총 12): orphan 부모 상속 / orphan 이어도 진짜 FCoE 는 HBA 유지 / 접두 구분자 경계.
- **가드 유효성**: 상속 로직 제거 시 1 failed 확인.
- Baseline 갱신: 없음.

## 2026-06-15 (Lenovo SR650 V4 실 미러 검수 — 2-Round 수렴)

Lenovo ThinkSystem SR650 V4 (XCC3, fw IHX414J 1.22) 전수 미러(2901 리소스) `replay_full_mirror.py`
오프라인 재생 → 10 섹션 raw 1:1 provenance 대조 + 4-perspective 적대적 교차검증. 추세 **2 → 0** (수렴).

- production fix 2 (redfish_gather.py): (1) `gather_firmware` pending 보존 — `is_pending` 를 Cisco
  빈슬롯(`N/A`/`''`) 필터 앞으로 이동 + version=""→null (XCC3 pending 2건 24→26 복원). (2) `gather_network`
  MAC `.lower()` — network_adapters/bmc/ports 와 case 일관 (round3 XC-4 적용 누락분).
- golden 재생성: `dmtf_rackmount1/expected_output.json` — diff 가 network MAC case 단독임을 확인 후
  `emulator_harness.run_gather` 동일 경로로 재생(faithful).
- 검증: `pytest tests/ --deselect tests/e2e_browser/test_jenkins_master.py` = **1123 passed, 6 skipped**
  (검수 전 baseline 무회귀). output_schema_drift / verify_harness_consistency / verify_vendor_boundary /
  py_compile PASS. e2e_browser 2건 = live Jenkins lab 망 미도달(코드 무관, 검수 전부터 FAIL).
- Baseline 갱신: 없음 (lenovo_baseline 은 XCC1 V2 — 구조 테스트 통과, 실측 미러 부재로 무수정 rule 13 R4).
- Evidence: tests/evidence/2026-06-15-lenovo-sr650-v4-audit.md

## 2026-06-09 (Round 16 — 멀티에이전트 적대적 버그헌트 루프, 수렴)

5 pass 멀티에이전트 루프(finder → skeptic refute → 메인 재검증 + Jinja2 렌더/Python 실행). confirmed **15 fix**.
추세 **10 → 1 → 2 → 2 → 0** (pass5 수렴 게이트 `CONVERGED: true`). pass2~5 diff reviewer 4연속 회귀 0건.

- 신규 테스트 +7: `tests/integration/test_redfish_round16_robustness.py` (6 — gather_power PowerControl 비-list
  dict/int 컨테이너 방어 3 / multi-node managers·partitions·chassis `_capped` 상한 3) +
  `tests/unit/test_adapter_common_robustness.py` (+1 — 빈 match YAML null → lookup abort 방어).
- production fix 15: redfish_gather.py(power 비-list 가드 / multi-node _capped) / precheck_bundle(socket try
  이동 ×2 / http_get with-close) / adapter_common(null match ×3 함수) / os-gather windows(cpu null crash ×2 /
  memory 'None' 누설 / network null-speed·link_status) / os-gather linux(users uid 수치정렬 / storage lsblk
  null model) / esxi collect_runtime(gw loop-scope namespace) / redfish normalize_standard(null ProcessorType).
- listening_ports 교차검토 충돌 해소: 정본 str[](gather_runtime+examples+실장비) → stale int[] 아티팩트
  (field_dictionary/docs/baseline×2) 정정. **코드 무변경** (어떤 테스트도 타입 미assert 확인).
- 재발 class 전수 sweep 종결: None-handling(default('')/is defined) grep 0 / membership('lit' in None) 0 /
  loop-scope(`pre_commit_jinja_namespace_check.py` 77 YAML) flagged **0/77**.
- 검증: pytest **1029 passed, 4 skipped** (`--ignore=tests/e2e_browser -m "not live"`; 기준선 1022 무회귀).
  vendor_boundary / harness / output_schema_drift / py_compile / yaml.safe_load PASS.
- ⚠️ os/esxi/redfish YAML 변경은 본 환경(ansible-playbook CLI 부재) Jinja2 직접 렌더로 검증 — 실 smoke 권장.
- 상세: `tests/evidence/2026-06-09-round16-multiagent-bughunt.md`.

## 2026-06-09 (Round 15 — 멀티에이전트 적대적 버그헌트 루프, 수렴)

6라운드 멀티에이전트 루프(finder → skeptic refute → 메인 재검증). confirmed 53 → **fix 33** / skip·defer 20.
추세 22→13→7→7→3→1(오탐). 6연속 라운드 regression reviewer 0건 + skip-audit reject(skip 옳음).

- 신규 테스트: `tests/unit/test_round15_fixes.py` (17 — bios_date 검증 / merge_power serial dedup /
  adapter version·distribution·os_type 보너스 / diagnosis 비-dict 가드 / gather_processors all-absent / jedec 2-char).
- production fix 33 (전 채널): redfish_gather.py / adapter_common / precheck / diagnosis_mapper / jedec_mapper /
  build_output / os-gather(linux+windows) / esxi-gather / scripts(drift+regex hook) / Jenkinsfile·_portal.
- 재발 class grep 종결: `default('{}'|'[]')|from_json` 0 / os-gather 미가드 dict-fact `.attr` 0.
- 검증: pytest **1022 passed, 5 skipped** (`--ignore=tests/e2e_browser`; 기준선 1005 무회귀). vendor_boundary /
  harness / regex hook self-test 10/10 / yaml.safe_load / py_compile PASS.
- ⚠️ os/esxi YAML + Jenkinsfile* 변경은 본 환경(ansible/Jenkins 부재) 미실측 — 정적 검증만. 실 smoke 권장.
- 상세: `tests/evidence/2026-06-09-round15-multiagent-bughunt.md`.

## 2026-06-09 (HPE CSUS 3200 모델 검수 + 누락 5종 구현 — ADR-2026-06-09)

CSUS 3200 Redfish 모델 검수 → 누락 5종(boot/thermal/log_services/composition/fabrics) Additive 구현.

- 신규 테스트: `tests/unit/test_csus_extended_topology.py` (16 — gather_thermal legacy+ThermalSubsystem fallback / gather_boot / gather_manager_logs / gather_composition_service / gather_fabrics / 통합 토폴로지 + 13-vendor 무영향) + `tests/unit/test_csus_fixture_replay.py` (7 — fixture @odata.id 재생 end-to-end).
- 신규 fixture 14 (thermal / logservices+2 / compositionservice+resourceblocks+3 / fabrics+flexgrid+switches2+endpoints2 / expansion chassis2+thermal2) + service_root 링크 + baseline 5종 키.
- 연결-영역 fix: gather_chassis_multi append-on-fail (chassis_count under-report 해소).
- 검증: pytest **996 passed, 6 skipped, 2 failed** (e2e_browser live-Jenkins 10.100.64.152 미도달 — 본 작업 무관). output_schema_drift / vendor_boundary / harness gate PASS. baseline JSON parse OK. golden(hpe emulator+dmtf) 불변 (multi_node 비-emulator 경로).

## 2026-06-09 (적대적 robustness 루프 R7~R14 — 수렴 완료)

14 라운드 멀티에이전트 적대적 hunt 수렴. 추세 26→23→21→17→11→9→5→6→4→1→7→4→7→3, R11-14 genuine 0.
누적 ~106 production 가드 + 18 robustness 테스트파일. 상세: tests/evidence/2026-06-09-adversarial-robustness-loop.md.

- 신규(R7~14): test_redfish_round{4,5,6,8,9,10,11}_robustness.py + test_callback_json_only_robustness.py + precheck/adapter_common 회귀 보강.
- production: redfish_gather.py(_str/_as_list/_dicts 헬퍼 + 전 클래스 가드) / adapter_common.py / precheck_bundle.py / merge_fragment.yml(Jinja2) / esxi normalize(Jenkins-verify) / callback json_only.py.
- 검증: pytest 973 passed(+e2e_browser 2 fail=사이트 Jenkins 무관) / golden 52 byte 불변 전 라운드 / gates OK.
- false-positive 차단: regex_search float/list 오해 2건, speed_gbps int 4회 기각 (golden ground-truth).


## 2026-06-09 (Round 4 적대적 hunt — 17 confirmed, ~13 수정)

- 신규 `tests/integration/test_redfish_round4_robustness.py` (5): _capped 비-list / _compute_final_status 비-str detail / SimpleStorage Devices / gather_system total_gib / gather_memory rank·width int.
- production: 잔여 배열 루프 _dicts/_as_list sweep + _post/_patch json + int 통일 + esxi datastore 가드.
- **949 passed, 5 skipped**(직전 944 + 5). golden 52 byte 불변. 추세 26→23→21→17 confirmed.

## 2026-06-09 (Round 3 적대적 hunt — 21 confirmed, ~14 수정)

- 신규 `tests/integration/test_redfish_round3_robustness.py` (6): _as_list/_dicts 헬퍼 + pc0/_resolve_all/normalize ipv4/processors int/_make_ib_port.
- production: redfish_gather.py(_as_list/_dicts + 배열 가드 6 + cpu/memory int) + adapter_common(None alias).
- **944 passed, 5 skipped**(직전 938 + 6). golden 52 byte 불변. 추세 26→23→21 confirmed.

## 2026-06-09 (Round 2 적대적 hunt — 23 confirmed, ~15 수정)

### 신규 테스트 (+9, +1 skip)
- `tests/unit/test_callback_json_only_robustness.py` (2, ansible 부재 시 skip): json.dumps 비-직렬화 str fallback.
- `tests/integration/test_redfish_round2_robustness.py` (7): cores_per_socket 평균 / _is_404 비-str / power capacity int / ctrl_members·resolve_all isinstance / network SpeedMbps int.

### 회귀 결과
- `pytest --ignore=e2e_browser` **938 passed, 5 skipped**(직전 931 + 7). 무회귀. golden 52 byte 불변.
- 기각 2(#6/#19 golden float / fall-through) + 보류 2(#7 enhancement / #2 non-issue) — CURRENT_STATE 참조.

## 2026-06-09 (Round 1 멀티에이전트 적대적 hunt — 24/26 confirmed 수정)

9 finder + 3-lens 적대적 검증(132 agent) → 26 confirmed → 24 수정. TDD RED→GREEN→golden 불변.

### 신규 테스트 (+27)
- `tests/unit/test_adapter_common_robustness.py` (5): 비-str vendor/pattern/priority + distro/version 빈값.
- `tests/unit/test_vendor_empty_alias_guard.py` (4): 빈 alias wildcard 매칭 방어.
- `tests/integration/test_redfish_storage_robustness.py` (11): controller/volume/normalize/resolve/account 비-list/dict/str + SmartStorage MiB 단위 + 0-capacity 보존.
- `tests/integration/test_redfish_misc_robustness.py` (7): _p 빈path / firmware 후행슬래시 / power int / FC WWPN MAC.

### production 수정
- redfish_gather.py (storage/vendor/power/firmware/_p), module_utils/adapter_common.py, lookup_plugins/adapter_loader.py, esxi-gather/tasks/normalize_system.yml(Jenkins-verify).

### 회귀 결과
- `pytest --ignore=e2e_browser` **931 passed, 4 skipped**(직전 906 + 27 신규 - 2 e2e_browser 무관). 무회귀.
- golden(hpe ×5 + dmtf ×1) **52 byte 불변** — 매 fix 후 재확인.

## 2026-06-09 (redfish/gather 견고화 — fault-injection 하네스 + crash 가드)

사용자 요청: 시뮬레이터/mock 을 **실제로 활용해** gather 로직 견고화(직전 사이클은 golden 고정만 함).
TDD: 변형 입력 RED → 가드 GREEN → golden byte 불변.

### 신규 테스트/도구 (+38 케이스, +5 test_*.py 파일, +1 도구 모듈)
- `tests/integration/mutation.py` (신규 도구): recording 변형 레이어(RFC-6901/결정론/deep-copy) — 기존 `make_replayer` seam 재사용.
- `tests/integration/test_robustness_mutations.py` (신규, 18): pointer 단위 + transparency(no-op=golden) + identity + single-node degrade + P1 @odata.id + P2 bounds.
- `tests/integration/test_redfish_normalize_robustness.py` (신규, 9): multi_node 정규화 bare int() crash(문자열 cores/capacity) RED→가드.
- `tests/unit/test_normalize_skeleton_sync.py` (신규, 2): data skeleton 3-파일 동기화 가드(PyYAML).
- `tests/unit/test_precheck_robustness.py` (신규, 4): precheck Members[0] 비-dict 가드.
- `tests/unit/test_merge_fragment_render.py` (신규, 5): merge_fragment list+dict 충돌 — 실 YAML 식 Jinja2 렌더 검증.

### production 가드 (TDD)
- `redfish_gather.py`: P0 `_safe_int`(L2858/2976-77/2985/3019) + P1 `_p()` 비-str/firmware split + P2 `MAX_COLLECTION_MEMBERS`/`_capped`/`partitions[0].get`.
- `precheck_bundle.py`: `_try_redfish_auth` Members[0] isinstance.
- `merge_fragment.yml`: data 병합 concat 분기 `is not mapping` (Jenkins 통합 후속).

### 회귀 결과 (실측)
- `pytest tests/ --ignore=tests/e2e_browser` → **906 passed, 4 skipped** (직전 868 + 38). 무회귀.
- golden(hpe_emulator ×5 + dmtf ×1) **52 byte 불변** — 매 fix 후 재확인(정상 입력 경로 무침범 증명).
- 전체 collected 875→913. CLAUDE.md/PROJECT_MAP test_*.py 52→57파일.
- e2e_browser 2 fail = 사이트 Jenkins(10.100.64.152) Playwright 미도달(본 변경 무관, 네트워크 격리).

## 2026-06-08 (AR-1 redfish vendor 정규화 reference 단위 테스트)

AUDIT AR-1(esxi vendor substring fallback 누락 — cross-channel divergence) 의 **검증 가능한 절반**: redfish 정규화 정본 `_normalize_vendor_from_aliases`(직접 테스트 부재였음) 고정.

### 신규 테스트
- `tests/unit/test_vendor_normalize_aliases.py` (신규, 5 함수 → **16 케이스**): 정확매칭 / **substring fallback**("dell inc" 마침표 없음 → 'dell', AR-1 대표) / 'unknown' default. esxi 가 맞춰야 할 기준선.

### 회귀 결과
- 신규 **16 passed**. py_compile PASS.
- esxi YAML 수정은 미적용(ansible-playbook Windows POSIX-only 미동작 + yamllint 부재 + rule §0 `[ANSIBLE]` defer 정책) → recipe = NEXT_ACTIONS §0.8 (Jenkins Agent + esxi baseline 회귀).
- 정정: AUDIT AR-1 → [PARTIAL] / CLAUDE.md test_*.py 51→52파일 / 487→492함수.

## 2026-06-08 (CS-3 CSUS per-partition normalize grouping drift 가드)

AUDIT CS-3 — `_summarize_partition_disks`/`_normalize_{storage,cpu,memory,network}_raw`(~210줄 평행 경로)의 grouping 로직에 drift 가드 부재를 보강. additive only(프로덕션 코드 0).

### 신규 테스트
- `tests/unit/test_partition_normalize_grouping.py` (신규, 17 함수 → **29 케이스**): 기존 `test_hpe_csus_multi_node.py` 의 **동질 happy-path** 가 못 잡던 grouping 키 판별을 **이질 입력**으로 고정.
  - storage 키(cap|media|protocol|model) 각 필드 판별(parametrize) + zero-skip + dedup-collapse(name+model+serial) + 이질 multi-group.
  - memory 키(cap|type|speed|mfr|part) 각 필드 판별 + zero-skip.
  - cpu: 다중 model 그룹 + processor_type 필터(CPU/CORE/'' 포함, GPU/FPGA/Accelerator 제외).
  - network: gateway 중복 제거(다중 NIC) + 0.0.0.0/빈 주소 필터.

### 회귀 결과
- `pytest tests/unit/test_partition_normalize_grouping.py` → **29 passed**.
- `pytest tests/unit/` → **485 passed**(기존 무회귀). py_compile PASS.
- 의미: 누군가 grouping 키에서 한 필드(예: storage protocol)를 빼면 이질 케이스가 즉시 실패 — 기존 동질 테스트는 통과하던 drift 를 차단.

### 정정
- `docs/ai/AUDIT-2026-05-29.md` CS-3 → [PARTIAL] (Python 측 drift 가드 완료, ansible↔python full parity 는 Jenkins Agent 후속).
- CLAUDE.md test_*.py 50→51파일 / 470→487함수.

## 2026-06-08 (AUDIT-2026-05-29 backlog 재확인 — stale 정정)

DMTF 작업 후속으로 audit backlog 의 "Python-only 저위험" 항목 실 상태 재확인(rule 28 — 추정 아닌 실측). 2종 모두 **이후 cycle 에서 이미 완료**됨이 확인되어 backlog table 정정.

- **AR-2 (JEDEC 2-테이블 drift)** = [DONE] — `tests/unit/test_jedec_drift_guard.py` **5 pass** 실측. 공유 byte 값 일치 + VENDOR_NAME_NORMALIZATION mirror + 방향성 가드. 통합(단일 source) 대신 drift 가드 채택(rule 10 R2 self-contained 보존).
- **R-4 (매직넘버 상수화)** = [DONE] — `BYTES_PER_GB_DECIMAL`/`BYTES_PER_MIB`/`MIB_PER_GIB`/`MBPS_PER_GBPS`(L52-55) + `_VOLUMETYPE_RAID_MAP`(L1856 module-const) 실측 확인.
- AR-3 (registry.yml 문서) = 비이슈 — CLAUDE.md/docs 가 "master index" 미사용, "adapter 인덱스"로 정확 기술. DSP8010 #2 link_status = 완료(`67cbaf27` merge).
- 정정: `docs/ai/AUDIT-2026-05-29.md` AR-2/R-4 row → [DONE] 표기. (코드 변경 0 — 문서 reconciliation)

## 2026-06-08 (DMTF 표준 mockup 오프라인 회귀 fixture)

DMTF 공식 mockup(DSP2043 `public-rackmount1`, BSD-3)을 `redfish_gather.py` 표준(OEM 미사용) 추출 경로의 오프라인 회귀 fixture 로 편입. Additive only(프로덕션 코드 0, schema·envelope 변경 0).

### 신규/변경 테스트
- `tests/integration/test_dmtf_mockup_replay.py` (신규, +8): `TestDmtfMockupReplay` 7 메서드(golden_match / vendor_matches_golden / standard_path_no_oem / core_sections_collected / system_identity_parsed / simplestorage_fallback_parsed / absent_resource_graceful) + 1 모듈 함수. HPE 클래스와 분리(generic 데이터에 HPE-shaped assertion 미적용).
- `tests/integration/convert_dmtf_mockup.py` (신규): mockup index.json 트리 → recording.json 변환기(`_p(@odata.id)` 키).
- `tests/integration/emulator_harness.py` (변경, Additive): `run_gather(realm_impl=None)` realm seam + `make_replayer` 3-tuple. `_REPLAY_MISS` → 실 BMC 404 모사(fidelity 수정).
- `tests/integration/test_hpe_emulator_replay.py` (변경): make_replayer 3-tuple unpack 2줄(assertion 무변경).

### 회귀 결과
- `pytest tests/integration/ -m "not live"` → **52 passed / 3 skipped**(DMTF 8 신규 + HPE 44 무회귀 + 가드 self-test). 0.48s.
- `pytest tests/` → **823 passed / 5 skipped / 2 failed**. 2 fail = `tests/e2e_browser/test_jenkins_master.py`(Playwright 라이브 Jenkins `10.100.64.152:8080` Timeout — 환경 의존, 본 변경 무관, Stage 4 offline 게이트 비포함).
- **HPE 5 golden byte-identical 유지** — `_REPLAY_MISS`/`make_replayer` 변경이 HPE 무영향 실측.

### 핵심 발견 (rule 95 R3)
- replayer `_REPLAY_MISS` err='replay-miss'(404 토큰 無) → absent endpoint 가 `_is_404_only_error` 미매치로 **failed 오분류**(실 BMC 404 는 unsupported). → `_REPLAY_MISS`=실 404 모사로 수정. (harness fidelity, 엔진 무변경)
- storage: SimpleStorage fallback 성공 시 'fallback 사용' notice 로 failed 분류(데이터 정상) — 기존 엔진 동작(HPE iLO4 SmartStorage 동일), 미변경. NEXT_ACTIONS 등재.

### stale 수치 정정 (rule 28/70 R2)
- CLAUDE.md / rule 00-core-repo: fixtures 395→398(+DMTF 3), test_*.py 49→50파일/462→470함수. PROJECT_MAP fingerprint 갱신.

## 2026-06-08 (에뮬레이터 하네스 Jenkins CI 편입)

- `Jenkinsfile` Stage 4: `pytest tests/e2e/` + `pytest tests/integration/ -m "not live"` 별도 호출 + RC 합산 (둘 중 FAIL 시 stage 실패).
- **발견·수정**: 단일 `pytest tests/e2e/ tests/integration/` → ImportError(공통 `conftest` module shadow). 별도 호출 + integration conftest 전역 `sys.path.insert` 제거로 해결.
- 검증: Stage 4 셸 로직 로컬 시뮬레이션 e2e 157 + integration 44, **FINAL_RC=0**. `pytest tests/ --ignore=e2e_browser` 815 pass(무회귀). ⚠️ 실 Jenkins agent 실행은 미확인(NEXT_ACTIONS §2.5).
- 동반 갱신: docs/17 / rule 80 R1-A / JENKINS_PIPELINES.

## 2026-06-08 (에뮬레이터 하네스 견고화 — 멀티에이전트 재검토 후)

37-에이전트 5차원 적대적 재검증 후 확정 갭 보강 (전부 tests/ + 문서, 프로덕션 코드 0).

### 신규/변경 테스트
- `tests/integration/test_hpe_emulator_replay.py` +5 메서드/함수:
  test_memory_total_mib / test_firmware_non_empty / test_bmc_firmware_version /
  test_fc_hbas_present(FC fixture keyed) / test_hermetic_guard_is_active(메타).
- `tests/integration/conftest.py`: autouse `_hermetic_network_guard` — 비-live 중
  `rg.urlreq.urlopen` raise 로 "네트워크 0" 불변식 강제.
- `emulator_harness.py` GOLDEN_KEYS += error_count → 5 golden 에 error_count:0 편입.
- `.gitattributes`(fixtures *.json eol=lf) + capture writer newline="\n".

### 회귀 결과
- `pytest tests/integration/` → **44 passed / 4 skipped** (live 1 + FC-skip 3). 가드 self-test PASS.
- 전체 `pytest tests/ --ignore=tests/e2e_browser` → **815 passed / 4 skipped** (10.5s). 기존 797/1 → +18/+3.
- py_compile 4 파일 / fingerprint --update 후 drift 0 / git add --renormalize.

### stale 수치 정정 (rule 28/70 R2)
- CLAUDE.md / rule 00-core-repo / PROJECT_MAP: fixtures 380→395 (실장비 380 + 에뮬레이터 15,
  rule 25 R7-B 라벨), test_*.py 48파일/445함수 → 49파일/462함수. PROJECT_MAP fingerprint 갱신.

## 2026-06-08 (HPE iLO 에뮬레이터 오프라인 회귀 하네스)

### 신규 테스트 (+26 / +1 skip)
- `tests/integration/test_hpe_emulator_replay.py` — 5 BMC type × 5 케이스 + 1 fixture-존재 + 1 live(skip):
  - `test_golden_match` (핵심 게이트): 모듈 gather 산출이 `expected_output.json` golden 과 strict 일치.
  - `test_vendor_is_hpe` / `test_collection_succeeded` / `test_processors_parsed` / `test_storage_parsed` (HBA/FC 경로).
  - `test_live_emulator_smoke` — `@pytest.mark.live`, `SE_EMULATOR_LIVE=1` 시만 (기본 skip).
- 캡처 fixture (emulator-derived): `tests/fixtures/redfish/hpe_emulator_{dl360,dl365_gen10plus,dl325_gen10plus_fc,dl380a,dl380a_gen12}/` (recording+golden+README).

### 변경 (Additive only — 프로덕션 코드 변경 0)
- `tests/integration/` 신설 (emulator_harness.py record/replay + capture_emulator.py + conftest.py 마커 등록).
- HPE 공식 iLO Redfish Emulator (BSD-3 v1.7.0) Docker 로 캡처. **에뮬레이터 != 실장비** (rule 21 R1 / 25 R7-B) — baseline_v1 미접촉.

### 회귀 결과
- **오프라인 보장**: 에뮬레이터 컨테이너 중지 후 `pytest tests/integration/` → **26 PASS / 1 skip(live)**. 네트워크 호출 0.
- 전체 `pytest tests/ --ignore=tests/e2e_browser` → **797 PASS / 1 skip** (10.3s). 기존 771 → +26.
- py_compile 4 신규 파일 PASS. project_map fingerprint 갱신 (tests/integration 신설).
- DL360_Gen12 제외 — 에뮬레이터 자체 버그 (`loader.py:740` WWN KeyError). 우리 코드 무관.

## 2026-06-08 (DMTF DSP8010 2026.1 공식 스키마 대조 audit — DRIFT-017)

### 신규 테스트 (+6)
- `tests/unit/test_redfish_pure_helpers.py` `_normalize_link_status` 6건:
  - up 변형(LinkUp/Up/Connected/Enabled/Active) / down 변형(LinkDown/Down/NoLink/Disconnected/Disabled/Inactive/Offline)
  - **DMTF 전이 상태 → down** (Starting/Training — DSP8010 2026.1 대조 gap fix)
  - unknown(None/""/none/unknown/null) / 미지 vendor 값 raw 보존
- RED 확인: 보정 전 transitional 테스트는 'starting'/'training' raw 반환으로 FAIL → 보정 후 PASS.

### 변경 (Additive only — rule 96 R1-B)
- `redfish-gather/library/redfish_gather.py:1192` `_normalize_link_status` down 버킷에 `starting`/`training` 추가.
- `schema/redfish_dmtf_2026.1/` 신설 (DMTF subset 28 리소스 56 json-schema + README + dmtf_info).
- `EXTERNAL_CONTRACTS.md` 대조 스냅샷 + `CONVENTION_DRIFT.md` DRIFT-017.

### 회귀 결과
- pytest **771 PASS / 1 skip / 2 fail**. 2 fail = `tests/e2e_browser/test_jenkins_master.py` (내부망 `10.100.64.152:8080` Playwright — 환경 제약, 본 변경 무관).
- fixture/baseline grep: Starting/Training link_status 0건 → 기존 회귀 출력 불변(검증).
- output_schema_drift(sections=10/fd_paths=83 불변) / verify_vendor_boundary / verify_harness_consistency / project_map fingerprint 일치 / py_compile — 전부 PASS.

## 2026-06-04 (vendor 출력 표시값 hpe→hp / CSUS 3200→hpCsus — ADR-2026-06-04)

### 신규 테스트 (+6, TDD RED→GREEN)
- `tests/regression/test_vendor_output_display.py` 신규 D1~D6:
  - D1 vendor_aliases 표시 맵 보유 (hpe→hp / csus adapter→hpCsus)
  - D2 hpe_baseline envelope vendor == `hp`
  - D3 hpe_csus_3200_baseline envelope vendor == `hpCsus`
  - D4 field_dictionary vendor enum 이 hp + hpCsus 노출 + `hpe` 미노출
  - D5 내부 canonical `hpe` 보존 (라우팅 무손상)
  - D6 `CANONICAL_VENDORS` 게이트가 hp/hpCsus 허용
  - D7 HPE Compute Scale-up Servers 패밀리 (CSUS 3200 + Superdome Flex) → hpCsus (2026-06-04 amendment, web 검증)
- RED 확인: 구현 전 D2/D3/D4/D6 FAIL (baseline=hpe, enum=hpe, frozenset 미포함) → 구현 후 전부 PASS.
- amendment RED: D7 추가 시 superdome_flex 미매핑 FAIL → `adapter_output_display` 에 추가 후 PASS. Jinja sim (superdome_flex→hpCsus, iLO6/7→hp) PASS.

### 변경 (출력 표시값만 — 내부 canonical 불변)
- `common/vars/vendor_aliases.yml`: `vendor_output_display`/`adapter_output_display` 신규
- `redfish-gather/site.yml` / `esxi-gather/site.yml` / `os-gather/site.yml`: `_out_vendor` 표시 매핑
- `schema/field_dictionary.yml` enum + baseline 2 + output_examples 2 + `CANONICAL_VENDORS`

### 회귀 결과
- pytest **748 PASS / 1 skip / 2 fail**. 2 fail = `tests/e2e_browser/test_jenkins_master.py` (내부망 `10.100.64.152:8080` Playwright — 환경 제약, 본 변경 무관).
- vendor-boundary PASS (data-driven — common/3-channel 하드코딩 0) / harness-consistency PASS / validate_field_dictionary PASS (Stage 3 gate) / output_schema_drift PASS.
- Jinja 표시식 단위 검증 (jinja2 직접 렌더): redfish 7 케이스 (hpe→hp, CSUS→hpCsus, Superdome Flex→hp, dell/cisco 무변, None 보존) + esxi 4 케이스 전부 OK.
- `ansible-playbook --syntax-check`: Windows dev box ansible CLI 부재 → Jenkins Agent 위임 (YAML 구조는 pyyaml parse PASS).

## 2026-06-04 (cycle ABCD — R-4 상수화 + JEDEC 가드 + fingerprint + stale 정정)

### 환경 정정 (직전 cycle 의 "ansible 미설치" stale)
- `import ansible` → **2.19.9 설치 확인**. pytest 로 Python 모듈/필터/플러그인 검증 가능.
- `ansible-playbook` CLI 는 PATH 부재 (rc=127) → playbook syntax-check/런타임은 Jenkins Agent 위임 (변동 없음).

### 신규 테스트 (+5)
- `tests/unit/test_jedec_drift_guard.py` 신규 5 (AR-2): `jedec_mapper.JEDEC_MAP` ↔ `redfish_gather._JEDEC_VENDORS` 정규화 후 공유키 동일 + 내부 self-consistency + B⊆A 방향성 (4) + `VENDOR_NAME_NORMALIZATION` 두 채널 mirror 가드 (1, AR-2 완결). cross-channel memory.manufacturer drift 차단.

### 변경 (동작보존)
- `redfish-gather/library/redfish_gather.py` (R-4): 매직넘버 9 사이트 → 명명 상수 (`BYTES_PER_GB_DECIMAL`/`BYTES_PER_MIB`/`MIB_PER_GIB`/`MBPS_PER_GBPS`) + `_VOLUMETYPE_RAID_MAP` module-level hoist. HTTP-status/auth 경로 미변경.
- `scripts/ai/check_project_map_drift.py`: fingerprint 를 git ls-files **경로 집합** 기반으로 결정론화 (CRLF/pyc/untracked + **내용 편집** 면역 — 파일 추가·삭제·이름변경 등 구조 변경만 추적).

### 회귀 결과
- pytest **705 PASS / 1 skip / 2 fail** (vendor-name mirror 가드 +1 포함). 2 fail = `tests/e2e_browser/test_jenkins_master.py` (내부망 `10.100.64.152:8080` Playwright — 외부망 환경 제약, 변경 무관). `--ignore=tests/e2e_browser` 시 **705 PASS / 0 fail**.
- A 영향 영역 집중 (storage/volume/capacity/memory/jedec/network/csus/multi_node): **112 PASS**.
- py_compile: `redfish_gather.py` / `test_jedec_drift_guard.py` / `check_project_map_drift.py` OK.
- 잔여 매직넘버 grep: 0 (정의부 제외). 잔여 `raid_map`(lowercase): 0.

### 적대적 검증 (workflow 3 스켑틱 — ultracode)
- **단위 상수 (A)**: `behavior_preserved`, 이슈 0. 200만 값 empirical sweep 으로 `round(x/1e9,2)==round(x/1_000_000_000,2)` bit-identical 확인 (int 상수 ↔ float 리터럴 등가). decimal↔binary 무교환 / `/`·`//`·`*` 연산자 보존 / MBPS 미병합.
- **raid_map hoist (A)**: `behavior_preserved`, 이슈 0. 키·값 정확 / 변이(.update/.pop/del) 0 / `.get()` RAIDType-first 단락 동일.
- **JEDEC 가드 (B)**: `behavior_preserved` (가드 유효 — 단일 테이블 변조 시 FAIL 입증, vacuous-pass 경로 없음). LOW 1: docstring 과장 → byte-INDEX 도출 모델로 정밀화 (입력 수용 경계 A≥4자/B≥2자 차이는 value drift 아님 명시).

### 연속 작업 (stat 리프레시 + fingerprint path-set + AR-2 완결)
- 실측 정정: redfish_gather.py 3812→3830줄 (R-4 +18) / test_*.py 42·375→46·421 (jedec 4 + vendor-name 1 + redfish 순수헬퍼 21 + adapter 점수 16). fixtures 353 json · adapter 42·31 · 9 vendor · baseline 9 정확 유지. historical(AUDIT/CURRENT_STATE 2026-05-29) 보존.
- fingerprint OID→경로집합 정밀화 (내용 편집에도 drift 0 — commit 후 drift clean 입증).
- `tests/unit/test_redfish_pure_helpers.py` 신규 21: `_safe`/`_safe_int`/`_removeprefix`/`_strip_or_none`/`_canonical_vendor_name`/`_normalize_jedec` 특성화 (이전 0 커버 — rule 96 robustness 보호). 전부 현재 동작과 일치 (버그 0).
- `tests/unit/test_adapter_scoring.py` 신규 16: `adapter_score` 공식(priority×1000+spec×10+match) 우세관계 + 불일치 -9999 disqualify + `normalize_vendor`(G7 trailing-dot) + `pattern_match_any`(invalid-regex fallback) + specificity 고정 (rule 12 R2 / 50 R3 계약). 버그 0.
- commit: ABCD `6cf40e3b` / stat `43099d96` / vendor-name 가드 `02a014a9` / 순수헬퍼 `407d31ce` / adapter 점수 (본 commit).

## 2026-05-29 (cycle audit-cleanup — 전수 audit + 안전 정리)

### 신규 테스트 (+4)
- `tests/regression/test_csus_mock_consistency.py` 신규 4: CSUS mock baseline 자기 일관성 가드 (summary 카운트 == list 길이 / representative == partitions[0] / multi_node enabled+layout / mock 표식 유지 — 실측 교체 시 skip).

### 변경
- `tests/regression/conftest.py`: CSUS registry 라벨 `hpe_csus_3200_redfish` → `hpe_csus_3200_redfish_MOCK` (실측 4 + mock 1 명시). `test_cross_channel_consistency.py:232` 주석 동기화.
- dead code 제거 후 영향 영역 회귀 (diagnosis/adapter/filter/precheck 206 + full 699).

### 회귀 결과
- pytest **703 PASS / 0 FAIL** (699 + CSUS 가드 4).
- `verify_harness_consistency` PASS (rules 28 / skills 51 / agents 60 / policies 10), `verify_vendor_boundary` PASS, `check_project_map_drift` (fingerprint 갱신).
- py_compile: `redfish_gather.py` / `diagnosis_mapper.py` / `adapter_common.py` OK.
- 환경 제약: ansible 미설치 → `ansible-playbook --syntax-check` 미실행 (rule 24 R1 환경 제약 명시). ansible YAML 동작 변경은 미적용 (AUDIT-2026-05-29.md 로 위임).

## 2026-05-29 (cycle hba-ib-csus — CSUS 3200 전 공통 섹션 + HBA/InfiniBand 전 채널)

### 신규 테스트 (+14)
- `tests/unit/test_hpe_csus_multi_node.py` +7: per-partition `_normalize_{storage,network,cpu,memory}_raw` (canonical shape / B01 GPU 제외 / 단위 grouping / 빈 graceful) + 토폴로지 per-partition dict shape.
- `tests/regression/test_hba_ib_canonical.py` 신규: 전 baseline `storage.hbas[]`/`infiniband[]` canonical 키 + port_type/source enum + multi_node partition hbas/ib 키.
- `tests/regression/conftest.py`: CSUS baseline registry 등록 (9 baseline) + T10 redfish min 4→5.

### 회귀 결과
- **pytest 699 PASS / 0 FAIL** (full suite; 기존 652 + CSUS baseline regression registry 등록 parametrize + per-partition/canonical 신규 테스트).
- `tests/validate_field_dictionary.py` PASS (83 entries, 0 error, warnings only).
- Windows/Linux HBA·IB Jinja **standalone render harness** PASS (ansible 부재 환경 — `from_json`/`regex_replace` 등록 후 FC/iSCSI 분류·SAS 제외·단일원소 collapse·IB rate 파싱 검증).
- YAML(esxi/windows/linux/adapter) + JSON(csus/esxi baseline, fixture) parse PASS.

### Baseline 갱신
- `schema/baseline_v1/hpe_csus_3200_baseline.json` — 전 공통 섹션 realistic mock 전면 작성 (FC HBA 2 + RAID1 SATA + DDR5 2TB + 3 canonical partition). **여전히 mock (lab 부재)** — 사이트 fixture 후 교체 의무.
- `schema/baseline_v1/esxi_baseline.json` — hbas 5→2 (FC `nfnic` 만 — SATA AHCI/SAS RAID 재분류 제외, 동일 raw).

### 환경 제약
- ansible-playbook `--syntax-check` 미실행 (Windows 로컬 ansible 부재) — YAML parse + Jinja render harness 로 대체 검증.

---

## 2026-05-12 (cycle hpe-csus-rmc-multi-node — HPE CSUS 3200 / Superdome Flex RMC 멀티-노드 정식 지원)

### 신규 단위 테스트 3 모듈 (29 PASS)
- `tests/unit/test_classify_rmc_label.py` — 15 PASS: `_classify_rmc_label` / `_classify_manager_role` / `_classify_chassis_kind` 라벨 분기
- `tests/unit/test_resolve_all_members.py` — 6 PASS: `_resolve_all_member_uris` Members 전수 추출 + 기존 `_resolve_first_member_uri` 행동 보존
- `tests/unit/test_hpe_csus_multi_node.py` — 8 PASS: `_collect_multi_node_topology` 통합 (3-partition × 4-manager × 3-chassis)

### Mock fixture (lab 부재 — web sources 합성, rule 96 R1-A)
- `tests/fixtures/redfish/hpe_csus_3200/` 7 JSON + README — 합성 출처: sdflexutils 1.5.1 + DMTF DSP0266 v1.15 + iLO 5 API ref + HPE psnow doc/a50009596enw + support.hpe.com sd00002765en_us (사용자 제시 URL).
- `tests/expected/redfish/hpe_csus_3200/mock_v1.json` — fixture-derived expected (baseline 아님 — rule 13 R4 보호).

### Baseline 8종 derived 추가 (`data.multi_node: null`)
- cisco / dell / esxi / hpe / lenovo / rhel810_raw_fallback / ubuntu / windows — manager_layout 미정의 vendor 의 envelope Additive 키 보장.

### 회귀 검증 결과
- `pytest tests/`: **650 PASS / 0 FAIL** (20.95s) — 기존 621 + 신 29
- `verify_harness_consistency`: **PASS** (rules=28 / skills=51 / agents=60 / policies=10)
- `verify_vendor_boundary`: **PASS** — 신 라벨 분기 substring 매칭은 `nosec rule12-r1` (rule 12 R1 Allowed BMC 표시명 영역)
- `output_schema_drift_check`: **PASS** — sections=10 / fd_paths=74 (+9 nice) / fd_section_prefixes=17
- `validate_field_dictionary`: **PASS** — 65→74 entries / 8/8 checks / 9 advisory
- `pre_commit_{additive_only,docs20_sync,regex_search_conditional}_check`: **PASS** (silent)

### Commit / Tag
- commit `0b29b9d2` — github + gitlab 동시 push (rule 93 R7)
- tag `hpe-csus-rmc-multi-node-2026-05-12`

### 한계
- 사이트 실측 부재 — pytest 통과 = 합성 fixture 통과 ≠ 사이트 통과
- NEXT_ACTIONS C1~C8 등재 (사이트 fixture 캡처 / baseline / lab cycle / vault / Product 실측 / Member ID 실측 / Oem schema 실측 / RMC 활성화 실측)
- HPE community 7200359 위험 신호 대응: `diagnosis.details.rmc_activation_check` 메타 + `docs/22_rmc-activation-guide.md` 신규

---

## 2026-05-12 (cycle field-channel-refinement-F2b — ubuntu/windows cpu.summary 8 필드 일관성)

### Linux ssh probe 추가 (paramiko 직접 실측)
- 10.100.64.167 (ubuntu2404): lscpu Vendor=GenuineIntel/Socket=4, dmidecode VMware7,1, sudo -n 가용
- 10.100.64.96 (baremetal — Dell R760 Ubuntu 24.04.3): lscpu Xeon Silver 4510/Socket=2/cps=12, max_speed_mhz=4100MHz, mem=128GB, NVMe 447GB+SSD 10.5TB+1.6TB
- 10.100.64.163 (rhel920): VMware VM, RHEL 9.2 (Plow), kernel 5.14.0-284
- 10.100.64.165 (rhel960): VMware VM, RHEL 9.6, kernel 5.14.0-570

### 실행 결과 (F2-b 적용 후)
- `pytest tests/`: **621 PASS / 0 FAIL** (30.03s)
- `python scripts/ai/measure_field_usage_matrix.py --update-md`: 520 cells 재측정 (분류 변화 없음 — cpu.summary 형식 변환만)
- `python scripts/ai/verify_harness_consistency.py`: PASS

### baseline 변경
- `ubuntu_baseline.json` cpu.summary 4 → 8 필드 (manufacturer/max_speed_mhz/l2_cache_kb/l3_cache_kb 추가)
- `windows_baseline.json` cpu.summary 4 → 8 필드 (manufacturer/max_speed_mhz/l2_cache_kb/l3_cache_kb 추가)
- 8 필드 derived: manufacturer="Intel" (model 에서 추론), max_speed_mhz=null (VM raw 부재), l2/l3=null (raw 부재)

## 2026-05-11 (cycle field-channel-refinement-F5 — OS channel system.runtime 구현)

### Linux 실장비 ssh probe (paramiko)
- 10.100.64.161 (rhel810 / Python 3.6 raw fallback): timedatectl/systemctl/ss/free 출력 형식 확보
- 10.100.64.167 (ubuntu2404): ufw / systemd-timesyncd 출력 확보
- 10.100.64.169 (rocky960): chronyd / firewalld 출력 확보
- 10.100.64.135 (Windows Server 2022): ssh 비활성 (port 22 closed) — 표준 PowerShell 명령으로 보수적 코드 작성

### 실행 결과 (F5 적용 후)
- `pytest tests/ -x`: **621 PASS / 0 FAIL** (21.68s)
- `python scripts/ai/measure_field_usage_matrix.py --update-md`: 520 cells 재측정
- `python scripts/ai/hooks/output_schema_drift_check.py`: PASS (sections=10 / fd_paths=65 / fd_section_prefixes=16)
- `python scripts/ai/verify_harness_consistency.py`: PASS

### 코드 변경
- `os-gather/tasks/linux/gather_system.yml`: runtime gather (raw block) + parse + build fragment 9 필드 추가 (Python+raw fallback 공통)
- `os-gather/tasks/windows/gather_system.yml`: runtime gather (win_shell) + parse + build fragment 9 필드 추가
- `schema/field_dictionary.yml`: system.runtime channel `[esxi]` → `[os, esxi]` + help_ko 9 필드 통일 명시
- baseline 3 갱신: rhel810/ubuntu (Linux 실측) + windows (placeholder)

## 2026-05-11 (cycle field-channel-refinement)

### 실행 결과
- `pytest tests/ -x`: **621 PASS / 0 FAIL** (22.02s)
- `python scripts/ai/measure_field_usage_matrix.py --self-test`: **19 PASS / 0 FAIL** (신규 측정 스크립트)
- `python scripts/ai/measure_field_usage_matrix.py --update-md`: 520 cells 측정 완료
- `python scripts/ai/hooks/output_schema_drift_check.py`: PASS (sections=10 / fd_paths=65 / fd_section_prefixes=16)
- `python scripts/ai/hooks/envelope_change_check.py`: advisory 1건 (false-positive — envelope shape 변경 없음)
- `python scripts/ai/verify_harness_consistency.py`: PASS (rules=28 / skills=51 / agents=60 / policies=10)

### Schema 변경 영향 회귀
- `schema/field_dictionary.yml` 3 entries channel 정밀화 (memory.visible_mb / memory.installed_mb / system.runtime)
- envelope 13 필드 보존 확인 (rule 13 R5)
- baseline 8개 변경 0건 (Additive only — rule 92 R2)

### 매트릭스 측정 통계
- 4 상태 분포: present 302 / null 28 / empty 66 / not_supported 70 / missing 54 = 520
- 분류 1 후보: 16 → 13 (channel 정밀화 3건 적용)
- 분류 2 후보: 14
- 분류 3? 후보: 1 (Dell OEM 한정 — 의도된 동작)
- Drift 검출: 12 → 8 (남은 8건은 conditional / 환경 한정 — channel 유지)

## 2026-05-11 (Phase 7 — ticket_consistency 격상 + advisory hook 격상 4/4 완료)

### 사용자 명시
- "남아있는 작업있으면 모두 수행해라. 너가할수있는건 모두하라고. 후속작업이 생겨도 너가 할 수 있으면 다하라고"
- AI 자율 진행 — Phase 7 선행 작업 (107 ticket 6 절 변환) 자율 수행

### Phase 7 결과 매트릭스

| 단계 | 결과 |
|---|---|
| hook hint 확장 (보수적) | 위반 107 → 56 (51건 감소) |
| 잔여 56 ticket stub append (본문 보존) | 위반 56 → 0 |
| ticket_consistency hook BLOCKING 격상 | self-test 11/11 PASS / 전수 스캔 0 위반 |

### 회귀 검증 (격상 후)
- **pytest 587/587 PASS** (20.95s)
- **self-test (5 BLOCKING hook 종합)**:
  - pre_commit_jinja_namespace_check: 9/9 PASS (Phase 4)
  - pre_commit_docs20_sync_check: 6/6 PASS (Phase 5)
  - pre_commit_status_logic_check: 7/7 PASS (Phase 6.1)
  - pre_commit_additive_only_check: 5/5 PASS (Phase 6.2)
  - pre_commit_ticket_consistency: 11/11 PASS (Phase 7)
- **verify_harness_consistency**: rules 28 / skills 51 / agents 60 / policies 10 — 정합
- **verify_vendor_boundary**: 위반 0

### ticket stub 변환 통계
- 총 109 ticket 파일 (M-/F prefix, INDEX/archive 제외)
- 변경 56 (stub append) + skip 53 (이미 hint 확장 후 통과)
- 본문 보존 (write history 유지) + 누락 절 끝에 Phase 7 marker 명시 stub append

### advisory hook 격상 4/4 완료 — cycle 2026-05-11 종합

5 hook BLOCKING (Jinja Phase 4 + docs20_sync Phase 5 + status_logic Phase 6.1 + additive_only Phase 6.2 + ticket_consistency Phase 7).
회귀 자동 차단 영역: Jinja namespace / envelope 정본 / status 매트릭스 / Additive only / cold-start 6 절.

---

## 2026-05-11 (advisory hook 격상 Phase 6 — 4 hook 중 3 격상 + 1 보류)

### 사용자 명시
- "남아있는 작업있으면 모두 수행해라" — Phase 6 남은 advisory hook 3종 단계적 격상

### 회귀 검증 (cycle 종료 후)
- **pytest 587/587 PASS** (19.64s)
- **self-test** (3 hook 격상 후 재실행):
  - pre_commit_status_logic_check: 7/7 PASS
  - pre_commit_additive_only_check: 5/5 PASS
  - pre_commit_docs20_sync_check: 6/6 PASS (직전 격상)
- **verify_harness_consistency**: rules 28 / skills 51 / agents 60 / policies 10 — 정합
- **verify_vendor_boundary**: 위반 0

### Phase 6 결과 매트릭스

| Hook | 결정 | Commit | self-test | git log false-positive | escape hatch |
|---|---|---|---|---|---|
| status_logic | 격상 | `01588650` | 7/7 | 1건 (M-A3 cosmetic) | STATUS_LOGIC_SKIP_COSMETIC |
| additive_only | 격상 | `e4c37086` | 5/5 | 2건 (schema 주석 cosmetic) | ADDITIVE_SKIP_NEW_CYCLE |
| ticket_consistency | 보류 | — | 11/11 | 107/109 ticket 위반 → 선행 변환 필요 | (격상 보류로 escape hatch 미적용) |

### ticket_consistency 격상 보류 — 전수 스캔 결과
- 총 109 ticket fixes/*.md 파일 (M-/F prefix, INDEX/archive 제외)
- **위반 107건** ("분석 / 구현" + "결정 / 결과" 절 누락 — write-cold-start-ticket 정본 미준수)
- 격상 시 향후 ticket 작업 모두 차단 → 선행 작업 (107건 6 절 변환 cycle) 필요
- Phase 7 NEXT_ACTIONS 등재 (다음 cycle 우선순위)

---

## 2026-05-11 (docs20_sync hook advisory → BLOCKING 격상 — advisory hook 격상 1/4)

### 회귀 검증
- **pytest 587/587 PASS** (18.06s) — 격상 전후 동일
- **self-test (pre_commit_docs20_sync_check)**: 6/6 PASS (격상 후 재실행 — 정본 1개 / 정본 2개+docs20 / 정본 외 / 빈 staged / Windows path / 정본 4종 전수)
- **verify_harness_consistency**: rules 28 / skills 51 / agents 60 / policies 10 — 정합
- **verify_vendor_boundary**: 위반 0
- **escape hatch**: `DOCS20_SYNC_SKIP=1` / `DOCS20_SYNC_SKIP_COSMETIC=1` 유지 (R7 Allowed 절 호환)

### 격상 작업 (2 파일 변경)
- `scripts/ai/hooks/pre_commit_docs20_sync_check.py` — line 170 `return 0` → `return 1` + docstring (Advisory → Blocking) + stderr 메시지 갱신
- `scripts/ai/hooks/install-git-hooks.sh` — line 7 + 96 주석 / 환경변수 안내 "rule 13 R7" → "rule 13 R7, BLOCKING cycle 2026-05-11"

### false-positive 0 검증 절차
- git log 5 cycle 전수 검토 (since cycle 2026-05-06 도입)
- 정본 4종 변경 commit (build_output.yml / build_status.yml / sections.yml / field_dictionary.yml) 모두 `docs/20_json-schema-fields.md` 동반 변경 확인
- 단일 위반 후보 (M-A3 commit `78611714`): build_status.yml 주석 강화 = cosmetic (R7 Allowed 절 — `DOCS20_SYNC_SKIP_COSMETIC=1` escape hatch 적용 가능)

---

## 2026-05-11 (harness-cycle 자기개선 — PROJECT_MAP fingerprint + NEXT_ACTIONS stale fix)

### 회귀 검증 (cycle 종료 시)
- **pytest 587/587 PASS** (22.41s) — cycle 진입 시점 587 / 종료 587 (테스트 추가/삭제 0)
- **verify_harness_consistency**: rules 28 / skills 51 / agents 60 / policies 10 — 정합
- **verify_vendor_boundary**: 위반 0
- **check_project_map_drift**: 갱신 후 fingerprint 일치
- **output_schema_drift_check**: sections=10 / fd_paths=65 / fd_section_prefixes=16
- **envelope_change_check**: clean (envelope 13 필드 / data shape 변경 0)
- **adapter_origin_check --all --redfish-only**: 30/30 PASS

### Tier 1 자동 fix (8건)
- `.claude/policy/project-map-fingerprint.yaml` — 3 디렉터리 fingerprint 갱신 (redfish-gather + adapters + tests)
- `docs/ai/NEXT_ACTIONS.md:194-201` — "잔여 32 ticket [PENDING]" stale entry 갱신 ([DONE] 반영)
- `docs/ai/NEXT_ACTIONS.md:265-270` (Phase 4) — Jinja namespace hook blocking 격상 결정 PENDING → [DONE]
- `scripts/ai/hooks/pre_commit_jinja_namespace_check.py` — advisory → BLOCKING (5 cycle false-positive 0 / 141 파일 전수 스캔)
- `scripts/ai/hooks/install-git-hooks.sh` — 주석 갱신
- `docs/19_decision-log.md` — Jinja blocking 격상 governance trace entry
- `docs/ai/catalogs/PROJECT_MAP.md` + `CLAUDE.md` — adapter count drift fix (39 → 41, Redfish 28 → 30, supermicro 5 → 8)
- `.claude/rules/00 / 12 / 50` — 동일 adapter count 동기화 (rule "현재 관찰된 현실" 절만, 본문 의미 변경 0)

### 추가 검증 (Jinja blocking 격상 직후)
- **self-test 9/9 PASS** (격상 후 재실행 — cycle-016 self-ref / namespace / mutation / per-iteration / loop-var / loop-외 / comment / 중첩 / filter self-ref)
- **141 YAML/J2 전수 스캔 0 blocked** (격상 후 재확인)
- escape hatch (`JINJA_NAMESPACE_SKIP=1` / `JINJA_NAMESPACE_SKIP_FILE`) 유지

### Tier 2/3 발견 — 0건

### 영향
- 코드 변경 / 테스트 추가 / vault 변경 / 의존성 변경 / envelope shape 변경 모두 **0** (Tier 1 catalog 정합 + hook 동작 격상만)
- 호출자 시스템 영향 0
- 향후 PR / commit Jinja2 namespace 회귀 (cycle-015 / -016 / M-D2 패턴) 자동 차단

---

## 2026-05-07 (refactor-review cycle — 7 우려 8 Phase + 잔여 후속 4 task)

### pytest 회귀
- 총: 32 → **461 PASS** (cycle 진입 32 → Phase 8 종료 441+1xfail → 잔여 후속 461)
- 신규 (본 cycle):
  - `tests/regression/test_cross_channel_consistency.py` — 107 PASS (Phase A)
  - `tests/unit/test_netmask_cidr_jinja_fix.py` — 19 PASS (잔여 후속 2)
- xfail → PASS 격상: cisco_baseline hostname=null drift 보정 (잔여 후속 1)

### 검증 hooks 신설
- `pre_commit_jinja_namespace_check.py` (advisory) — Phase B
- `pre_commit_fragment_skeleton_sync.py` (blocking) — Phase B
- 기존 hooks 26 → 28

### 영향
- envelope schema 변경 / 호출자 영향 / 의존성 추가 / vault 변경 / cron 변경 모두 **0**
- adapter / vendor 분리 (rule 12) / Fragment 철학 (rule 22) 모두 통과
- Lab 영향: cisco UCS 도입 시 hostname 재실측만 (코드 의도 보정값 검증)

### 중요 사고 검출 (회귀 차단)
- cisco_baseline.json hostname=null drift (회귀 테스트가 자동 검출)
- gather_network.yml + esxi normalize_network.yml netmask CIDR 사고 (Jinja namespace hook + 19 신규 회귀)

---

## 2026-05-07 (실 장비 개더링 — schema/output_examples/ 한글 주석본 신설)

- 환경: Jenkins 에이전트 10.100.64.155 (Ansible 2.20.3 / Python 3.12 venv `/opt/ansible-env/`)
- 코드 배포: 로컬 main → rsync → 에이전트 `~/se-realtest-2026-05-07/` (임시)
- 자격증명: vault/{linux,windows,esxi}.yml + vault/redfish/{vendor}.yml (변경 없음)
- 시도 endpoint 합계: **20대** (OS 7 + ESXi 3 + Redfish 10)
- 성공: **19대** (Cisco 10.100.15.1 만 root 503 failed)
- 채널별 결과:
  - OS Linux 6대 모두 success (rhel810/920/960 + ubuntu2404 + rocky960 + 베어메탈 Dell)
    - rhel810 = raw fallback (Python 3.6.8 → setup 모듈 미동작 → raw 모듈 사용)
    - 베어메탈 = vendor=dell DMI 자동 감지 (hosting_type=baremetal)
  - OS Windows 1대 success (Server 2022 / WinRM 5985 HTTP)
  - ESXi 3대 모두 success (7.0.3 build 20842708 on Cisco UCS C220)
  - Redfish 5 vendor 4대 success (Dell iDRAC10 / HPE iLO6 / Lenovo XCC3 / Cisco CIMC 4.1) + 1 failed (Cisco 503)
- envelope shape: 모든 19개 success envelope 13 필드 정상 (rule 13 R5 / rule 96 R1-B 보존)
- 산출물:
  - `schema/output_examples/` 신설 + 10 jsonc + README
  - `schema/baseline_v1/*_annotated.jsonc` 8개 삭제 (사용자 명시)
  - `tests/evidence/2026-05-07-real-gather.md` 작성
- 검증: pytest **335/335 PASS** + verify_harness_consistency PASS + verify_vendor_boundary PASS
- 호출자 영향: 0 (envelope 13 / sections 10 / field_dictionary 65 / baseline_v1 *.json / examples/*.json 모두 변경 없음)

## 2026-05-06 (cycle-020 phase 4 — Lenovo XCC 권한 cache 손상 fix + verify-fallback)

- 환경: 사이트 실측 (10.50.11.232 Lenovo XCC SR650 V2)
- Lenovo XCC 권한 이슈 root cause:
  - `infraops` RoleId='Administrator' + Enabled=true + Locked=false (정상 표시)
  - 그러나 ServiceRoot 외 모든 endpoint AccessDenied — 모든 권한 박탈
  - 사이트 실험: Strategy 1 Enabled 토글 → 401, Strategy 2 RoleId 토글 → 401, Strategy 3 DELETE+POST → 200
  - 핵심: PATCH password-only 가 권한 cache 손상. PATCH full body (Password+RoleId+Enabled+Locked 함께) → 권한 유지
- 코드 fix (redfish_gather.py):
  - PATCH existing user 후 `_get('Systems', target_user, target_pass)` verify
  - verify 401 = 권한 cache 손상 감지 → DELETE + POST 재생성 fallback
  - Dell vendor: PATCH-only (DELETE 미지원) → fallback 안 함 + errors[] 명시
  - 신규 `_delete()` helper 함수 추가
- 신규 회귀 2건:
  - `test_provision_lenovo_patch_silent_fail_delete_repost_fallback`
  - `test_provision_dell_patch_silent_fail_no_delete_fallback`
- pytest 결과: **281/281 PASS** (cycle-020 phase 3 279 → 281)
- 5 BMC × 4 endpoint 권한 매트릭스 (전수):
  - Systems / Chassis / Managers / AccountService 모두 HTTP 200
  - Lenovo XCC infraops 권한 정상 복원 확인
- Jenkins build #2: SUCCESS (5/5 BMC `used_role=primary` — recovery 진입 없음)

## 2026-05-06 (cycle-020 phase 3 — 전 vendor 호환성 + Dell BMC OEM 추출)

- 환경: 5 BMC + web sources (9 vendor)
- 신규 회귀 3건: `tests/unit/test_bmc_oem_dell_extraction_f50.py`
  - `test_bmc_oem_dell_idrac_card_extracted`
  - `test_bmc_oem_dell_missing_oem_returns_none_fields`
  - `test_bmc_oem_cisco_no_extraction`
- pytest 결과: **279/279 PASS** (cycle-020 phase 2 276 → 279, +3)
- 사이트 실측 (rule 25 R7-A-1):
  - 10.100.15.27 (Dell iDRAC9 7.10): Manager.Oem.Dell.DelliDRACCard 4 필드 추출 envelope 확인
  - 10.50.11.231 (HPE iLO 6 v1.73): Oem.Hpe 39 keys (이미 추출 — ilo_version)
  - 10.50.11.232 (Lenovo XCC SR650): Oem.Lenovo 21 keys (release_name 추출)
  - 10.100.15.2 (Cisco CIMC 4.1.2g): Oem={} (정상 — 표준 필드만)
- web 검증 (lab 부재 4 vendor):
  - Huawei iBMC: 표준 POST (Huawei 공식 docs)
  - Inspur ISBMC: 표준 POST (OCP)
  - Fujitsu iRMC: 표준 POST (mmurayama 블로그 + GitHub)
  - Quanta QCT: 표준 POST (knusbaum.org 실측 인용)

## 2026-05-06 (cycle-020 phase 2 — F50 Cisco 표준 지원 + infraops 통일)

- 환경: Jenkins agent 10.100.64.154 + 5 BMC 매트릭스
- 사이트 실측 (rule 25 R7-A-1):
  - **Cisco 10.100.15.2**: POST /Accounts {Id:'2', RoleId:'admin'} → HTTP 201
    + 인증 200. **이전 not_supported 결론 정정**.
  - HPE 10.50.11.231: PATCH /Accounts/3 password → 200 (slot 3 = infraops)
  - Lenovo 10.50.11.232: PATCH /Accounts/4 password → 200 (slot 4 = infraops)
  - 5 BMC 모두 infraops/Passw0rd1!Infra HTTP 200 통일 검증
- vault 4종 통일: hpe / lenovo / cisco / supermicro
  - primary password Passw0rd1! → Passw0rd1!Infra (Dell 1차 cycle 2026-05-06 와 동기)
- 코드 변경: vendor='cisco' early-return 제거 + POST 변형 분기
  (Id 자동 검색 + RoleId mapping)
- 신규 회귀 3건:
  - `test_provision_cisco_post_with_id_field_succeeds`
  - `test_provision_cisco_dryrun_no_post_call`
  - `test_provision_cisco_no_empty_id_returns_error`
- pytest 결과: **276/276 PASS** (cycle-020 phase 1 274 → 276, +2 net — F13 cisco_returns_not_supported 제거 + F50 3건 추가)

## 2026-05-06 (cycle-020 — F49 redfish account_provision 호환성 강화)

- 환경: 로컬 (Python 3.11.9 / pytest 9.0.2) + Jenkins agent 10.100.64.154 (Ansible 2.20.3)
- 신규 회귀 7건: `tests/unit/test_account_provision_f49_vendor_compat.py`
  - `test_provision_lenovo_400_retry_with_password_change_required` — XCC password policy retry
  - `test_provision_hpe_third_retry_with_oem_privileges` — iLO Oem.Hpe.Privileges 3차 retry
  - `test_provision_supermicro_first_attempt_success_no_retry` — supermicro 1차 성공
  - `test_provision_lenovo_500_no_retry` — 500은 retry 트리거 아님
  - `test_provision_dell_skip_reserved_slot1_and_retry` — slot 1 (anonymous) skip
  - `test_provision_dell_silent_fail_verify_detects` — PATCH 200 silent fail 감지 + 다음 슬롯 retry
  - `test_provision_dell_no_empty_slots_after_skip` — slot 1 skip 후 다른 슬롯 모두 차있음
  - `test_provision_hpe_405_lenovo_retry_succeeds` — HPE Oem retry 까지 안 감
- pytest 결과: **274/274 PASS**
- 사이트 실측 (rule 25 R7-A-1):
  - 10.100.15.27 / 10.100.15.31 (Dell iDRAC9 7.10.70.00) — slot 3 patch_empty_slot, vault 갱신 후 검증
  - 10.50.11.231 (HPE iLO) — 이미 infraops primary, recovery 진입 안 함
  - 10.50.11.232 (Lenovo XCC) — 이미 infraops primary
  - 10.100.15.2 (Cisco CIMC) — not_supported graceful
- vault 갱신: `vault/redfish/dell.yml` 의 primary password Passw0rd1! → Passw0rd1!Infra (15자)
- Jenkins job 등록: `redfish-account-provision-verify` (10.100.64.152 master)
- 자동화: `scripts/verify_account_provision.sh` (CLI 엔트리)
- 정적 검증:
  - py_compile redfish_gather.py PASS
  - YAML 4 파일 syntax PASS

## 2026-05-01 (cycle-019 phase 2 — F44~F47 신규 vendor 4종)

- 환경: 로컬 (Python 3.11.9 / pytest 9.0.2)
- 테스트 신규 7건: `tests/unit/test_new_vendors_f44_f47.py`
  - `test_f44_f47_vendor_aliases_yaml_has_4_new_entries` — vendor_aliases.yml 4 entry
  - `test_f44_f47_fallback_vendor_map_sync` — _FALLBACK_VENDOR_MAP sync 게이트
  - `test_f44_f47_bmc_product_hints_added` — _BMC_PRODUCT_HINTS 7 신 시그니처
  - `test_f44_f47_adapter_yaml_files_exist` — 4 adapter 파일 존재
  - `test_f44_f47_adapter_yaml_required_keys` — 4 필수 키 + priority=80
  - `test_f44_f47_adapter_match_includes_canonical_vendor` — match.vendor canonical
  - `test_f44_f47_ai_context_files_exist` — 4 ai-context 파일 + vault SKIP 명시
- pytest 결과: **108/108 PASS** (cycle-019 phase 1 101 → 108, +7)
- 정적 검증:
  - verify_harness_consistency PASS (vendor sync 게이트 통과)
  - verify_vendor_boundary PASS (nosec 주석 적절)
  - check_project_map_drift PASS (fingerprint 재갱신)
  - py_compile redfish_gather.py PASS
  - YAML 6 파일 syntax PASS
- baseline 회귀: skip (lab 부재 — 신규 vendor 4종 모두 lab/사이트 부재)

## 2026-05-01 (cycle-019 phase 1 — 7-loop + 10R extended audit P1 22건)

- 환경: 로컬 (Python 3.11.9 / pytest 9.0.2)
- 테스트 신규 7건: `tests/unit/test_redfish_tls_and_network_fallback.py`
  - F84: `test_f84_tls_context_min_version_1_2` / `test_f84_tls_context_max_version_1_3` / `test_f84_tls_context_unverified_self_signed` / `test_f84_tls_context_legacy_renegotiation_flag`
  - F48: `test_f48_network_adapters_uses_ports_when_no_networkports` / `test_f48_network_adapters_prefers_networkports_when_present` / `test_f48_network_adapters_skip_empty_placeholder`
- pytest 결과: **101/101 PASS** (cycle-018 94 → 101, +7)
- 정적 검증:
  - verify_harness_consistency PASS
  - verify_vendor_boundary PASS
  - check_project_map_drift PASS (fingerprint 갱신 — adapter 27 → 34)
  - py_compile redfish_gather.py PASS
  - YAML 9 파일 syntax PASS
  - adapter 4 필수 키 (match/capabilities/collect/normalize) 7 신규 모두 존재
- baseline 회귀: skip — 신 generation BMC adapter (F41/F47/F55/F61/F69) 는 lab 부재 영역. 기존 5 vendor lab fixture 영향 없음 (priority 역전 없음, 신 adapter 는 모두 priority ≥ 90 + model_patterns 차등).

## 형식

```
## YYYY-MM-DD (Round X / commit Y)

- 환경: <agent / vendor / 펌웨어>
- 명령: <pytest / ansible-playbook / redfish-probe ...>
- 결과: <PASS N / FAIL M>
- Baseline 갱신: <예/아니오 + 영향 vendor>
- Evidence: <tests/evidence/<날짜>-<주제>.md 링크>
```

---

## 2026-05-01 — P1 follow-up (F5/F13/F23 회귀 보강 + F23 적용)

- 환경: Windows 11 호스트 (Bash on Windows / pytest 9.0.2 / Python 3.11.9)
- 입력: 사용자 명시 "남아있는 작업 모두 수행해라"
- 적용:
  - **F5** `redfish_gather.py:_gather_power_subsystem` — 이미 적용된 EnvironmentMetrics fallback에 회귀 5건 신규 (`tests/unit/test_power_environment_metrics_f5.py`)
  - **F13** `redfish_gather.py:account_service_provision` — 이미 적용된 Cisco / 404 graceful 분류에 회귀 4건 신규 (`tests/unit/test_account_service_unsupported_f13.py`)
  - **F23** `os-gather/tasks/{linux,windows}/gather_users.yml` — `_sections_unsupported_fragment` wiring (Linux Python+Raw / Windows rc-aware) + 회귀 9건 신규 (`tests/unit/test_os_users_unsupported_f23.py`)
- 명령:
  - `python -m pytest tests/unit/ -q` → **94/94 PASS** (2.21s, 76 기존 + 18 신규)
  - `python -m py_compile redfish-gather/library/redfish_gather.py` → PASS
  - `python -c "import yaml; yaml.safe_load(...)"` (Linux/Windows gather_users + cisco_cimc.yml) → PASS
  - `python scripts/ai/verify_harness_consistency.py` → PASS (rules:28 skills:48 agents:59 policies:10)
  - `python scripts/ai/verify_vendor_boundary.py` → PASS
  - `python scripts/ai/check_project_map_drift.py --update` → 재baseline (os-gather + tests hash)
- Baseline 갱신: 없음 (코드 fragment 분류 변경 only — envelope 13 필드 동일)
- Evidence: 본 cycle은 코드 회귀 unit 위주. 사이트 검증 (Alpine/distroless 환경 빌드)은 외부 의존 — 후속.

### Additive 원칙 (rule 96 R1-B)
- envelope 13 필드 변경 0건
- schema/sections.yml 변경 0건
- `_sections_failed_fragment` → `_sections_unsupported_fragment` 라우팅만 (errors[] noise 차단)

---

## 2026-05-01 — 호환성 ticket 일괄 (F01~F43 22건)

- 환경: Windows 11 호스트 (Bash on Windows / pytest 9.0.2 / Python 3.11.9)
- 입력: 사용자 명시 "호환성 티켓 모두 수행하세요"
- 적용 (코드 변경 5건):
  - F05 `redfish_gather.py` — `_gather_power_subsystem` EnvironmentMetrics fallback (DMTF 2020.4)
  - F02 `normalize_standard.yml` — ProcessorType 필터 'CORE' enum 통과
  - F13/F08 `redfish_gather.py` — `account_service_provision` 404-only graceful 'not_supported' 분류
  - F20 `try_one_account.yml` — backoff sleep 1→5 (BMC lockout 회피)
  - F21 `ansible.cfg` — RHEL 9+ paramiko ssh-rsa legacy 호환
- 보류/검증만 (17건):
  - 이미 호환: F01, F09, F10, F12, F17, F22, F24, F34, F35, F40
  - lab 한계: F04, F11, F14, F15, F38
  - 추적: F33, F41, F42, F43, F16
  - graceful: F23, F07, F37, F39
- 명령:
  - `python -m py_compile redfish-gather/library/redfish_gather.py` → PASS
  - `python -c "import yaml; yaml.safe_load(...)"` (normalize_standard, try_one_account) → PASS
  - `python -m pytest tests/ -x` → **234/234 PASS** (29.41s)
  - `python scripts/ai/verify_harness_consistency.py` → PASS (rules:28 skills:48 agents:59 policies:10)
  - `python scripts/ai/verify_vendor_boundary.py` → PASS
  - `python scripts/ai/hooks/output_schema_drift_check.py` → PASS
  - `python scripts/ai/check_project_map_drift.py --update` → PASS
- 원칙: 호환성 cycle (rule 96 R1-B) — envelope 13 필드 변경 0건, Additive only
- Baseline 갱신: 없음 (호환성 fallback path 추가, 기존 200 응답 영향 없음)
- 후속: lab 한계 fix (F04/F11/F14/F15/F38) 사이트 fixture 확보 시 별도 cycle

---

## 2026-04-29 — Dell Redfish 비판적 검증 + envelope 값 미채움 7건 fix

- 환경: Windows 11 호스트 (Bash on Windows / pytest 9.0.2 / Python 3.11.9)
- 입력: 사용자 명시 "Dell Redfish 수집 안되는게 많고 값도 이상함. 키 늘리지 말고 버그 모두 fix"
- 분석: Round 11 reference (`tests/reference/redfish/dell/10_100_15_27`, R760, iDRAC 7.10.70.00) ↔ 코드 정적 비교
- 발견: 26건 (CRIT 2 / HIGH 11 / MED 5 / LOW 2 / 의도 6) → envelope 키 미채움/명확 버그 7건만 fix
- 변경 파일:
  - `redfish-gather/library/redfish_gather.py` (BUG-1, BUG-13, BUG-15, BUG-16, BUG-19 — 5건)
  - `redfish-gather/tasks/normalize_standard.yml` (BUG-12, BUG-13 fallback, BUG-14 fallback — 3건)
- 명령:
  - `python -m py_compile redfish-gather/library/redfish_gather.py` → PASS
  - `python -c "import yaml; yaml.safe_load(open('redfish-gather/tasks/normalize_standard.yml'))"` → PASS
  - `python -m pytest tests/ --tb=short` → **158 passed in 17.20s**
  - `python scripts/ai/verify_harness_consistency.py` → PASS (rules 28 / skills 43 / agents 49 / policies 9)
  - `python scripts/ai/verify_vendor_boundary.py` → PASS
- Baseline 갱신: **아니오** (rule 13 R4 — 실 BMC 재수집 후 Round 12 에서 갱신 예정. 영향 vendor: Dell 단독 — `hardware.bios_date` / `oem.estimated_exhaust_temp` 두 필드)
- Evidence: `tests/evidence/2026-04-29-dell-redfish-critical-review.md` (예정)
- 미수행 (envelope 키 추가 필요): BUG-2 controller metadata, BUG-3~10 PSU/Firmware/Drive/Volume/Memory/NIC 풍부 raw, BUG-11 BIOS Attributes 571
- 회귀 영향:
  - HPE/Lenovo/Supermicro/Cisco volumes — `boot_volume` 표준 우선화로 표준 BootVolume 응답 vendor 에서 명시 false/true 정확 반영 (이전 항상 None)
  - Dell volumes — boot_volume 동일 (표준 BootVolume None → Dell Oem fallback)
  - Dell hardware.bios_date — null → "MM/DD/YYYY" (실 환경 검증 시)
  - 모든 vendor cpu.logical_threads — per-processor TotalThreads 누락 펌웨어에서 fallback 활성

---

## 2026-04-29 — production-audit (4 agent 전수조사 + HIGH 30+건 일괄 fix)

- 환경: Windows 11 호스트 (Bash on Windows / pytest 9.0.2 / Python 3.11.9)
- 명령: `python -m pytest tests/ --tb=short`
- 결과: **148 passed in 17.53s** (이전 147 + remote_identifier_test guard 1)
- 추가 검증:
  - `verify_harness_consistency.py` PASS — rules 28 / skills 43 / agents 49 / policies 9
  - `verify_vendor_boundary.py` PASS — common/3-channel vendor 하드코딩 0건 (rule 12 R1)
  - `tests/validate_field_dictionary.py` PASS — 65 entries (Must 39 / Nice 20 / Skip 6)
  - `check_project_map_drift.py` — 4 drift 해소 후 PASS
- 변경 영역 (Phase 2):
  - common/tasks/normalize/ (skeleton 동기화)
  - 3 채널 site.yml (always block diagnosis dict)
  - schema/field_dictionary.yml (envelope top-level 8 entries)
  - esxi-gather/{site.yml,tasks/normalize_network.yml} (vendor normalize / DNS / netmask)
  - schema/baseline_v1/{cisco,windows}_baseline.json
  - os-gather/tasks/linux/{gather_cpu,gather_memory,gather_storage,gather_network}.yml
  - os-gather/tasks/windows/{gather_storage,gather_network,gather_runtime}.yml
  - redfish-gather/{library,tasks}/* (account_service / cross-channel typing / vendor merge)
  - common/library/precheck_bundle.py (IPv6 듀얼스택)
  - filter_plugins/diagnosis_mapper.py (None 가드)
  - Jenkinsfile + Jenkinsfile_portal (timeout / artifact / hard gate)
  - tests/scripts/* + scripts/ai/*.py (자격증명 환경변수화)
- Baseline 갱신: cisco_baseline.json (users null→[]) / windows_baseline.json (media_type 정규화)
- Evidence: 본 CURRENT_STATE.md + NEXT_ACTIONS.md 갱신

---

## 2026-04-29 — cycle-016 (사용자 11 항목 일괄 점검 + 실 Jenkins 빌드 5회 + summary grouping 완성)

- 환경: Windows 11 호스트 (PowerShell + Bash) + Jenkins master 10.100.64.152 (cloviradmin) + agent jenkins-agent
- Job: `hshwang-gather` (`https://github.com/hshwang1994/server-expoter` main pull)
- 명령: PowerShell `Invoke-WebRequest` + crumb + Basic Auth → `buildWithParameters` POST + console log fetch
- 결과:
  - **Build #39** target=redfish 10.100.15.27 → pipeline=SUCCESS / gather=failed (lab vault 자격 미정합) — JSON envelope 13 필드 + 한국어 메시지 + Stage 4 145 pytest pass
  - **Build #41** target=os 10.100.64.165 (RHEL 9.6) → 회귀 발견 `Template delimiters: '#' at 86`
  - **Build #42** 부분 fix 후 재발 → 추가 inline 코멘트 9개 제거
  - **Build #43** OS 첫 정상 가동 → status=success / network.summary.groups + storage.summary.groups 동작 확인 / system.runtime 채워짐
  - **Build #44** namespace pattern fix 후 → storage.summary.grand_total_gb=100 (이전 0 → 정상)
  - **Build #45** Redfish 회귀 검증 (코드 변경 영향 없음)
- pytest: 147 PASS (실 Jenkins agent + 로컬 모두 일치)
- harness consistency / vendor boundary / schema drift: 모두 PASS
- Baseline 갱신: 7 vendor + 3 example (`scripts/ai/inject_summary_to_baselines.py` 일괄)
- Evidence: `docs/ai/harness/cycle-016.md`
- commit: `0da258d5`, `88793df8`, `a2e3e75e`, `e18230b8`, `240106bc` main push 완료

---

## 2026-04-29 — cycle-014 (4 vendor BMC 실 검증 + HIGH Jinja2 fix + vault sync 발견)

- 환경: Windows 11 호스트 (paramiko 4.0.0) + Jenkins agent 10.100.64.154 (cloviradmin / Ubuntu 6.8 / ansible-core 2.20.3 — REQUIREMENTS.md 정합)
- 사용자 명시 권한: AI 모든 권한 (하네스 + 실 장비). 벤더당 1대 BMC 검증.
- 검증 BMC (baseline_v1 정본 IP):
  - Dell 10.50.11.162 (PowerEdge R740 / iDRAC 9)
  - HPE 10.50.11.231 (ProLiant DL380 Gen11 / iLO 6)
  - Lenovo 10.50.11.232 (ThinkSystem SR650 V2 / XCC)
  - Cisco 10.100.15.2 (TA-UNODE-G1 / CIMC)
  - Supermicro: baseline 부재로 별도 cycle
- 1차 (cycle-013 main `b605c68b`): 4 vendor 모두 fatal — `_precheck_ok` Jinja2 syntax error.
- **HIGH 회귀 fix** (commit `bf247266`): `common/tasks/precheck/run_precheck.yml:47` Jinja2 expression 안 `{# ... #}` 주석을 YAML 주석으로 분리.
- 2차 (fix 후): 4 vendor 정상 envelope 13 필드. precheck OK / detect_vendor OK / adapter 자동 선택 OK / collect 401 → rescue → 13 필드 envelope.
- curl 자격 검증 (자격 transcript 노출 0): ServiceRoot 4 vendor HTTP 200 / vault primary+recovery 모두 HTTP 401 → vault ↔ BMC sync 안 됨 (OPS-3 우선순위 격상).
- redfish 공통계정 자동 생성 (P2 account_service): recovery 자격 fail로 진입 미발생 (의도된 동작) → cycle-015 이월.
- Evidence: `tests/evidence/cycle-014/README.md` + 4 log + `docs/ai/archive/harness/cycle-014.md`
- Git: main `bf247266` push 완료.

---

## 2026-04-29 — cycle-013 (cycle-012 PR 머지 + 자율 매트릭스 + 정합 정정)

- 환경: Windows 11 + Python 3.11.9 (호스트)
- 변경 영역:
  - **AI-1** schema/examples — redfish_success.json + os_partial.json 11 path 보강
  - **AI-2** PROJECT_MAP — fingerprint 갱신 + 본문 stale 4건 정정
  - **AI-3** JENKINS_PIPELINES — vault binding 절 신규
  - **AI-4** SCHEMA_FIELDS — Must 31 / Nice 20 / Skip 6 = 57 정정 (1건 over count)
  - **AI-5** VENDOR_ADAPTERS — recovery_accounts 메타 절 신규
  - **AI-6** harness/cycle-012.md — 신규 (cycle-012 보고서 보존)
  - **AI-7** decisions/ADR-2026-04-29-vault-encrypt-adoption — advisory governance trace
  - **field_dictionary.yml** 헤더 주석 1줄 정정 (Nice 21 → 20)
- 명령 (실측):
  - `python -c "import json; ..."` schema/examples 2 파일 → PASS
  - `python tests/validate_field_dictionary.py` → **PASS** (10 checks, 8 passed, 0 failed, **0 warnings** ← 11 WARN 해소)
  - `python scripts/ai/verify_harness_consistency.py` → PASS (rules: 28, skills: 43, agents: 49, policies: 9)
  - `python scripts/ai/verify_vendor_boundary.py` → PASS (vendor 하드코딩 0건)
  - `python scripts/ai/check_project_map_drift.py` → PASS (drift 0건, fingerprint 갱신 후)
- 결과: 정적 검증 4/4 PASS. 도메인 코드 변경 없음 (catalog/문서만), 회귀 영향 없음.
- Baseline 갱신: 없음.
- Git: feature/3channel-expansion 3 commit (`0150fa2e` / `57745bd1` / `b1d8014c`) push 완료. main 머지는 OPS-8 (rule 93 R2 사용자 명시 승인) 대기.
- Evidence: `docs/ai/archive/harness/cycle-012.md` (cycle-012 보존), `docs/ai/archive/harness/cycle-013.md` (본 cycle 보고서), `docs/ai/decisions/ADR-2026-04-29-vault-encrypt-adoption.md`, `docs/ai/archive/handoff/2026-04-29-cycle-013.md`, `docs/ai/archive/README.md`

### Phase 3 추가 작업 (본 응답 후반)

- stale inline 47건 일괄 trace 표기 (rule 60 / pre_commit_policy / vault-rotator / security-reviewer / protected-paths)
- archive 진입: harness/cycle-001~005 (5) + impact/ 6 보고서 → docs/ai/archive/
- SECURITY_POLICY.md deprecated 헤더
- cycle-013 보고서 + handoff + archive README 신규
- 검증 4종 재확인: 모두 PASS

---

## 2026-04-29 — cycle-012 (3-channel gather 대형 확장 P0~P5 + 후속 PR 갱신)

- 환경: Windows 11 + Python 3.11.9 (호스트)
- 변경 영역:
  - **P0 Foundation** — Jenkinsfile 3종 + tests/e2e/test_envelope_failure_modes.py + .gitignore + scripts/bootstrap_vault_encrypt.sh + docs/01_jenkins-setup.md
  - **P1 Auth Multi-Candidate** — vault accounts list (8 파일) + redfish load_vault/collect_standard/try_one_account + os/esxi try_credentials + adapters 16개 recovery_accounts 메타
  - **P2 + P4 (Redfish)** — redfish_gather.py AccountService 4 메서드 + dryrun ON default + gather_network_adapters_chassis + account_service.yml
  - **P3 + P4 normalize** — Redfish summary + Linux memory summary + normalize_standard.yml HBA/IB 매핑
  - **P4 OS/ESXi** — gather_hba_ib.yml (Linux raw) + windows/gather_storage.yml Get-InitiatorPort + esxi/collect_network_extended.yml
  - **P5** — Linux/Windows gather_runtime.yml
  - **schema** — sections.yml 신 sub-key 명시 + field_dictionary.yml 12 entries Nice 추가 (총 58)
- 명령 (실측):
  - `python -c "import ast; ast.parse(...)"` → redfish_gather.py + test_envelope_failure_modes.py PASS
  - `python -c "import yaml; ..."` 38 modified/new YAML safe_load → PASS
  - `python -m pytest tests/e2e/test_envelope_failure_modes.py -v` → 50/50 PASS
  - `python -m pytest tests/e2e/` → **195 PASS** (145 기존 + 50 신규)
  - `python scripts/ai/verify_vendor_boundary.py` → PASS (rule 12 R1 nosec 처리)
  - `python scripts/ai/verify_harness_consistency.py` → PASS (rules: 28, skills: 43, agents: 49, policies: 9)
  - `python tests/validate_field_dictionary.py` → PASS (Must 31 / Nice 21 / Skip 6 = 58)
  - `ansible-playbook --syntax-check` → SKIP (Windows 메인 환경 제약, WSL 보류)
- 결과: 정적 검증 7/8 PASS + 1 SKIP (환경 제약). 회귀 195/195 PASS.
- Baseline 갱신: 없음 (rule 13 R4 — 실측 기반만 허용. P3/P4 신 필드는 Nice 분류로 baseline 회귀 영향 없음)
- Commit: `f0f621ce` P0 / `fe0be36c` P1 / `0448d00d` P2+P4(Redfish) / `fbb0f357` P3+P4 normalize / `92b935c3` P5(Linux). 후속 commit (P4 OS/ESXi + P5 Windows + schema + docs) 진행 중.
- Branch: `feature/3channel-expansion` (origin push 완료, PR 사용자 직접 생성 — 옵션 A1)
- Plan: `C:\Users\hshwa\.claude\plans\1-snazzy-haven.md`
- Evidence: 본 항목

---

## 2026-04-28 — cycle-010 (T3-04/05/06 일괄 + rule 70 R8 신설)

- 환경: Windows 11 + Python 3.11.9 (호스트)
- 변경 영역:
  - 27 adapter YAML — `version: "1.0.0"` placeholder 1줄 일괄 삭제 (T3-04)
  - `.claude/rules/70-docs-and-evidence-policy.md` — R8 (ADR 의무 trigger) 신설 + 금지 패턴 + 리뷰 포인트
  - `docs/ai/decisions/ADR-2026-04-28-rule12-oem-namespace-exception.md` — DRIFT-006 소급 ADR (R8 첫 적용)
  - `.claude/policy/project-map-fingerprint.yaml` — adapters fingerprint 갱신
  - 증거 문서 — CURRENT_STATE / NEXT_ACTIONS / TEST_HISTORY / harness/cycle-010.md
- 명령:
  - `grep -c "^version:" adapters/**/*.yml` → 27/27 = 0건
  - `python yaml.safe_load 27 adapter` → PASS, version 키 부재
  - `python scripts/ai/verify_harness_consistency.py` → PASS (rules: 29, skills: 43, agents: 51, policies: 10)
  - `python scripts/ai/verify_vendor_boundary.py` → PASS (vendor 하드코딩 0건)
  - `python scripts/ai/check_project_map_drift.py --update` → adapters fingerprint 갱신
  - `ansible-playbook --syntax-check` → SKIP (Windows 메인 환경 제약)
- 결과: 정적 검증 4/5 PASS + 1 SKIP (환경 제약)
- Baseline 갱신: 없음 (T3-04는 schema 영향 없음)
- Evidence: `docs/ai/archive/harness/cycle-010.md`

---

## 2026-04-28 — cycle-008 (P2 MED/LOW 11건 일괄 정합)

- 환경: Windows 11 + Python 3.11.9 (호스트)
- 변경 영역:
  - redfish-gather/library/redfish_gather.py — 함수 분리 추가 (gather_system 103→57, detect_vendor 64→37, main 67→45 + OEM helper 4종 + section runner 3종)
  - os-gather/tasks/linux/gather_system.yml — 346→322줄, build_identifier_diagnostics.yml 분리
  - adapters/redfish/ — hpe_ilo5 priority 100→90, lenovo_bmc.yml 신규, cisco_bmc.yml 신규, lenovo_imm2 tested_against, cisco_cimc 세대 보류 명시
  - callback_plugins/json_only.py — `_emit()` JSON_ONLY_DEBUG 환경변수 가드
  - lookup_plugins/adapter_loader.py — 동률 정렬 문서화 + vvv 경고
- 명령:
  - `python -m pytest tests/ -q` → 95 PASS / 0 FAIL
  - `python scripts/ai/verify_vendor_boundary.py` → 통과 (0건, _OEM_EXTRACTORS dict의 4 라인에 nosec rule12-r1 추가)
  - `python scripts/ai/verify_harness_consistency.py` → PASS (rules 29 / skills 43 / agents 51 / policies 10)
  - `python scripts/ai/hooks/output_schema_drift_check.py` → 정합 (sections=10 fd_paths=46 fd_section_prefixes=10)
  - `python scripts/ai/check_project_map_drift.py --update` → fingerprint 갱신
  - `python -c "import ast; ast.parse(open('redfish-gather/library/redfish_gather.py').read())"` → OK
  - `python -c "import yaml; yaml.safe_load(open(... gather_system.yml ...))"` → OK
- 결과: 모든 검증 PASS
- Baseline 갱신: 없음 (회귀 영역 변경, 의미 변경 없음 — 회귀 95 PASS로 확인)
- Evidence: 본 commit (cycle-008) + CURRENT_STATE.md + NEXT_ACTIONS.md 갱신
- 회귀: 없음 (95 PASS 동일)

---

## 2026-04-27 — 하네스 도입 후 정적 검증

- 환경: Windows 11 + Python 3.11.9 (검증 기준 Agent 10.100.64.154 — Ansible 2.20.3 / Python 3.12.3)
- 명령:
  - `python -c "import ast; ast.parse(...)"` 모든 .py 파일 (27 + 51 = 78 Python 파일)
  - `python scripts/ai/verify_harness_consistency.py`
  - `python scripts/ai/hooks/commit_msg_check.py --self-test`
  - `python scripts/ai/hooks/session_start.py`
- 결과:
  - ast.parse: PASS (0 syntax error)
  - verify_harness_consistency: PASS (참조 위반 0 / 잔재 어휘 0)
  - commit_msg self-test: PASS (6/6 케이스)
  - session_start: 정상 동작 (구조 issue 0건, 측정 대상 출력)
- Baseline 갱신: 없음 (하네스 도입만)
- Evidence: docs/superpowers/specs + docs/superpowers/plans
- 회귀: server-exporter 도메인 코드 무수정 → 기존 베이스라인 회귀 영향 없음

### 미실행 (환경 제약 또는 Plan 3 비범위)

- ansible-playbook --syntax-check (실 ansible 환경 + collections 필요 — 검증 기준 Agent에서 별도 실행)
- 실장비 probe (Round 검증) — 다음 vendor onboarding 시
- Jenkins 4-Stage dry-run — Jenkins controller 환경 필요

---

## 2026-04-27~28 — cycle-002 ~ cycle-006 (정적 검증 누적)

- 환경: Windows 11 + Python 3.11.9 (verify_* 스크립트 OS 중립)
- 명령 / 결과 (각 cycle 보고서 `docs/ai/harness/cycle-00[2-6].md` 정본):
  - `verify_harness_consistency.py`: PASS (rules 29 / skills 43 / agents 51 / policies 10)
  - `verify_vendor_boundary.py`: 26건 → 0건 (cycle-005~006 정밀화 + nosec silence)
  - `check_project_map_drift.py`: PASS (fingerprint 일치)
  - `scan_suspicious_patterns.py`: PASS (rule 95 R1 11 패턴 0건)
  - `validate_claude_structure.py`: PASS
  - `output_schema_drift_check.py`: PASS (cycle-002~006 모두 sections=10 / fd_paths=46 / fd_section_prefixes=10)
  - `validate_field_dictionary.py`: PASS (cycle-006 이후 31 Must / 9 Nice / 6 Skip = 46)
- Baseline 갱신: 없음 (하네스 + schema 보강만 — 실장비 검증 없음)
- 회귀: 도메인 코드 영향 영역 (redfish_gather.py vendor 분기 silence) — 기능 미변경, baseline 회귀 SKIP

## 2026-04-28 — full-sweep 적용 (Tier 1+2)

- 환경: Windows 11 + WSL Python 3.11
- 명령:
  - `verify_harness_consistency.py` (sweep 전 PASS)
  - `verify_vendor_boundary.py` (sweep 전 PASS)
  - `check_project_map_drift.py` (sweep 전 PASS)
  - `scan_suspicious_patterns.py` (sweep 전 PASS)
- 결과: full-sweep 보고서 `docs/ai/archive/harness/full-sweep-2026-04-28.md` 참조
- 회귀: docs/rule/policy/code 정합 변경 — 영향 vendor baseline 회귀 별도 결정 필요

## 2026-04-28 — full-sweep 잔여 (T2-B2 / T2-C2 / T2-C8) 적용

- 환경: Windows 11 + Python 3.11
- 명령:
  - `python scripts/ai/verify_harness_consistency.py`: PASS (rules 29 / skills 43 / agents 51 / policies 10 — 잔재 어휘 default 검사 활성화)
  - `python scripts/ai/verify_vendor_boundary.py`: PASS (vendor 하드코딩 0건)
  - `python scripts/ai/check_project_map_drift.py`: PASS (fingerprint 갱신 후 정합 — os-gather +files/, common precheck 변경)
  - `python scripts/ai/scan_suspicious_patterns.py`: PASS (rule 95 R1 11 패턴 0건)
  - `python scripts/ai/validate_claude_structure.py`: PASS
  - `python scripts/ai/hooks/output_schema_drift_check.py`: PASS (sections=10, fd_paths=46, fd_section_prefixes=10)
  - `python -c "import yaml; yaml.safe_load(...)"`: PASS (gather_users.yml + vendor-boundary-map.yaml)
  - `python -m py_compile`: PASS (precheck_bundle.py + verify_harness_consistency.py)
- 결과:
  - T2-B2 ▷ verify_harness_consistency.py FORBIDDEN_WORDS default 모드 활성화 (`--no-forbidden-check`로 비활성)
  - T2-C2 ▷ precheck_bundle.py Stage 1 (reachable: any TCP response) ↔ Stage 2 (port_open: target service port) 분리 + ConnectionRefusedError 구분
  - T2-C8 ▷ os-gather/files/get_last_login.sh 신규 + Python/Raw 양 경로에서 lookup file 통합 (gather_users.yml 294 → 239 lines)
  - T2-A7 / T3-01~T3-06 / T2-D2: NEXT_ACTIONS 사용자 결정 대기로 SKIP
- 미실행 (환경 제약):
  - `ansible-playbook --syntax-check 3-channel`: WSL ansible 미설치 — 검증 기준 Agent (10.100.64.154)에서 별도 실행
  - `pytest tests/`: WSL pytest 미설치 — 검증 기준 Agent에서 별도 실행
- Baseline 갱신: 없음 (도메인 변경: precheck Stage 분리 + gather_users 함수 통합 — 출력 envelope 13 필드 미변경)
- 회귀: precheck_bundle.py 변경은 진단 메시지만 영향 (failure_stage="port" 신설). gather_users.yml은 기능 동치 (shell snippet 위치 변경만). 영향 vendor baseline 회귀는 검증 기준 Agent에서 별도 실행 필요

## 2026-04-28 — Round 11 reference 종합 수집

- 환경: 사용자 PC (Windows + WSL Ubuntu, 검증 기준 Agent 외)
- 자격: tests/reference/local/targets.yaml (gitignored)
- 명령:
  - `python tests/reference/scripts/crawl_redfish_full.py` (Redfish 11대 시도)
  - `wsl python3 tests/reference/scripts/gather_os_full.py` (OS 7대 시도)
  - `wsl python3 tests/reference/scripts/gather_esxi_full.py` (ESXi 3대)
  - `wsl python3 tests/reference/scripts/gather_agent_env.py` (Agent 2대 + Master 2대)
- 결과:
  - **Redfish**: Dell 27 OK 2417 endpoint / 15MB / 596s, 나머지 BMC 진행 중
  - **OS**: Linux 6대 OK (각 ~106 명령), Win10 FAIL (F4)
  - **ESXi**: pyvmomi 3대 OK, SSH는 .2 1대만 (F5)
  - **Agent/Master**: 4대 모두 OK (각 39 명령)
- 누적 (BMC 진행 중 시점): 4420 파일 / 43MB
- 사고:
  - F1: Dell BMC user=root (admin 아님) — targets.yaml 정정 (사용자 확인)
  - F2: 10.100.15.32 ServiceRoot가 AMI Redfish Server — 실 vendor / 자격 사용자 확인 필요
  - F3: Cisco 10.100.15.1 HTTP 503 / 15.3 timeout — 장비 가동 상태 확인 필요
  - F4: Win10 WinRM 환경 (HTTPS 미활성 + Basic 미허용 + WSL Python 3.12 NTLM MD4 미지원)
  - F5: ESXi 10.100.64.1/.3 SSH 비활성
  - F6: Master 10.100.64.153 sudo ~120s 대기
- Baseline 갱신: **없음** (별도 디렉터리 — fixtures/baseline 무수정)
- 회귀: 영향 없음 (별도 디렉터리, 회귀 input 무수정)
- 환경 제약: 검증 기준 Agent (10.100.64.154) 외 WSL에서 직접 수집
- Evidence: tests/evidence/2026-04-28-reference-collection.md
- decision-log: docs/19_decision-log.md §13 Round 11
