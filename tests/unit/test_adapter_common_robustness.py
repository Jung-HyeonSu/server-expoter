"""adapter_common fault-injection 회귀 (Round 1 멀티에이전트 검출 — rule 95 R1).

배경: adapter 선택은 벤더 자동 감지의 핵심. probe_facts(외부 BMC ServiceRoot 유래)나
내부 adapter YAML 의 오염 값이 loader 전체를 죽이거나 잘못된 매칭을 유발할 수 있다.
Round 1 적대적 검증 confirmed:
  - #4 normalize_vendor: 비-str vendor(BMC Manufacturer=숫자) → .strip() AttributeError
  - #3 pattern_match_any: 비-str pattern → re.search/.lower() crash
  - #5 adapter_score: priority='high' → int() ValueError (loader 전체 실패)
  - #18 adapter_matches: distribution/version_patterns 있는데 facts 빈 값 → 무조건 disqualify
    (model/firmware 는 빈 값 통과인데 distro/version 만 불일치 — 일관성 위반)
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "module_utils"))

from adapter_common import (  # noqa: E402
    adapter_matches,
    adapter_score,
    normalize_vendor,
    pattern_match_any,
)


# #4 — normalize_vendor 비-str
def test_normalize_vendor_non_str_does_not_crash():
    """BMC Manufacturer 가 숫자(JSON 오염) → .strip() AttributeError 방어."""
    assert normalize_vendor(12345) is not None  # 가드 전: AttributeError
    assert normalize_vendor(["Dell"]) is not None
    # 정상 입력 불변
    assert normalize_vendor("Dell Inc.", {"dell inc.": "dell"}) == "dell"


# #3 — pattern_match_any 비-str pattern
def test_pattern_match_any_non_str_pattern_does_not_crash():
    """adapter YAML model_patterns 에 비-str 원소 → re.search/.lower() crash 방어."""
    assert pattern_match_any([123, None, "PowerEdge"], "PowerEdge R760") is True  # 가드 전: crash
    assert pattern_match_any([123, None], "PowerEdge R760") is False
    # 정상 입력 불변
    assert pattern_match_any(["R7[0-9]0"], "PowerEdge R760") is True


# #5 — adapter_score priority 비-숫자
def test_adapter_score_non_numeric_priority_does_not_crash():
    """adapter YAML priority='high'/'1.5' → int() ValueError 로 loader 전체 죽던 것 방어."""
    s = adapter_score({"priority": "high", "match": {}}, {"vendor": "dell"})  # 가드 전: ValueError
    assert isinstance(s, int)
    # 정상 int priority 불변 (generic match, priority=10 → 10*1000)
    assert adapter_score({"priority": 10, "match": {}}, {"vendor": "dell"}) == 10 * 1000


# #18 — adapter_matches distro/version 빈 값 일관성
def test_adapter_matches_empty_distro_passes_like_model():
    """distribution_patterns 있고 facts.distribution='' → model/firmware 처럼 통과해야 함."""
    adapter = {"match": {"distribution_patterns": ["rhel.*"]}}
    # 빈 distribution = 정보 없음 → disqualify 아님 (model/firmware 와 동일 정책)
    assert adapter_matches(adapter, {"distribution": ""}) is True  # 가드 전: False
    # 정보 있는데 불일치하면 여전히 disqualify
    assert adapter_matches(adapter, {"distribution": "ubuntu"}) is False
    # 일치하면 통과
    assert adapter_matches(adapter, {"distribution": "rhel9"}) is True


def test_adapter_matches_empty_version_passes_like_model():
    adapter = {"match": {"version_patterns": ["9\\..*"]}}
    assert adapter_matches(adapter, {"version": ""}) is True  # 가드 전: False
    assert adapter_matches(adapter, {"version": "8.10"}) is False


# Round 9 #2 — whitespace-only vendor → None (empty-string substring 오탐 방지)
def test_normalize_vendor_whitespace_only_returns_none():
    assert normalize_vendor("   ") is None  # 가드 전: '' 가 모든 alias 에 substring 매칭
    assert normalize_vendor("\t\n ") is None
    assert normalize_vendor("Dell Inc.", {"dell inc.": "dell"}) == "dell"  # 정상 불변
