# server-exporter Reference Library

> 외부 시스템 / 라이브러리 / 표준 규격 참고 문서. AI가 skills / agents / rule 작성 시 참조.
> 1차 수집 2026-04-27 (Plan 2) → 보강 2026-04-27 (Plan 3 후 — 코드에서 실 사용하는 모든 외부 자원).

## 구조

```
docs/ai/references/
├── ansible/
│   ├── builtin-modules.md         # ansible.builtin (setup/raw/include_tasks 등)
│   ├── windows-modules.md         # ansible.windows 3.3.0
│   ├── posix-collection.md        # ansible.posix 2.1.0 (selinux 등)
│   ├── ansible-vault.md           # Vault 명령 / 2단계 로딩
│   ├── jmespath.md                # JMESPath (json_query 필터)
│   ├── jinja-filters.md           # Ansible Jinja2 필터 종합
│   └── plugin-development.md      # callback / lookup / filter / module_utils 개발
├── redfish/
│   ├── redfish-spec.md            # DMTF Redfish 표준 + 벤더별 BMC
│   ├── vendor-bmc-guides.md       # 5 vendor BMC 공식 정보 + adapter 매핑
│   └── python-clients.md          # stdlib vs Sushy / ilorest / python-redfish 비교
├── vmware/
│   └── community-vmware-modules.md # community.vmware 6.2.0
├── python/
│   ├── pyvmomi.md                 # vSphere SDK
│   └── netaddr.md                 # IP 주소 처리
├── winrm/
│   └── pywinrm.md                 # Session / Protocol API
└── jenkins/
    └── pipeline-syntax.md         # Declarative Pipeline + 4-Stage 템플릿
```

## 코드에서 실 사용하는 모든 자원 매핑

### Ansible

- `ansible-core 2.20.3` — 모든 playbook 실행
- `ansible.builtin` — setup / raw / include_tasks / set_fact / debug / assert / block-rescue 등 (`ansible/builtin-modules.md`)
- `ansible.windows 3.3.0` — Windows gather (`ansible/windows-modules.md`)
- `ansible.posix 2.1.0` — Linux SELinux 등 (`ansible/posix-collection.md`)
- `community.vmware 6.2.0` — ESXi gather (`vmware/community-vmware-modules.md`)
- `community.windows 3.1.0` — Windows 보조 (간접)
- `community.general 12.4.0` — json_query / 기타 필터
- `ansible.utils 6.0.1` — ipaddr 필터
- Ansible Plugin 개발 (server-exporter 자체구현): callback / lookup / filter / module_utils (`ansible/plugin-development.md`)
- Ansible Vault (`ansible/ansible-vault.md`)
- Jinja2 3.1.6 + filters (`ansible/jinja-filters.md`)
- JMESPath (json_query) (`ansible/jmespath.md`)

### Python

- Python 3.12.3 stdlib — `urllib`, `ssl`, `json`, `base64`, `subprocess`, `socket` (redfish_gather.py / precheck_bundle.py)
- `pywinrm 0.5.0` — Windows WinRM (`winrm/pywinrm.md`)
- `pyvmomi 9.0.0` — vSphere SDK (간접 — community.vmware backend) (`python/pyvmomi.md`)
- `redis 7.3.0` — Ansible fact cache (직접 사용 없음, ansible.cfg 설정)
- `jmespath 1.1.0` — json_query backend (`ansible/jmespath.md`)
- `netaddr 1.3.0` — ipaddr 필터 backend (`python/netaddr.md`)
- `lxml 6.0.2` — VMware XML 파싱 (간접)

### Redfish (DMTF 표준)

- ServiceRoot + Chassis + Systems + Storage + Volumes + Drives + Managers + UpdateService + AccountService + Power
- 5 vendor BMC: Dell iDRAC8/9 / HPE iLO5/6 / Lenovo XCC / Supermicro / Cisco CIMC (`redfish/vendor-bmc-guides.md`)
- 인증: HTTP Basic + Session-based (X-Auth-Token)
- 표준 정본 (`redfish/redfish-spec.md`)
- Python client 비교 (`redfish/python-clients.md`) — server-exporter는 stdlib 자체구현 (rule 10 R2)

### Jenkins

- Declarative Pipeline (`jenkins/pipeline-syntax.md`)
- 4-Stage (Validate / Gather / Validate Schema / E2E Regression)
- agent-master 망 분리
- `Jenkinsfile`, `grafana 파이프라인(제거됨)`, `Jenkinsfile_portal` 3종

## 활용 원칙

1. **인덱스로만**: 본문은 정본 (Ansible 공식 / 벤더 BMC manual / RFC). 본 reference는 핵심 추출 + server-exporter 적용 매핑
2. **TTL 90일** (rule 28 #11 외부 계약): 분기마다 재 fetch 권장
3. **drift 감지 시 보강**: 새 펌웨어 / 새 ansible 버전 / 새 라이브러리 시 갱신
4. **skill / agent / rule 본문은 본 reference 참조**: skill 본문에 외부 정보 풀어 쓰지 말고 `docs/ai/references/...` link

## 갱신 절차

1. WebFetch로 source URL fetch
2. server-exporter 적용 매핑 추가 (어떤 rule / skill / agent와 연결되는지)
3. version 명시 (검증 기준 Agent 10.100.64.154 기준)
4. 적용 rule 명시
5. `docs/ai/catalogs/EXTERNAL_CONTRACTS.md`에 drift 발견 시 추가

## 향후 추가 후보

- DMTF Redfish OData 스키마 상세 (probe-redfish-vendor skill 보강 시)
- IPMI fallback 정보 (Redfish 미지원 BMC 대응 시)
- Ansible callback API 더 깊이 (json_only.py 변경 시)
- Jenkins Shared Library (3 Jenkinsfile 공통 로직 추출 시)
