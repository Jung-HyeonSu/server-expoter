# Evidence — ESXi physical_disks serial/wwn 신규 수집

> 일자: 2026-06-22. 신규 feature (사용자 승인): ESXi 가 디스크 자체를 안 모으던 것(`physical_disks: []`)을
> pyvmomi 로 수집하도록 추가. 코드 commit `583dc293`, baseline `82926268`.

## 배경

기존 esxi-gather 는 datastore 만 수집하고 `physical_disks` 는 항상 `[]` 였다(normalize_storage.yml 하드코딩).
vSphere API 가 디스크 식별자를 노출하는지 실 ESXi 로 확인 → 가능 확인 후 구현.

## 구현

- 신규 모듈 `esxi-gather/library/esxi_disks.py` (pyvmomi — ESXi 채널 표준 의존, rule 10 R2는 redfish 한정).
  - `configManager.storageSystem.storageDeviceInfo.scsiLun` 에서 `ScsiDisk` 필터.
  - **wwn** = `canonicalName`(naa.*), **serial** = `alternateName[namespace=SERIALNUM]` ASCII 디코딩,
    model = vendor+model, media_type = `ssd` flag, total_mb = capacity(block×blockSize).
- `collect_disks.yml` + `site.yml` 배선 + `normalize_storage.yml` physical_disks 채움.
- field_dictionary: serial channel `[redfish,os]`→`[redfish,os,esxi]`, wwn `[os]`→`[os,esxi]`, id help 갱신.

## 실측 검증 ([OK])

- **로컬 pyvmomi** (esxi01 10.100.64.1 + esxi02 10.100.64.2, root, ESXi 7.0.3): 각 2 disks, serial+wwn(naa) 실값.
- **gatherESXi #3 SUCCESS** (esxi02, GitLab main 빌드) — physical_disks 2개, **gather 출력 == 로컬 pyvmomi 정확 일치**:
```json
{ "id": "naa.6f80bcbeac326eb02f7f66c81ba3c352", "model": "Cisco UCSC-MRAID12G",
  "serial": "0052c3a31bc8667f2fb06e32acbebc80", "wwn": "naa.6f80bcbeac326eb02f7f66c81ba3c352",
  "total_mb": 6099700, "media_type": "HDD" }
{ "id": "naa.6f80bcbeac326eb02f7f66fd1ece98e3", "model": "Cisco UCSC-MRAID12G",
  "serial": "00e398ce1efd667f2fb06e32acbebc80", "wwn": "naa.6f80bcbeac326eb02f7f66fd1ece98e3",
  "total_mb": 10986327, "media_type": "HDD" }
```
- status=success, sections.storage=success. pytest 1254 passed. esxi_baseline 실측 반영.

## 한계

- protocol/health = null (vSphere ScsiDisk 가 transport/health 미노출 — RAID LUN). best-effort.
- RAID logical_volumes / controllers 상세는 vSphere 미노출(BMC/Redfish 영역) — 본 작업 범위 밖(아래 audit 참조).
