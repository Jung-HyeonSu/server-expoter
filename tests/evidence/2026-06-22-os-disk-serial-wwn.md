# Evidence — OS physical_disks serial/wwn 실측 (Jenkins gatherOS)

> 일자: 2026-06-22. 작업: OS(Linux/Windows) 디스크 serial/wwn 수집 추가.
> SPEC: `docs/ai/tickets/2026-06-22-os-disk-serial-wwn/SPEC.md`. 코드 commit: `8e0aed95`.

## 검증 환경

- Jenkins: `http://10.100.64.152:8080` `portal/gather/gatherOS` (Jenkinsfile_portal, GitLab main 빌드)
- 빌드 SHA: `8e0aed95`(serial/wwn 코드 포함) 푸시 후 트리거
- loc=git, target_type=os, callbackUrl=http://10.100.64.151:8080

## 결과 (3대, 양쪽 코드 경로)

| 빌드 | 호스트 | distro | gather_mode | 경로 | 결과 | physical_disks serial/wwn |
|---|---|---|---|---|---|---|
| #41 | 10.100.64.119 | Ubuntu 24.04 | python_ok | python | SUCCESS | `serial=null, wwn=null` (VM virtio) |
| #42 | 10.100.64.161 | RedHat 8.10 | python_incompatible | **raw fallback** | SUCCESS | `serial=null, wwn=null` (VM virtio) |
| #42 | 10.100.64.165 | RedHat 9.6 | python_ok | python | SUCCESS | `serial=null, wwn=null` (VM virtio) |
| **#43** | **10.100.64.96** | **Ubuntu 24.04 (baremetal)** | python_ok | python | SUCCESS | **non-null 실값 (SATA RAID + NVMe)** |

baremetal 실 출력 (#43, 96) — **gather == SSH ground truth 정확 일치**:
```json
{ "device": "/dev/sda", "model": "RAID",
  "serial": "00e0faed649a980a6900653b7780e04e", "wwn": "0x6f4ee080773b6500690a989a64edfae0", "media_type": "SSD" }
{ "device": "/dev/sdb", "model": "RAID",
  "serial": "0021b319c1d8980a6900653b7780e04e", "wwn": "0x6f4ee080773b6500690a98d8c119b321", "media_type": "HDD" }
{ "device": "/dev/nvme0n1", "model": "Dell BOSS-N1",
  "serial": "CN0WW56VFCP0049K01Y0", "wwn": "eui.0050434d07000001", "protocol": "NVMe" }
```

VM 가상디스크 출력 (#41, 119): `serial=null, wwn=null` (정상).

## false-null 분석 (실값 있는데 null로 나오는 증상)

SSH(paramiko) 로 96/161/165 의 lsblk `-o SERIAL,WWN` + udevadm 원천을 직접 떠서 gather 출력과 대조:

| 호스트 | lsblk SERIAL/WWN 원천 | udev ID_SERIAL_SHORT/ID_WWN | gather 출력 | 판정 |
|---|---|---|---|---|
| 96 sda | `00e0...`/`0x6f4e...` | `6f4e...`/`0x6f4ee080773b6500` | `00e0...`/`0x6f4e...` | **일치 (false-null 없음)** |
| 96 nvme0n1 | `CN0WW56...`/`eui.0050...` | 동일 | 동일 | **일치** |
| 161/165 sda,sdb | **빈 값** | **빈 값** | null | **진짜 null** (VMware disk.EnableUUID 미설정) |

- **결론**: 실값이 존재하면(96 baremetal) gather 가 그대로 출력 — **누락(false-null) 증상 없음**.
- 161/165 의 null 은 원천(lsblk+udev)이 모두 빈 값이라 정상 — 코드 버그 아님.
- 참고: 96 sda 는 lsblk WWN(full 32hex `0x6f4ee080773b6500690a989a64edfae0`) 과 udev ID_WWN(short 16hex `0x6f4ee080773b6500`) 이 다름(util-linux #321 RAID short/full). 본 구현은 **lsblk 우선**이라 full WWN 채택(더 구체적).

## 확인 사항 (✅)

- ✅ `serial`/`wwn` 키가 physical_disks 에 emit 됨 (build #41/#42 console OUTPUT).
- ✅ **python_ok 경로 + raw fallback 경로 양쪽** 정상 (161=raw, 119/165=python).
- ✅ 3대 빌드 SUCCESS — lsblk `-o ...,SERIAL,WWN` + udevadm 보강 task 가 빌드 깨뜨리지 않음.
- ✅ virtio/VMware 가상디스크 → `serial=null, wwn=null` (연구 결과대로 정상, 누락 아님).
- ✅ pytest 1254 passed (회귀 0), field_dictionary validator PASS.

## 채널별 현황 (2026-06-22 재확인)

- **OS Linux**: ✅ python_ok + raw fallback + **baremetal 실값**(#43) + VM null 모두 검증. false-null 없음.
- **OS Windows**: ⚠️ live 미실행 — gatherOS 에 Windows 타깃 미제공. windows_baseline serial/wwn=null 은
  "VMware Virtual disk" 클래스 추론값. 실 Windows 확보 시 serial hex/swap 정규화 + WWN UniqueIdFormat 실측 필요.
- **Redfish**: 코드 변경 없음. 이미 `physical_disks[].serial` emit (5 vendor baseline 실값: dell `S5CNNA0MC03697` 등).
  `wwn` 은 미수집. gatherRedfish live 는 본 세션 미실행(Jenkins API 간헐 빈응답 + BMC 타깃 미확정).
- **ESXi**: `physical_disks: []` — **디스크 자체 미수집**(datastore 만). serial/wwn N/A.
  pyvmomi `HostScsiDisk`(canonicalName/uuid/serialNumber) 로 구현 가능하나 **현재 미구현 = 별도 feature**.

## baseline 갱신

- ubuntu / rhel810_raw_fallback: live 검증 virtio null 반영 (serial:null, wwn:null 추가).
- windows: 동일 가상디스크 클래스 기준 추론 null (Windows 실측은 후속).
