"""RF-04: Cisco CIMC baseline 전용 E2E 검증.

Cisco 특이사항:
  - system 섹션: not_supported (fqdn만 값 있고 나머지 null)
  - users 섹션: not_supported
  - 나머지 8개 섹션 (hardware, bmc, cpu, memory, storage, network, firmware, power): success
  - system 계열 필드 (vendor, model, serial, uuid)는 hardware 섹션에 위치
  - assert_channel_critical_fields의 system→hardware fallback 로직으로 검증

검증 수준:
  1. 공통 JSON 구조 (최상위 키, schema_version, meta.adapter_id)
  2. adapter_id == redfish_cisco_cimc
  3. 핵심 필드 존재 (Redfish 채널 기준, system→hardware fallback 포함)
  4. 수집된 섹션 8개 + not_supported 2개 명시 확인
  5. hardware.oem object 존재
  6. 배열 내부 필드 (physical_disks, power_supplies, firmware, interfaces)
  7. correlation 필드 (UUID 형식 + host_ip)
"""

from conftest import (
    assert_array_element_fields,
    assert_channel_critical_fields,
    assert_common_structure,
    assert_correlation_fields,
    assert_correlation_host_ip,
    assert_hardware_oem_is_object,
    REDFISH_ARRAY_FIELDS,
    REDFISH_CRITICAL,
    REDFISH_FIELD_MAP,
)


class TestCiscoBaseline:
    """RF-04: Cisco CIMC baseline 검증."""

    def test_common_structure(self, cisco_baseline):
        assert_common_structure(cisco_baseline)

    def test_adapter_id(self, cisco_baseline):
        assert cisco_baseline["meta"]["adapter_id"] == "redfish_cisco_cimc"

    def test_critical_fields(self, cisco_baseline):
        """Cisco는 system이 not_supported이므로 system 필드는 hardware fallback으로 검증."""
        assert_channel_critical_fields(
            cisco_baseline, REDFISH_CRITICAL, REDFISH_FIELD_MAP
        )

    def test_sections_collected(self, cisco_baseline):
        """8개 섹션 success, 2개 not_supported 확인."""
        sections = cisco_baseline.get("sections", {})
        collected = [k for k, v in sections.items() if v == "success"]
        not_supported = [k for k, v in sections.items() if v == "not_supported"]

        assert len(collected) == 8, f"수집 섹션 8개 기대, 실제: {collected}"
        assert "system" in not_supported, "system이 not_supported이어야 함"
        assert "users" in not_supported, "users가 not_supported이어야 함"

    def test_hardware_oem_is_object(self, cisco_baseline):
        assert_hardware_oem_is_object(cisco_baseline)

    def test_array_element_fields(self, cisco_baseline):
        assert_array_element_fields(
            cisco_baseline, REDFISH_ARRAY_FIELDS, "cisco_baseline"
        )

    def test_correlation(self, cisco_baseline):
        assert_correlation_fields(cisco_baseline)

    def test_correlation_host_ip(self, cisco_baseline):
        assert_correlation_host_ip(cisco_baseline)
