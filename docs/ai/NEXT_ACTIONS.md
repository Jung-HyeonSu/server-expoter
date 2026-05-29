# server-exporter 다음 작업 (NEXT_ACTIONS)

> **본 파일**: 진정 active PENDING 만 유지 (rule 70 R5 / R6 / R7 cycle 자문 정책).
> **lab 매트릭스**: `docs/ai/catalogs/LAB_PENDING_MATRIX.md` (8 vendor × generation × 4 column).
> **archive**: `docs/ai/archive/NEXT_ACTIONS-history-2026-04-to-05.md` (OPS-* + cycle-013/014/015/016 잔여).
> **마지막 정리**: 2026-05-21 (1371 줄 → 압축).

---

## 1. AI 환경에서 즉시 가능 — F6 OS baseline expansion (사용자 access 제공 완료)

| 항목 | 상태 | 진입 |
|---|---|---|
| rhel920 / rhel960 / rocky960 baseline 3건 신설 | **trigger 충족** (사용자 IP 제공 2026-05-11) | `docs/ai/handoff/2026-05-21-os-baseline-expansion.md` cold-start |

- 3 IP: 10.100.64.163 / 10.100.64.165 / 10.100.64.169
- F5 system.runtime 9 필드 빌더 실측 검증 포함
- Jenkins Agent 환경 필요 (ansible-playbook 실 수집)

---

## 2. 외부 trigger 대기 PENDING (lab / 사이트 / 운영 환경)

### 2.1 baseline 확장 (lab 도입 시)

| # | 항목 | trigger |
|---|---|---|
| F3 | Supermicro baseline | 사이트 BMC IP 확보 |
| F4 | Windows + 베어메탈 OS baseline | winrm/sudo 환경 도입 |

각 진입 시: `update-vendor-baseline` skill + rule 13 R4 절차.

### 2.2 HPE CSUS 3200 / Superdome Flex RMC (lab 부재)

- **trigger**: RMC IP 확보 + Redfish 활성화 (`docs/22_rmc-activation-guide.md` 4 절)
- **상세 8 항목 (C1~C8)**: `docs/ai/catalogs/LAB_PENDING_MATRIX.md` HPE 행
- **handoff 후보 A**: `docs/ai/handoff/2026-05-11-next-cycles.md` "후보 A — HPE CSUS 3200 lab 검증"
- **ADR**: `docs/ai/decisions/ADR-2026-05-12-csus-rmc-multi-node.md`, `ADR-2026-05-29-hba-ib-csus.md`
- **cycle 2026-05-29 (hba-ib-csus)**: baseline 을 전 공통 섹션 realistic mock 으로 채움 (FC HBA + RAID1 SATA + DDR5 + 3 partition canonical). 여전히 **mock** — C1 사이트 fixture 캡처 후 실 baseline 으로 교체 의무 ("검증됨" 주장 금지 — rule 25 R7-B).

### 2.4 HBA / InfiniBand 사이트 fixture (lab 부재 — cycle 2026-05-29)

- **trigger**: FC HBA / IB HCA 보유 사이트 BMC/OS/ESXi 접근
- **항목**:
  - FC HBA 보유 Dell/HPE/Lenovo/Cisco BMC → Redfish `storage.hbas` 실측 fixture + baseline (현 4 redfish baseline 은 FC 미보유로 빈)
  - FC HBA 보유 Windows/Linux 호스트 → `Get-InitiatorPort`+`MSFC_*` / sysfs 실측 (현 ubuntu/windows/rhel baseline 빈)
  - IB HCA (Mellanox/NVIDIA) 보유 호스트 → Linux ibstat/sysfs 실측 (IB 정본 채널)
  - ESXi FC SAN 호스트 → vmhba FC speed/wwnn 실측 (현 esxi_baseline 은 offline FC 2)
- **ESXi esxcli-over-SSH fallback (D1-B 재평가)**: SSH 활성 운영·보안 결정 시 `esxcli storage san fc list` / `rdma device list` 보강
- **절차**: `capture-site-fixture` skill + rule 13 R4 (실측 baseline) + EXTERNAL-CONTRACTS 갱신

### 2.3 8 vendor × generation 후속 매트릭스

→ `docs/ai/catalogs/LAB_PENDING_MATRIX.md` 정본 참조.

진행 가능한 generation 우선:
- Dell iDRAC8 / iDRAC9 (lab 미도입)
- HPE iLO5 / iLO6 / Superdome Flex
- Lenovo IMM2 / XCC / XCC2
- Cisco CIMC M5~M8 / UCS S-series
- Supermicro 전체 generation (사이트 BMC 0대)
- Huawei / Inspur / Fujitsu / Quanta 전체 (lab 부재)

---

## 3. 운영 / 보안 추적 (사용자 결정 대기)

위 archive 의 OPS-* 잔여 항목 trigger 발생 시 archive 에서 본 파일로 복원:

| 카테고리 | 추적 위치 |
|---|---|
| 보안 회전 (Goodmit0802! / vault) | archive OPS-AUDIT-1 / OPS-DELL-VAULT-1 |
| 운영팀 결정 (vault timing / repo private / dryrun OFF) | archive OPS-3 / OPS-5 / OPS-9 |
| 실 hardware 점검 (Lenovo PSU1) | archive OPS-LENOVO-PSU1 |
| WinRM / Win Server 2022 안정성 | archive AI-22 reopen / OPS-RESIDUAL-1 |
| baseline 재수집 (HPE iLO6 / Cisco / Dell) | archive OPS-HPE-REVIEW-1/2 / OPS-CISCO-REVIEW-1/2 |

---

## 4. 정기 추적 (분기 / 연간)

| 항목 | 주기 | 정본 |
|---|---|---|
| DMTF Redfish release 매트릭스 | 분기 | `EXTERNAL_CONTRACTS.md` |
| vendor EOL / CVE / errata | 분기 | `EXTERNAL_CONTRACTS.md` |
| community.vmware collection 업그레이드 | 연간 | `REQUIREMENTS.md` |
| 펌웨어 매트릭스 drift | TTL 90일 (rule 28 R1 #11) | adapter origin 주석 |
| COMPATIBILITY-MATRIX | TTL 14일 (rule 28 R1 #12) | `COMPATIBILITY-MATRIX.md` |
| LAB_PENDING_MATRIX | TTL 14일 (rule 28 R1 #12 와 동일) | `LAB_PENDING_MATRIX.md` |

---

## 5. AI 자율 진행 가능 (lab 없이 즉시)

| 작업 | skill / agent |
|---|---|
| harness 자기개선 cycle | `/harness-cycle` (6단계 파이프라인) |
| rule 28 측정 11종 drift 검사 | `measure-reality-snapshot` skill |
| repo 정리 (죽은 코드 / 중복 / archive 후보) | `repo-hygiene-planner` agent |
| `docs/ai/handoff/2026-05-11-next-cycles.md` 후보 B/C/D | handoff 후보 참조 |

---

## 관련

- rule: `70-docs-and-evidence-policy` R5 / R6 / R7 (보존 / archive / cycle 자문)
- catalog: `LAB_PENDING_MATRIX.md`, `COMPATIBILITY-MATRIX.md`, `VENDOR_ADAPTERS.md`, `EXTERNAL_CONTRACTS.md`
- archive: `docs/ai/archive/NEXT_ACTIONS-history-2026-04-to-05.md`
- handoff: `docs/ai/handoff/2026-05-21-os-baseline-expansion.md` (F6), `docs/ai/handoff/2026-05-11-next-cycles.md` (4 후보)
- ADR: `docs/ai/decisions/ADR-2026-05-12-csus-rmc-multi-node.md`
