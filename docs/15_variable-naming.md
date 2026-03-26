# 변수 네이밍 규칙

> 네이밍 공식과 Fragment/누적/builder 공통 변수는 `GUIDE_FOR_AI.md` 참조.
> 이 문서는 **채널별 변수 사전**과 **금지 패턴**을 정의한다.

---

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
