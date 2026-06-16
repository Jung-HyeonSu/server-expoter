# 2026-06-16 hostname 출처 cross-vendor 매트릭스

## 목적

hostname 우선순위에 BMC `Manager.NetworkProtocol.HostName/FQDN` fallback 을 추가하면서
(System.HostName 부재 시), **다른 벤더/세대에서 이 필드가 실제로 채워지는지** 4대 캡처만으로
일반화하지 않고 전수 확인 (rule 96 R1 — 외부 계약은 벤더/세대별로 다름).

## 방법 / 근거 종류

- **local_full_mirror** (실측, verified): 사이트 전수 미러 — Dell R740 / HPE DL380 / HPE CSUS3200(4노드) / Lenovo SR650.
- **local_reference_crawl** (실측, verified): `tests/reference/redfish/cisco` Cisco C220 전수 crawl.
- **local_fixture** (합성 mock, 부분): `tests/fixtures/redfish/<vendor>` — System.HostName 은 mock 값,
  NetworkProtocol 파일은 dell/hpe/lenovo 만 존재. 나머지는 NP 파일 부재(미검증).
- DMTF: `Manager.NetworkProtocol` 의 HostName/FQDN 은 표준 optional 속성 (DSP0266 ManagerNetworkProtocol).

> 주의: 웹 검색 워크플로우(2회)는 API rate-limit 으로 8/9 실패 + Cisco 에이전트가 System.HostName
> (`C220-FCH2116V1V0`)을 NetworkProtocol.HostName 으로 혼동(환각)함 → 폐기. 본 매트릭스는 **로컬
> 실데이터 직접 확인** 기반 (rule 25 R7 — 에이전트 주장 실측 검증).

## 매트릭스 (System.HostName / BMC NetworkProtocol.HostName / fallback 동작)

| 벤더 | 세대 | System.HostName | BMC NetProto.HostName | BMC fallback | 근거 | confidence |
|---|---|---|---|---|---|---|
| Dell | iDRAC9 (R740 실측) | `DELL01` | `iDRAC-J0KV603` | [OK] 동작 | full_mirror | verified |
| Dell | iDRAC9 (fixture) | `idrac9-r750` | `iDRAC-2BJ8033`(dell NP 파일) | [OK] | fixture+NP | verified |
| Dell | iDRAC8 | `IDRAC8R730` | (NP 파일 부재) | [INFO] System 보유 | fixture | unverified(NP) |
| HPE | iLO7 (DL380 실측) | `""` | `ILOSGHD3KHHRP` | [OK] **fallback 발동** | full_mirror | verified |
| HPE | RMC (CSUS 실측 4노드) | node01/02=`null`, node03/04=실명 | `RMC...`/`M10MESDB11-RMC` | [OK] **fallback 발동** | full_mirror | verified |
| HPE | iLO (fixture) | (empty) | `ILOSGH504HNZK`(hpe NP 파일) | [OK] | fixture+NP | verified |
| HPE | iLO4/5/6 | `ilo4/5/6-dl380` | (NP 파일 부재) | [INFO] System 보유 | fixture | unverified(NP) |
| Lenovo | XCC3 (SR650 실측) | (필드 부재) | `XCC-7DGD-J902E57T` | [OK] **fallback 발동** | full_mirror | verified |
| Lenovo | XCC (fixture) | `XCC-7Z73-J30AF7LC` | `XCC-7Z73-J30AF7LC`(lenovo NP 파일) | [OK] | fixture+NP | verified |
| Lenovo | IMM2 / XCC2 | `imm2-x3650-m5`/`xcc2-sr650-v3` | (NP 파일 부재) | [INFO] System 보유 | fixture | unverified(NP) |
| Cisco | CIMC (C220 실측) | `C220-FCH2116V1V0` | **`null`** | [NG] **fallback null** → System 사용 | reference_crawl | verified |
| Cisco | CIMC v2/v3/v4 | v3=`cisco-c220-m5`, v4=`cisco-c240-m6`, v2=null | (NP 파일 부재/null) | [NG] System 의존 | fixture | likely |
| Supermicro | X10/X12/X14 | `X10/X12/X14-HOST` | (NP 파일 부재) | [WARN] 미검증 | fixture | unverified |
| Huawei | iBMC v2/v4/Atlas | `HUAWEI-*` | (NP 파일 부재) | [WARN] 미검증 | fixture | unverified |
| Fujitsu | iRMC S5/S6 | `PRIMERGY-001/007` | (NP 파일 부재) | [WARN] 미검증 | fixture | unverified |
| Inspur | ISBMC | `INSPUR-NF5280` | (NP 파일 부재) | [WARN] 미검증 | fixture | unverified |
| Quanta | QCT | `quanta-d54q-001` | (NP 파일 부재) | [WARN] 미검증 | fixture | unverified |

## 핵심 결론

1. **System.HostName 이 대부분 벤더/세대에서 채워진다** (실측 + mock). 채워지면 `source=system`,
   BMC fallback 미발동. BMC fallback 이 실제로 필요한 케이스는 **System.HostName 이 빈/부재인 환경**
   (HPE DL380 / CSUS node01·02 / Lenovo SR650 실측) — 그곳에서 Dell/HPE/Lenovo 는 NetworkProtocol
   .HostName 을 줘서 fallback 이 동작함 (verified).
2. **BMC fallback 은 만능이 아니다**: Cisco CIMC 는 NetworkProtocol.HostName=null (verified). 단
   Cisco 는 System.HostName 을 주므로 hostname 결손 없음. (System·BMC 둘 다 없으면 graceful null.)
3. **lab 부재 벤더(Supermicro/Huawei/Fujitsu/Inspur/Quanta) + 구세대**: NetworkProtocol 실측 미확인
   (부분 합성 fixture 에 NP 파일 없음). DMTF 표준상 가능. graceful 구현이라 동작은 안전 — populated면
   사용, null/부재면 다음 순위/null. 실측 확정은 lab 도입 후 (NEXT_ACTIONS).

## 판정

`[OK]` graceful 구현(`System.HostName → system.fqdn → bmc.network_hostname → null` +
`hostname_source` 표시)은 populated / null / 부재 세 경우를 일관 처리 → **전 벤더/세대 안전**.
confidence 격상(unverified → verified)은 lab/실측 후에만 (rule 96 R1-C).

verified 4벤더(Dell/HPE/Lenovo/Cisco) / unverified 5벤더(Supermicro/Huawei/Fujitsu/Inspur/Quanta).
