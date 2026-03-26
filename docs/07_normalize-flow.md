# 07. Normalize 흐름 설명

## 개요

```
수집 단계 (gather별 raw 변수)
  ↓
Fragment 생성 (_data_fragment + _sections_*_fragment + _errors_fragment)
  ↓
merge_fragment.yml (누적 병합 — _merged_data, _all_sec_*, _all_errors)
  ↓
공통 builder (build_sections → build_status → build_errors → build_meta → build_correlation → build_output)
  ↓
schema_version 주입 → _output
```

---

## common/tasks/normalize/ 파일별 역할

### init_fragments.yml

gather 시작 시 반드시 첫 번째로 호출한다.
누적 변수들을 빈 상태로 초기화한다.

```yaml
_merged_data:       # data 병합 누적 (빈 뼈대)
_all_sec_supported: []
_all_sec_collected: []
_all_sec_failed:    []
_all_errors:        []
```

---

### merge_fragment.yml (핵심 엔진)

각 gather/normalize 태스크가 fragment 생성 직후 호출한다.

**입력:**
```yaml
_data_fragment:               {}   # 이번 태스크의 data 기여분
_sections_supported_fragment: []
_sections_collected_fragment: []
_sections_failed_fragment:    []
_errors_fragment:             []
```

**동작:**
1. `_merged_data` 에 `_data_fragment` 를 재귀 병합
   - dict + dict → 얕은 병합 (fragment 우선)
   - list + list → 합산
   - null + value → value 사용
2. `_all_sec_*` 에 fragment 의 섹션 목록 union 추가
3. `_all_errors` 에 errors 누적
4. fragment 변수 초기화 (다음 태스크 오염 방지)

---

### build_sections.yml

```yaml
# 입력
_all_sec_supported: ['system','cpu','memory','storage','network','users']
_all_sec_collected: ['system','cpu','memory','storage','network','users']
_all_sec_failed:    []

# 출력 (_norm_sections)
sections:
  system:   success
  hardware: not_supported   ← supported 에 없으면 자동으로
  cpu:      success
  ...
```

판정 우선순위:
- supported 목록에 없음 → `not_supported`
- failed 목록에 있음 → `failed`
- collected 목록에 있음 → `success`
- 위 어디에도 해당하지 않음 → `failed` (미분류 fallback)

---

### build_status.yml

```yaml
# supported 섹션 중:
# 모두 success           → "success"
# success + failed 혼재 → "partial"
# success 가 없음        → "failed"
```

---

### build_errors.yml

`_all_errors` 의 문자열/dict 혼합을 표준 `{section, message, detail}` 형식으로 정리.

---

### build_meta.yml

수집 메타데이터(타임스탬프, 소요시간 등) 생성. `_meta` 변수 출력.

---

### build_correlation.yml

호스트 간 상관관계 데이터 생성. `_correlation` 변수 출력.

---

### build_output.yml

```yaml
# 입력
_out_target_type / _out_collection_method / _out_ip / _out_vendor
_norm_sections / _norm_errors / _merged_data / _meta / _correlation

# 출력 (_output)
{target_type, collection_method, ip, hostname, vendor,
 status, sections, diagnosis, meta, correlation, errors, data}
```

---

### build_failed_output.yml

rescue / 연결 실패 등 완전 실패 시 단일 호출로 failed _output 생성.

```yaml
# 입력
_fail_sec_supported: ['system','cpu',...]  ← 이 gather 가 지원하는 섹션
_fail_error_section: "gather_name"
_fail_error_message: "에러 메시지"
_out_target_type, _out_collection_method, _out_ip, _out_vendor

# 출력: status=failed, 모든 supported 섹션 = failed, empty data
```

---

## 태스크별 fragment 패턴 예시

```yaml
# gather_memory.yml 예시
- name: "linux | memory | build fragment"
  set_fact:
    _data_fragment:
      memory:
        total_mb:    32768
        total_basis: "physical_installed"
        ...
    _sections_supported_fragment: ['memory']
    _sections_collected_fragment: ['memory']
    _sections_failed_fragment:    []
    _errors_fragment:             []

- include_tasks:
    file: "{{ lookup('env','REPO_ROOT') }}/common/tasks/normalize/merge_fragment.yml"
```

---

## os-gather normalize 흐름

```
Linux gather_*.yml (6개)
  각자 fragment 생성 → merge_fragment 호출 (6회)
  → _merged_data 에 system/cpu/memory/storage/network/users 누적
  → _all_sec_supported = [system,cpu,memory,storage,network,users]
  → _all_sec_collected = [system,cpu,memory,storage,network,users]

tasks/normalize/build_output.yml:
  build_sections  → sections (hardware/bmc/firmware = not_supported 자동)
  build_status    → success (실패 섹션 없으면)
  build_errors    → []
  set _out_*
  build_output    → _output
  inject schema_version
```

---

## redfish-gather normalize 흐름

```
normalize_standard.yml:
  _rf_d_* 추출 → 표준 fragment (전 섹션) → merge_fragment (1회)
  → _all_sec_supported = [system,hardware,bmc,cpu,memory,storage,network,firmware]
  → _all_sec_collected = _rf_raw_collect.collected 기반 동적 매핑
  → _all_sec_failed    = _rf_raw_collect.failed    기반 동적 매핑

vendors/{vendor}/collect_oem + normalize_oem:
  OEM fragment → merge_fragment (1회) [placeholder]

build_sections / build_status → partial 자동 판정
```
