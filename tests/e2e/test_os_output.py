"""OS-01, OS-04: OS 채널 baseline 핵심 필드 회귀 검증.

검증 수준:
  1. 공통 JSON 구조 (최상위 키, schema_version, meta.adapter_id)
  2. 필수 섹션 존재
  3. 핵심 필드 존재 (OS 채널 기준)
  4. adapter_id 기대값 일치
"""

from conftest import (
    assert_channel_critical_fields,
    assert_common_structure,
    assert_correlation_fields,
    assert_correlation_host_ip,
    OS_CRITICAL,
    OS_FIELD_MAP,
)


class TestUbuntuBaseline:
    """OS-01: Linux (Ubuntu) baseline 검증."""

    def test_common_structure(self, ubuntu_baseline):
        assert_common_structure(ubuntu_baseline)

    def test_adapter_id(self, ubuntu_baseline):
        assert ubuntu_baseline["meta"]["adapter_id"] == "os_linux_generic"

    def test_critical_fields(self, ubuntu_baseline):
        assert_channel_critical_fields(
            ubuntu_baseline, OS_CRITICAL, OS_FIELD_MAP
        )

    def test_sections_collected(self, ubuntu_baseline):
        """수집된 섹션이 하나 이상 있는지 확인."""
        sections = ubuntu_baseline.get("sections", {})
        collected = [k for k, v in sections.items() if v == "success"]
        assert len(collected) > 0, "수집된 섹션이 없음"
        assert "system" in collected, "system 섹션 미수집"

    def test_correlation(self, ubuntu_baseline):
        assert_correlation_fields(ubuntu_baseline)

    def test_correlation_host_ip(self, ubuntu_baseline):
        assert_correlation_host_ip(ubuntu_baseline)


class TestWindowsBaseline:
    """OS-04: Windows baseline 검증."""

    def test_common_structure(self, windows_baseline):
        assert_common_structure(windows_baseline)

    def test_adapter_id(self, windows_baseline):
        assert windows_baseline["meta"]["adapter_id"] == "os_windows_generic"

    def test_critical_fields(self, windows_baseline):
        assert_channel_critical_fields(
            windows_baseline, OS_CRITICAL, OS_FIELD_MAP
        )

    def test_sections_collected(self, windows_baseline):
        sections = windows_baseline.get("sections", {})
        collected = [k for k, v in sections.items() if v == "success"]
        assert len(collected) > 0, "수집된 섹션이 없음"
        assert "system" in collected, "system 섹션 미수집"

    def test_correlation(self, windows_baseline):
        """Windows는 correlation.system_uuid가 null일 수 있음 — 키 존재만 확인."""
        assert_correlation_fields(windows_baseline)

    def test_correlation_host_ip(self, windows_baseline):
        assert_correlation_host_ip(windows_baseline)
