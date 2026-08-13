# DMTF Redfish — 핵심 reference

> Source: Wikipedia (https://en.wikipedia.org/wiki/Redfish_(specification)) + DMTF 공개 문서 종합
> Fetched: 2026-04-27 (DMTF 직접 fetch는 403)
> server-exporter 적용: redfish-gather/library/redfish_gather.py + adapters/redfish/*.yml

## 개요

Redfish는 DMTF (Distributed Management Task Force)가 만든 RESTful 서버 관리 표준. 2015년 v1.0 공개. JSON + OData 메타로 hierarchical resource 표현.

## ServiceRoot

진입점: `https://<bmc_ip>/redfish/v1/`

- **무인증**: `GET /redfish/v1/`은 일반적으로 인증 없이 호출 가능 (Manufacturer / Model 추출 → vendor 자동 감지)
- 응답에서 `Chassis`, `Systems`, `Managers`, `UpdateService`, `AccountService` 등 link 제공

server-exporter Vault 2단계 로딩 (rule 27):
1. `/redfish/v1/` 무인증 GET → manufacturer 추출
2. vendor_aliases.yml로 정규화 → vendor 결정
3. `vault/<loc>/redfish/<vendor>.yml` 로드
4. 인증으로 본 수집 재개

## 핵심 Resource 타입

| Resource | Path 예시 | server-exporter 섹션 |
|---|---|---|
| ServiceRoot | `/redfish/v1/` | (메타) |
| Chassis | `/redfish/v1/Chassis` | hardware (vendor / model / serial) |
| Systems | `/redfish/v1/Systems` | system / cpu / memory |
| Storage | `/redfish/v1/Systems/<id>/Storage` | storage (controller) |
| Drives | `/redfish/v1/Systems/<id>/Storage/<sid>/Drives` | storage (drive list) |
| Volumes | `/redfish/v1/Systems/<id>/Storage/<sid>/Volumes` | storage (RAID volumes) |
| Managers | `/redfish/v1/Managers` | bmc (BMC info / firmware) |
| UpdateService | `/redfish/v1/UpdateService` | firmware (메타) |
| FirmwareInventory | `/redfish/v1/UpdateService/FirmwareInventory` | firmware |
| AccountService | `/redfish/v1/AccountService` | users (BMC accounts) |
| Power | `/redfish/v1/Chassis/<id>/Power` | power (PSU / 전력) |
| Thermal | `/redfish/v1/Chassis/<id>/Thermal` | (선택, server-exporter 미수집) |

## OData 메타

응답 JSON 표준 필드:
```json
{
  "@odata.id": "/redfish/v1/Systems/1",
  "@odata.type": "#ComputerSystem.v1_x_y.ComputerSystem",
  "@odata.context": "/redfish/v1/$metadata#ComputerSystem.ComputerSystem",
  "Id": "1",
  "Name": "...",
  "Manufacturer": "Dell Inc.",
  "Model": "PowerEdge R7525",
  "SerialNumber": "...",
  "ProcessorSummary": { "Count": 2, "Model": "AMD EPYC ..." },
  "MemorySummary": { "TotalSystemMemoryGiB": 256 },
  "Links": { ... }
}
```

server-exporter는 `Manufacturer` 필드로 vendor 자동 감지.

## 인증

| 방법 | 용도 |
|---|---|
| HTTP Basic Auth | 가장 일반. `Authorization: Basic <base64>` |
| Session-based | `POST /redfish/v1/SessionService/Sessions` 후 `X-Auth-Token` 사용 |

server-exporter는 **HTTP Basic** (vault에서 username/password 로드).

## 벤더별 BMC 매핑

| BMC 이름 | 벤더 | 펌웨어 시작 |
|---|---|---|
| iDRAC7/8 | Dell | iDRAC 2.40.40.40+ |
| iDRAC9 | Dell | 3.00+ |
| iLO4 | HPE | 2.30+ |
| iLO5/6 | HPE | 1.x / 2.x |
| XCC | Lenovo | 1.00+ |
| iRMCS5 | Fujitsu | (서버-exporter 미지원) |
| BMC (X10/X11/X12) | Supermicro | 펌웨어 다양 |
| CIMC | Cisco | 3.0+ |
| OpenBMC | 기타 (Linux Foundation) | (generic adapter fallback) |

## Vendor OEM 확장

각 vendor가 표준 외 OEM 필드 추가 가능:
```json
{
  "Oem": {
    "Dell": { "DellSystem": { ... } }
  }
}
```

server-exporter 는 OEM 처리를 라이브러리 `_extract_oem_*` 에서 한다.

## 펌웨어 inventory

`/redfish/v1/UpdateService/FirmwareInventory`:
```json
{
  "Members": [
    { "@odata.id": "/.../FirmwareInventory/BIOS-1" },
    { "@odata.id": "/.../FirmwareInventory/iDRAC-1" },
    { "@odata.id": "/.../FirmwareInventory/NIC-Slot.1" }
  ]
}
```

각 member는 `Name` / `Version` / `ReleaseDate` / `SoftwareId`.

## stdlib 구현 (server-exporter)

`redfish-gather/library/redfish_gather.py`는 외부 라이브러리 의존 없음 (rule 10 R2):
- `urllib.request` — HTTP/HTTPS GET
- `ssl.create_default_context()` + `verify_mode=ssl.CERT_NONE` (자체 서명 시)
- `json` — 응답 파싱
- `base64` — Basic Auth 인코딩

## Best Practices for server-exporter

1. **무인증 detect 우선**: 인증 정보 vault 로드 전 ServiceRoot로 vendor 결정 (rule 27)
2. **HTTPS verify**: 자체 서명 환경 → `verify=False` + 코드 의도 주석 (cycle-011: rule 60 해제)
3. **Timeout**: `urllib.request.urlopen(req, timeout=30)` 명시 (rule 30 R3)
4. **OEM 분리**: standard endpoint 우선 + OEM 은 라이브러리 `_extract_oem_*` 로 분리
5. **Adapter 점수**: 같은 vendor면 펌웨어 / 모델 매칭으로 specificity 차등 (rule 12 R2)

## 참고 클라이언트 라이브러리 (server-exporter 미사용)

- python-redfish (DMTF)
- Sushy (OpenStack)
- gofish (Go)

server-exporter는 stdlib만 사용 (의존성 최소화).

## 적용 rule

- rule 10 R2 (stdlib 우선)
- rule 12 (adapter-vendor-boundary)
- rule 27 (precheck-guard-first / Vault 2단계)
- rule 30 (integration-redfish-vmware-os)
- (cycle-011: rule 60 해제 — HTTPS verify는 운영자 결정)
- rule 96 (external-contract-integrity / origin 주석)

## 관련 표준

- IPMI (Intelligent Platform Management Interface) — 구식, Redfish 등장 전 표준
- OData — JSON 메타 스키마
- Swordfish (SNIA) — Redfish 확장 (네트워크 스토리지)
