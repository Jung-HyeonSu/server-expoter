"""RF-01~03: Redfish 채널 baseline 핵심 필드 회귀 검증.

검증 수준:
  1. 공통 JSON 구조 (최상위 키, schema_version, meta.adapter_id)
  2. 필수 섹션 존재 (sections에 선언된 supported/collected)
  3. 핵심 필드 존재 (채널별 CRITICAL_FIELDS)
  4. adapter_id 기대값 일치
"""

from conftest import (
    assert_channel_critical_fields,
    assert_common_structure,
    assert_hardware_oem_is_object,
    REDFISH_CRITICAL,
    REDFISH_FIELD_MAP,
)


class TestDellBaseline:
    """RF-01: Dell iDRAC9 baseline 검증."""

    def test_common_structure(self, dell_baseline):
        assert_common_structure(dell_baseline)

    def test_adapter_id(self, dell_baseline):
        assert dell_baseline["meta"]["adapter_id"] == "redfish_dell_idrac9"

    def test_critical_fields(self, dell_baseline):
        assert_channel_critical_fields(
            dell_baseline, REDFISH_CRITICAL, REDFISH_FIELD_MAP
        )

    def test_sections_collected(self, dell_baseline):
        """수집된 섹션이 하나 이상 있는지 확인."""
        sections = dell_baseline.get("sections", {})
        collected = [k for k, v in sections.items() if v == "success"]
        assert len(collected) > 0, "수집된 섹션이 없음"

    def test_hardware_oem_is_object(self, dell_baseline):
        assert_hardware_oem_is_object(dell_baseline)


class TestHpeBaseline:
    """RF-02: HPE iLO5 baseline 검증."""

    def test_common_structure(self, hpe_baseline):
        assert_common_structure(hpe_baseline)

    def test_adapter_id(self, hpe_baseline):
        assert hpe_baseline["meta"]["adapter_id"] == "redfish_hpe_ilo5"

    def test_critical_fields(self, hpe_baseline):
        assert_channel_critical_fields(
            hpe_baseline, REDFISH_CRITICAL, REDFISH_FIELD_MAP
        )

    def test_sections_collected(self, hpe_baseline):
        sections = hpe_baseline.get("sections", {})
        collected = [k for k, v in sections.items() if v == "success"]
        assert len(collected) > 0, "수집된 섹션이 없음"

    def test_hardware_oem_is_object(self, hpe_baseline):
        assert_hardware_oem_is_object(hpe_baseline)


class TestLenovoBaseline:
    """RF-03: Lenovo XCC baseline 검증."""

    def test_common_structure(self, lenovo_baseline):
        assert_common_structure(lenovo_baseline)

    def test_adapter_id(self, lenovo_baseline):
        assert lenovo_baseline["meta"]["adapter_id"] == "redfish_lenovo_xcc"

    def test_critical_fields(self, lenovo_baseline):
        assert_channel_critical_fields(
            lenovo_baseline, REDFISH_CRITICAL, REDFISH_FIELD_MAP
        )

    def test_sections_collected(self, lenovo_baseline):
        sections = lenovo_baseline.get("sections", {})
        collected = [k for k, v in sections.items() if v == "success"]
        assert len(collected) > 0, "수집된 섹션이 없음"

    def test_hardware_oem_is_object(self, lenovo_baseline):
        assert_hardware_oem_is_object(lenovo_baseline)


class TestDellR760Output:
    """Dell R760 output fixture (baseline과 별도 장비) 검증."""

    def test_common_structure(self, dell_r760_output):
        assert_common_structure(dell_r760_output)

    def test_adapter_id(self, dell_r760_output):
        assert dell_r760_output["meta"]["adapter_id"] == "redfish_dell_idrac9"

    def test_critical_fields(self, dell_r760_output):
        assert_channel_critical_fields(
            dell_r760_output, REDFISH_CRITICAL, REDFISH_FIELD_MAP
        )

    def test_hardware_oem_is_object(self, dell_r760_output):
        assert_hardware_oem_is_object(dell_r760_output)
