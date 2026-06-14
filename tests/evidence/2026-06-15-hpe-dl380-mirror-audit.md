# HPE ProLiant DL380 Gen12 (iLO7) 실 미러 전수 검수 — 2026-06-15

## 출처 (rule 70 R3 / rule 21 R2)

| 항목 | 값 |
|---|---|
| 장비 | HPE ProLiant Compute DL380 Gen12 |
| BMC | iLO 7 (펌웨어 1.20.00 Feb 12 2026) |
| RedfishVersion | 1.22.1 |
| 미러 도구 | `tests/redfish-probe/redfish_full_mirror.py` (BFS 자동발견, 2055 리소스 캡처) |
| 미러 위치 | `C:\github\서버mock데이터\HPE_DL380\01` (검수 시 `.verify/mirror/HPE_DL380` ASCII 사본) |
| 재생 도구 | `tests/redfish-probe/replay_full_mirror.py` (offline → redfish_gather.py 구동) |
| provenance 대조 | `tests/redfish-probe/mirror_lookup.py` (envelope 값 ↔ raw 리소스 1:1) |
| 검수 방식 | 4-round 반복 다관점 검수 (Workflow: 10 section + 7 perspective finder × 적대적 raw 재검증) |

## 방법

각 round: replay 로 envelope 생성 → 10 섹션 finder + 7 관점 finder(Redfish 데이터모델 / Ansible
태스크 / Vendor OEM / 병합 / 결과 JSON / 스키마 / 예외처리)가 `mirror_lookup.py` 로 모든 leaf 를
raw 와 대조 → 후보 dedup → 적대적 검증(독립 raw 재대조로 confirmed/rejected/device-limitation/
by-design/needs-human 판정) → 확정 버그 수정 → replay+pytest 회귀 → 다음 round 에서 과거 수정
재검증 + 신규 탐색. NEW 버그가 0 일 때까지 반복.

> 중요: replay 는 **라이브러리(redfish_gather.py)** 를 구동한다. envelope.data 는 라이브러리 산출물이며
> Ansible normalize YAML(normalize_standard.yml, build_*.yml) 은 replay 가 거치지 않는다. 따라서
> 라이브러리 결함은 replay 로 직접 검증, normalize/스키마/baseline-layer 결함은 코드 정독 + raw
> 입력 증명 + Jinja 렌더 테스트로 검증했다.

## 수정 완료 (7건) — 전부 raw 대조로 faithful 확인 + 회귀 테스트

| # | ID | sev | 파일 | 내용 | raw 증거 |
|---|---|---|---|---|---|
| 1 | cpu_summary.health | HIGH | redfish_gather.py gather_system | `ProcessorSummary.Status.Health` 부재 시 `HealthRollup` fallback (HPE 는 HealthRollup 만) | `Systems/1` ProcessorSummary.Status={"HealthRollup":"OK"} → 기존 null, 수정 후 "OK" |
| 2 | NIC MAC | HIGH | redfish_gather.py gather_network_adapters_chassis | 신 `Ports` 의 MAC 은 `Ethernet.AssociatedMACAddresses` / WWPN 은 `FibreChannel.AssociatedWWNs` — fallback 추가 (구 `AssociatedNetworkAddresses` 우선 보존) | `Chassis/1/NetworkAdapters/DE040000/Ports/1` Ethernet.AssociatedMACAddresses=["14:23:f3:b0:7a:40"], top-level AssociatedNetworkAddresses 부재 → adapters/ports MAC 전부 null 이던 것 회복 |
| 3 | link_speed_gbps | MED | redfish_gather.py `_normalize_port_speed` | 미연결(CurrentSpeedGbps=0) 포트 link_speed_gbps 0→null (field_dictionary 'null when unlinked' 계약 + 동일 포트 mbps=null 내부 일관) | FC `DE041000/Ports/1` CurrentSpeedGbps=0, LinkStatus=LinkDown |
| 4 | associated_address case | LOW | redfish_gather.py gather_network_adapters_chassis | `ports[].associated_address` 소문자 정규화 (#2 의 대문자 verbatim side-effect 교정) | HPE iLO 가 FC WWPN 을 Ethernet.AssociatedMACAddresses 에 대문자로 노출 |
| 5 | partial-404 | MED | redfish_gather.py `_make_section_runner._run` (+`_is_empty_result`) | collection-404(val 비어있음)만 unsupported, sub-멤버 404 부분수집(val 채워짐)은 collected+failed(partial) — 부분손실이 unsupported+success 로 은폐되던 latent 버그 | DL380 무발동(404 0건) — 구조적 결함 + 회귀 테스트로 고정 |
| 6 | bmc.mac_address case | LOW | redfish_gather.py gather_bmc | bmc.mac_address 소문자 정규화 (전 MAC 필드 canonical 소문자 일관) | `Managers/1/EthernetInterfaces/1` MAC=7C:A6:2A:87:6F:E0(대문자) → 7c:a6:... |
| 7 | network.summary join | MED | normalize_standard.yml `_rf_summary_network` | groups[].model/manufacturer 가 host-iface-id↔adapter-id 무관 id-regex join 으로 항상 null → port MAC→adapter 매핑 + nic_mac fallback (id-regex 매칭 vendor 불변 Additive) | host iface id '13' vs adapter id 'DE040000' / Model="BCM57414" 회복 |

### 회귀 (rule 24 R2/R6)
- `pytest tests/ --ignore=tests/e2e_browser` : **1111 passed, 5 skipped** (수정 전 baseline 1097 + 신규 회귀 테스트 14).
  - 신규: `tests/unit/test_hpe_dl380_audit_fixes.py` (11) + `tests/unit/test_network_summary_join_at1.py` (3).
- golden 재생성(faithful — 변동 leaf 가 정확히 해당 수정 필드뿐임을 blast-radius diff 로 확인 후):
  hpe_emulator 5종 + dmtf_rackmount1.
- `e2e_browser` 2건 FAIL 은 lab Jenkins(10.100.64.152:8080) 미도달 — 본 검수와 무관한 환경 이슈(검수 전부터 FAIL).

## 보고 — 결정/실측 필요 (gated, 미수정)

> 아래는 적대적 검증에서 confirmed 됐으나 (a) 보호 경로(schema/baseline_v1·field_dictionary, rule 13
> R2 사용자 승인) (b) status 계약 변경(rule 13 R8) (c) 다채널(os/esxi) 영향 — replay 로 미검증 (d)
> 실장비 재캡처 필요(rule 13 R4) 중 하나라 자율 수정하지 않고 보고한다.

| ID | sev | 내용 | 권장 조치 |
|---|---|---|---|
| ATX-01/02 | MED | Track4(2026-06-14) thermal 섹션이 라이브러리·supported_sections·normalize 엔 추가됐으나 `build_sections.yml`/`build_failed_output.yml` all_sec + `init_fragments.yml`/`build_empty_data.yml` skeleton 에 누락 → `sections.thermal` 미emit + overall status 미반영 | build_sections/build_failed_output all_sec 에 thermal 추가 + 3 skeleton 동기화. 단 os/esxi 다채널 영향 + status 계약(rule 13 R8) → 사용자 승인 + 3채널 baseline 회귀 |
| SCHEMA-01/04/06 | MED | HPE baseline(iLO5 구캡처)에 thermal·network.adapters·network.ports·storage.hbas·multi_node 누락 — 라이브러리는 정상 수집(faithful)이나 회귀 커버리지 공백 | 실장비(iLO7 DL380) 재캡처로 baseline 갱신(rule 13 R4) — AI 임의 편집 금지 |
| SCHEMA-05 | LOW | field_dictionary cpu.architecture channel=[os,esxi] 인데 redfish 도 emit | field_dictionary channel 에 redfish 추가(보호 경로) + docs/20 동기화 |
| SCHEMA-07/AT-3 | LOW | (normalize-layer) firmware[].category 가 'UBM3 BC BP' backplane 을 'nvme' substring 으로 drive 오분류 + 'System ROM' BIOS 미분류 + category 가 field_dictionary 미정의 | normalize_standard.yml category elif 보강 + field_dictionary 등록 |
| 단위/명명 (by-design) | — | volumes.total_mb 가 실제 MiB 값 / drive.capacity_gb(decimal) vs volume.total_mb(binary) 단위계 혼재 — 값은 faithful, 키 명명 계약 이슈 | 호출자 계약(rule 13 R5) 결정 필요 — 현행 명명 의도적 |
| 하드웨어 필드 (by-design) | — | normalize 가 hardware 에 emit 하는 asset_tag/system_type/part_number/last_reset_time/boot_progress/tpm + vendor/model/serial/uuid/bios_* 가 field_dictionary 미등록 | field_dictionary 등록(보호 경로) |

## 수렴 (round 별)

| round | envelope | confirmed (fix) | 비고 |
|---|---|---|---|
| 1 | v1 | cpu_summary.health, NIC MAC | MEM-1(replay artifact)/SCHEMA-01(faithful) reject |
| 2 | v2 | link_speed_gbps null, associated_address lowercase, partial-404 | associated_address 는 #1 의 side-effect (반복 검수가 포착) |
| 3 | v3 | bmc.mac_address lowercase, network.summary join(YAML) | leaf 전수 대조 |
| 4 | v4 | **0** | DM-PASS(rejected) / RJ-1(_network_meta, by-design — normalize_standard.yml:58 이 strip) 뿐. **NEW 데이터 정확성 버그 0 → 라이브러리 수렴** |

> RJ-1: replay 가 라이브러리(pre-normalize) 레이어를 캡처해 임시 키 `_network_meta` 가 보였을 뿐,
> production(post-normalize) envelope 은 `_rf_d_bmc_clean`(rejectattr) 으로 제거하고 dns_servers/
> default_gateways 를 data.network 하위에 생성한다(normalize_standard.yml:58,114). 2-layer 설계 의도.

## 후속 작업 진행 (사용자 승인 — 2026-06-15)

위 "보고" 항목 중 자율 수정 가능 + 검증 가능한 것을 사용자 승인 후 진행:

| 항목 | 처리 | 검증 | commit |
|---|---|---|---|
| thermal 섹션 배선 (ATX-01/02) | build_sections/build_failed_output all_sec + 3 skeleton 에 thermal 추가 (10→11) | render+skeleton-sync 5건, docs/19·20 동반(rule 13 R8 — status 4시나리오 결과 불변) | 7be8cdc0 |
| firmware category (SCHEMA-07) | 'System ROM'→bios + UBM 백플레인 'nvme' 선점 정정 + category/pending field_dictionary 등록(122) | render 7건(Dell/CSUS 무영향) | da215d68 |
| cpu.architecture channel (SCHEMA-05) | `[os,esxi]`→`[redfish,os,esxi]` + docs/20 | drift check PASS | da215d68 |
| hardware 12 식별필드 등록 (SCH-1/2, 사용자: 핵심 Must) | vendor/model/serial/uuid/bios_version=Must (전 esxi+redfish baseline 보유 실측), 나머지 7=Nice | drift PASS, dup 0 | (이 commit) |
| volumes.total_mb 단위 명명 (RJ-1, 사용자: total_mb 유지) | 키/값 유지 + "값은 MiB(÷2^20)" field_dictionary·docs/20 문서 명시 (rename=계약 breaking 회피) | — | (이 commit) |
| field_dictionary count 동기화 | 120→**134** 참조 14파일 일괄 (무관 `120`/`122`·commit 이력 제외) | grep 정합, dup 검출 0 | b58f8cfe + (이 commit) |

- 회귀: `pytest tests/ --ignore=tests/e2e_browser` = **1123 passed, 5 skipped** (1097 baseline 무회귀 + 신규 26).
- 주: hardware total_mb 는 *기존* field_dictionary 항목(must)에 MiB 주석 추가 — 신규 추가 시도 중 중복키 검출→복구(원본 must 보존).

### 잔여 — 실측 필요 (자율 불가)

- **HPE baseline 재캡처**: 본 환경(Windows)은 ansible control node 미지원(`os.get_blocking` 부재 — 검증함).
  faithful baseline 은 Linux control node 또는 lab Jenkins 의 실 site.yml 실행 필요 (rule 13 R4 — fabrication 금지).
  절차는 `docs/ai/NEXT_ACTIONS.md` 참조.

## 결론

- **라이브러리(redfish_gather.py) 데이터 정확성**: HPE DL380 Gen12 raw 2055 리소스 기준 전 leaf provenance
  대조 — 잘못된 리소스/속성 수집, OEM↔표준 혼동, 타입/기본값/빈값/중복/병합/실패처리 오류는
  6건 수정으로 해소. 4-round 반복 검수에서 수렴.
- **normalize-layer**: network.summary join(AT-1) 1건 수정. thermal 배선/baseline stale/firmware
  category/field_dictionary 정합은 보호 경로·다채널·실측 필요라 보고.
- 모든 수정은 raw 대조로 faithful 확인 + 회귀 테스트 + golden faithful 재생성.
