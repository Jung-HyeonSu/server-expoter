# -*- coding: utf-8 -*-
# ==============================================================================
# diagnosis_mapper.py — 진단 결과 변환 필터 플러그인
# ==============================================================================
# precheck_bundle 모듈의 결과를 공통 output JSON의
# diagnosis 및 errors 구조로 변환합니다.
#
# 사용법 (Ansible task):
#   - set_fact:
#       _diagnosis: "{{ precheck_result | build_diagnosis('redfish', 'dell_idrac9') }}"
#       _diagnosis_errors: "{{ precheck_result | build_errors_from_diagnosis }}"
# ==============================================================================

from __future__ import absolute_import, division, print_function
__metaclass__ = type


def build_diagnosis(precheck_result, channel, adapter_id=None):
    """
    precheck_bundle 결과를 공통 diagnosis 딕셔너리로 변환합니다.

    Args:
        precheck_result: precheck_bundle 모듈의 반환값
        channel: 수집 채널 (redfish/os/esxi)
        adapter_id: 선택된 adapter ID (없으면 None)

    Returns:
        diagnosis dict — output JSON의 diagnosis 필드에 들어감
    """
    details = {
        "channel": channel,
        "adapter_candidate": adapter_id,
        "checked_ports": precheck_result.get("checked_ports", []),
    }

    # OS 채널 추가 정보
    if channel == "os":
        details["detected_os"] = precheck_result.get("detected_os")
        details["detected_port"] = precheck_result.get("detected_port")

    # 선택된 포트
    selected_port = precheck_result.get("selected_port")
    if selected_port:
        details["selected_port"] = selected_port

    # probe_facts 병합
    probe_facts = precheck_result.get("probe_facts", {})
    if probe_facts:
        details.update(probe_facts)

    return {
        "reachable": precheck_result.get("reachable"),
        "port_open": precheck_result.get("port_open"),
        "protocol_supported": precheck_result.get("protocol_supported"),
        "auth_success": precheck_result.get("auth_success"),
        "failure_stage": precheck_result.get("failure_stage"),
        "failure_reason": precheck_result.get("failure_reason"),
        "details": details,
    }


def build_errors_from_diagnosis(precheck_result):
    """
    precheck_bundle 실패 결과를 errors 목록으로 변환합니다.

    Args:
        precheck_result: precheck_bundle 모듈의 반환값

    Returns:
        errors list — 실패 시 [{section, message, detail}], 성공 시 []
    """
    failure_reason = precheck_result.get("failure_reason")
    if not failure_reason:
        return []

    return [{
        "section": "diagnosis",
        "message": failure_reason,
        "detail": precheck_result.get("detail"),
    }]


class FilterModule(object):
    """Ansible filter plugin for diagnosis mapping"""

    def filters(self):
        return {
            "build_diagnosis": build_diagnosis,
            "build_errors_from_diagnosis": build_errors_from_diagnosis,
        }
