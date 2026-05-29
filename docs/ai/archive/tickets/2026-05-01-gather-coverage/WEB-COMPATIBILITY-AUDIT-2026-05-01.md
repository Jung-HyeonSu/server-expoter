# Web Compatibility Audit — 2026-05-01

> 사용자 명시 (2026-05-01): "redfish 코드의 벤더, 모델, 버전 호환성 전수조사. web 검색 이용. 부족한점은 모두 티켓으로 다음 세션에서 작업. 루프 7번."

## 목적

- Redfish adapter 16종 / 5 vendor 호환성 누락 식별
- lab 부재 영역 (Huawei / Inspur / Fujitsu / NEC) web 검색으로 sources 보강
- 다음 세션 작업 ticket (P1/P2/P3) 등재
- 더 이상 호환성 사고 발생 안 하도록 7-loop 강제

## 7-loop 구조

| Loop | 영역 | 적용 범위 |
|---|---|---|
| 1 | Dell iDRAC 7/8/9 + Gen11(iDRAC 10) | adapters/redfish/dell_idrac*.yml |
| 2 | HPE iLO 4/5/6/7 | adapters/redfish/hpe_ilo*.yml |
| 3 | Lenovo XCC / XCC2 / XCC3 / IMM2 | adapters/redfish/lenovo_*.yml |
| 4 | Supermicro X9~X14 + H12/H13 | adapters/redfish/supermicro_*.yml |
| 5 | Cisco CIMC + UCS | adapters/redfish/cisco_*.yml |
| 6 | 미보유 vendor (Huawei/Inspur/Fujitsu/NEC/Quanta) | 신규 후보 |
| 7 | 횡단 (DMTF / Auth / TLS / Schema 변천) | redfish_gather.py / common |

## 신뢰도 분류 (rule 96 R1-A)

- **공식**: developer.dell.com / support.hpe.com / pubs.lenovo.com / supermicro.com / cisco.com / huawei.com — 직접 적용 가능
- **표준**: redfish.dmtf.org — endpoint path / schema 정본
- **community**: GitHub issue / Reddit / blog — 보조 reference
- **사이트 실측**: tests/evidence/ — 최우선 (rule 25 R7-A-1)

---

## Findings (loop별 append)

---

## Loop 1/7 — Dell iDRAC 7/8/9/10

### 검색 일시
2026-05-01

### 현재 server-exporter 커버리지
- `dell_idrac.yml` (priority=10, generic) — vendor: Dell
- `dell_idrac8.yml` (priority=50) — iDRAC 8 / 13G PowerEdge
- `dell_idrac9.yml` (priority=100) — iDRAC 9 / 14G~16G PowerEdge / 펌웨어 4.x~7.x

### web sources (공식)
- [iDRAC9 Redfish API What's new](https://developer.dell.com/apis/2978/versions/7.xx) — 7.x release notes (공식)
- [iDRAC9 Versions and Release Notes](https://www.dell.com/support/kbdoc/en-us/000178115/idrac9-versions-and-release-notes)
- [iDRAC10 PowerEdge 17G support](https://www.dell.com/support/kbdoc/en-us/000348267/poweredge-support-for-integrated-dell-remote-access-controller-10-idrac10)
- [iDRAC10 1.20.55.10 Release Notes](https://manuals.plus/m/7fbce549aaa0031d4694fdbdfc75e0ff395f55c288a7ea3eb491a01a930424bf)
- [iDRAC10 User's Guide R670](https://www.dell.com/support/manuals/en-us/poweredge-r670/idrac10_1.xx_ug/accessing-redfish-api)
- [iDRAC10 BIOS upgrade 17G](https://www.dell.com/support/kbdoc/en-us/000356005/poweredge-recommended-bios-and-idrac10-upgrades-for-17th-gen)
- [iDRAC8 v2.70.70.70 Redfish API Guide](https://www.dell.com/support/manuals/en-us/poweredge-r730/idrac8_redfishapiguide_2.70.70.70/updating-firmware-using-simpleupdate)
- [iDRAC 7/8 v2.40.40.40 Redfish API Reference](https://www.dell.com/support/manuals/en-us/idrac7-8-lifecycle-controller-v2.40.40.40/redfish%202.40.40.40/overview)
- [Dell iDRAC-Redfish-Scripting (GitHub)](https://github.com/dell/iDRAC-Redfish-Scripting)

### 핵심 발견

#### F41 [HIGH/P1] iDRAC10 adapter 부재
- **상태**: 누락 — PowerEdge 17G (R470/R670/R770/R7715/R6715/R6815 등) 신규 PowerEdge 출하 시작
- **영향**: 호출자가 17G server 등록 시 dell_idrac9 adapter 가 매칭되지만 schema 일부 차이 가능 (OEM namespace / endpoint path)
- **변종**:
  - manufacturer 동일 ("Dell Inc.") 이나 firmware version 1.x (iDRAC9 = 4.x~7.x)
  - 펌웨어 bump: `iDRAC.Embedded.1` 동일 → OEM path 동일 가능
  - Open Server Manager (OSM) 모드 → iDRAC10 변환 필요한 일부 모델 R670/R770
- **action**:
  1. `adapters/redfish/dell_idrac10.yml` 신규 (priority=120)
  2. match.firmware_patterns: `^1\.[0-9]+`
  3. tested_against: lab 부재 → web sources only
  4. capabilities: dell_idrac9 와 동일 가정 + OEM 차이 발견 시 보강

#### F42 [P2] iDRAC9 7.x 신규 endpoint sources
- `/Systems/.../EnvironmentMetrics` — GPU/processor metrics
- `/Systems/.../MemoryMetrics` — DIMM 영역 신 metrics
- `/Chassis/.../EnvironmentMetrics` — chassis 레벨 PowerWatts
- `NetworkAdapter.StateSensors` / `DMFunctionality`
- `NetworkAdapter.SetPowerSavingMode` action
- `Managers/.../ManagerDiagnosticData` 신 resource
- **action**: 새 데이터 수집 영역 — 호환성 cycle 외 (rule 96 R1-B). F03/F19/F26 묶음으로 별도 ticket
- **검증만** (호환성): 현재 코드는 이 endpoint 미사용 → 호환성 fallback 불필요

#### F43 [P2] iDRAC9 7.x deprecated (제거된 endpoint)
- **LCWipe → SystemErase** — server-exporter 미사용 (action 미호출) → 영향 없음
- **Telemetry RSYSLOG (7.00+ 제거)** — server-exporter 미사용 → 영향 없음
- **GetLaneErrorInjectionInfo (DellSwitch OEM)** — server-exporter 미사용 → 영향 없음
- **action**: 검증만 — 영향 없음

#### F44 [P2] iDRAC8 schema 차이 명시
- iDRAC 8 (PowerEdge 13G) 펌웨어 2.70.70.70 Redfish 지원
- iDRAC 9 대비 한정:
  - Storage Volumes 5.x 표준 미지원 가능 → SimpleStorage fallback (A1 이미 적용)
  - PowerSubsystem 미지원 → /Power 사용 (A2 이미 적용)
  - NetworkAdapter root 부재 가능 → NetworkInterface 만
- **action**: dell_idrac8.yml capabilities 검증. 현재 호환성 fallback (A1, A2) 으로 cover됨

#### F45 [P3] iDRAC7 매우 제한적 Redfish
- PowerEdge 12G (R720/R620/R820) — iDRAC7
- Redfish 2.40.40.40 → 매우 제한적 (Systems 일부, OEM 거의 없음)
- 실 필드 운영 12G 거의 없음 (12G EOL: Dell 공식 2018)
- **action**: dell_idrac.yml (generic) 가 cover. 별도 dell_idrac7 adapter 불필요 (P3)

#### F46 [P2] DSA-2025-370 / DSA-2026-012 / DSA-2026-014 보안 패치
- iDRAC10 1.20.x 시리즈 보안 패치 — 서비스 운영 권장 사항
- server-exporter 영향: 직접적 적용 없음 (수집 동작 영향 없음)
- **action**: 외부 운영 정책 — server-exporter 자체 영향 0

### 적용 대상 (다음 세션)

| Ticket | 우선 | 작업 | 예상 분량 |
|---|---|---|---|
| F41 | P1 | dell_idrac10.yml 신규 | adapter 1 + tests/fixtures 1 |
| F42 | P2 | EnvironmentMetrics / MemoryMetrics / ManagerDiagnosticData (새 데이터, rule 96 R1-B → 별도 cycle) | — |
| F43 | P2 | deprecated 등재만 — 영향 없음 | docs/ai/catalogs/EXTERNAL_CONTRACTS.md |
| F44 | P2 | dell_idrac8 capabilities 검증 (이미 cover) | docs/ai/catalogs/VENDOR_ADAPTERS.md |
| F45 | P3 | iDRAC7 generic cover 등재만 | — |
| F46 | P2 | DSA 보안 패치 등재만 — server-exporter 영향 0 | — |

---

## Loop 2/7 — HPE iLO 4/5/6/7

### 검색 일시
2026-05-01

### 현재 server-exporter 커버리지
- `hpe_ilo.yml` (priority=10, generic) — vendor: HPE
- `hpe_ilo4.yml` (priority=50) — iLO 4 / Gen8/Gen9 ProLiant
- `hpe_ilo5.yml` (priority=80) — iLO 5 / Gen10/10+ ProLiant
- `hpe_ilo6.yml` (priority=100) — iLO 6 / Gen11 ProLiant

### web sources (공식)
- [iLO 6 Redfish API Reference](https://hewlettpackard.github.io/ilo-rest-api-docs/ilo6/)
- [iLO 6 changelog](https://servermanagementportal.ext.hpe.com/docs/redfishservices/ilos/ilo6/ilo6_changelog) — DMTF 1.20.0 + schema bundle 8010_2024.1
- [iLO 6 adapting from iLO 5](https://servermanagementportal.ext.hpe.com/docs/redfishservices/ilos/ilo6/ilo6_adaptation)
- [iLO 7 documentation](https://servermanagementportal.ext.hpe.com/docs/redfishservices/ilos/ilo7) — Gen12 신규 (2025-02 출시)
- [iLO 7 adaptation guide (from iLO 6)](https://servermanagementportal.ext.hpe.com/docs/redfishservices/ilos/ilo7/ilo7_adaptation)
- [HPE Gen12 announcement (Feb 2025)](https://www.hpe.com/us/en/newsroom/press-release/2025/02/hpe-introduces-next-generation-proliant-servers-engineered-for-advanced-security-ai-automation-and-greater-performance.html)
- [iLO 7 v1.16.00 Release Notes](https://www.scribd.com/document/917390429/HPE-sd00006383en-us-HPE-ILO-7-v1-16-00-Release-Notes)
- [HPE iLO Wikipedia](https://en.wikipedia.org/wiki/HP_Integrated_Lights-Out)

### 핵심 발견

#### F47 [HIGH/P1] iLO 7 adapter 부재 (Gen12)
- **상태**: 누락 — HPE ProLiant Gen12 (DL360/DL380/DL580/ML350 등) 2025-02 출시
- **신규 manufacturer signature**: 동일 "HPE" / "Hewlett Packard Enterprise" → vendor 감지는 OK
- **펌웨어 version 형식 변경**: "Major.Minor" (1.67) → "Major.Minor.Patch date" (1.12.00 Mar 28 2025)
  - 현재 hpe_ilo6.yml `firmware_patterns: ["iLO.*6", "^[12]\\."]` → "1.12.00"도 매칭됨 (오탐 가능)
  - **필요**: hpe_ilo7.yml 신규 + match.product_name 또는 manager_type 으로 분리
- **OEM 네임스페이스**: `Oem.Hpe` 동일
- **action**:
  1. `adapters/redfish/hpe_ilo7.yml` 신규 (priority=120)
  2. match: ilo_version pattern 또는 product_name "ProLiant DL360 Gen12"
  3. lab 부재 — web sources only

#### F48 [P1/HIGH] NetworkPorts / BaseNetworkAdapters deprecated (iLO 6+)
- **deprecated**: BaseNetworkAdapters + NetworkPorts → EthernetInterface
- **server-exporter 영향**: cycle 2026-04-29 commit (B93) NIC mac fold-in 이 NetworkPorts 사용 중
- **현재 상태**: 이미 EthernetInterface fallback 있을 수 있음 — 코드 검증 필요
- **action**:
  1. `redfish-gather/library/redfish_gather.py` _gather_network 검토
  2. NetworkPorts 응답 0건일 때 EthernetInterface 만 사용하는지 확인
  3. 호환성 fallback 추가 (Additive — rule 96 R1-B 준수)

#### F49 [P2] iLO 7 deprecated `Oem.Hpe.Firmware.Current.*`
- iLO 7부터 `Oem.Hpe.Firmware.Current.MajorVersion / MinorVersion / VersionString` deprecated
- 권장: `FirmwareVersion` property 또는 `/UpdateService/FirmwareInventory/{item}`
- **server-exporter 영향**: redfish_gather.py 가 `Oem.Hpe.Firmware` 어디서 읽는지 확인 필요
- **action**: gather_firmware → FirmwareInventory 우선, OEM fallback 만 유지

#### F50 [P2] iLO 7 SecurityState: SecureStandard (default)
- iLO 6 HighSecurity 와 동등하나 명칭 변경
- TLS 1.0/1.1 enum 제거 → server-exporter ssl context 가 이미 TLS 1.2+ 인지 검증 필요
- **action**: redfish_gather.py 의 ssl context 설정 검토. K2 (weak cipher fallback) 와 충돌 없는지 확인

#### F51 [P2] iLO 7 Federation / SerialInterface / SCEP 제거
- server-exporter 미사용 → 영향 없음
- 등재만

#### F52 [P2] iLO 6 신규 endpoint (호환성 영역 외 — 새 데이터)
- ComponentIntegrity / SecureBootDatabase / Fabric / StorageController.Port
- ThermalSubsystem (≠ /Thermal)
- EnvironmentMetrics / PortMetrics / ProcessorMetrics / MemoryMetrics
- ManagerDiagnosticData / SecurityPolicy / ComponentIntegrityPolicy
- **action**: 호환성 cycle 외 — F03 / F19 / F26 / F27 묶음 (이미 등재)

#### F53 [P2] iLO 6 신규 OEM property
- `Oem.Hpe.AggregateHealthStatus.AirFilter` (Gen11)
- HBM memory in Memory collection (Gen11 신규)
- CloudConnect WorkspaceId (deprecated ActivationKey)
- PowerLimitWatts AllowableMax/Min/SetPoint (processors)
- FanWatts under HpePowerMeter
- **action**: 호환성 영역 외 — 새 데이터. F03 / F06 묶음

#### F54 [P3] iLO 4 (Gen8/Gen9) Redfish 1.0/1.1 매우 제한적
- 일부 endpoint 부재 (NetworkAdapter / Storage Volumes 등)
- 기존 hpe_ilo4.yml + redfish_generic.yml 로 cover
- **action**: 검증만 — 영향 없음

### 적용 대상 (다음 세션)

| Ticket | 우선 | 작업 |
|---|---|---|
| F47 | P1 | hpe_ilo7.yml 신규 (Gen12) + 펌웨어 version 형식 변경 매칭 |
| F48 | P1 | EthernetInterface fallback 검증 + 코드 보강 |
| F49 | P2 | FirmwareInventory 우선 + Oem.Hpe.Firmware fallback |
| F50 | P2 | SSL context TLS 1.2+ 검증 |
| F51 | P2 | Federation/Serial/SCEP 등재만 |
| F52 | P2 | iLO 6 새 endpoint (호환성 외) |
| F53 | P2 | iLO 6 새 OEM property (호환성 외) |
| F54 | P3 | iLO 4 cover 등재만 |

---

## Loop 3/7 — Lenovo XCC / XCC2 / XCC3 / IMM2

### 검색 일시
2026-05-01

### 현재 server-exporter 커버리지
- `lenovo_bmc.yml` (priority=10, generic) — vendor: Lenovo
- `lenovo_imm2.yml` (priority=50) — IMM2 / 구 ThinkServer
- `lenovo_xcc.yml` (priority=100) — XCC 1.x / 2.x / 3.x 통합 (`firmware_patterns: ["XCC"]`)

### web sources (공식)
- [XCC2 Product Guide](https://lenovopress.lenovo.com/lp1800-lenovo-xclarity-controller-2-xcc2)
- [XCC3 Product Guide](https://lenovopress.lenovo.com/lp2273-lenovo-xclarity-controller-3-xcc3)
- [XCC3 Product Guide PDF](https://lenovopress.lenovo.com/lp2273.pdf)
- [XCC2 REST API docs](https://pubs.lenovo.com/xcc2-restapi/) — Redfish 1.20.0 / bundle 2023.3
- [XCC3 REST API docs](https://pubs.lenovo.com/xcc3-restapi/) — Redfish 1.17.0 / bundle 2024.3
- [XCC3 REST API book PDF](https://pubs.lenovo.com/xcc3-restapi/xcc3_restapi_book.pdf)
- [XCC3 setting names](https://pubs.lenovo.com/xcc3/dw1lm_t_xcc3settingname)
- [ThinkSystem V3/V4 firmware best practices](https://lenovopress.lenovo.com/lp1991-thinksystem-v3-v4-server-firmware-and-drivers-best-practices-advanced-guide)
- [SR680a V4 Product Guide](https://lenovopress.lenovo.com/lp2264-thinksystem-sr680a-v4-server)
- [SR630 V4 Product Guide](https://lenovopress.lenovo.com/lp1971-thinksystem-sr630-v4-server)

### 핵심 발견

#### F55 [HIGH/P1] XCC3 / ThinkSystem V4 신 generation — adapter 분리 필요
- **상태**: lenovo_xcc.yml 가 XCC 1.x/2.x/3.x 통합. XCC3는 **OpenBMC 기반**으로 schema/setting/Oem 일부 변경
- **변종**:
  - XCC3 = ThinkSystem V4 (SR630 V4 / SR650 V4 / SR680a V4 등) 2025-2026 출하
  - OpenBMC 기반 → Oem.Lenovo 영역이 표준 Redfish 우선 (alignment) → OEM 의존 감소
  - Redfish 1.17.0 / schema bundle 2024.3
  - UEFI/BMC 설정 이름 형식 변경 (IMM.xyz → Redfish style — read-only 우리 영향 작음)
  - FPGA firmware separate item (V4+) — FirmwareInventory 신 entry
  - ExtendedError.1.2.2.json OEM registry 신규
- **action**:
  1. `adapters/redfish/lenovo_xcc3.yml` 신규 (priority=120) — match: ThinkSystem V4 model
  2. `lenovo_xcc.yml` 을 XCC1/XCC2 로 좁히거나 priority 조정 (역전 방지)
  3. lab 부재 — web sources only

#### F56 [P1] XCC2 vs XCC3 schema bundle 역전
- XCC2: Redfish 1.20.0 + bundle 2023.3 (구식 schema, 신 spec)
- XCC3: Redfish 1.17.0 + bundle 2024.3 (신 schema, 구 spec) ← 의도된 OpenBMC 정렬
- **server-exporter 영향**: schema_version 필드는 envelope 포함되지 않으므로 영향 작음. 단 endpoint 응답 형식 차이 가능
- **action**: F55 의 adapter 신규 시 capabilities 매트릭스 다시 정의

#### F57 [P2] XCC reverse regression (cycle 2026-04-30 사이트 사고) 회귀 회피
- 사용자 사이트 BMC: AFBT58B 5.70 (lab) 가 OK 인데 사이트 다른 펌웨어 reject
- 현재 hotfix: Accept-only 헤더 (J2)
- **action**: F55 신규 adapter 작성 시 Accept-only 패턴 유지. OData-Version / User-Agent 추가 금지

#### F58 [P2] XCC3 Health 영역 endpoint
- OpenBMC 정렬 → ComponentIntegrity / SecureBoot / Fabric 신 endpoint
- **action**: 호환성 영역 외 — 새 데이터 ticket (F03 / F19 묶음)

#### F59 [P3] IMM2 (구 BMC) deprecated 경로 지속 cover
- ThinkServer 구 시리즈 (RD/RS/TS) — IMM2
- 현재 lenovo_imm2.yml priority=50, lenovo_bmc.yml priority=10 cover
- **action**: 검증만 — 영향 없음

#### F60 [P2] FPGA firmware 별도 inventory (V4+)
- ThinkSystem V4 (XCC3) 부터 FPGA 가 XCC firmware 와 분리
- /UpdateService/FirmwareInventory/FPGA 신 entry 가능
- **server-exporter 영향**: gather_firmware 가 모든 FirmwareInventory member 수집 → 자동 cover
- **action**: 검증만. 필요 시 baseline 추가

### 적용 대상 (다음 세션)

| Ticket | 우선 | 작업 |
|---|---|---|
| F55 | P1 | lenovo_xcc3.yml 신규 + 모델 매칭 (ThinkSystem V4) |
| F56 | P1 | XCC2 vs XCC3 capabilities 매트릭스 분리 |
| F57 | P2 | Accept-only 헤더 패턴 신 adapter 적용 |
| F58 | P2 | XCC3 OpenBMC 신 endpoint (호환성 외) |
| F59 | P3 | IMM2 cover 등재만 |
| F60 | P2 | FPGA inventory 검증 |

---

## Loop 4/7 — Supermicro X9~X14 / H12~H14

### 검색 일시
2026-05-01

### 현재 server-exporter 커버리지
- `supermicro_bmc.yml` (priority=10, generic) — vendor: Supermicro
- `supermicro_x9.yml` (priority=50) — X9 / 구형
- `supermicro_x11.yml` (priority=80) — X11 / AST2500

### web sources (공식)
- [BMC IPMI X14/H14 Manual](https://www.supermicro.com/manuals/other/BMC_IPMI_X14_H14.pdf)
- [BMC IPMI X13/H13/B13 Manual](https://www.supermicro.com/manuals/other/BMC_IPMI_X13_H13_B13.pdf)
- [Redfish User Guide rev 6.1](https://www.supermicro.com/manuals/other/RedfishUserGuide.pdf)
- [Redfish Reference Guide HTML](https://www.supermicro.com/manuals/other/redfish-ref-guide-html/Content/general-content/firmware-inventory-update-service.htm)
- [Redfish User Guide 5.0 PDF](https://www.scribd.com/document/871728509/Redfish-User-Guide)
- [Supermicro BMC security updates 2024-04 (Thomas-Krenn)](https://www.thomas-krenn.com/en/wiki/Supermicro_BMC_security_updates_2024-04)
- [BMC Download Center](https://www.supermicro.com/support/resources/bios_ipmi.php?type=BMC)

### 핵심 발견

#### F61 [HIGH/P1] X12 / X13 / X14 adapter 부재
- **상태**: 누락 — server-exporter 는 X9 / X11 만. X12 (Whitley/Tatlow), X13 (Eagle), X14/H14 (2024-2025 신) 미커버
- **하드웨어 차이**:
  - X9/X10/X11/H11 = AST2500 / ARM11
  - X12/H12/X13/H13/X14/H14 = AST2600 / Dual-core ARM Cortex A7 (Root of Trust 지원)
- **firmware update parameters 차이**:
  - X12+ 신: PreserveOA / PreserveSETUPCONF / PreserveSETUPPWD / PreserveSECBOOTKEY / PreserveBOOTCONF / UpdateRollbackID
  - server-exporter 는 read-only → 직접 영향 없음
- **X14/H14 신 features**:
  - CPLD APIs (CPLD firmware inventory)
  - StartTLS
  - Boot Certificates
  - ClearCMOS action
  - iHDT / standby power cycle
  - CPU power capping
  - Redfish 1.21.0 / bundle 2024.3
- **action**:
  1. `adapters/redfish/supermicro_x12.yml` 신규 (priority=90)
  2. `adapters/redfish/supermicro_x13.yml` 신규 (priority=100)
  3. `adapters/redfish/supermicro_x14.yml` 신규 (priority=110)
  4. lab 부재 — web sources only

#### F62 [P2] X10 generic cover 검증
- 현재 supermicro_bmc.yml (priority=10) 가 X10 cover
- X9 → X10 → X11 같은 ARM11 / AST2500 계열 → schema 호환
- **action**: 검증만 — supermicro_x10.yml 별도 필요 없음

#### F63 [P2] H12 / H13 / B13 변종
- H12 — 일부 variant AST2500, 일부 AST2600 (의도된 hybrid)
- H13 — AST2600 (X13 와 동일 BMC)
- B13 — Building blocks platform (X13 derivative)
- **action**: F61 의 supermicro_x12 / supermicro_x13 가 cover. match.model_patterns 에 H12 / H13 / B13 추가

#### F64 [P2] X14 신 endpoint (호환성 외 — 새 데이터)
- CPLD firmware inventory
- Boot Certificates
- iHDT (intelligent hardware diagnostic test)
- CPU power capping
- **action**: 호환성 영역 외 — F03 / F19 묶음

#### F65 [P2] StartTLS (Supermicro X14)
- Redfish over StartTLS — server-exporter 는 HTTPS 직접 사용 (StartTLS 불필요)
- 그러나 일부 BMC 가 StartTLS 만 지원하면 영향
- **action**: 검증만 — 현재 사례 없음

#### F66 [P2] 2024-04 Supermicro BMC 보안 패치 모든 X / H / M / B 시리즈
- Thomas-Krenn 게시 — 운영 권장 사항
- server-exporter 영향: 직접 0
- **action**: 운영 정책 — 등재만

#### F67 [P3] X9 / X10 SimpleStorage only
- 구 Supermicro BMC 는 /Storage 미지원 → /SimpleStorage 만
- 이미 A1 (호환성 fallback) cover
- **action**: 검증만

### 적용 대상 (다음 세션)

| Ticket | 우선 | 작업 |
|---|---|---|
| F61 | P1 | supermicro_x12 / x13 / x14 adapter 신규 (3개) |
| F62 | P2 | X10 generic cover 등재만 |
| F63 | P2 | H12/H13/B13 model_patterns 추가 |
| F64 | P2 | X14 신 endpoint (호환성 외) |
| F65 | P2 | StartTLS 등재만 — 영향 없음 |
| F66 | P2 | 보안 패치 운영 정책 등재만 |
| F67 | P3 | SimpleStorage cover 등재만 |

---

## Loop 5/7 — Cisco CIMC + UCS

### 검색 일시
2026-05-01

### 현재 server-exporter 커버리지
- `cisco_cimc.yml` (priority?, lab tested) — UCS C-Series M4 / 4.1.x 펌웨어
- `cisco_bmc.yml` (priority=10, generic)

### web sources (공식)
- [Cisco UCS C-Series REST API Programmer's Guide 4.3](https://www.cisco.com/c/en/us/td/docs/unified_computing/ucs/c/sw/api/4_3/b-cisco-ucs-c-series-servers-rest-api-programmer-s-guide-release-4-3/m-cisco-imc-rest-api-overview.html)
- [Release Notes Cisco UCS Rack Server SW 6.0(1)](https://www.cisco.com/c/en/us/td/docs/unified_computing/ucs/release/notes/b_release-notes-for-cisco-ucs-rack-server-software-release-6-0-1.html)
- [Release Notes 4.3(5)](https://www.cisco.com/c/en/us/td/docs/unified_computing/ucs/release/notes/b_release-notes-for-cisco-ucs-rack-server-software-release-4_3_5.html)
- [Release Notes 4.3(6)](https://www.cisco.com/c/en/us/td/docs/unified_computing/ucs/release/notes/b_release-notes-for-cisco-ucs-rack-server-software-release-4_3_6.html)
- [UCS X-Series Modular System](https://www.cisco.com/c/en/us/support/servers-unified-computing/ucs-x-series-modular-system/series.html)
- [Intersight Managed Mode Configuration](https://www.cisco.com/c/en/us/td/docs/unified_computing/Intersight/b_Intersight_Managed_Mode_Configuration_Guide/b_intersight_managed_mode_guide_chapter_01010.html)
- [Cisco Intersight Server Firmware Release Notes (4.3 / 5.2 / 5.3 / 5.4)](https://www.cisco.com/c/en/us/td/docs/unified_computing/Intersight/Server-Firmware/4_3/b_intersight_server_fw_rn_4_3.html)
- [Cisco Redfish API Examples 4.2](https://www.cisco.com/c/en/us/td/docs/unified_computing/ucs/c/sw/api/3_0/b_Cisco_IMC_REST_API_guide_301/m_redfish_api_examples.html)

### 핵심 발견

#### F68 [P1] M5 / M6 / M7 / M8 generation adapter 분리
- **상태**: cisco_cimc.yml 가 M4 / 4.1.x 만 실측. M5 ~ M8 cover 검증 필요
- **세대 매트릭스**:
  - M4 (lab tested 10.100.15.2 4.1.x) — Broadwell-EP / DDR4-2400 → 본 adapter cover
  - M5 (Skylake-SP) — 4.3(3.240022)+ 미지원. 4.3(2.x) 마지막 (2024-2025 EOL)
  - M6 (Ice Lake-SP) — Redfish 1.x 정식 지원
  - M7 (Sapphire Rapids) — Redfish 활발 지원
  - M8 (2025 출하 — C220 M8 / C240 M8) — IMC 4.3(6.250039) 첫 지원
- **action**:
  1. cisco_cimc.yml capabilities 매트릭스 확장 (M4 ~ M7)
  2. `adapters/redfish/cisco_cimc_m8.yml` 신규 (priority=110) 검토 — 차이점 확인 후
  3. lab 부재 영역 (M5/M6/M7/M8) — web sources only

#### F69 [HIGH/P1] UCS X-Series (X210c / X410c) 별도 처리
- **상태**: server-exporter 미커버
- **변종**:
  - X210c M6 / X410c M7 / X-Series M8 — Intersight Managed Mode (IMM)
  - **standalone 모드**: CIMC Redfish 가능 (M-series 와 유사)
  - **IMM 모드**: Intersight cloud 만 — server-exporter 직접 BMC 연결 불가
- **action**:
  1. standalone 사용 사례 우선 — X-series CIMC Redfish 적용
  2. IMM 모드는 Intersight API 별도 — 새 채널 영역 (server-exporter 범위 외 또는 별도 cycle)
  3. `adapters/redfish/cisco_ucs_xseries.yml` 신규 (priority=110, match.product_name)
- **주의**: X-Series 도 manufacturer "Cisco Systems Inc."(.) — vendor 감지는 OK

#### F70 [P2] Cisco IMC 3.0 매우 구식 Redfish 1.0.1
- IMC 3.0 (구) — Redfish 1.0.1 (DMTF 1.0)
- 현재 lab 4.1.x 가 Redfish 1.2.0
- M3/M4 구펌웨어 일부 — `/Systems`/`/Chassis`/`/Managers` 일부만 + OEM 부재
- **action**: cisco_bmc.yml (generic, priority=10) cover. 호환성 fallback (404 → not_supported, I4) 이미 적용

#### F71 [P2] M5 EOL (4.3(2.x) 마지막)
- M5 운영 사이트는 4.3(2.x) 펌웨어 동결 → 향후 신 endpoint 미지원
- server-exporter 영향 없음 (read-only)
- **action**: 운영 정책 등재만 — server-exporter 자체 영향 0

#### F72 [P2] Manufacturer 마침표 변종 (Q1 cycle 2026-04-29 확인)
- ServiceRoot.Vendor = "Cisco Systems Inc."(.) vs System.Manufacturer = "Cisco Systems Inc"(.없음)
- 이미 _FALLBACK_VENDOR_MAP / adapter match list 등록 → 매치 OK
- **action**: 검증만 — 영향 없음

#### F73 [P3] PSU PowerCapacityWatts null (Q2)
- 이미 cycle 2026-04-29 fallback (H1) cover
- **action**: 검증만

### 적용 대상 (다음 세션)

| Ticket | 우선 | 작업 |
|---|---|---|
| F68 | P1 | M5~M8 capabilities 매트릭스 확장 / cisco_cimc_m8.yml 검토 |
| F69 | P1 | UCS X-Series standalone CIMC adapter 신규 (IMM 모드 별도) |
| F70 | P2 | IMC 3.0 cover 검증 (cisco_bmc.yml) |
| F71 | P2 | M5 EOL 등재만 — server-exporter 영향 0 |
| F72 | P3 | manufacturer 변종 cover 등재만 |
| F73 | P3 | PSU null fallback 검증 |

---

## Loop 6/7 — 미보유 vendor (Huawei / Inspur / Fujitsu / Quanta / NEC)

### 검색 일시
2026-05-01

### 현재 server-exporter 커버리지
- **5 vendor cover** — Dell / HPE / Lenovo / Supermicro / Cisco
- **redfish_generic.yml** (priority=0) — fallback for unknown vendor

### web sources (공식)

#### Huawei
- [iBMC FusionServer Pro 2288H V5 User Guide](https://support.huawei.com/enterprise/en/doc/EDOC1000163550/41dfb258/ibmc)
- [iBMC FusionServer Pro V5/V6 Datasheet](https://networktelecom.ru/images/data/gallery/3071_9834_Huawei-FusionServer-Pro-V5-Rack-Server-Data-Sheet.pdf)
- [Huawei-iBMC-Cmdlets (GitHub)](https://github.com/Huawei/Huawei-iBMC-Cmdlets) — PowerShell Redfish wrapper

#### Inspur
- [Inspur NF5280M5 User Manual section 9.14 Redfish](https://manualzz.com/doc/o/v7c5h/inspur-server-user-manual-nf5280m5-9.14-redfish)
- [NF5280M5 Technical White Paper](https://www.inspur.com/eportal/fileDir/defaultCurSite/resource/cms/2020/04/2020040211224398612.pdf)
- [Inspur NF5280M/LM6 White Paper (2023)](https://www.inspur.com/eportal/fileDir/en/resource/cms/2023/01/2023011012511875447.pdf)

#### Fujitsu
- [iRMCtools (GitHub Fujitsu official)](https://github.com/fujitsu/iRMCtools)
- [iRMC-REST-API examples (GitHub Fujitsu)](https://github.com/fujitsu/iRMC-REST-API)
- [Fujitsu iRMC Redfish Examples](https://mmurayama.blogspot.com/2018/05/fujitsu-irmc-redfish-examples.html)
- [Fujitsu PRIMERGY iRMC S5 RESTful API Spec](https://manualzz.com/doc/37690590/irmc-restful-api-v5.0---fujitsu-manual-server)
- [iRMC S5 Login docs](https://docs.ts.fujitsu.com/dl.aspx?id=a5785619-b9c4-448b-9438-00d54f5d0884)

#### Quanta (QCT)
- [QuantaGrid D54Q-2U](https://www.qct.io/product/index/Server/rackmount-server/2U-Rackmount-Server/QuantaGrid-D54Q-2U)
- [D54Q-2U Spec PDF](https://www.exalit.com/storage/2023/09/D54Q-2U_v20230330.pdf)
- [QuantaGrid D52BQ-2U User Guide](https://www.hyperscalers.com/image/catalog/00-Products/Servers/QuantaGrid-D52BQ-2U-UG%202.0%20-%20HS.pdf)
- [Red Hat Catalog D54Q](https://catalog.redhat.com/en/hardware/system/detail/218837)
- [bmc-toolbox](https://bmc-toolbox.github.io/) — multi-vendor BMC abstraction

#### NEC
- [NEC Express5800 iLO 5 User Guide](http://www.58support.nec.co.jp/global/download/pdf/R120h/UG_iLO5_EN_1.15_R2.pdf)
- [NEC iLO 5 ManualsLib](https://www.manualslib.com/manual/1433139/Nec-Ilo-5.html)

### 핵심 발견

#### F74 [HIGH/P1] Huawei iBMC adapter 신규 후보
- **상태**: 미커버. FusionServer Pro V5 / V6 / Atlas 시리즈에서 Redfish/IPMI/SNMP/IPMI 2.0 지원
- **공식 vendor signature**:
  - manufacturer: "Huawei" / "Huawei Technologies Co., Ltd."
  - manager URI: `/redfish/v1/Managers/iBMC` (예상 — web sources confirm)
  - OEM namespace: `Oem.Huawei`
- **action**:
  1. `common/vars/vendor_aliases.yml` 매핑 추가 — "huawei"
  2. `adapters/redfish/huawei_ibmc.yml` 신규 (priority=80, lab 부재)
  3. `vault/redfish/huawei.yml` 생성
  4. `redfish-gather/tasks/vendors/huawei/` (선택)
  5. lab 부재 — web sources only / 사용자 사이트 도입 시 fixture 캡처
- **보류 사유**: 운영 상 Huawei 사이트 도입 신호 없으면 P3로 격하 가능 — 사용자 결정 필요

#### F75 [P2] Inspur ISBMC adapter 신규 후보
- **상태**: 미커버. NF5280M5 / NF5280M6 등 Redfish 지원
- **공식 vendor signature**:
  - manufacturer: "Inspur" / "Inspur Information Technology Company Limited"
  - INSPUR BMC (IPMI 2.0 / Redfish)
- **action**:
  1. `common/vars/vendor_aliases.yml` 매핑 추가 — "inspur"
  2. `adapters/redfish/inspur_isbmc.yml` 신규 (priority=80)
  3. lab 부재 — web sources only
- **보류 사유**: F74 와 동일 — 사용자 도입 신호 후 P1 격상

#### F76 [P2] Fujitsu iRMC S5 adapter 신규 후보
- **상태**: 미커버. PRIMERGY RX2540 M5 등 Redfish 지원
- **공식 vendor signature**:
  - manufacturer: "Fujitsu" / "FUJITSU"
  - manager URI: `/redfish/v1/Managers/iRMC` (예상)
  - Redfish based on iRMC S4 / S5 firmware
- **action**:
  1. `common/vars/vendor_aliases.yml` 매핑 추가 — "fujitsu"
  2. `adapters/redfish/fujitsu_irmc.yml` 신규 (priority=80)
  3. lab 부재 — web sources only

#### F77 [P3] Quanta (QCT) BMC OpenBMC adapter 신규 후보
- **상태**: 미커버. D54Q-2U / D52BQ-2U OpenBMC 기반
- **OpenBMC 표준** — 기존 redfish_generic.yml 가 부분 cover 가능
- **action**:
  1. 일단 redfish_generic.yml 로 cover 시도 — 부족 시 quanta_bmc.yml 신규
  2. lab 부재 + 운영 신호 없음 → P3

#### F78 [HIGH/P2] NEC Express5800 = HPE iLO rebadge
- **상태**: NEC Express5800 R 시리즈는 HPE iLO 5/6 펌웨어 그대로 사용 (rebadge OEM)
- **server-exporter 영향**:
  - manufacturer 가 "HPE" / "Hewlett Packard Enterprise" 로 응답 → 기존 hpe_ilo5/6 adapter 자동 매칭
  - 단 vendor_aliases.yml 에 "NEC" 별도 매핑 시 NEC adapter 분기 필요할 수 있음
- **action**:
  1. vendor_aliases.yml 검토 — NEC 가 별도 vendor 로 매핑되는지
  2. 별도 매핑 안 되면 HPE adapter 가 자동 cover (현 상태 OK)
  3. 등재만 — server-exporter 영향 0

#### F79 [P3] Intel Server System OpenBMC
- **상태**: 미커버. Intel Server System (M50CYP / M70KLP 등) OpenBMC Redfish
- **action**:
  - redfish_generic.yml fallback 로 cover 가능
  - 별도 adapter 우선 낮음 (운영 신호 없음)

### 적용 대상 (다음 세션)

| Ticket | 우선 | 작업 |
|---|---|---|
| F74 | P1 (사용자 도입 시) / P3 (lab 부재 유지) | Huawei iBMC adapter — 사용자 결정 |
| F75 | P2 | Inspur ISBMC adapter — 사용자 도입 신호 시 P1 |
| F76 | P2 | Fujitsu iRMC adapter — 사용자 도입 신호 시 P1 |
| F77 | P3 | Quanta QCT BMC — generic fallback 우선 시도 |
| F78 | P2 | NEC = HPE rebadge 등재만 |
| F79 | P3 | Intel Server System — generic fallback |

### 사용자 결정 필요

> **F74~F77 의 신규 vendor 추가는 사용자 명시 승인 필요** (rule 50 R2 — 9단계 vendor 추가 절차). lab 부재 + 운영 신호 없는 상태에서 무계획 신규는 비효율. 다음 cycle 에서 사용자께 도입 의향 확인 후 우선순위 재배정.

---

## Loop 7/7 — 횡단 (DMTF / Auth / TLS / Schema / HTTP)

### 검색 일시
2026-05-01

### web sources (DMTF 공식 표준)
- [Redfish Release 2025.4](https://www.dmtf.org/content/redfish-release-20254-now-available-0)
- [Redfish Release 2025.2](https://www.dmtf.org/content/redfish-release-20252-now-available)
- [Redfish Release 2025.1](https://www.dmtf.org/content/redfish-release-20251-now-available)
- [Redfish Release 2024.4](https://www.dmtf.org/content/redfish-release-20244-now-available)
- [Redfish Release 2024.1](https://www.dmtf.org/content/redfish-release-20241-now-available)
- [DSP2046 Resource Guide 2025.1](https://www.dmtf.org/sites/default/files/standards/documents/DSP2046_2025.1.pdf)
- [DSP8010 Schema Bundle 2025.2](https://redfish.dmtf.org/schemas/v1/DSP8010_2025.2.pdf)
- [DSP2064 Vendor Spec 1.1.0](https://www.dmtf.org/sites/default/files/standards/documents/DSP2064_1.1.0.pdf)
- [DSP2060 User Guide](https://www.dmtf.org/sites/default/files/standards/documents/DSP2060_1.0.0.pdf)
- [DSP0266 Specification](http://redfish.dmtf.org/schemas/DSP0266_1.6.1.html)

### 핵심 발견

#### F80 [P1] DMTF schema bundle 진화 추적
- **현재 server-exporter 가정**: Redfish 1.x 표준 + bundle 2023.x ~ 2024.x
- **2025 신 spec**:
  - 2024.1 (4 신 schema, 29 update)
  - 2024.4 (StorageMetrics, CDU Controls, 20 update)
  - 2025.1, 2025.2 (8 신 schema, 36 update, IIoT)
  - 2025.4 (최신)
- **server-exporter 영향**:
  - 우리는 raw passthrough → spec 변경에 직접 영향 작음
  - 단 신 schema (StorageMetrics / CDU / Environmental v1.2.0 liquid cooling) 가 새 endpoint 추가
  - 호환성 영역: 신 endpoint 자동 fallback (404 = not_supported, I4 이미 적용)
- **action**:
  1. EXTERNAL_CONTRACTS.md 에 DMTF spec 연도별 매트릭스 등재
  2. 신 schema (CDU / Liquid cooling) 는 새 데이터 영역 — 별도 cycle

#### F81 [P1] PowerSubsystem / ThermalSubsystem 마이그레이션 (DMTF 2020.4+)
- **현재 적용**: A2 (gather_power + _gather_power_subsystem) 호환성 fallback
- **현재 미적용**: ThermalSubsystem (chassis 의 신 thermal endpoint)
- **server-exporter 영향**: 현재 thermal 섹션 미수집 → 영향 없음. 향후 thermal 추가 시 PowerSubsystem 패턴 따라 ThermalSubsystem fallback 동시 적용
- **action**:
  1. 검증만 — 현재 thermal 미수집
  2. 향후 thermal 추가 ticket (F06 묶음) 진입 시 ThermalSubsystem 우선 + Thermal fallback 패턴

#### F82 [P2] X-Auth-Token vs Basic Authentication
- **현재 server-exporter**: Basic Auth 만
- **5 vendor 모두 X-Auth-Token 지원** (HPE / Lenovo / Supermicro / Dell / Cisco)
- **장점**: session lifetime 동안 재인증 부담 감소 → BMC CPU 부하 ↓
- **단점**: session 누수 시 BMC session list 한계 도달 → 잠금
- **server-exporter 사용 패턴**: 단발성 gather (collection 후 즉시 종료) → Basic Auth 가 자기-청소 + 단순
- **action**:
  1. 현재 패턴 유지 (Basic Auth + 단발성)
  2. 향후 F33 ticket (cycle 2026-05-01 등재) 진행 시 session login 도입 + DELETE session 보장 (graceful logout)
- **결론**: P2 — 운영 부하 신호 없으면 P3 격하

#### F83 [P1] ETag / If-Match 위험 회피 (read-only)
- **개요**: bmcweb 의 If-Match + ETag 일부 펌웨어에서 crash 사례 (OpenBMC issue #262)
- **server-exporter**: read-only (GET only) → If-Match 미사용 → 영향 없음
- **검증**: redfish_gather.py 가 PATCH / POST 보내지 않는지 확인
- **action**: redfish_gather.py 에 PATCH/POST 미사용 주석 추가 (origin 명시) — 안전 표시

#### F84 [P1] TLS 1.3 / cipher suite 강화
- **현재 적용**:
  - K1 OP_LEGACY_SERVER_CONNECT (구 BMC OpenSSL 3.x renegotiation)
  - K2 SECLEVEL=0 (weak cipher / iLO 4 / IMM2)
  - K3 verify=False (self-signed cert)
- **TLS 1.3 시대**:
  - HPE iLO 7 부터 TLS 1.0 / 1.1 enum 제거
  - 신 BMC (Gen11+ / XCC3+ / X14+) TLS 1.3 강제 가능
- **호환성**: 구식 BMC (TLS 1.0/1.1 만) ↔ 신식 BMC (TLS 1.3) 양쪽 지원 필요
- **action**:
  1. SSLContext 의 minimum_version / maximum_version 검증
  2. SECLEVEL=0 + TLS 1.3 호환성 회귀 (P1)
  3. mutual TLS (client cert) 는 사용자 결정 (lab 부재)

#### F85 [P2] HTTP 헤더 변종 ((cycle 2026-04-30 hotfix 회귀 회피)
- **현재 hotfix**: J2 — Accept-only (Lenovo XCC 사이트 사고로 추가)
- **표준 권장**: Accept + OData-Version + User-Agent
- **충돌**: 일부 사이트 BMC (Lenovo 1.17.0) 에서 OData-Version reject
- **action**:
  - **사용자 사이트 실측 우선** (rule 25 R7-A-1) — 현 hotfix 유지
  - 신규 vendor / 신 펌웨어 lab 검증 시 OData-Version 추가 시도 후 회귀 통과해야 적용

#### F86 [P3] 다양한 BMC IPv6 / 듀얼스택
- **현재 적용**: precheck IPv6 듀얼스택 cover (cycle 2026-04-29)
- **action**: 검증만

#### F87 [P3] OEM Action / Operation 호출 무시 (read-only 보장)
- **현재**: server-exporter 는 GET only
- **OEM Action**: SystemErase / SetBiosTime / RetryCloudConnect / ClearCMOS 등 — 절대 호출 안 함
- **action**: redfish_gather.py 에 "GET only" 주석 명시

#### F88 [P2] Redfish Service Root 응답 다양성
- **현재 적용 호환성**:
  - B1 (Vendor 필드 부재)
  - B2 (ServiceRoot 빈 응답 / WWW-Authenticate realm fallback)
- **추가 변종 (web sources)**:
  - 일부 OpenBMC 가 ServiceRoot.Vendor 자동 값 부재 → Manufacturer 만
  - Quanta/Intel OpenBMC 에서 ServiceRoot.Oem 부재
- **action**: 검증만 — 현재 fallback cover

#### F89 [P3] Pagination / @odata.nextLink
- **DMTF spec**: `Members@odata.nextLink` 로 pagination
- **현재 server-exporter**: 단일 fetch (members 가 큰 컬렉션 시 일부 누락 가능)
- **영향**: BMC 의 일반 가정 — collection size < 100 → 영향 작음
- **action**:
  1. _gather_collection 에 nextLink 처리 검증
  2. 누락 시 보강 — 새 수집 영역 (호환성 외)

#### F90 [P3] EventService / SubscriptionService
- **DMTF spec**: 이벤트 구독 — server-exporter 미사용
- **action**: 등재만 — 영향 없음

### 적용 대상 (다음 세션)

| Ticket | 우선 | 작업 |
|---|---|---|
| F80 | P1 | EXTERNAL_CONTRACTS.md DMTF spec 연도별 매트릭스 |
| F81 | P1 | ThermalSubsystem fallback (thermal 섹션 진입 시) |
| F82 | P2 | X-Auth-Token 도입 (운영 부하 신호 시) |
| F83 | P1 | redfish_gather.py "GET only" + If-Match 미사용 주석 |
| F84 | P1 | SSLContext min/max version 검증 + TLS 1.3 회귀 |
| F85 | P2 | HTTP 헤더 사용자 사이트 우선 (rule 25 R7-A-1) |
| F86 | P3 | IPv6 듀얼스택 검증만 |
| F87 | P3 | OEM Action read-only 주석 |
| F88 | P3 | ServiceRoot 변종 cover 등재만 |
| F89 | P3 | nextLink pagination 검증 |
| F90 | P3 | EventService 미사용 등재만 |

---

## 종합 요약

### Ticket 추가 (F41 ~ F90 — 50건)

| 우선 | 건수 | 영역 |
|---|---|---|
| P1 (HIGH) | 12 | Dell iDRAC10 / HPE iLO7 / Lenovo XCC3 / Supermicro X12-X14 / Cisco UCS X-Series + M8 / DMTF / TLS / GET-only |
| P2 (MED) | 26 | 신 endpoint 호환성 / 새 데이터 영역 분리 / 보안 패치 등재 |
| P3 (LOW) | 12 | 검증만 / 등재만 / generic fallback cover |

### 호환성 사고 사전 차단 효과

7-loop 검색 결과:
1. **현재 cover**: 41건 (A~M 카테고리, 이미 적용)
2. **신규 발견 호환성 영역**: 50건 (F41~F90, 다음 세션)
3. **호환성 영역 외 (새 데이터)**: ~15건 — 별도 cycle

### 다음 세션 첫 우선순위 (P1 12건)

1. **F41** Dell iDRAC10 adapter — PowerEdge 17G 신규 출하
2. **F47** HPE iLO 7 adapter — Gen12 (2025-02 출시)
3. **F48** NetworkPorts → EthernetInterface fallback (HPE)
4. **F55** Lenovo XCC3 adapter — ThinkSystem V4
5. **F56** XCC2 vs XCC3 capabilities 매트릭스
6. **F61** Supermicro X12 / X13 / X14 adapter (3개)
7. **F68** Cisco M5~M8 capabilities 확장
8. **F69** Cisco UCS X-Series standalone CIMC adapter
9. **F80** EXTERNAL_CONTRACTS.md DMTF spec 매트릭스
10. **F81** ThermalSubsystem fallback (향후 thermal 진입 시)
11. **F83** redfish_gather.py "GET only" 명시
12. **F84** SSLContext min/max version + TLS 1.3 회귀

### 사용자 결정 대기

- **F74~F77 신규 vendor** (Huawei / Inspur / Fujitsu / Quanta) — 운영 사이트 도입 신호 후 P1 격상

### 권고 작업 순서

```
Phase 1 (호환성 P1, 다음 세션):
  F83 (read-only 주석) → F84 (TLS 검증) → F48 (NetworkPorts fallback)

Phase 2 (신 generation adapter, 다음 세션):
  F41 (iDRAC10) → F47 (iLO7) → F55 (XCC3) → F61 (X12-X14) → F68/F69 (Cisco M8 / X-Series)

Phase 3 (정합 / 매트릭스):
  F56 (XCC2 vs XCC3) → F80 (DMTF 매트릭스) → F88 (ServiceRoot 변종) → F89 (pagination)

Phase 4 (사용자 결정):
  F74~F77 vendor 도입 의향 확인 → 승인 시 9단계 절차 (rule 50 R2)
```

---

## 갱신 history

- 2026-05-01: 7-loop web compatibility audit 완료. F41~F90 신규 50건 ticket 추가.
- 사용자 명시 (2026-05-01): 다음 세션에서 작업. 본 cycle 은 ticket 등재만.







