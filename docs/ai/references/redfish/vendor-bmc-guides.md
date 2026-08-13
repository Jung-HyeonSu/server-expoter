# Vendor BMC Guides — Redfish 공식 정보

> 5 vendor BMC의 Redfish 구현 차이 및 공식 문서 링크.
> Fetched: 2026-04-27 (대부분 Wikipedia + 공식 dev portal). 직접 fetch 실패한 일부는 일반 정보.

## Dell iDRAC

- **BMC 이름**: iDRAC (Integrated Dell Remote Access Controller)
- **세대**: iDRAC7/8/9 (server-exporter는 iDRAC8/9 지원)
- **Manufacturer**: "Dell Inc.", "Dell EMC"
- **공식 문서 진입점**: https://developer.dell.com (Dell Technologies Developer)
- **Redfish 시작**: iDRAC 7/8 펌웨어 2.40.40.40+ / iDRAC9 펌웨어 3.00+

### Dell OEM 특이사항

- **OEM path**: `/redfish/v1/Dell/...` 별도 경로
- **DellSystem / DellAttributes**: 표준 Systems의 OEM 확장
- **Storage**: iDRAC9 5.x+부터 `/Storage/<id>/Volumes` 표준 endpoint 노출 (이전엔 OEM only)
- **Firmware Inventory**: `/redfish/v1/UpdateService/FirmwareInventory` 표준
- **Authentication**: HTTP Basic + X-Auth-Token (Sessions endpoint)

### server-exporter Adapter 매핑

| Adapter | priority | Firmware |
|---|---|---|
| dell_idrac9.yml | 100 | 5.x / 6.x / 7.x |
| dell_idrac8.yml | 50 | 2.40+ |
| dell_idrac.yml | 10 | generic Dell |

---

## HPE iLO

- **BMC 이름**: iLO (Integrated Lights-Out)
- **세대**: iLO 4/5/6 (server-exporter는 iLO 5/6)
- **Manufacturer**: "HPE", "Hewlett Packard Enterprise", "Hewlett-Packard"
- **공식 라이브러리**: https://github.com/HewlettPackard/python-ilorest-library (`ilorest`)
- **Redfish 시작**: iLO4 펌웨어 2.30+, iLO5/6 표준

### HPE OEM 특이사항

- **Smart Storage**: `Oem.Hp.Links.SmartStorage` (HPE OEM)
- **Smart Components**: 펌웨어 inventory의 OEM 확장
- **Boot order**: OEM 별도 endpoint
- **Authentication**: Basic + Session-based

### server-exporter Adapter 매핑 (실측 2026-04-27 — DRIFT-003 정리)

| Adapter | priority |
|---|---|
| hpe_ilo6.yml | 100 |
| hpe_ilo5.yml | 100 |
| hpe_ilo4.yml | 50 |
| hpe_ilo.yml | 10 (generic HPE) |

---

## Lenovo XCC

- **BMC 이름**: XCC (XClarity Controller) / 구 IMM2
- **Manufacturer**: "Lenovo", "IBM" (구 IBM x-series 인수)
- **공식 문서**: Lenovo Data Center docs
- **Redfish 시작**: XCC 1.00+

### Lenovo OEM 특이사항

- 표준 Redfish에 가까움 (OEM 적음)
- **Drive bay path**: `Chassis/<id>/Drives` 표준 + 일부 OEM
- **UpdateService**: 표준
- **PowerSupplies**: 표준

### server-exporter Adapter 매핑 (실측 2026-04-27)

| Adapter | priority |
|---|---|
| lenovo_xcc.yml | 100 |
| lenovo_imm2.yml | 50 (구 IBM IMM2) |

---

## Supermicro

- **BMC**: AMI MegaRAC 기반 (벤더-agnostic 칩셋)
- **Manufacturer**: "Supermicro", "Super Micro Computer", "SMCI"
- **세대**: X10 / X11 / X12

### Supermicro 특이사항

- 표준 Redfish에 가까움 (AMI MegaRAC 펌웨어)
- IPMI 동시 활성 (Redfish 미지원 펌웨어 fallback 가능)
- 펌웨어 버전별 일부 path 차이

### server-exporter Adapter 매핑 (실측 2026-04-27)

| Adapter | priority |
|---|---|
| supermicro_x11.yml | 100 |
| supermicro_x9.yml | 50 |
| supermicro_bmc.yml | 10 (generic SMC) |

---

## Cisco

- **BMC 이름**: CIMC (Cisco Integrated Management Controller)
- **Manufacturer**: "Cisco Systems", "Cisco"
- **대상**: UCS C-Series standalone (UCS Manager 제외)
- **Redfish 시작**: CIMC 3.0+

### Cisco OEM 특이사항

- **UCS RAID controller**: OEM 확장
- **VIC adapter**: 네트워크 OEM
- **표준 endpoint** 보장 (Storage / Systems / Managers)

### server-exporter Adapter 매핑

| Adapter | priority |
|---|---|
| cisco_cimc.yml | 100 |

---

## Generic Redfish (fallback)

- **사용 시점**: 위 5 vendor 매치 안 될 때
- **Adapter**: `redfish_generic.yml` (priority 0)
- **server-exporter**: 표준 endpoint만 시도, OEM 없음, 그대로 collect → 일부 섹션 누락 가능 (status: partial)

---

## 공통 Redfish 표준 endpoint (모든 vendor 공유)

| Path | 표준 응답 |
|---|---|
| `/redfish/v1/` | ServiceRoot — Manufacturer / Model / RedfishVersion |
| `/redfish/v1/Chassis` | Chassis collection |
| `/redfish/v1/Systems` | Systems collection |
| `/redfish/v1/Systems/<id>/Storage` | Storage controllers |
| `/redfish/v1/Systems/<id>/Storage/<sid>/Drives` | Drives |
| `/redfish/v1/Systems/<id>/Storage/<sid>/Volumes` | Volumes |
| `/redfish/v1/Managers` | BMC info |
| `/redfish/v1/UpdateService/FirmwareInventory` | 펌웨어 |
| `/redfish/v1/AccountService/Accounts` | BMC 사용자 |
| `/redfish/v1/Chassis/<id>/Power` | PSU / 전력 |

## OData 메타 (모든 vendor)

```json
{
  "@odata.id": "/redfish/v1/Systems/1",
  "@odata.type": "#ComputerSystem.v1_x_y.ComputerSystem",
  "@odata.context": "/redfish/v1/$metadata#ComputerSystem.ComputerSystem",
  "Members": [...],
  "Members@odata.count": 2,
  "Members@odata.nextLink": "/redfish/v1/.../?$skip=10"
}
```

## Status 객체 (헬스 모니터링)

```json
{
  "Status": {
    "State": "Enabled",
    "Health": "OK",
    "HealthRollup": "OK"
  }
}
```

`Health` 값: `OK / Warning / Critical`. server-exporter는 OK 외를 errors로 기록.

## 인증 방법 (모든 vendor 공통)

1. **HTTP Basic** (server-exporter 기본): `Authorization: Basic <base64>`
2. **Session-based**: `POST /redfish/v1/SessionService/Sessions` → `X-Auth-Token`

## 적용 rule

- rule 12 (adapter-vendor-boundary)
- rule 27 R3 (Vault 2단계 로딩)
- rule 30 (integration-redfish-vmware-os)
- rule 96 (external-contract-integrity) — vendor별 origin 주석

## 정본 reference

- `.claude/ai-context/vendors/{vendor}.md` (5 vendor 메모)
- `docs/ai/references/redfish/redfish-spec.md` (DMTF 표준)
- `docs/reference/live-validation.md` (Round 검증 결과)
