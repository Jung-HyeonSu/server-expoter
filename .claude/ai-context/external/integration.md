# External Systems Integration — server-exporter

> 외부 시스템 연동 노트. 정본: `docs/develop/` (rule 30)에 운영 절차, 본 문서는 메모.

## Redfish API

- **진입점**: `https://<bmc_ip>/redfish/v1/` (ServiceRoot, 무인증 detect 가능)
- **인증**: HTTPS Basic Auth (Vault 2단계 로딩으로 vendor에 맞는 자격증명 사용)
- **HTTPS verify**: 자체 서명 인증서 환경에서는 verify=False (코드에 의도 명시 — cycle-011: rule 60 해제)
- **TLS 버전**: 일부 구 펌웨어는 TLS 1.0/1.1만 — Python ssl context로 명시
- **라이브러리**: stdlib만 (urllib / ssl / json) — `redfish-gather/library/redfish_gather.py`
- **계약 변경**: rule 96 R1 origin 주석 + R3 영향 범위 분석 의무

### 주요 endpoint

| Path | 용도 |
|---|---|
| `/redfish/v1/` | ServiceRoot (무인증) |
| `/redfish/v1/Chassis` | Chassis list |
| `/redfish/v1/Systems` | Systems list (CPU/Memory) |
| `/redfish/v1/Systems/<id>/Storage` | Storage controllers |
| `/redfish/v1/Systems/<id>/Storage/<sid>/Drives` | Drives |
| `/redfish/v1/Systems/<id>/Storage/<sid>/Volumes` | Volumes |
| `/redfish/v1/Managers` | BMC info |
| `/redfish/v1/UpdateService/FirmwareInventory` | 펌웨어 |
| `/redfish/v1/AccountService/Accounts` | BMC 사용자 |

## IPMI

- 일부 구 BMC가 Redfish 미지원/제한적 → IPMI fallback (현재 server-exporter는 Redfish 우선)
- 향후 확장 시 ipmitool 또는 pyghmi 검토

## SSH (Linux gather)

- **라이브러리**: paramiko (Ansible 내부)
- **인증**: SSH key 또는 password (vault/<loc>/os/linux.yml)
- **Linux 2-tier**: Python 3.9+ 있으면 setup/shell/command, 없으면 raw 모듈만
- **Privilege escalation**: become_method=sudo

## WinRM (Windows gather)

- **라이브러리**: pywinrm 0.5.0
- **인증**: NTLM 또는 Basic
- **Vault**: vault/<loc>/os/windows.yml

## vSphere API (ESXi gather)

- **라이브러리**: pyvmomi 9.0.0
- **인증**: vault/<loc>/esxi.yml (vSphere 사용자/비밀번호)
- **Collection**: community.vmware 6.2.0
- **버전 지원**: ESXi 6.x / 7.x / 8.x (adapters/esxi/*.yml로 분기)
- **XML 파싱**: lxml 6.0.2 (vmware 응답 일부 XML)

## callback URL (호출자 통보)

- **HTTP method**: POST
- **무결성 (rule 31)**: 공백 / 후행 슬래시 방어 (`url.strip().rstrip('/')`)
- **payload**: callback_plugins/json_only.py 출력 envelope
- **재시도**: Jenkins post stage에서 일부 재시도 가능

## 외부 계약 변경 대응 (rule 96)

새 펌웨어 / API path 변경 발견 시:
1. `debug-external-integrated-feature` skill 호출
2. 사용자에게 외부 계약 질의 (origin 주석 / 담당자 / 마지막 동기화)
3. 영향 분석: 동일 vendor 다른 adapter / vendor_aliases / vault / OEM tasks
4. drift 발견 시 docs/ai/catalogs/EXTERNAL_CONTRACTS.md + CONVENTION_DRIFT.md 기록
5. adapter YAML metadata 주석 갱신 (vendor / firmware / tested_against / oem_path)
