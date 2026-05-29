# 2026-05-29 — CSUS 3200 개편 + HBA/InfiniBand 전 채널 수집

> cycle 진입점 (rule 26 R10 정본 1). 사용자 요청 2건의 작업 계획 + 외부 계약 evidence.

## 사용자 요청 (2026-05-29)

1. **CSUS 3200 개더링 대대적 개편** — 다른 장비처럼 공통 JSON 전 섹션이 모두 담기게. lab 장비 없음 → web 검색 evidence 기반.
2. **HBA + InfiniBand 수집** — **모든 서버** (os Linux/Windows + esxi + redfish 전 채널).

## 문서 구조

| 문서 | 내용 |
|---|---|
| `INDEX.md` (본 문서) | 진입점 + 요청 + 핵심 결론 |
| `PLAN.md` | 작업 계획 (현행 실측 / 통일 shape / Phase P1~P6 / 회귀 / 결정) |
| `EXTERNAL-CONTRACTS.md` | web-research 외부 계약 (Redfish/ESXi/Windows/CSUS) + sources (rule 96 R1-A) |

## 핵심 결론 (실측 2026-05-29 — 10-agent workflow + 직접 검증)

- **HBA/IB schema 는 이미 v1 에 존재** — `sections.yml` (storage.hbas/infiniband, network.adapters/ports/driver_map placeholder) + `field_dictionary.yml` (array-level entries, channel=[redfish,os,esxi]). → **schema version bump 불필요**, 본 작업은 **수집 구현 + baseline 채움 + 일관화** (Additive only).
- **[CRIT 버그] Redfish FC/IB 분류가 dead code** — `redfish_gather.py` 가 `Port.PortType` 로 FC/IB 판정하나 DMTF `PortType` enum 에 FC/IB 값 **없음**. → 실장비에서 영원히 미매치. FC=`PortProtocol=='FC'`, IB=`LinkNetworkTechnology=='InfiniBand'` 로 정정 필요.
- **ESXi IB 분류도 dead code** (`'infiniband' in adapter_type` — 절대 매치 안 됨). FC 는 수집되나 `port_type`/`speed`/`wwnn` 누락.
- **Windows** — `Get-InitiatorPort` 로 부분 HBA 수집하나 FC 필터 없음(SAS/iSCSI 혼입) + model/vendor/firmware/speed 없음 + IB 는 hardcoded `[]`.
- **Linux** — sysfs 기반 동작 (FC + IB + driver_map). 보강 여지: WWNN / vendor / firmware.
- **CSUS 3200 baseline** — lab 부재 mock skeleton. storage/network/disks/hbas/ib + per-partition storage/network 전부 `[]`. multi_node per-partition 은 redfish_gather.py 가 수집은 하나 normalize 안 됨.

## 상태

- [PASS] 결정 D1=API-only / D2=Linux 보강 / D3=Additive (사용자 확정 2026-05-29).
- [PASS] P1~P6 전부 구현 완료. pytest 699 PASS / 0 FAIL. ADR-2026-05-29.
  - P1 Redfish FC/IB dead-code fix / P2 CSUS 전 섹션 + realistic mock / P3 ESXi enrich / P4 Windows enrich+IB / P5 Linux 보강 / P6 schema(74→83)+baseline+test+docs.
- [TODO] lab 부재 후속 (NEXT_ACTIONS §2.2 / §2.4) — 사이트 fixture 캡처 → 실 baseline.
