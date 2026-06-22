# Evidence — Windows gather 전수 검증 (10.100.64.120)

> 일자: 2026-06-22. 사용자 제공 Windows 타깃으로 그동안 미검증이던 **OS Windows 경로 전체** 실측.
> 대상: 10.100.64.120 (Windows Server 2022 Standard 21H2, VMware VM). gatherOS (loc=git, target_type=os).
> 전체 envelope: `tests/evidence/2026-06-22-windows-120-envelope.json`.

## 결과: status=success, errors=[]

sections: system/hardware/cpu/memory/storage/network/users = **success**, bmc/firmware/power/thermal = not_supported (OS Windows 정상).

## 핵심 — 그동안 미검증이던 Windows 필드 (✅ 실측)

### physical_disks serial/wwn (2026-06-22 feature, Windows live 최초 검증)
```json
{ "id": "\\\\.\\PHYSICALDRIVE0", "model": "VMware Virtual disk SCSI Disk Device",
  "serial": "6000c291a8a27597a22732589449427c", "wwn": "6000C291A8A27597A22732589449427C",
  "total_mb": 102398, "media_type": "HDD", "protocol": "SAS", "health": "healthy" }
```
- ✅ **serial + wwn 실값 populate** — VMware Windows 가 `Get-PhysicalDisk.SerialNumber`/`UniqueId`(NAA)로 노출.
  (VMware 가상디스크는 serial 과 wwn 이 동일 NAA id 의 대소문자 차이 — 실 HW 면 serial=드라이브 시리얼, wwn=NAA 로 상이. 정상.)
- ✅ **health = "healthy"** (Tier 2 — Get-PhysicalDisk.HealthStatus, field_dictionary 등록 완료).
- serial 정규화: hex/`20` 패딩 없어 디코딩 미적용(그대로) — 정상.

### memory.slots (Tier 2 channel os)
```json
{ "capacity_mb": 8192, "manufacturer": "VMware Virtual RAM", "part_number": "VMW-8192MB",
  "type": null, "speed_mhz": null, "serial": null }
```
- ✅ Win32_PhysicalMemory 수집 (channel os 추가 완료). type/speed 는 VMware 미노출(null 정상).

### 기타 섹션
- users: 2 / network.interfaces: 9 / filesystems: 2 / cpu/hardware: success. adapter_id=os_windows_2022.

## 발견 / 정정 사항

- 📌 **windows_baseline serial/wwn=null 은 부정확**: 2026-06-22 에 "VMware 가상디스크 클래스 추론 null"로 넣었으나,
  실 VMware Windows(120)는 serial/wwn 을 **populate** 한다. windows_baseline(다른 host, adapter_id=os_windows_generic)
  은 실 host 값으로 **재캡처 필요**(120 은 os_windows_2022 라 adapter_id 단정 충돌 — 통째 교체 불가).
- **Windows 미구현(정상)**: `storage.controllers[]`=[] (Tier3 Storage Spaces 영역), `network.adapters[]`=0 (Windows NIC firmware Tier1 미적용 — Linux 한정).

## 결론

- ✅ **Windows gather 전 섹션 정상 동작** + disk serial/wwn/health + memory.slots 실측 확인.
- ⚠️ windows_baseline serial/wwn 재캡처 (NEXT_ACTIONS) — 실 host 값으로.
- (참고) Windows controllers / NIC firmware 는 Tier3/별도 — 현재 미구현.
