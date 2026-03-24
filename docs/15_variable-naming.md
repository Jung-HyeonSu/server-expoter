# 15. 변수 네이밍 규칙

## 규칙

```
_{채널}_{단계}_{의미}

채널 : rf(Redfish) e(ESXi) l(Linux) w(Windows)
단계 : raw   — 모듈/명령 직접 반환값
       d     — raw 에서 추출한 하위 데이터
       norm  — 정규화된 중간 변수
       ok    — 수집 성공 bool
       (없음) — 단일 값 또는 최종

예:
  _rf_raw_collect        Redfish 모듈 직접 반환값
  _rf_d_system           raw 에서 추출한 system 데이터
  _rf_norm_interfaces    정규화된 인터페이스 목록
  _e_raw_facts           ESXi vmware_host_facts 직접 반환값
  _e_norm_interfaces     정규화된 인터페이스
  _l_norm_filesystems    Linux 정규화된 파일시스템
  _l_norm_interfaces     Linux 정규화된 인터페이스
  _l_norm_users_list     Linux 정규화된 사용자 목록
  _w_norm_filesystems    Windows 정규화된 파일시스템
  _w_norm_interfaces     Windows 정규화된 인터페이스
  _w_norm_users_list     Windows 정규화된 사용자 목록
```

---

## Fragment 관련 변수 (모든 gather 공통)

| 변수 | 타입 | 설명 |
|------|------|------|
| `_data_fragment` | dict | 이번 태스크의 data 기여분 |
| `_sections_supported_fragment` | list | 이번 태스크가 지원하는 섹션 |
| `_sections_collected_fragment` | list | 이번 태스크에서 수집 성공한 섹션 |
| `_sections_failed_fragment` | list | 이번 태스크에서 수집 실패한 섹션 |
| `_errors_fragment` | list | 이번 태스크의 errors |

## 누적 변수 (merge_fragment.yml 이 관리)

| 변수 | 타입 | 설명 |
|------|------|------|
| `_merged_data` | dict | data 재귀 병합 결과 |
| `_all_sec_supported` | list | 지원 섹션 누적 |
| `_all_sec_collected` | list | 수집 성공 누적 |
| `_all_sec_failed` | list | 수집 실패 누적 |
| `_all_errors` | list | errors 누적 |

## 공통 builder 입력 변수

| 변수 | 설명 |
|------|------|
| `_out_target_type` | "os"\|"esxi"\|"redfish" |
| `_out_collection_method` | "agent"\|"vsphere_api"\|"redfish_api" |
| `_out_ip` | 접속 IP |
| `_out_vendor` | 벤더 (null 허용) |
| `_out_status` | build_status.yml 출력 |

## 실패 전용 변수

| 변수 | 설명 |
|------|------|
| `_fail_sec_supported` | 이 gather 가 지원하는 섹션 목록 |
| `_fail_error_section` | 에러 섹션명 |
| `_fail_error_message` | 에러 메시지 |

## OS 수집 변수

| 변수 | 설명 |
|------|------|
| `_l_python` | Linux Python 실행 경로 (preflight) |
| `_l_has_lsblk`, `_l_has_dmi`, `_l_has_last` | 명령 존재 여부 (preflight) |
| `_l_fb` | Linux raw fallback 파싱 결과 |

## ESXi 수집 변수

| 변수 | 설명 |
|------|------|
| `_e_raw_facts` | vmware_host_facts 직접 반환값 |
| `_e_raw_config` | vmware_host_config_info 직접 반환값 |
| `_e_raw_ds` | vmware_datastore_info 직접 반환값 |
| `_e_facts_ok` | facts 수집 성공 여부 |
| `_e_config_ok` | config 수집 성공 여부 |
| `_e_ds_ok` | datastore 수집 성공 여부 |
| `_e_default_gw` | ESXi 기본 게이트웨이 |
| `_e_dns_servers` | ESXi DNS 서버 목록 |
| `_e_norm_interfaces` | 정규화된 인터페이스 |
| `_e_norm_datastores` | 정규화된 데이터스토어 |

## Redfish 수집 변수

| 변수 | 설명 |
|------|------|
| `_rf_detected_vendor` | 1차 감지 벤더 ('unknown' 가능) |
| `_rf_vault_profile` | 실제 로딩된 vault 프로파일 |
| `_rf_raw_collect` | redfish_gather 모듈 전체 반환값 |
| `_rf_collect_ok` | 수집 성공 여부 |
| `_rf_vendor` | 최종 확정 벤더 (null 허용, "unknown" 금지) |
| `_rf_d_system` | 모듈 반환값에서 추출한 system raw |
| `_rf_d_bmc` | bmc raw |
| `_rf_d_procs` | processors raw |
| `_rf_d_memory` | memory raw |
| `_rf_d_storage` | storage raw |
| `_rf_d_network` | network raw |
| `_rf_norm_interfaces` | 정규화된 인터페이스 |
| `_rf_norm_gateways` | 집계된 default_gateways |
| `_rf_norm_controllers` | 정규화된 controllers |
| `_rf_norm_physical_disks` | controllers.drives 에서 추출 |

## 최종 변수

| 변수 | 설명 |
|------|------|
| `_output` | 최종 표준 JSON — **이름 변경 절대 금지** |

---

## 금지 패턴

- `_f`, `_d`, `_d_system` 등 너무 짧은 이름 금지
- `_raw` prefix 없이 모듈 결과 직접 저장 금지
- `vendor = "unknown"` 문자열 금지 (null 사용)
- 빈 문자열 `""` 금지 (null 또는 [] 사용)
- schema_version 필드 누락 금지 (항상 `combine({'schema_version':'1'})` 으로 주입)
