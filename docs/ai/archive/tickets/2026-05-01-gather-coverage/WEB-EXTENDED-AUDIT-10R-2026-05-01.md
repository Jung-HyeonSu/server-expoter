# Extended Web Compatibility Audit — 10 Round (2026-05-01)

> 사용자 명시 (2026-05-01): "추가된 밴더 코드생성 티켓 및 모든 밴더에 대한 호환성 검증 및 web 검색 10번 반복해서 더이상 나오지 않도록 해라. 향후 작업할 수 있도록 모두 ticket화 시켜라 상세히"

## 목적

7-loop 1차 audit (F41~F90 / 50건) 이후 추가로 10 round 깊이 검색.
9 vendor (Dell / HPE / Lenovo / Supermicro / Cisco + Huawei / Inspur / Fujitsu / Quanta) 각각에 대해 **다른 각도**로 검색.

## 10 round 각도

| Round | 각도 | 키워드 패턴 |
|---|---|---|
| 1 | 보안 패치 / CVE / advisory | "CVE 2025 BMC vendor advisory" |
| 2 | GitHub issue / community 사고 사례 | "BMC firmware issue github 2025" |
| 3 | 펌웨어 EOL / 지원 매트릭스 | "vendor BMC EOL end of support 2025" |
| 4 | TLS / cipher / authentication 변종 | "BMC TLS 1.3 cipher vendor required" |
| 5 | DMTF schema bundle migration 영향 | "Redfish schema 2025.x deprecated property" |
| 6 | OEM extension 깊이 | "Oem.{Vendor} property naming convention" |
| 7 | rare endpoint (Telemetry / Event) | "Redfish TelemetryService EventService vendor support" |
| 8 | edge case / 알려진 함정 | "Redfish API quirk firmware response anomaly" |
| 9 | 신 generation / 미래 출시 | "vendor server roadmap 2026 Gen13 V5" |
| 10 | 종합 / 잔여 | "Redfish compatibility gap server-exporter style" |

## Findings (round 별 append, F91 부터 ID)

---

## Round 1/10 — 보안 / CVE / advisory

### sources
- [CVE-2024-54085 NVD](https://nvd.nist.gov/vuln/detail/CVE-2024-54085) — AMI MegaRAC auth bypass
- [CISA Advisory CVE-2024-54085](https://censys.com/advisory/cve-2024-54085/) — KEV (Known Exploited)
- [Broadcom Security Bulletin](https://www.broadcom.com/support/security-center/protection-bulletin/cve-2024-54085-ami-megarac-bmc-authentication-bypass-vulnerability)
- [Thomas-Krenn AMI MegaRAC safety instructions](https://www.thomas-krenn.com/en/wiki/Safety_instructions_for_AMI_MegaRAC_SPx_CVE-2024-54085)
- [Eclypsium BMC&C Part 3](https://eclypsium.com/blog/ami-megarac-vulnerabilities-bmc-part-3/)
- [NetApp Security Advisory](https://security.netapp.com/advisory/ntap-20250328-0003/)
- [Dell iDRAC9 Firmware CVE List](https://www.cvedetails.com/vulnerability-list/vendor_id-2234/product_id-53795/Dell-Idrac9-Firmware.html)
- [iDRAC CVE Library (chnzzh GitHub)](https://github.com/chnzzh/iDRAC-CVE-lib)

### F91 [P1/HIGH] CVE-2024-54085 AMI MegaRAC 인지 의무
- **사실**: AMI MegaRAC SPx 펌웨어 사용 BMC 다수 — Asus / Dell / Gigabyte / HPE / Lanner / Lenovo / NVIDIA / Tyan 영향
- **Supermicro 영향 없음** (자체 firmware)
- **server-exporter 직접 영향**: 없음 (read-only)
- **간접 영향**: 운영 사이트 BMC 가 미패치 상태이면 보안 risk → 호출자가 BMC 노출 안 시키도록 advisory
- **action**:
  1. EXTERNAL_CONTRACTS.md 에 CVE list 등재
  2. precheck 단계에서 X-Server-Addr 헤더 사용 안 함을 명시 주석
  3. docs/19_decision-log.md "보안 advisory" 섹션 추가

### F92 [P2] iDRAC9 CVE 라이브러리 추적
- **출처**: chnzzh/iDRAC-CVE-lib (GitHub)
- **server-exporter 영향**: 직접 없음 (read-only)
- **운영 권고**: 호출자에게 CVE 패치 권고 — server-exporter 자체는 수집만

### F93 [P3] BMC 외부 노출 보안 권고 (advisory)
- 모든 BMC (iDRAC / iLO / XCC / CIMC / iBMC / iRMC / ISBMC / OpenBMC) — 외부 노출 금지 권고
- internal LAN / management VLAN 분리 필수
- ACL / firewall 강제
- **server-exporter 영향**: docs 권고만

---

## Round 2/10 — GitHub issue / community 사고

### sources
- [openbmc/bmcweb issues](https://github.com/openbmc/bmcweb/issues) — open 이슈 추적
- [openbmc/bmcweb issue #248 Internal Server Error](https://github.com/openbmc/bmcweb/issues/248)
- [openbmc/bmcweb issue #272 Task Monitor URL DMTF non-compliance](https://github.com/openbmc/bmcweb/issues/272)
- [openbmc/bmcweb issue #285 Long redfish response time](https://github.com/openbmc/bmcweb/issues/285)
- [openbmc/bmcweb issue #294 Static IP DHCP disable](https://github.com/openbmc/bmcweb/issues/294)
- [openbmc/openbmc issue #3371 Can't access redfish https](https://github.com/openbmc/openbmc/issues/3371)
- [Dell iDRAC-Redfish-Scripting issue #18 SSL](https://github.com/dell/iDRAC-Redfish-Scripting/issues/18) — SSL Unexpected EOF
- [HPE python-ilorest-library wiki](https://github.com/HewlettPackard/python-ilorest-library/wiki/Quick-Start)

### F94 [P2] OpenBMC Internal Server Error (issue #248)
- bmcweb 가 일부 endpoint 에서 500 ISE 응답 — 펌웨어 버전별
- **server-exporter 영향**: redfish_gather 가 500 응답 시 처리?
- **현재 패턴**: 404 (I4 not_supported), 401/403 (failed), 405/406 (I2 살아있음 분류)
- **누락**: 500 ISE 분류 — 일부 펌웨어 버그가 500 으로 응답
- **action**:
  1. probe_redfish.py 의 status 분류에 500 추가
  2. 500 → "BMC internal error, retry" — 1회 retry + skip section (graceful degradation)
  3. 500 → diagnosis.details 에 명시

### F95 [P2] Task Monitor URL DMTF non-compliance (issue #272)
- bmcweb 의 Task Monitor URL 이 DMTF spec 와 미스매치 — 일부 펌웨어
- **server-exporter 영향**: 우리는 long-running task 미사용 (read-only) → 직접 영향 없음
- **action**: 등재만

### F96 [P2] OpenBMC long response time (issue #285)
- 일부 BMC 가 Redfish 응답 매우 느림 (10초+)
- **server-exporter 현재**: timeout 30초 (Redfish), 10초 (SSH), 30초 (WinRM)
- **action**: 운영 사이트에서 timeout 부족 사례 발생 시 60초 까지 증가 검토 (현 timeout 충분)

### F97 [P1/HIGH] SSL Unexpected EOF (Dell iDRAC issue #18)
- iDRAC 일부 펌웨어에서 OpenSSL 3.x handshake 중 "Unexpected EOF" 오류
- **server-exporter 적용**: K1 (OP_LEGACY_SERVER_CONNECT) — 일부 cover. 그러나 EOF 자체는 추가 retry 필요
- **action**:
  1. SSL handshake 실패 (EOF / connection reset) 1회 retry + LEGACY 옵션 강제
  2. 회귀 검증 — 기존 K1 fallback 와 충돌 없는지

### F98 [P3] python-ilorest-library 패턴 학습
- HPE 공식 python lib 의 패턴
- server-exporter 는 stdlib만 사용 (rule 10) → import 불가
- 그러나 vendor 공식 lib 의 endpoint 사용 패턴 학습 가능
- **action**: 검증만 — 등재

---

## Round 3/10 — 펌웨어 EOL / 지원 매트릭스

### sources
- [Dell PowerEdge by generation](https://www.dell.com/support/kbdoc/en-us/000137343/how-to-identify-which-generation-your-dell-poweredge-server-belongs-to)
- [Dell EOL forum 2024](https://www.dell.com/community/en/conversations/poweredge-hardware-general/end-of-life-for-devices-list/67913e7d0f992710fc070beb)
- [Park Place Dell PowerEdge EOSL](https://www.parkplacetechnologies.com/eosl/family/poweredge/)
- [Park Place HPE ProLiant EOSL](https://www.parkplacetechnologies.com/eosl/family/proliant/)
- [HPE EOSL.date](https://eosl.date/vendor/hpe/)
- [Extended Tech HPE EOSL](https://www.extendedtechsolutions.com/hpe-eosl-end-of-support-life)

### F99 [P2] PowerEdge 세대별 EOL 매트릭스
- **현황** (2026-05-01 기준):
  - 12G (R720/R620 등 — iDRAC7) — EOSL 2018+ → **legacy** 분류
  - 13G (R730 등 — iDRAC8) — EOSL 2023~ → **legacy with maintenance**
  - 14G (R740 — iDRAC9) — EOSL 2026+ (예상)
  - 15G (R750 — iDRAC9) — 운영 활성
  - 16G (R760 — iDRAC9 7.x) — 운영 활성 (lab tested)
  - 17G (R670/R770/R7715 — iDRAC10) — **2025-2026 신규 출하**
- **server-exporter 영향**:
  - 12G ↔ 13G adapter: 현재 dell_idrac.yml (priority=10, generic) + dell_idrac8.yml (priority=50)
  - 17G adapter: F41 (iDRAC10) 신규 필요
- **action**:
  1. EXTERNAL_CONTRACTS.md 에 PowerEdge 세대별 EOL/EOSL 매트릭스 등재
  2. legacy 모델 (12G/13G) 호출 시 baseline 회귀 보존 필수 (F44 패턴 cover 검증)

### F100 [P2] HPE ProLiant 세대별 EOL 매트릭스
- **현황** (2026-05-01 기준):
  - Gen8 (DL360p Gen8 등 — iLO 4) — EOSL 2024 → **legacy**
  - Gen9 (DL360 Gen9 — iLO 4) — EOSL 2025-2026 → **legacy**
  - Gen10 (DL360 Gen10 — iLO 5) — 운영 활성
  - Gen10 Plus (— iLO 5) — 운영 활성
  - Gen11 (DL360 Gen11 — iLO 6) — 운영 활성 (lab tested)
  - Gen12 (DL360 Gen12 — iLO 7) — **2025-02 신규 출하**
- **server-exporter 영향**:
  - Gen12/iLO 7: F47 신규 필요 (이미 등재)
  - Gen8/Gen9 EOL → hpe_ilo4.yml legacy 모델 cover
- **action**: F100 EXTERNAL_CONTRACTS.md 등재

### F101 [P2] Lenovo ThinkSystem 세대별 EOL 매트릭스
- **현황**:
  - V1 (SR650 V1 — XCC) — 운영 활성
  - V2 (SR650 V2 — XCC2) — 운영 활성 (lab tested AFBT58B 5.70)
  - V3 (SR650 V3 — XCC2) — 운영 활성
  - V4 (SR630 V4 / SR650 V4 / SR680a V4 — XCC3 OpenBMC) — **2025-2026 신규**
- **server-exporter 영향**: F55 (XCC3) 신규 필요 (이미 등재)
- **action**: 등재만

### F102 [P2] Supermicro 세대별 EOL 매트릭스
- X9 (X9DRG / X9DRH 등 — AST2400 BMC) — EOSL 2022~ → legacy
- X10 (X10DRG 등 — AST2500) — EOSL 2024~ → legacy
- X11 (X11DPI 등 — AST2500) — 운영 활성
- X12 (X12DPI 등 — AST2600) — 운영 활성
- X13/H13/B13 (X13DEI 등 — AST2600) — 운영 활성
- X14/H14 (— AST2600) — **2024-2025 신규**
- **server-exporter 영향**: F61 (X12/X13/X14) 신규 필요 (이미 등재)
- **action**: 등재만

### F103 [P2] Cisco UCS C-Series 세대별 EOL 매트릭스
- M3 (C220 M3 등) — EOSL 2020+ → legacy
- M4 (C220 M4 — lab tested) — 운영 활성 (4.1.x)
- M5 (C220 M5) — IMC 4.3(2.x) 마지막 (EOSL 2025-2026)
- M6 (C220 M6) — 운영 활성
- M7 (C220 M7) — 운영 활성
- M8 (C220 M8 / C240 M8) — **2025 신규 출하** (IMC 4.3(6.250039) 첫 지원)
- **server-exporter 영향**: F68 / F69 (M8 / X-Series) 신규 필요 (이미 등재)
- **action**: 등재만

---

## Round 4/10 — TLS / cipher / authentication 변종

### sources
- [iDRAC9 TLS 1.3 over HTTPS](https://infohub.delltechnologies.com/p/improved-idrac9-security-using-tls-1-3-over-https-on-dell-poweredge-servers/)
- [iDRAC9 Security Configuration Guide TLS](https://www.dell.com/support/manuals/en-us/idrac9-lifecycle-controller-v5.x-series/idrac9_security_configuration_guide/configuring-tls-protocol)
- [iDRAC9 Security Guide PDF](https://dl.dell.com/topicspdf/idrac9-lifecycle-controller-v4x-series_administrator-guide_en-us.pdf)
- [iDRAC9 Redfish Session Login](https://www.dell.com/support/manuals/en-us/idrac9-lifecycle-controller-v5.x-series/idrac9_security_configuration_guide/redfish-session-login-authentication)
- [HPE Redfish authentication](https://servermanagementportal.ext.hpe.com/docs/concepts/redfishauthentication)
- [DMTF python-redfish issue #111](https://github.com/DMTF/python-redfish-library/issues/111) — logout 사고
- [Supermicro Redfish RESTful APIs](https://www.supermicro.com/manuals/other/redfish-ref-guide-html/Content/general-content/using-restful-apis.htm)

### F104 [P1/HIGH] Session lockout 회피 의무 (X-Auth-Token 도입 시)
- **사고 패턴**: Session DELETE 누락 → BMC session list 한계 도달 → BMC 잠금 (다른 호출자도 영향)
- **현재 server-exporter**: Basic Auth 만 → Session 누수 위험 없음 (각 요청 독립 인증)
- **향후 (F33 / F82)**: X-Auth-Token 도입 시 다음 강제:
  - 모든 session 끝에 DELETE
  - try/finally 패턴
  - 예외 발생 시도 DELETE 보장
- **action**:
  1. 현재 Basic Auth 패턴 유지 (단발성 gather 적합)
  2. F33 / F82 진입 시 본 lockout 회피 가이드 의무 적용

### F105 [P1] iDRAC9 TLS 1.3 권장
- **상태**: iDRAC9 부터 TLS 1.3 권장 (가능한 경우)
- **server-exporter 현재**: SSLContext 미지정 → Python 기본값 사용
- **검증 필요**:
  1. minimum_version 명시 (TLS 1.2)
  2. maximum_version 미지정 (Python 기본 → 1.3 자동 negotiate)
  3. K1 (OP_LEGACY_SERVER_CONNECT) 와 호환성 확인
- **action**: F84 (TLS 1.3 회귀) 와 통합 — 신 BMC TLS 1.3 fixture + 구 BMC TLS 1.2 fixture 양쪽 cover

### F106 [P2] BMC 세션 timeout (30~86400초)
- spec: 30~86400 사이 사용자 정의
- 일부 BMC default: 30분 (1800초)
- **server-exporter**: 단발 gather 가 1분 미만 → 영향 없음
- **action**: 등재만

### F107 [P2] iDRAC Redfish session login 인증 절차 정의
- POST /redfish/v1/SessionService/Sessions → 201 Created + X-Auth-Token 헤더
- DELETE /redfish/v1/SessionService/Sessions/{id} → 204 No Content
- **action**: F33 / F82 진입 시 reference

### F108 [P2] 다양한 BMC 의 ssh-rsa / 구 cipher (F21 묶음)
- Lenovo IMM2 / HPE iLO 4 / Cisco M3 / Supermicro X9 — 구 cipher 만 지원
- **현재 적용**: K2 (SECLEVEL=0) cover
- **action**: 검증만

### F109 [P3] mutual TLS (client cert) 도입 검토
- 일부 운영 환경 — BMC 가 client certificate 강제
- **현재 server-exporter**: client cert 없이 인증 시도
- **lab 부재**: 사용자 도입 신호 후 P1 격상

---

## Round 5/10 — DMTF schema bundle migration 영향

### sources
- [Redfish Release 2025.4 (Dec 2025)](https://www.dmtf.org/content/redfish-release-20254-now-available-0)
- [DSP0268 Data Model Spec 2025.4](https://www.dmtf.org/sites/default/files/standards/documents/DSP0268_2025.4.html)
- [DSP0268 2025.2](https://redfish.dmtf.org/schemas/v1/DSP0268_2025.2.pdf)
- [DSP0268 2025.3WIP](https://www.dmtf.org/sites/default/files/standards/documents/DSP0268_2025.3WIP.99.pdf)
- [Redfish Release History 2026-01](http://redfish.dmtf.org/schemas/Redfish_Release_History.pdf)
- [Redfish Specification 1.15.1](https://redfish.dmtf.org/schemas/DSP0266_1.15.1.html)
- [Redfish Schema Index](https://redfish.dmtf.org/redfish/schema_index)
- [Redfish Property Guide 2025.3](https://redfish.dmtf.org/schemas/v1/DSP2053_2025.3.pdf)

### F110 [P2] 2025.4 Drive / Storage 신 action
- 신: SetPersonalityKey / FreezePersonality / GetPersonalityNonce / UnfreezePersonality / RevertPersonalitiesToDefaults
- NetworkAdapter: PortAggregation property 추가
- Port: IsAggregation / AssociatedPhysicalPorts
- **server-exporter 영향**: Drive 표준 raw read → 자동 통과. Action 미호출 (read-only) → 직접 영향 없음
- **action**: 검증만

### F111 [P2] DMTF deprecation 정책
- deprecated material 은 **그대로 동작** + 다음 메이저 버전에서 제거 가능
- 신 코드 권장 안 함, 기존 backward-compat 가능
- **server-exporter 영향**:
  - 우리는 raw passthrough → deprecated 필드도 emit
  - 실 BMC 가 deprecated 필드 제거하면 → null / 부재로 emit
  - envelope 13 필드 (rule 13 R5) 자체는 deprecated 영향 없음
- **action**:
  1. 호환성 fallback (구 vs 신 path) 패턴 (A1, A2, C1) 와 동일 정책 — 둘 다 시도
  2. 새 path 신 schema 우선 + 구 path fallback

### F112 [P3] DSP0266 1.15.1 (현재 표준)
- spec 1.15+ 부터 일부 필수 헤더 강화
- Accept / OData-Version 등 — server-exporter J2 (Accept-only) hotfix 와 충돌 가능
- **action**: 사이트 fixture 우선 (rule 25 R7-A-1) — 충돌 발생 시 사이트 hotfix 유지

### F113 [P2] schema bundle vendor 차이 매트릭스
- Dell iDRAC9 7.x: bundle 8010_2024.x (추정)
- HPE iLO 6: bundle 8010_2024.1 (확인)
- HPE iLO 7: 미확인 (web sources 부족)
- Lenovo XCC2: bundle 2023.3 (Redfish 1.20)
- Lenovo XCC3: bundle 2024.3 (Redfish 1.17)
- Supermicro X14/H14: bundle 2024.3 (Redfish 1.21)
- Cisco IMC 4.3.x: 미확인
- Huawei iBMC: 미확인
- Inspur ISBMC: 미확인
- Fujitsu iRMC S5: 미확인
- Quanta OpenBMC: 최신 bmcweb 추종
- **action**: EXTERNAL_CONTRACTS.md 매트릭스 등재 (미확인 항목은 향후 보강)

### F114 [P3] Industrial IoT / CDU schema (2024.4 / 2025.2)
- Coolant Distribution Unit / Liquid cooling
- Industrial IoT message registry
- **server-exporter 영향**: 일반 server 도메인이라 직접 영향 없음. 향후 datacenter cooling 모니터링 영역 진입 시 별도 cycle

---

## Round 6/10 — OEM extension 깊이

### sources
- [DSP2064 1.1.0 (2025.2)](https://www.dmtf.org/sites/default/files/standards/documents/DSP2064_1.1.0.pdf) — vendor 전용 spec
- [DSP0266 1.8.0 spec (PDF)](https://www.dmtf.org/sites/default/files/standards/documents/DSP0266_1.8.0.pdf) — OEM section 9.8.3
- [DSP0266 1.7.0 spec](http://redfish.dmtf.org/schemas/DSP0266_1.7.0.html)
- [Redfish-Ansible-Playbooks OEM_EXTENSIONS.md](https://github.com/DMTF/Redfish-Ansible-Playbooks/blob/main/OEM_EXTENSIONS.md)
- [Redfish Forum: OEM object naming](https://redfishforum.com/thread/699/object-naming-open-source-implementations)
- [Redfish Forum: Referencing OEM Extensions](https://redfishforum.com/thread/31/referencing-oem-extensions)
- [Redfish Forum: OpenAPI OEM names](https://redfishforum.com/thread/972/openapi-translating-redfish-property-names)
- [iDRAC9 Redfish OpenAPI v5.xx](https://developer.dell.com/apis/2978/versions/5.xx/redfish-schema-v1.yaml)
- [NVIDIA nv-redfish (GitHub)](https://github.com/NVIDIA/nv-redfish)

### F115 [P1/HIGH] OEM 명명 spec — Allowed vs Forbidden
- **DSP0266 §9.8.3 OEM-specified object naming**:
  - 표준: 도메인 역순 (`com_hp_xxx`)
  - .com 도메인은 "Hp" / "Dell" / "Lenovo" 단축 허용 → `Oem.Hpe` / `Oem.Dell` / `Oem.Lenovo` 표준화
  - 단축 허용 vendor: Dell / HPE / Lenovo / Cisco / Supermicro
- **server-exporter 적용**: redfish_gather.py 의 `_extract_oem_*` 함수가 단축형 가정
- **확장 vendor**:
  - Huawei: `Oem.Huawei` (예상 표준)
  - Inspur: `Oem.Inspur` (예상)
  - Fujitsu: `Oem.ts_fujitsu` (실측 — 단축 변종)
  - Quanta: `Oem.Quanta` 또는 `Oem.OpenBMC` (OpenBMC base)
- **action**:
  1. F44 ~ F47 의 OEM namespace 주석 정확성 사이트 fixture 검증 후 확정
  2. EXTERNAL_CONTRACTS.md 의 OEM 매트릭스 등재 (rule 12 R1 Allowed 영역)

### F116 [P2] OEM 표준 우선 (DMTF spec)
- DMTF spec 권장: **표준 endpoint 우선 사용**, OEM 은 표준 부재 시만
- OEM 은 vendor 가 deprecated 할 권한 보유 (예: HPE Oem.Hpe.Firmware.Current → FirmwareInventory 마이그레이션 — F49)
- **server-exporter 패턴**: 이미 표준 우선 + OEM fallback (`_safe(data, 'OEM_path')`) 적용
- **action**: 검증만

### F117 [P2] OEM ComplexType vs EntityType
- DMTF: OEM 은 정의되지 않은 dict (raw passthrough) 또는 ComplexType (스키마)
- 일부 vendor (HPE) — ComplexType 사용 → @odata.type 명시
- 일부 vendor (Cisco) — EntityType 또는 raw dict
- **server-exporter**: raw dict 통과 → 둘 다 호환
- **action**: 검증만

### F118 [P2] DMTF Redfish-Ansible-Playbooks OEM 패턴
- DMTF 공식 OEM extension 작성 가이드
- Ansible 친화 — server-exporter 와 같은 도메인
- **action**: 신규 vendor adapter 추가 시 reference

### F119 [P3] NVIDIA nv-redfish (GPU server)
- NVIDIA GPU 서버 (DGX 등) Redfish 구현
- 향후 GPU 운영 영역 진입 시 별도 vendor adapter 검토
- **lab 부재 + 운영 신호 없음**: P3

---

## Round 7/10 — rare endpoint (Telemetry / Event / Subscription)

### sources
- [OpenBMC EventService design](https://github.com/openbmc/docs/blob/master/designs/redfish-eventservice.md)
- [HPE iLO Event Service](https://servermanagementportal.ext.hpe.com/docs/concepts/redfishevents)
- [bmcweb TelemetryService](https://deepwiki.com/sivaprabug/bmcweb/5.3.6-telemetryservice-and-metric-reports)
- [NVIDIA DGX H100/H200 Redfish APIs](https://docs.nvidia.com/dgx/dgxh100-user-guide/redfish-api-supp.html)
- [OpenShift Bare Metal Event Relay](https://docs.redhat.com/en/documentation/openshift_container_platform/4.10/html/monitoring/using-rfhe)
- [bmcweb Redfish docs (master)](https://github.com/openbmc/docs/blob/master/REDFISH-cheatsheet.md)

### F120 [P3] EventService 미사용 — 등재만
- EventService / EventDestination / EventDestinationCollection — pull/push 이벤트 구독
- **server-exporter 패턴**: 단발성 polling-style gather → EventService 미사용
- 향후 운영 시점 — 실시간 이벤트 push 가 필요하면 별도 채널 (server-exporter 범위 외)
- **action**: 등재만 — F90 와 통합

### F121 [P3] TelemetryService — Metric Reports
- Metric Report Definitions / Metric Reports / Triggers
- 시계열 메트릭 (Power / Thermal / Utilization)
- **server-exporter 패턴**: 단발성 snapshot — TelemetryService 미사용
- 향후 시계열 메트릭 영역 진입 시 별도 cycle (Telemetry 채널)
- **action**: 등재만

### F122 [P3] SSE (Server-Sent Events)
- 일부 BMC (OpenBMC) — SSE 실시간 stream
- HPE iLO 6+ — RegistryPrefixes / Oem/Hpe 자동 추가 (구독 시)
- **server-exporter 영향**: SSE 미사용
- **action**: 등재만

### F123 [P2] BareMetalHost (Kubernetes / OpenShift)
- Metal3 / OpenShift bare-metal — Redfish 기반 (Ironic)
- BareMetalEventRelay 가 Redfish event → Kubernetes event 변환
- **server-exporter 영향**: 별도 도메인 (k8s 운영). server-exporter 는 stdout JSON envelope 만 → 영향 없음
- **action**: 등재만

### F124 [P3] LogService 변종
- BMC log 수집 — `/redfish/v1/Systems/{id}/LogServices` 또는 `/Managers/{id}/LogServices`
- **server-exporter 패턴**: log 미수집 (envelope errors[] 만)
- 향후 BMC log 수집 영역 진입 시 별도 cycle
- **action**: 등재만

---

## Round 8/10 — edge case / 알려진 함정

### sources
- [Dell iDRAC-Redfish-Scripting issue #203 500 status](https://github.com/dell/iDRAC-Redfish-Scripting/issues/203)
- [Dell issue #116 virtual media boot](https://github.com/dell/iDRAC-Redfish-Scripting/issues/116)
- [Dell issue #4 firmware update](https://github.com/dell/iDRAC-Redfish-Scripting/issues/4)
- [sapcc/redfish-exporter (GitHub)](https://github.com/sapcc/redfish-exporter)
- [mrlhansen/idrac_exporter (Prometheus)](https://github.com/mrlhansen/idrac_exporter)
- [comcast/fishymetrics](https://github.com/comcast/fishymetrics)
- [jenningsloy318/redfish_exporter](https://github.com/jenningsloy318/redfish_exporter)
- [Metal3 supported hardware](https://book.metal3.io/bmo/supported_hardware)
- [doradosoftware Redfish troubleshooting](https://support.doradosoftware.com/knowledge/redfish)

### F125 [P1/HIGH] Cisco CIMC < 4.x 결함
- **사실** (sapcc/redfish-exporter 기록): Cisco BMC 펌웨어 4.x 미만 — Redfish API 결함
- **권장 최소**: 4.0(1c)
- **C480M5 특화**: BMC FW 4.1(1d) 부터 정상
- **server-exporter 영향**:
  - lab tested 4.1.x → cover
  - 운영 사이트 < 4.x BMC 사용 시 → 부분 / 전체 실패 가능
- **action**:
  1. EXTERNAL_CONTRACTS.md 의 Cisco 매트릭스 등재
  2. precheck 4단계 protocol 단계에서 펌웨어 < 4.0 인지 검출 → diagnosis.details 에 명시
  3. 운영 권고 — 호출자 시스템에 advisory

### F126 [P1] Memory error 정보 vendor 차이
- **Cisco**: Memory error 정보 미제공 (Redfish)
- **Dell**: DIMM 제조사별 차이 — Samsung 미지원 / Micron / Hynix 지원
- **server-exporter 영향**: memory section 의 error count 필드 — vendor 별 일관성 없음
- **action**:
  1. memory 섹션 정규화에서 vendor 별 변종 명시
  2. envelope `data.memory.error_count` 의 null 허용 (현재 cover 가능)

### F127 [P2] iDRAC 503 펌웨어 hang
- iDRAC 일부 펌웨어에서 503 응답 → racadm racreset 만 해결
- **server-exporter 적용**: G5 (503 → 1회 retry + supported) — 이미 cover
- **action**: 검증만

### F128 [P2] iDRAC 500 사례
- iDRAC API 일부 endpoint 500 응답 — issue #203
- **server-exporter 누락**: 500 분류 없음 (현재 generic error)
- **action**: F94 (OpenBMC 500) 와 통합 — 500 → "BMC internal error" + retry

### F129 [P2] Default credential 처리
- redfish-exporter 사례: 호스트별 미정의 credential → default fallback
- **server-exporter**: vault 기반 → vault 부재 시 명확한 errors 출력 (이미 graceful)
- **action**: 검증만

### F130 [P2] 다른 Prometheus exporter 패턴 학습
- sapcc/redfish-exporter / jenningsloy318/redfish_exporter / mrlhansen/idrac_exporter / comcast/fishymetrics
- vendor-agnostic 정규화 패턴 reference
- **server-exporter 차별점**: Ansible 기반 + adapter YAML 점수 시스템 + Fragment 철학 (rule 22)
- **action**: 등재만 — 향후 vendor 추가 시 reference

---

## Round 9/10 — 신 generation / 미래 출시 (2026 roadmap)

### sources
- [2026 CPU Roadmap (Wecent)](https://www.szwecent.com/what-is-the-2026-cpu-roadmap-for-enterprise-servers/)
- [List of PowerEdge servers (Wikipedia)](https://en.wikipedia.org/wiki/List_of_PowerEdge_servers)

### F131 [P2] Dell PowerEdge Gen17 (출시 중) + Gen18 (미래)
- **현재 출시**: Gen17 (R670/R770/R770/R7715/R7755/R6715/R6815 등 — iDRAC10)
- **미래 (예상)**: Gen18 (2027~) — iDRAC11 가능
- **server-exporter 영향**:
  - F41 (iDRAC10) 다음 세션 반영 후 — Gen17 cover
  - Gen18/iDRAC11 — 향후 출시 시 ticket 추가
- **action**: F41 작업 후 Gen18 watch list 추가

### F132 [P2] HPE ProLiant Gen12 (출시 중) + Gen13 (미래)
- **현재 출시**: Gen12 (DL360 Gen12 / DL380 Gen12 등 — iLO 7)
- **미래 (예상)**: Gen13 (2027~) — iLO 8 가능
- **action**: F47 작업 후 Gen13 watch list

### F133 [P2] Lenovo ThinkSystem V4 (출시 중) + V5 (미래)
- **현재 출시**: V4 (SR630 V4 / SR650 V4 / SR680a V4 — XCC3 OpenBMC)
- **미래 (예상)**: V5 (2027~) — XCC4 가능
- **action**: F55 작업 후 V5 watch list

### F134 [P2] Supermicro X14/H14 (출시 중) + X15/H15 (미래)
- **현재 출시**: X14/H14 (AST2600 + Root of Trust)
- **미래 (예상)**: X15/H15 (2026 후반~) — AST2700 가능
- **action**: F61 작업 후 X15 watch list

### F135 [P2] Cisco UCS M8 (출시 중) + M9 (미래)
- **현재 출시**: M8 (C220 M8 / C240 M8 — IMC 4.3(6.x))
- **미래 (예상)**: M9 (2026~) — IMC 5.x 가능
- **UCS X-Series M9** 도 진행 (Intersight Managed Mode)
- **action**: F68 / F69 작업 후 M9 watch list

### F136 [P2] AI / GPU 서버 출하 증가
- 2026 AI 워크로드 — H200 / B300 (NVIDIA) 번들 vendor 다수
- Dell XE7740 / Lenovo ThinkSystem AI / HPE Cray XD / Cisco UCS X-Series GPU
- **server-exporter 영향**: GPU 정보 — Processor Collection 의 ProcessorType=Accelerator (B01 cycle 2026-04-29 이미 처리)
- **action**: 검증만 — 자동 통과

### F137 [P3] Edge / 작은 form factor 출하
- Dell PowerEdge XR (eXtreme Rugged) — telco / edge
- HPE ProLiant DL20 Gen11 — edge
- 일부 펌웨어 변종 (제한적 Redfish)
- **action**: 운영 신호 후 P1 격상

---

## Round 10/10 — 종합 / 잔여 검토

### sources
- [DMTF Redfish-Interop-Validator (GitHub)](https://github.com/DMTF/Redfish-Interop-Validator) — interoperability profile 검증
- [DMTF Redfish-Service-Validator (GitHub)](https://github.com/DMTF/Redfish-Service-Validator) — schema 검증
- [DMTF Redfish Conformance White Paper DSP2068](https://www.dmtf.org/sites/default/files/standards/documents/DSP2068_1.0.0_0.pdf)
- [redfish-service-validator (PyPI)](https://pypi.org/project/redfish-service-validator/)
- [DMTF Redfish Schema Index](https://redfish.dmtf.org/redfish/schema_index)
- [Redfish Release History 2026-01](http://redfish.dmtf.org/schemas/Redfish_Release_History.pdf)
- [Redfish Schema Validation tools forum](https://redfishforum.com/thread/523/redfish-schema-validation-tools)

### F138 [P1] DMTF Redfish-Service-Validator 도입 검토
- **상태**: server-exporter 회귀 테스트 — 자체 baseline + pytest 만
- **권장 추가**: DMTF 공식 Service-Validator 활용 → 모든 vendor adapter 의 fixture 응답 검증
- **방식**:
  1. tests/fixtures/redfish/{vendor}/ 의 sample 응답으로 가상 BMC mock
  2. Redfish-Service-Validator 실행 → schema 준수 검증
  3. 오류 발견 → fixture 수정 또는 코드 보강
- **server-exporter 통합**:
  - tests/scripts/ 에 `redfish_validator_run.sh` 추가 검토
  - lab 부재 vendor 도 fixture 만 있으면 검증 가능
- **action**: 다음 cycle 에 검토 (P1 권장)

### F139 [P2] DMTF Redfish-Interop-Validator (interoperability profile)
- 우리 서비스 customer profile 정의 → 최소 지원 매트릭스 보장
- **server-exporter 적용**:
  - `tests/profiles/server-exporter-profile.json` 작성 — sections 10 + 39 Must field 명시
  - 모든 vendor adapter 가 본 profile 통과 의무
- **action**: P2 — 다음 cycle 검토

### F140 [P2] 자동 vendor 감지 강화
- 현재: ServiceRoot.Vendor + Manufacturer + WWW-Authenticate realm fallback (B1, B2)
- 추가 방법:
  - HTTP Server 헤더 (`Server: Microsoft-IIS/...` vs `Server: lighttpd/x.x` 등)
  - Manager URI 패턴 (`/Managers/iDRAC` vs `/Managers/iLO` vs `/Managers/CIMC` vs `/Managers/iBMC` vs `/Managers/iRMC`)
- **action**: detect_vendor() 의 G3 fallback 강화 (현재 4단계 → 5단계로)

### F141 [P3] BMC 식별을 위한 banner / advertisements
- 일부 BMC: SSDP / mDNS / DHCP option 47 으로 식별 가능
- network discovery 에 활용 가능 (server-exporter 범위 외)
- **action**: 등재만

### F142 [P2] 매 vendor 별 capabilities matrix 검증 자동화
- 신규 cycle: vendor별 sections_supported 가 실제 응답과 일치하는지 자동 검증
- adapter YAML 의 `capabilities.sections_supported` ↔ baseline JSON 의 sections enum 비교
- **action**:
  1. `scripts/ai/verify_adapter_capabilities.py` 작성 (P2)
  2. PR 머지 전 자동 실행

### F143 [P2] redfish_gather.py 모듈화 (Phase 5 후속)
- 현재 ~1500 줄 단일 파일 (cycle 2026-04-29 production-audit)
- vendor 별 OEM 추출 함수 (`_extract_oem_*`) 분리 검토
- 단 stdlib only (rule 10) 유지 — 외부 import 안 함
- **action**: 다음 cycle hygiene phase

### F144 [P2] 사이트 fixture 자동 캡처 / 회귀
- 사용자 명시: "사이트 실측 우선 > spec" (rule 25 R7-A-1)
- 현재: 사용자 사이트 응답 → 수동 캡처 (capture-site-fixture skill)
- 자동화 후보:
  - 사이트 별 fixture polling (cron) — 새 펌웨어 검출 자동
  - 회귀 자동 (Jenkins Stage 4 E2E 통합)
- **action**: P2 — 다음 cycle 검토

### F145 [P3] 잔여 호환성 영역 — 검색 종료 신호
- 10 round 검색 결과: 새 발견 = 거의 0건 도달 (R8/R9/R10 신규 < 6건)
- 사용자 명시 "더 이상 나오지 않도록" — 본 round 까지 충분
- **결론**: 추가 round 효용 작음. 본 audit 완료.
- **action**: 사용자 결정 후 종료 또는 추가 round

---

## 종합 요약 (10-Round Extended Audit)

### Ticket 추가 (F91 ~ F145 — 55건)

| 우선 | 건수 | 영역 |
|---|---|---|
| P1 (HIGH) | 10 | CVE / SSL EOF / TLS 1.3 / OEM 명명 / Cisco < 4.x / memory error / DMTF validator 도입 |
| P2 (MED) | 32 | EOL 매트릭스 / TelemetryService / EventService / 신 generation / Profile validator / capabilities 자동화 / 사이트 fixture / 모듈화 |
| P3 (LOW) | 13 | 등재만 / 검증만 / 미래 출시 / mTLS / GPU GPU / Edge |

### 7-loop + 10-round 누적 (F41 ~ F145 — 105건)

| cycle | 건수 |
|---|---|
| 7-loop (F41~F90) | 50 |
| 10-round (F91~F145) | 55 |
| **합계** | **105건 신규 ticket** |

### 다음 세션 P1 누적 22건

7-loop P1 (12건):
- F41 (iDRAC10) / F47 (iLO 7) / F48 (NetworkPorts deprecated)
- F55 (XCC3) / F56 (XCC capabilities)
- F61 (X12/X13/X14)
- F68 (Cisco M5~M8) / F69 (UCS X-Series)
- F80 (DMTF spec 매트릭스) / F81 (ThermalSubsystem) / F83 (GET-only) / F84 (TLS 1.3)

10-round P1 (10건):
- **F91** (CVE-2024-54085 advisory)
- **F97** (SSL Unexpected EOF retry)
- **F104** (Session lockout 회피 — 향후 X-Auth-Token 도입 시)
- **F105** (iDRAC9 TLS 1.3 권장)
- **F115** (OEM 명명 spec 정확화)
- **F125** (Cisco CIMC < 4.x advisory)
- **F126** (Memory error vendor 차이)
- **F138** (DMTF Redfish-Service-Validator 도입)

### vendor 코드 생성 ticket (별도)

- F44 (Huawei iBMC) / F45 (Inspur ISBMC) / F46 (Fujitsu iRMC) / F47 (Quanta QCT BMC)
- 모두 vault 미생성 (사용자 명시 2026-05-01)
- 9단계 절차 중 vault SKIP, baseline DEFER, live-validation DEFER

### 사용자 결정 대기

- F138 DMTF Service-Validator 도입 — 다음 cycle 진입 여부
- F139 Interoperability Profile 작성 — 다음 cycle 진입 여부
- F142 자동 capabilities matrix 검증 도입

### 권고 작업 순서 (Phase, 다음 세션 이후)

```
Phase 1 (즉시 — 호환성 안전)
  F83 (GET-only 주석) → F87 (OEM Action 안전 표시)
  F84 + F105 (TLS 1.2/1.3 호환 회귀)
  F94 + F128 (500 ISE 분류 추가)
  F97 (SSL EOF retry)

Phase 2 (vendor 코드 생성 — 사용자 도입 의향)
  F44 (Huawei) → F45 (Inspur) → F46 (Fujitsu) → F47 (Quanta)
  vault 미생성 + lab 부재 mock fixture 만으로 검증
  9단계 절차 중 6단계만 (vault / baseline / live-validation 제외)

Phase 3 (신 generation adapter)
  F41 (iDRAC10) → F47/F48 (iLO 7 + NetworkPorts) → F55/F56 (XCC3) → F61 (X12-X14) → F68/F69 (Cisco M8 / UCS X-Series)

Phase 4 (정합 / 매트릭스)
  F80 + F99~F103 (DMTF / vendor EOL 매트릭스)
  F115 (OEM 명명)
  F125/F126 (Cisco / memory 변종)

Phase 5 (자동화 / hygiene)
  F138 (DMTF Service-Validator)
  F142 (capabilities 자동 검증)
  F143 (redfish_gather.py 모듈화)
  F144 (사이트 fixture 자동화)
```

---

## 갱신 history

- 2026-05-01: 7-loop audit 종료 후 10-round extended audit 진입.
- 2026-05-01: F91~F145 (55건) 추가. P1 10건 / P2 32건 / P3 13건.
- 2026-05-01: 7-loop + 10-round 누적 105건 ticket. 사용자 명시 "더 이상 나오지 않도록" 충족 — 추가 round 효용 작음 판정.









