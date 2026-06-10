"""LV-01~05: logical_volumes + physical_disks[].id E2E 검증.

검증 수준:
  1. storage.logical_volumes 키 존재 (모든 Redfish baseline)
  2. logical_volumes 요소 필수 필드 (id, controller_id, member_drive_ids, raid_level, health)
  3. member_drive_ids ↔ physical_disks[].id 교차 참조 (참조 무결성)
  4. physical_disks[].id 키 존재
  5. 벤더별 볼륨 수 기대값 (실장비 라이브 프로브 기준)
     - Dell R740: 1 volume (RAID1)
     - HPE DL380 Gen11: 1 volume (RAID1)
     - Lenovo SR650 V2: 0 volumes (JBOD 모드)
     - Cisco C220 M4: 2 volumes (RAID5 + RAID0)

실장비 검증일: 2026-04-01 (Cisco/HPE/Lenovo), Dell은 기존 baseline 유지
"""

import pytest

from conftest import load_json, BASELINE_DIR

# ---------------------------------------------------------------------------
# logical_volumes 요소 필수 필드
# ---------------------------------------------------------------------------
LOGICAL_VOLUME_REQUIRED_FIELDS = [
    "id",
    "controller_id",
    "member_drive_ids",
    "raid_level",
    "health",
]

LOGICAL_VOLUME_ALL_FIELDS = [
    "id",
    "name",
    "controller_id",
    "member_drive_ids",
    "raid_level",
    "total_mb",
    "health",
    "state",
    "boot_volume",
]


# ---------------------------------------------------------------------------
# 헬퍼
# ---------------------------------------------------------------------------
def _get_storage(baseline: dict) -> dict:
    """baseline['data']['storage'] 반환. 없으면 빈 dict."""
    return baseline.get("data", {}).get("storage", {})


def _get_logical_volumes(baseline: dict) -> list:
    return _get_storage(baseline).get("logical_volumes", [])


def _get_physical_disk_ids(baseline: dict) -> set:
    """physical_disks[].id 값 집합 반환."""
    disks = _get_storage(baseline).get("physical_disks", [])
    return {d["id"] for d in disks if d.get("id") is not None}


def _member_resolves(member_id: str, disk_ids: set) -> bool:
    """member_drive_id가 physical_disks[].id 중 하나와 매칭되는지 확인.

    physical_disks id는 '{drive_id}:{controller_id}' 복합 포맷일 수 있음.
    member_drive_ids는 Volume Links 경로의 마지막 세그먼트(단순 id).
    예: member="PD-1", physical_disk="PD-1:SLOT-HBA" → 매칭.
    예: member="0", physical_disk="0:DE00C000" → 매칭.
    예: member="Disk.Bay.0:...", physical_disk="Disk.Bay.0:..." → 정확 매칭.
    """
    if member_id in disk_ids:
        return True
    return any(
        did.startswith(member_id + ":") or did.startswith(member_id + "/")
        for did in disk_ids
    )


# ===========================================================================
# LV-01: logical_volumes 키 존재 + 구조 검증 (모든 Redfish baseline)
# ===========================================================================
class TestLogicalVolumesStructure:
    """모든 Redfish baseline에 storage.logical_volumes 키가 존재하고,
    요소가 있으면 필수 필드를 포함하는지 검증."""

    @pytest.mark.parametrize("vendor", ["dell", "hpe", "lenovo", "cisco"])
    def test_logical_volumes_key_exists(self, vendor: str):
        baseline = load_json(BASELINE_DIR / f"{vendor}_baseline.json")
        storage = _get_storage(baseline)
        assert "logical_volumes" in storage, (
            f"{vendor}: storage.logical_volumes 키 누락"
        )
        assert isinstance(storage["logical_volumes"], list), (
            f"{vendor}: logical_volumes가 list가 아님"
        )

    @pytest.mark.parametrize("vendor", ["dell", "hpe", "lenovo", "cisco"])
    def test_logical_volume_required_fields(self, vendor: str):
        baseline = load_json(BASELINE_DIR / f"{vendor}_baseline.json")
        volumes = _get_logical_volumes(baseline)
        for i, vol in enumerate(volumes):
            assert isinstance(vol, dict), (
                f"{vendor}: logical_volumes[{i}]이 dict가 아님"
            )
            for field in LOGICAL_VOLUME_REQUIRED_FIELDS:
                assert field in vol, (
                    f"{vendor}: logical_volumes[{i}].{field} 키 누락"
                )

    @pytest.mark.parametrize("vendor", ["dell", "hpe", "lenovo", "cisco"])
    def test_logical_volume_all_fields(self, vendor: str):
        """전체 9개 필드 존재 확인 (값은 null 허용)."""
        baseline = load_json(BASELINE_DIR / f"{vendor}_baseline.json")
        volumes = _get_logical_volumes(baseline)
        for i, vol in enumerate(volumes):
            for field in LOGICAL_VOLUME_ALL_FIELDS:
                assert field in vol, (
                    f"{vendor}: logical_volumes[{i}].{field} 키 누락"
                )


# ===========================================================================
# LV-02: physical_disks[].id 존재 검증
# ===========================================================================
class TestPhysicalDiskId:
    """모든 Redfish baseline의 physical_disks 요소에 id 키가 존재하는지 검증."""

    @pytest.mark.parametrize("vendor", ["dell", "hpe", "lenovo", "cisco"])
    def test_physical_disk_has_id(self, vendor: str):
        baseline = load_json(BASELINE_DIR / f"{vendor}_baseline.json")
        disks = _get_storage(baseline).get("physical_disks", [])
        for i, disk in enumerate(disks):
            assert "id" in disk, (
                f"{vendor}: physical_disks[{i}].id 키 누락"
            )


# ===========================================================================
# LV-03: member_drive_ids ↔ physical_disks[].id 교차 참조
# ===========================================================================
class TestMemberDriveCrossReference:
    """logical_volumes[].member_drive_ids의 모든 값이
    physical_disks[].id에 존재하는지 검증 (참조 무결성)."""

    @pytest.mark.parametrize("vendor", ["hpe", "cisco"])
    def test_member_drive_ids_resolve(self, vendor: str):
        """볼륨이 있는 벤더 교차 참조 검증.

        Dell 제외: BOSS-S1 컨트롤러에서 Drive URI path ('Disk.Direct.0-0:...')와
        Drive.Id ('Disk.Direct.0:...')가 불일치 — Dell BOSS 특유 패턴.
        Lenovo 제외: lenovo_baseline 은 logical_volumes 가 0건 (JBOD 모드)이라
        교차 참조할 member_drive_ids 자체가 없음 (physical_disks 는 Disk.0~Disk.3 4건 모두 존재).
        그래서 parametrize 는 volumes 가 있는 hpe / cisco 만 대상으로 한다.

        physical_disks id가 '{drive_id}:{controller_id}' 복합 포맷일 수 있으므로
        prefix 매칭도 허용."""
        baseline = load_json(BASELINE_DIR / f"{vendor}_baseline.json")
        volumes = _get_logical_volumes(baseline)
        disk_ids = _get_physical_disk_ids(baseline)

        if not volumes:
            pytest.skip(f"{vendor}: logical_volumes 비어있음")

        for i, vol in enumerate(volumes):
            member_ids = vol.get("member_drive_ids", [])
            assert isinstance(member_ids, list), (
                f"{vendor}: logical_volumes[{i}].member_drive_ids가 list가 아님"
            )
            for mid in member_ids:
                assert _member_resolves(mid, disk_ids), (
                    f"{vendor}: logical_volumes[{i}].member_drive_ids "
                    f"'{mid}'가 physical_disks[].id에 매칭 안됨. "
                    f"사용 가능한 id: {sorted(disk_ids)}"
                )

    def test_hpe_cross_ref_strict(self, hpe_baseline):
        """HPE: physical_disks dedup 해소 — strict 교차 참조 검증.

        이전: physical_disks가 dedup으로 4→1건이어서 member_drive_ids '1'이
        resolve 불가였음 (known limitation).
        현재 (2026-04-01 baseline refresh): physical_disks 4건 모두 존재,
        member_drive_ids ['0','1'] → physical_disks ids ['0','1','2','3']에 매칭."""
        volumes = _get_logical_volumes(hpe_baseline)
        disk_ids = _get_physical_disk_ids(hpe_baseline)
        assert len(volumes) == 1, "HPE: 1 volume 기대"
        assert len(disk_ids) >= len(volumes[0]["member_drive_ids"]), (
            f"HPE physical_disks({len(disk_ids)})가 "
            f"member_drive_ids({len(volumes[0]['member_drive_ids'])})보다 적음"
        )
        for mid in volumes[0]["member_drive_ids"]:
            assert _member_resolves(mid, disk_ids), (
                f"HPE: member_drive_id '{mid}'가 physical_disks[].id에 "
                f"매칭 안됨. 사용 가능한 id: {sorted(disk_ids)}"
            )


# ===========================================================================
# LV-04: 벤더별 볼륨 수 검증 (실장비 라이브 프로브 기준)
# ===========================================================================
class TestVendorVolumeCount:
    """실장비 프로브 결과 기반 볼륨 수 검증."""

    def test_dell_volume_count(self, dell_baseline):
        """Dell R740: 1 volume (BOSS-S1 RAID1, 2 drives).
        PERC H330 JBOD 6개는 필터링되고 BOSS-S1 RAID1만 남음."""
        volumes = _get_logical_volumes(dell_baseline)
        assert len(volumes) == 1, f"Dell: 1 volume 기대, 실제: {len(volumes)}"
        assert volumes[0]["raid_level"] == "RAID1"
        assert volumes[0]["controller_id"] == "AHCI.Slot.2-1"
        assert len(volumes[0]["member_drive_ids"]) == 2

    def test_hpe_volume_count(self, hpe_baseline):
        """HPE DL380 Gen11: 1 volume (RAID1, 2 drives).
        실장비 프로브: Volume 239 "RAID1_OS"."""
        volumes = _get_logical_volumes(hpe_baseline)
        assert len(volumes) == 1, f"HPE: 1 volume 기대, 실제: {len(volumes)}"
        assert volumes[0]["raid_level"] == "RAID1"
        assert volumes[0]["id"] == "239"
        assert volumes[0]["name"] == "RAID1_OS"
        assert len(volumes[0]["member_drive_ids"]) == 2

    def test_lenovo_volume_count(self, lenovo_baseline):
        """Lenovo SR650 V2: 0 volumes (JBOD 모드, 개별 디스크 4개).
        실 파이프라인 결과 (2026-04-01): logical_volumes 빈 배열.
        RAID 930-8i 컨트롤러에 4개 SSD가 JBOD로 연결되어 있음."""
        volumes = _get_logical_volumes(lenovo_baseline)
        assert len(volumes) == 0, f"Lenovo: 0 volumes 기대, 실제: {len(volumes)}"

    def test_cisco_volume_count(self, cisco_baseline):
        """Cisco C220 M4: 2 volumes (RAID5 + RAID0).
        실장비 프로브: VD-0 (RAID5, 5 drives), VD-1 (RAID0, 3 drives)."""
        volumes = _get_logical_volumes(cisco_baseline)
        assert len(volumes) == 2, f"Cisco: 2 volumes 기대, 실제: {len(volumes)}"

        raid_levels = sorted([v["raid_level"] for v in volumes])
        assert raid_levels == ["RAID0", "RAID5"], (
            f"Cisco RAID 구성 불일치: {raid_levels}"
        )


# ===========================================================================
# LV-05: Cisco VolumeType→RAIDType fallback 검증
# ===========================================================================
class TestCiscoVolumeTypeFallback:
    """Cisco CIMC는 Redfish v1_0_3 (RAIDType 미지원).
    VolumeType → raid_level 매핑이 올바른지 검증.

    실장비 확인:
      VD-0: VolumeType=StripedWithParity → RAID5
      VD-1: VolumeType=NonRedundant → RAID0
    """

    def test_cisco_raid5_volume(self, cisco_baseline):
        volumes = _get_logical_volumes(cisco_baseline)
        raid5_vols = [v for v in volumes if v["raid_level"] == "RAID5"]
        assert len(raid5_vols) == 1, "Cisco RAID5 볼륨 1개 기대"
        vol = raid5_vols[0]
        assert vol["id"] == "0"
        assert len(vol["member_drive_ids"]) == 5, (
            f"RAID5 드라이브 5개 기대, 실제: {len(vol['member_drive_ids'])}"
        )

    def test_cisco_raid0_volume(self, cisco_baseline):
        volumes = _get_logical_volumes(cisco_baseline)
        raid0_vols = [v for v in volumes if v["raid_level"] == "RAID0"]
        assert len(raid0_vols) == 1, "Cisco RAID0 볼륨 1개 기대"
        vol = raid0_vols[0]
        assert vol["id"] == "1"
        assert len(vol["member_drive_ids"]) == 3, (
            f"RAID0 드라이브 3개 기대, 실제: {len(vol['member_drive_ids'])}"
        )


# ===========================================================================
# LV-06: Dell R740 JBOD 필터링 회귀 테스트
# ===========================================================================
class TestJbodFiltering:
    """Dell R740 PERC H330 JBOD 모드: 물리 디스크가 Volume으로 노출되는 패턴.
    redfish_gather.py의 JBOD 필터가 이를 올바르게 제거하는지 검증.

    실장비 확인 (2026-04-01):
      RAID.Slot.6-1: 6 drives, 6 RawDevice volumes → 전부 필터링
      AHCI.Slot.2-1 (BOSS-S1): 2 drives, 1 RAID1 volume → 유지
    """

    def test_dell_no_jbod_volumes(self, dell_baseline):
        """Dell baseline에 JBOD pseudo-volume이 없어야 한다.
        RAID.Slot.6-1 컨트롤러의 볼륨은 모두 필터링되고,
        AHCI.Slot.2-1 (BOSS-S1)의 RAID1만 남아야 함."""
        volumes = _get_logical_volumes(dell_baseline)
        jbod_volumes = [
            v for v in volumes
            if v.get("controller_id") == "RAID.Slot.6-1"
        ]
        assert len(jbod_volumes) == 0, (
            f"JBOD pseudo-volume이 남아있음: {jbod_volumes}"
        )

    def test_dell_boss_volume_kept(self, dell_baseline):
        """Dell BOSS-S1 RAID1 volume은 JBOD 필터에 영향받지 않아야 한다."""
        volumes = _get_logical_volumes(dell_baseline)
        boss_volumes = [
            v for v in volumes
            if v.get("controller_id") == "AHCI.Slot.2-1"
        ]
        assert len(boss_volumes) == 1, (
            f"BOSS-S1 RAID1 volume 1개 기대, 실제: {len(boss_volumes)}"
        )
        assert boss_volumes[0]["raid_level"] == "RAID1"
