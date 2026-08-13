# community.vmware Collection — 핵심 reference

> Source: https://docs.ansible.com/ansible/latest/collections/community/vmware/index.html
> Fetched: 2026-04-27
> Collection version (server-exporter 검증 기준): community.vmware 6.2.0
> Repo: https://github.com/ansible-collections/community.vmware

server-exporter esxi-gather에서 사용. ESXi 6.x / 7.x / 8.x 지원 (adapters/esxi/*.yml로 분기).

## Connection 패턴

```yaml
- name: ESXi 직접 연결
  community.vmware.vmware_host_facts:
    hostname: "{{ esxi_ip }}"
    username: "root"
    password: "{{ vault_esxi_password }}"
    validate_certs: false  # 자체 서명 시
```

```yaml
- name: vCenter 경유
  community.vmware.vmware_vm_info:
    hostname: "vcenter.example.com"
    username: "administrator@vsphere.local"
    password: "{{ vault_vcenter_password }}"
    validate_certs: false
```

server-exporter는 **ESXi 직접 연결** 우선 (vCenter 의존성 최소화).

## 핵심 Fact-Gathering 모듈

### ESXi Host (server-exporter 주 사용)

| Module | 용도 |
|---|---|
| `vmware_host_facts` | ESXi host 종합 fact (hostname / hw / network / storage / capabilities) |
| `vmware_host_capability_info` | 기능 (vMotion / HA / DRS / vSAN) |
| `vmware_host_config_info` | advanced configuration |
| `vmware_host_service_info` | 서비스 list |
| `vmware_host_feature_info` | CPU / virtualization / memory encryption flag |

### Hardware / Storage

| Module | 용도 | server-exporter 섹션 |
|---|---|---|
| `vmware_host_disk_info` | 물리 디스크 (vendor / firmware / size) | storage |
| `vmware_host_scsidisk_info` | SCSI 디스크 (NAA id / capacity) | storage |
| `vmware_host_vmhba_info` | HBA / 스토리지 어댑터 | storage |
| `vmware_host_vmnic_info` | NIC (MAC / driver / speed) | network |

### Network

| Module | 용도 |
|---|---|
| `vmware_dvswitch_info` | DVS (port count / MTU / LACP) |
| `vmware_dvs_portgroup_info` | DVS portgroup (VLAN) |
| `vmware_portgroup_info` | 표준 vSwitch portgroup |
| `vmware_vmkernel_info` | vmk interface (vMotion / management / vSAN) |

### Storage / Compute

| Module | 용도 |
|---|---|
| `vmware_datastore_info` | 데이터스토어 (capacity / free / type) |
| `vmware_cluster_info` | 클러스터 (deprecated) |
| `vmware_vm_info` / `vmware_guest_info` | VM 목록 / 단일 VM |

## 공통 파라미터

| 파라미터 | 타입 | 비고 |
|---|---|---|
| `hostname` | string | ESXi 또는 vCenter FQDN/IP |
| `username` | string | root (ESXi) 또는 SSO (vCenter) |
| `password` | string | vault에서 로드 |
| `validate_certs` | bool | 자체 서명 시 false |
| `port` | int | 기본 443 |
| `datacenter` | string | filter (vCenter용) |
| `cluster_name` | string | filter |
| `esxi_hostname` | string | filter |

## ESXi 버전별 adapter

server-exporter `adapters/esxi/`:

| Adapter | 대상 |
|---|---|
| `esxi_6x.yml` | ESXi 6.x |
| `esxi_7x.yml` | ESXi 7.x |
| `esxi_8x.yml` | ESXi 8.x |
| `esxi_generic.yml` | 미매치 fallback |

각 adapter의 `match.api_version` 또는 `match.version_pattern`으로 분기.

## Best Practices for server-exporter

1. **vault**: `vault/<loc>/esxi.yml`의 `vault_esxi_user` (root) + `vault_esxi_password`
2. **validate_certs**: 자체 서명 인증서 환경 → `false` + 코드에 의도 주석 (cycle-011: rule 60 해제)
3. **stdlib 보완**: 일부 vmware 모듈이 lxml 기반 — `pip install lxml`
4. **Connection 재사용**: 한 host에 여러 facts → 각 모듈마다 connect/disconnect 발생. 가능하면 vmware_host_facts 한 번에
5. **Adapter capability**: 일부 모듈이 vCenter 전용 (datacenter / cluster) — ESXi 직접 연결 시 미동작

## 정본 reference

- `.claude/ai-context/external/integration.md` — vSphere API 노트
- 외부 API 공식 문서 — pyvmomi SDK 설명
- `adapters/esxi/*.yml` — 버전별 adapter

## 적용 rule

- rule 10 (gather-core) — 모듈 선택
- rule 12 (adapter-vendor-boundary) — esxi 버전 분기는 adapter
- rule 30 (integration-redfish-vmware-os) — vSphere 통합
- rule 40 (qa-pytest-baseline) — ESXi 실장비 검증
