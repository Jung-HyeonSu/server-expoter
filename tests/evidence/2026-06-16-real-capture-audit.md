# 2026-06-16 실장비 4대 전수 감사 + 캡처 회귀 반입

## 배경

사용자가 운영망 개더링 결과 오류 보고: hostname 이 IP 로 나옴, 일부 섹션 status 가
power=failed / thermal=not_supported, "등등"(눈에 보이는 것 외 다수). 실측 raw 전수 미러
4대 제공 — DELL R740 / HPE DL380 / HPE CSUS3200 / Lenovo SR650.

## 방법 (검증 층을 사용자 층까지)

기존 오프라인 검증(`replay_full_mirror.py`)은 Python 모듈 출력까지만 봤고, 사용자가 보는
최종 envelope 은 그 뒤 Ansible normalize(`build_sections`/`build_output`)를 거친다 —
검증 층 ≠ 사용자 층. 본 cycle 은 4대 실측 미러를 ground truth 로 놓고 모듈 산출 + 최종
envelope 변환(hostname/sections)을 함께 재현해 전수 대조.

## 확정·수정 (전부 검증, 회귀 0)

| 항목 | 내용 | 검증 |
|---|---|---|
| hostname=IP | `build_output`/`build_failed_output` 의 `or _out_ip` 제거 → strict null (사용자 지시 "없는 건 없는 것"). cycle 2026-05-07 ip fallback 폐지 | 편집 표현식 jinja2 렌더: Dell=`DELL01`, HPE DL380/CSUS/Lenovo=`null` |
| thermal 절삭 (G1) | 온도 `_safe_int` 절삭 → `_safe_round_int` 반올림 | replay: CSUS 44.7→45, Lenovo 38.86→39, -68.75→-69 |
| 누락 필드 (G4, Additive) | bmc serial/part_number/manufacturer, PSU part_number, multi_node chassis uuid/asset_tag/power_state | replay: CSUS bmc.serial=`SGHD3TLNDD`, PSU part=`CSU2400AP-3-500` |
| baseline 정합 | cisco/hpe/csus baseline 의 top-level hostname 이 자기 data.system.fqdn 과 불일치(ip/mock 수동 주입) → 정정 | cisco→`C220-FCH2116V1V0`, hpe→`null`, csus→`csus-p0` |
| docs/test 동기화 | `docs/contract/03-fields.md` §8 strict-null 재작성, T3 `test_hostname_not_ip_fallback`(null 허용/ip 금지), README | 전체 1225 passed |

## 회귀 fixture 반입 (실장비 4대)

`tests/integration/capture_mirror_fixture.py` 로 전수 미러를 gather 가 touch 한 endpoint
만 recording 으로 압축 + `run_gather` 산출을 golden snapshot:

| fixture | vendor | recorded endpoints | (mirror keyed) |
|---|---|---|---|
| `real_dell_r740` | dell | 165 | 6130 |
| `real_hpe_dl380` | hpe | 129 | 2021 |
| `real_hpe_csus3200` | hpe(csus, rmc_primary) | 129 | 489 |
| `real_lenovo_sr650` | lenovo | 121 | 2897 |

`tests/integration/test_real_capture_replay.py` 가 오프라인(네트워크 0) 재생해 회귀 검증.
emulator/mock 보다 강한 실장비 ground truth. (출처: rule 21 R2 각 fixture README.md)

## 정직 보고 — 미재현 항목

**power=failed / thermal=not_supported 운영 증상은 4대 캡처로 재현되지 않음.** 캡처 재생 시
전부 status=success, power/thermal 정상 수집(CSUS PSU 4 / 온도 47 / 팬 10). 데이터 수집도
대체로 충실(CSUS network 0 / firmware 2 도 raw 실제값과 일치 — 누락 아님). 해당 증상은
운영 라이브 환경 차이(타임아웃 / 권한 403 / 5xx / 다른 펌웨어)로 추정 — 정확한 원인 규명에는
그 증상이 난 서버의 실제 출력 envelope(errors[] / sections) 필요.

## 한계 / 다음

- 본 fixture golden 은 **모듈 산출(GOLDEN_KEYS)** 층 — 최종 envelope(13필드) baseline
  (`schema/baseline_v1/`)은 ansible 정규화 필요(lab). CSUS MOCK baseline 의 실측 교체는
  lab 도입 후 별도 cycle (rule 96 R1-C, NEXT_ACTIONS).
- 감사 판단필요 항목(G2 mem mfr / G3 cpu speed / G5 link 0 / G6 단위 / G7 bmc name)은
  사용자 결정 "현 수정으로 충분" — 의도된 동작으로 유지, 문서화만.
