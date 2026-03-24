# 리팩토링 체크리스트 — 실장비 검증 기반

> 검증일: 2026-03-18
> 코드 수정일: 2026-03-18

## P0 — 바로 수정 필요 → ✅ 모두 완료

### 1. ✅ [redfish_gather.py] HPE Storage Controllers fallback
- **현상**: HPE Gen11은 `StorageControllers` 인라인 배열이 없고, `Controllers` 서브링크 사용
- **영향**: HPE 장비에서 스토리지 컨트롤러 정보 완전 누락
- **수정 완료**: `gather_storage()`에서 `StorageControllers` 확인 → 비었으면 `Controllers.@odata.id` 드릴다운
- **추가**: `controller_model`, `controller_firmware`, `controller_manufacturer`, `controller_health` 필드 병합
- **추가**: `Status.Health` 없을 때 `Status.HealthRollup` fallback

### 2. ✅ [redfish_gather.py] gather_power() ServiceRoot 중복 호출 제거
- **현상**: `gather_power()`가 Chassis URI를 얻기 위해 ServiceRoot를 다시 호출
- **영향**: 불필요한 HTTP 호출 3회 (ServiceRoot + Chassis 컬렉션 + Chassis 멤버) 매 실행마다
- **수정 완료**: `detect_vendor()` 반환값 4→5개 (`chassis_uri` 추가), `gather_power()`에 직접 전달
- **변경 파일**: `redfish_gather.py` — `detect_vendor()`, `gather_power()`, `main()`

### 3. ✅ [adapters/redfish/] HPE iLO 6 어댑터 누락
- **현상**: `hpe_ilo5.yml` 패턴이 `iLO.*5` / `^2\.` — iLO 6 (FW: "iLO 6 v1.73")과 불일치
- **영향**: HPE Gen11은 base adapter (`hpe_ilo`, priority 10)로 fallback → 최적화 안됨
- **수정 완료**: `hpe_ilo6.yml` 신규 생성 (priority 100, `firmware_patterns: ["iLO.*6", "^1\\.[5-9]", "^1\\.7"]`)
- **추가**: `vendor_notes`에 iLO 6 특이사항 기록 (Controllers 서브링크, LocationIndicatorActive, Fan 퍼센트 등)

## P1 — 현재 유지 가능하지만 추후 보강 → 일부 완료

### 3. ✅ [redfish_gather.py] 벤더별 null 필드 경고 로깅
- **현상**: HPE는 IndicatorLED, SpeedMbps, LinkStatus 미제공. Lenovo는 Manager.Status.Health 미제공.
- **수정 완료**: `gather_system()`에서 주요 필드 누락 시 errors에 경고 기록
- **감시 필드**: manufacturer, model, serial, hostname, health, bios_version

### 4. ✅ [redfish_gather.py] HostName 빈 문자열 처리
- **현상**: HPE System.HostName이 "" (빈 문자열). 코드는 None 체크만 함.
- **수정 완료**: `gather_system()`에서 빈 문자열/공백만인 경우 → None 변환

### 5. [field_mapper.py] 단위 변환 개선 — 보류
- **현상**: CapacityBytes를 GB로 변환할 때 `round(int(cap) / 1e9, 2)` 사용 (1000 기반)
- **주의**: 스토리지는 보통 10^9 (GB), 메모리는 2^20 (MiB) 사용 — 현재 코드 정확
- **제안**: 단위 변환 함수를 통일하여 `_bytes_to_gb()`, `_mib_to_gib()` 헬퍼 추가

### 6. [redfish_gather.py] Thermal 수집 추가 — 보류
- **현상**: 3대 장비 모두 Thermal endpoint 존재 (Temperatures 40~46개, Fans 6개)
- **영향**: 현재 미수집
- **제안**: `gather_thermal()` 함수 추가, power section 하위 또는 별도 section으로
- **참고**: `chassis_uri`가 이미 `detect_vendor()`에서 반환되므로 추가 구현 용이

### 7. ✅ [redfish_gather.py] MemorySummary.Status.Health vs HealthRollup
- **현상**: HPE는 MemorySummary.Status.Health 미제공, HealthRollup만 제공
- **수정 완료**: `gather_system()`에서 Health 없으면 HealthRollup fallback

### 7-2. ✅ [redfish_gather.py] IndicatorLED → LocationIndicatorActive fallback
- **현상**: HPE Gen11은 IndicatorLED 미제공, LocationIndicatorActive (bool) 사용
- **수정 완료**: `gather_system()`에서 IndicatorLED 없으면 LocationIndicatorActive → 'Blinking'/'Off' 변환

## P2 — 세대 다양성 부족으로 보류

### 8. Supermicro 지원 검증
- 코드에 Supermicro 분기 있으나 실장비 미보유
- 보류 until 장비 확보

### 9. 다중 System member 처리
- 현재 Members[0]만 사용
- 블레이드/다중 노드 서버는 복수 member 가능
- 보류 until 해당 장비 확보

### 10. Session Auth 지원
- 현재 Basic Auth만 사용
- 일부 보안 정책에서 Basic Auth 비활성화 가능
- 보류 until 실제 필요 발생

### 11. HPE iLO5 vs iLO6 차이 검증
- 코드에 `Oem.Hpe` or `Oem.Hp` fallback 있음
- iLO5 이하 미검증
- 보류 until 장비 확보

## 수정 우선순위 요약

| 순위 | 항목 | 파일 | 난이도 | 상태 |
|------|------|------|--------|------|
| P0-1 | HPE Storage Controllers fallback | redfish_gather.py | 중 | ✅ 완료 |
| P0-2 | gather_power ServiceRoot 중복 제거 | redfish_gather.py | 하 | ✅ 완료 |
| P0-3 | HPE iLO 6 어댑터 누락 | adapters/redfish/hpe_ilo6.yml | 하 | ✅ 완료 |
| P1-3 | null 필드 경고 로깅 | redfish_gather.py | 하 | ✅ 완료 |
| P1-4 | HostName 빈 문자열 처리 | redfish_gather.py | 하 | ✅ 완료 |
| P1-5 | 단위 변환 헬퍼 | field_mapper.py | 하 | 보류 |
| P1-6 | Thermal 수집 추가 | redfish_gather.py + normalize | 중 | 보류 |
| P1-7 | HealthRollup fallback | redfish_gather.py | 하 | ✅ 완료 |
| P1-7-2 | IndicatorLED fallback | redfish_gather.py | 하 | ✅ 완료 |
| P2-8~11 | 다양성 보류 | — | — | 보류 |

## 코드 변경 이력

| 날짜 | 파일 | 변경 내용 |
|------|------|----------|
| 2026-03-18 | `redfish_gather.py` | P0-1: gather_storage() Controllers 서브링크 fallback 추가 |
| 2026-03-18 | `redfish_gather.py` | P0-2: detect_vendor() → chassis_uri 반환, gather_power() ServiceRoot 제거 |
| 2026-03-18 | `hpe_ilo6.yml` | P0-3: HPE iLO 6 전용 어댑터 신규 생성 |
| 2026-03-18 | `redfish_gather.py` | P1-3: gather_system() 주요 필드 누락 경고 추가 |
| 2026-03-18 | `redfish_gather.py` | P1-4: HostName 빈 문자열 → None 변환 |
| 2026-03-18 | `redfish_gather.py` | P1-7: MemorySummary Health → HealthRollup fallback |
| 2026-03-18 | `redfish_gather.py` | P1-7-2: IndicatorLED → LocationIndicatorActive fallback |
