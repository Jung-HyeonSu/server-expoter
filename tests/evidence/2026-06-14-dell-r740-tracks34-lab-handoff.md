# DELL R740 검수 후속 — Track 3(link_status) / Track 4(thermal) lab 완료 handoff — 2026-06-14

> 브랜치 `feature/r740-audit-fixes`. Track 1(firmware category) / Track 2(field_dictionary 문서)는
> 본 브랜치에서 **오프라인 검증 완료**(아래 "검증 완료" 참조). Track 3 / 4 는 **Ansible 실행 + 전 벤더
> 실장비 baseline 재캡처**가 필요해 오프라인(인터넷망, ansible 부재)에서 **완결·검증 불가** → 본 문서로
> lab 완료 절차를 명세한다. 무단 blind 변경은 검증 불가 + Jenkins Stage 4(전 벤더 baseline) 파손 위험이라
> 의도적으로 보류했다(rule 13 R4 / 21 R1 / 92 R2 + 검증 규칙).

## 왜 오프라인에서 불가한가 (근본 제약)
- baseline(`schema/baseline_v1/*.json`)은 **post-normalize**(Ansible Jinja2 거친) 전체 envelope.
- 오프라인 `replay_full_mirror.py`는 **module(`redfish_gather.py`)만** 재생 — normalize 계층 미실행.
- normalize 변경/새 섹션은 전 벤더 baseline 재캡처를 요구하나, ansible + 실장비(또는 미러 4종 외
  Cisco 등)가 lab 에만 있음. rule 13 R4: baseline 은 **실측 기반**만 — AI 임의 편집 금지.

---

## Track 3 — link_status enum 3-채널 통일

### 현 실태 (검증된 불일치)
| 채널 | 코드 emit | baseline 실제값 |
|---|---|---|
| redfish | `up/down/unknown` (`redfish_gather.py` `_normalize_link_status` 1326-) | dell/hpe/lenovo=`linkup/linkdown/none`(stale), cisco=`unknown`, csus=`up/down`(최신, 코드 일치) |
| os(linux) | `linkup/linkdown` (`os-gather/tasks/linux/gather_network.yml:140,388`) | ubuntu/win/rhel=`up` (**자기 코드와도 불일치** — 추가 stale 의심) |
| esxi | `up/unknown` (`esxi-gather/tasks/normalize_network.yml:80`) | `Connected/Disconnected/offline`(raw 미정규화) |
| 문서 | — | `field_dictionary.yml:509` enum=`["linkup","linkdown","none",null]` (어느 코드와도 불일치) |

### 권장 canonical: `up` / `down` / `unknown`
근거: redfish + esxi 코드가 이미 지향, 최신 csus/os baseline 이 `up`, DMTF LinkUp/LinkDown 정규화 기준.

### lab 변경 + 검증 절차
1. **os linux** `gather_network.yml`: line 140 `'linkup' if active else 'linkdown'` → `'up' if active else 'down'`; line 388 `'linkup'/'linkdown'` → `'up'/'down'` (raw fallback). `link_up` 비교(158/448)는 이미 `['up','linkup']` 수용 — 무해.
2. **esxi** `normalize_network.yml:80`: `'up' if active else 'unknown'` 유지(이미 canonical). 단 baseline 의 raw `Connected/Disconnected/offline` 는 **정규화 미적용 경로 존재 가능** — 별도 조사(왜 baseline 에 raw 가 들어갔는지). `_normalize_link_status` 등가 정규화를 esxi 수집 경로에도 적용 검토.
3. **redfish**: 코드 변경 불필요(이미 up/down/unknown).
4. **field_dictionary.yml:507-525**: enum `["linkup","linkdown","none",null]` → `["up","down","unknown",null]`, help_ko/en 의 linkup/linkdown 설명 → up/down. (rule 13 R7 docs/20 동기화 동반.)
5. **전 9 baseline 재캡처**(실장비 live run, rule 13 R4): dell/hpe/lenovo/cisco/csus(redfish) + ubuntu/windows/rhel(os) + esxi. mechanical find-replace 금지 — 실 envelope 로 교체.
6. **검증**: Jenkins Stage 3(schema) + Stage 4(baseline 회귀) 전 벤더 PASS. `tests/e2e/conftest.py` link_status 키 presence 유지.

### 주의 (추가 발견)
os baseline 이 `up`인데 os 코드가 `linkup` emit → **baseline 또는 코드 한쪽이 이미 stale**. 통일 전
이 모순부터 실장비로 규명(어느 게 진실인지). 단순 enum 변경으로 덮지 말 것.

---

## Track 4 — thermal 섹션 신설 (단일노드 fan/temp 수집)

### 현 실태
- `redfish_gather.py` 에 `gather_thermal`(2978) / `_gather_thermal_subsystem`(3033) **구현 완료**.
- 그러나 호출처는 `gather_chassis_multi`(3561, multi-node CSUS/Superdome) **단 1곳** — 단일노드
  (`_collect_all_sections` ~3862)에서 미호출 → DELL R740 등은 thermal 미수집.
- 실 미러 `/Chassis/System.Embedded.1/Thermal` 에 fan 6(5640-5880 RPM) + temp 4(CPU1 47°C/CPU2 42°C/
  Inlet 13°C/Exhaust 24°C) 노출되나 envelope 부재. (schema 에 thermal 섹션 없어 거짓 아님 — 설계 범위.)

### lab 변경 + 검증 절차 (rule 22 R2 7단계 schema 추가)
1. **module**: `_collect_all_sections`(~3862)에 `gather_thermal(bmc_ip, chassis_uri, …)` 호출 추가
   (gather_power 패턴 mirror), 결과를 `data.thermal` 로. **오프라인 replay 로 Dell thermal 출력 검증 가능**.
2. **sections.yml**: `thermal` 섹션 추가(key/display_name/channels=[redfish, esxi?]/empty_value).
3. **field_dictionary.yml**: `thermal.temperatures[]`(name/reading_celsius/health/upper_critical/physical_context)
   + `thermal.fans[]`(name/reading/reading_units/health) 문서화 (+docs/20 동기화).
4. **normalize_standard.yml**: `_rf_d_thermal` 추출 + `data.thermal` fragment + `_sections_*` 매핑.
5. **공통 빌더**: `supported_sections.yml` 에 thermal 등록.
6. **전 redfish baseline 재캡처**(thermal 섹션 포함): dell/hpe/lenovo/cisco/csus. **Cisco 미러 부재**
   — Cisco 실장비 또는 미러 확보 필수.
7. **문서**: docs/06(구조)/docs/20/docs/19(ADR) 갱신. ADR-2026-06-09(thermal multi-chassis 한정) 갱신.
8. **검증**: replay(module thermal) + Jenkins Stage 3/4 전 벤더.

### 대안 (가벼움)
thermal 을 독립 섹션 대신 `data.power.fans` / `data.power.temperatures` 로 병합(섹션 추가 회피).
단 power 섹션 의미 확장 → 호출자 계약 영향. 사용자 재결정 필요.

---

## 이 브랜치에서 검증 완료(오프라인) — Track 1 / 2
- **Track 1 (firmware category)**: `normalize_standard.yml` elif specific-before-broad 재정렬.
  `tests/unit/test_firmware_category.py`(실 템플릿 추출 렌더, 16 pass)로 Dell 7건 정정 + CSUS 무영향 고정.
  jinja2 compile PASS. pytest 1097 pass. CSUS/Dell baseline 무영향(Stage-4-safe) → main 병합 가능.
- **Track 2 (field_dictionary 문서)**: bmc.* 15 + memory.total_mb/slots[] 15 = +30 entry(83→113),
  network.summary 보강(NETAD-1), docs/20 `data.bmc` 절 추가. validator PASS, pytest 1097 pass,
  baseline 무영향 → main 병합 가능.

## 권장 병합 순서
1. **즉시 main 병합 가능**(Stage-4-safe, 오프라인 검증 완료): Track 1 + Track 2.
2. **lab 검증 후 병합**: Track 3 + Track 4 (위 절차 + 전 벤더 baseline 재캡처 통과 후).
