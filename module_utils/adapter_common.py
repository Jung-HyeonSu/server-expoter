# -*- coding: utf-8 -*-
# ==============================================================================
# adapter_common.py — adapter 시스템 공유 유틸리티
# ==============================================================================
# adapter_loader lookup plugin과 기타 모듈에서 공통으로 사용하는
# 벤더 정규화, match 평가, 점수 계산 함수들입니다.
# ==============================================================================

# NOTE: 이 파일은 Ansible module_utils로 사용되므로 Display API를 직접 import 할 수 없다.
# module_utils 환경에서는 stdout/stderr가 Ansible에 의해 캡처되므로 print(stderr)를 사용한다.
__metaclass__ = type

import re
import yaml
import os


def load_vendor_aliases(aliases_path):
    """
    vendor_aliases.yml 파일을 로드하여 {alias_lower: canonical} 매핑을 반환합니다.

    Args:
        aliases_path: vendor_aliases.yml 파일 경로

    Returns:
        dict: {"dell inc.": "dell", "hewlett packard enterprise": "hpe", ...}
    """
    mapping = {}
    try:
        with open(aliases_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        aliases = data.get("vendor_aliases", {})
        for canonical, alias_list in aliases.items():
            for alias in alias_list:
                mapping[alias.strip().lower()] = canonical
    except (IOError, OSError, yaml.YAMLError, AttributeError, TypeError) as exc:
        import sys
        print(f"[adapter_common] vendor_aliases 로드 경고: {exc}", file=sys.stderr)
    return mapping


def normalize_vendor(raw_vendor, aliases=None):
    """
    원시 벤더 문자열을 정규화된 이름으로 변환합니다.

    Args:
        raw_vendor: Redfish Manufacturer 등에서 가져온 원시 문자열
        aliases: {alias_lower: canonical} 매핑 딕셔너리

    Returns:
        str or None: 정규화된 벤더명 ("dell", "hpe" 등) 또는 None
    """
    if not raw_vendor:
        return None

    v = raw_vendor.strip().lower()

    if aliases:
        canonical = aliases.get(v)
        if canonical:
            # {canonical: [alias_list]} 형태로 잘못 전달된 경우 방어
            if isinstance(canonical, list):
                # v가 키(=canonical)와 일치 → v 자체가 정규화된 이름
                return v
            return canonical
        # 부분 매칭 시도
        for alias, canon in aliases.items():
            if isinstance(canon, list):
                # {canonical: [alias_list]} 형태 — alias_list에서 검색
                if v in [a.strip().lower() for a in canon]:
                    return alias
                continue
            if alias in v or v in alias:
                return canon

    return v if v else None


def pattern_match_any(patterns, value):
    """
    패턴 목록 중 하나라도 value에 매칭되는지 확인합니다.

    Args:
        patterns: 정규식 패턴 문자열 목록
        value: 대조할 문자열

    Returns:
        bool: 하나라도 매칭되면 True
    """
    if not patterns or not value:
        return False
    value = str(value)
    for pattern in patterns:
        try:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        except re.error:
            if pattern.lower() in value.lower():
                return True
    return False


def adapter_matches(adapter, facts, aliases=None):
    """
    adapter의 match 조건이 facts와 일치하는지 평가합니다.

    Args:
        adapter: adapter YAML 딕셔너리
        facts: probe_facts 딕셔너리 (vendor, firmware, model 등)
        aliases: 벤더 aliases 매핑 (optional)

    Returns:
        bool: 모든 match 조건이 충족되면 True
    """
    match = adapter.get("match", {})
    if not match:
        return True  # match 조건 없으면 항상 매칭 (generic)

    # vendor 매칭
    vendor_patterns = match.get("vendor", [])
    if vendor_patterns:
        raw_vendor = facts.get("vendor", "")
        norm_vendor = normalize_vendor(raw_vendor, aliases)

        # adapter의 vendor 목록도 정규화해서 비교
        matched = False
        for vp in vendor_patterns:
            norm_vp = normalize_vendor(vp, aliases)
            if norm_vendor and norm_vp and norm_vendor == norm_vp:
                matched = True
                break
        if not matched:
            return False

    # model 패턴 매칭
    model_patterns = match.get("model_patterns", [])
    if model_patterns:
        model = facts.get("model", "")
        if model and not pattern_match_any(model_patterns, model):
            return False
        # model이 빈 문자열(정보 없음)이면 통과 — scoring에서 보너스만 제외

    # firmware 패턴 매칭
    firmware_patterns = match.get("firmware_patterns", [])
    if firmware_patterns:
        firmware = facts.get("firmware", "")
        if firmware and not pattern_match_any(firmware_patterns, firmware):
            return False
        # firmware가 빈 문자열(정보 없음)이면 통과 — scoring에서 보너스만 제외

    # OS 유형 매칭 (os/esxi 채널용)
    os_type = match.get("os_type")
    if os_type:
        detected = facts.get("detected_os") or facts.get("os_type") or ""
        if detected.lower() != os_type.lower():
            return False

    # 배포판 패턴 매칭
    distribution_patterns = match.get("distribution_patterns", [])
    if distribution_patterns:
        distro = facts.get("distribution", "")
        if not pattern_match_any(distribution_patterns, distro):
            return False

    # 버전 패턴 매칭
    version_patterns = match.get("version_patterns", [])
    if version_patterns:
        version = facts.get("version", "")
        if not pattern_match_any(version_patterns, version):
            return False

    return True


def adapter_specificity(adapter):
    """
    adapter의 match 조건이 얼마나 구체적인지 점수를 계산합니다.
    조건이 많을수록 높은 점수 = 더 구체적.

    Returns:
        int: specificity 점수
    """
    match = adapter.get("match", {})
    score = 0

    if match.get("vendor"):
        score += 10
    if match.get("model_patterns"):
        score += 20
    if match.get("firmware_patterns"):
        score += 20
    if match.get("version_patterns"):
        score += 15
    if match.get("distribution_patterns"):
        score += 15
    if match.get("os_type"):
        score += 5

    # generic adapter는 감점
    if adapter.get("generic", False):
        score -= 40

    return score


def adapter_match_score(adapter, facts, aliases=None):
    """
    adapter가 facts와 얼마나 잘 맞는지 실제 매칭 점수를 계산합니다.

    Returns:
        int: match 점수 (매칭 실패 시 -9999)
    """
    match = adapter.get("match", {})
    score = 0

    # vendor 매칭 보너스
    vendor_patterns = match.get("vendor", [])
    if vendor_patterns:
        raw_vendor = facts.get("vendor", "")
        norm_vendor = normalize_vendor(raw_vendor, aliases)
        matched = False
        for vp in vendor_patterns:
            norm_vp = normalize_vendor(vp, aliases)
            if norm_vendor and norm_vp and norm_vendor == norm_vp:
                matched = True
                break
        if matched:
            score += 20
        else:
            return -9999

    # model 매칭 보너스
    model_patterns = match.get("model_patterns", [])
    if model_patterns:
        if pattern_match_any(model_patterns, facts.get("model", "")):
            score += 25
        elif not facts.get("model", ""):
            # model info unavailable (empty) - don't disqualify, just skip bonus
            pass
        else:
            return -9999

    # firmware 매칭 보너스
    firmware_patterns = match.get("firmware_patterns", [])
    if firmware_patterns:
        if pattern_match_any(firmware_patterns, facts.get("firmware", "")):
            score += 25
        elif not facts.get("firmware", ""):
            # firmware info unavailable (empty) - don't disqualify, just skip bonus
            pass
        else:
            return -9999  # firmware known but doesn't match - disqualify

    return score


def adapter_score(adapter, facts, aliases=None):
    """
    adapter의 최종 점수를 계산합니다.
    priority × 1000 + specificity × 10 + match_score

    Returns:
        int: 최종 점수 (높을수록 우선)
    """
    priority = int(adapter.get("priority", 0))
    specificity = adapter_specificity(adapter)
    match_sc = adapter_match_score(adapter, facts, aliases)

    if match_sc == -9999:
        return -9999

    return priority * 1000 + specificity * 10 + match_sc
