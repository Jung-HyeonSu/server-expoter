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
| #41 | 10.100.64.119 | Ubuntu 24.04 | python_ok | python | SUCCESS | `serial=null, wwn=null` |
| #42 | 10.100.64.161 | RedHat 8.10 | python_incompatible | **raw fallback** | SUCCESS | `serial=null, wwn=null` |
| #42 | 10.100.64.165 | RedHat 9.6 | python_ok | python | SUCCESS | `serial=null, wwn=null` |

실 출력 예 (#41, 119):
```json
{ "id": "/dev/sda", "device": "/dev/sda", "model": "Virtual disk",
  "serial": null, "wwn": null, "total_mb": 184320, "media_type": "HDD",
  "protocol": null, "health": null }
```

## 확인 사항 (✅)

- ✅ `serial`/`wwn` 키가 physical_disks 에 emit 됨 (build #41/#42 console OUTPUT).
- ✅ **python_ok 경로 + raw fallback 경로 양쪽** 정상 (161=raw, 119/165=python).
- ✅ 3대 빌드 SUCCESS — lsblk `-o ...,SERIAL,WWN` + udevadm 보강 task 가 빌드 깨뜨리지 않음.
- ✅ virtio/VMware 가상디스크 → `serial=null, wwn=null` (연구 결과대로 정상, 누락 아님).
- ✅ pytest 1254 passed (회귀 0), field_dictionary validator PASS.

## 한계 / 미확인 (⚠️)

- ⚠️ **실 물리 디스크(baremetal)의 non-null serial/wwn 미관측** — lab Linux 3대가 전부 VMware 가상디스크.
  lsblk SERIAL/WWN 컬럼이 실HW에서 채워짐은 util-linux 소스 + redfish baseline(실 디스크 serial 존재)로
  간접 확인. baremetal Linux 호스트 확보 시 재검증 권장.
- ⚠️ **Windows live 미실행** — gatherOS 에 Windows 타깃 미제공. windows_baseline 의 serial/wwn=null 은
  "VMware Virtual disk SCSI Disk Device"(가상디스크 클래스) 기준 추론값 (Linux virtio null 동작과 동형).
  Windows 실 타깃 확보 시 실측 필요 (특히 serial hex/swap 정규화, WWN UniqueIdFormat 실문자열).

## baseline 갱신

- ubuntu / rhel810_raw_fallback: live 검증 virtio null 반영 (serial:null, wwn:null 추가).
- windows: 동일 가상디스크 클래스 기준 추론 null (Windows 실측은 후속).
