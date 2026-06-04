"""redfish_gather.py 순수 헬퍼 특성화 테스트 (cycle 2026-06-04).

외부 계약(rule 96) robustness 함수들 — 펌웨어 응답 변형(non-numeric capacity,
trailing space, 0x-prefixed JEDEC, 중첩 dict 부재 등)에 모듈이 죽지 않도록 방어하는
순수 함수. 직접 단위 테스트가 없어(0 커버) 본 파일에서 현재 동작을 고정한다.

대상: _safe / _safe_int / _removeprefix / _strip_or_none / _canonical_vendor_name
      / _normalize_jedec  (모두 stdlib-only, 부수효과 없음)

NOTE: filter-side `jedec_mapper.jedec_to_vendor` 는 test_jedec_mapper.py 가 커버.
본 파일은 **redfish-side** 별도 구현(`_normalize_jedec`)을 검증 — 입력 수용 경계가
filter-side 와 다르다(예: bare '2C' 를 redfish 는 해석, filter 는 raw 반환).
두 테이블 값 정합은 test_jedec_drift_guard.py 가 보장.
"""
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]


def _load_redfish_module():
    if "ansible.module_utils.basic" not in sys.modules:
        mock_basic = types.ModuleType("ansible.module_utils.basic")
        mock_basic.AnsibleModule = type("AnsibleModule", (), {})
        sys.modules.setdefault("ansible", types.ModuleType("ansible"))
        sys.modules.setdefault("ansible.module_utils", types.ModuleType("ansible.module_utils"))
        sys.modules["ansible.module_utils.basic"] = mock_basic
    src = REPO / "redfish-gather" / "library" / "redfish_gather.py"
    spec = importlib.util.spec_from_file_location("redfish_gather_pure_helpers", str(src))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def rfg():
    return _load_redfish_module()


# ── _safe (중첩 dict 안전 getter) ─────────────────────────────────────────────

def test_safe_nested_hit(rfg):
    assert rfg._safe({"a": {"b": {"c": 1}}}, "a", "b", "c") == 1


def test_safe_single_key(rfg):
    assert rfg._safe({"a": 1}, "a") == 1
    assert rfg._safe({"a": {"b": 1}}, "a") == {"b": 1}


def test_safe_missing_key_default(rfg):
    assert rfg._safe({"a": 1}, "x") is None
    assert rfg._safe({"a": 1}, "x", default=0) == 0


def test_safe_non_dict_short_circuits(rfg):
    assert rfg._safe(None, "a") is None
    assert rfg._safe("notadict", "a") is None
    assert rfg._safe(123, "a", default="d") == "d"


def test_safe_none_value_treated_as_missing(rfg):
    assert rfg._safe({"a": None}, "a") is None
    assert rfg._safe({"a": {"b": None}}, "a", "b", default="x") == "x"


# ── _safe_int (firmware drift ValueError 가드, rule 96) ───────────────────────

def test_safe_int_numeric(rfg):
    assert rfg._safe_int("5") == 5
    assert rfg._safe_int(5) == 5
    assert rfg._safe_int(5.9) == 5  # int() truncates


def test_safe_int_non_numeric_returns_default(rfg):
    assert rfg._safe_int("abc") is None
    assert rfg._safe_int(None) is None
    assert rfg._safe_int("3.5") is None  # int('3.5') raises ValueError → default
    assert rfg._safe_int("") is None


def test_safe_int_custom_default(rfg):
    assert rfg._safe_int("abc", default=0) == 0
    assert rfg._safe_int("42", default=0) == 42


# ── _removeprefix (Python 3.8 이하 호환) ──────────────────────────────────────

def test_removeprefix_strips(rfg):
    assert rfg._removeprefix("redfish/v1/Systems", "redfish/v1/") == "Systems"


def test_removeprefix_no_match_unchanged(rfg):
    assert rfg._removeprefix("abc", "xyz") == "abc"
    assert rfg._removeprefix("", "x") == ""


# ── _strip_or_none (Cisco trailing space, non-str passthrough) ────────────────

def test_strip_or_none_trims(rfg):
    assert rfg._strip_or_none("M386A8K40BM1-CRC    ") == "M386A8K40BM1-CRC"
    assert rfg._strip_or_none("  abc  ") == "abc"


def test_strip_or_none_empty_becomes_none(rfg):
    assert rfg._strip_or_none("") is None
    assert rfg._strip_or_none("   ") is None


def test_strip_or_none_non_string_passthrough(rfg):
    assert rfg._strip_or_none(None) is None
    assert rfg._strip_or_none(123) == 123
    assert rfg._strip_or_none(["x"]) == ["x"]


# ── _canonical_vendor_name (cross-vendor 이름 정규화) ─────────────────────────

def test_canonical_vendor_name_normalizes_variants(rfg):
    assert rfg._canonical_vendor_name("Hynix Semiconductor") == "SK hynix"
    assert rfg._canonical_vendor_name("hynix") == "SK hynix"
    assert rfg._canonical_vendor_name("Samsung Electronics") == "Samsung"
    assert rfg._canonical_vendor_name("Micron") == "Micron Technology"


def test_canonical_vendor_name_passthrough_and_guards(rfg):
    assert rfg._canonical_vendor_name("Samsung") == "Samsung"  # 이미 canonical
    assert rfg._canonical_vendor_name(None) is None
    assert rfg._canonical_vendor_name("") == ""  # falsy → 그대로 반환


# ── _normalize_jedec (redfish-side JEDEC ID 해석) ─────────────────────────────

def test_normalize_jedec_prefixed_hex(rfg):
    assert rfg._normalize_jedec("0xCE00") == "Samsung"
    assert rfg._normalize_jedec("0xAD") == "SK hynix"


def test_normalize_jedec_plain_hex_with_bank(rfg):
    # dmidecode raw: 앞 바이트(continuation)=00, 다음 바이트=ID
    assert rfg._normalize_jedec("00AD063200AD") == "SK hynix"


def test_normalize_jedec_bare_two_char(rfg):
    # redfish-side 는 bare 2자리도 해석 (filter-side 와의 수용 경계 차이)
    assert rfg._normalize_jedec("2C") == "Micron Technology"


def test_normalize_jedec_vendor_name_passthrough(rfg):
    assert rfg._normalize_jedec("Samsung") == "Samsung"
    assert rfg._normalize_jedec("Hynix Semiconductor") == "SK hynix"


def test_normalize_jedec_unknown_hex_kept_raw(rfg):
    # 미지의 ID 는 추적성 위해 raw 보존
    assert rfg._normalize_jedec("0xFF00") == "0xFF00"


def test_normalize_jedec_sentinels_to_none(rfg):
    for v in (None, "", "Unknown", "Not Specified", "none"):
        assert rfg._normalize_jedec(v) is None
