# -*- coding: utf-8 -*-
# DEPRECATED: This filter is currently unused in the project.
# All normalization uses direct Jinja2 expressions in task files.
# Kept for potential future use. If still unused after next major version, remove.
# ==============================================================================
# field_mapper.py — 필드 스키마 기반 데이터 정규화 필터
# ==============================================================================
# raw 수집 데이터와 필드 스키마를 입력받아 정규화된 data fragment를 반환합니다.
#
# 사용법 (Ansible):
#   {{ raw_data | field_map(field_schema, section='system') }}
#   {{ raw_data | field_defaults(field_schema, section='cpu') }}
# ==============================================================================

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import re


def _coerce_type(value, field_type):
    """필드 타입에 맞게 값을 변환합니다."""
    if value is None:
        return None

    try:
        if field_type == "int":
            if isinstance(value, str):
                # "16 GB" -> 16, "3.2 GHz" -> 3, "16.5 GB" -> 16
                m = re.match(r"^[\s]*([0-9]+\.?[0-9]*)", str(value))
                if m:
                    return int(float(m.group(1)))
            return int(value)
        elif field_type == "float":
            if isinstance(value, str):
                m = re.match(r"^[\s]*([0-9]+\.?[0-9]*)", str(value))
                if m:
                    return float(m.group(1))
            return float(value)
        elif field_type == "bool":
            if isinstance(value, str):
                return value.lower() in ("true", "yes", "1", "on")
            return bool(value)
        elif field_type == "str":
            return str(value).strip() if value else None
        elif field_type == "list":
            if isinstance(value, list):
                return value
            return [value] if value else []
        elif field_type == "dict":
            return value if isinstance(value, dict) else {}
    except (ValueError, TypeError):
        return None

    return value


def _get_nested(data, key_path):
    """점(.) 구분 경로로 중첩 딕셔너리에서 값을 추출합니다."""
    if not data or not key_path:
        return None
    keys = key_path.split(".")
    current = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
        else:
            return None
    return current


def field_map(raw_data, field_schema, section=None):
    """
    raw 데이터를 필드 스키마에 따라 정규화합니다.

    Args:
        raw_data: dict — 원시 수집 데이터
        field_schema: dict — 필드 정의 (fields 키 안에 섹션별 필드 목록)
        section: str — 처리할 섹션 이름 (없으면 전체)

    Returns:
        dict: 정규화된 데이터
    """
    if not raw_data or not field_schema:
        return {}

    fields = field_schema.get("fields", {})
    if section:
        fields = {section: fields.get(section, {})}

    result = {}
    for sec_name, sec_fields in fields.items():
        if not sec_fields:
            continue
        sec_result = {}
        for field_name, field_def in sec_fields.items():
            if not isinstance(field_def, dict):
                continue
            # source 경로에서 값 추출
            source = field_def.get("source", field_name)
            value = _get_nested(raw_data, source)
            # 타입 변환
            field_type = field_def.get("type", "str")
            value = _coerce_type(value, field_type)
            # 기본값 적용
            if value is None:
                value = field_def.get("default")
            sec_result[field_name] = value

        if section:
            result = sec_result
        else:
            result[sec_name] = sec_result

    return result


def field_defaults(field_schema, section=None):
    """
    필드 스키마에서 기본값만 추출하여 빈 데이터 구조를 생성합니다.

    Args:
        field_schema: dict — 필드 정의
        section: str — 처리할 섹션 이름

    Returns:
        dict: 기본값으로 채워진 데이터 구조
    """
    if not field_schema:
        return {}

    fields = field_schema.get("fields", {})
    if section:
        fields = {section: fields.get(section, {})}

    result = {}
    for sec_name, sec_fields in fields.items():
        if not sec_fields:
            continue
        sec_result = {}
        for field_name, field_def in sec_fields.items():
            if not isinstance(field_def, dict):
                continue
            sec_result[field_name] = field_def.get("default")

        if section:
            result = sec_result
        else:
            result[sec_name] = sec_result

    return result


class FilterModule(object):
    """Ansible field_mapper 필터 플러그인"""
    def filters(self):
        return {
            "field_map": field_map,
            "field_defaults": field_defaults,
        }
