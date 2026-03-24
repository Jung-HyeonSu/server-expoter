#!/usr/bin/python3
# -*- coding: utf-8 -*-
# ==============================================================================
# precheck_bundle.py — 통합 사전 진단 모듈
# ==============================================================================
# 수집 전 대상 호스트의 연결 상태를 4단계로 진단합니다.
#
# 단계:
#   1. reachable   — TCP 포트 연결로 호스트 도달 가능성 확인
#   2. port_open   — 채널별 서비스 포트 확인 (443/22/5985/5986)
#   3. protocol_supported — 프로토콜 핸드셰이크 (Redfish/SSH banner/vSphere)
#   4. auth_success — 인증 시도 (선택적)
#
# 사용법:
#   - name: Run precheck
#     precheck_bundle:
#       host: "{{ ansible_host }}"
#       channel: redfish
#       ports: [443]
#     delegate_to: localhost
#     register: precheck_result
# ==============================================================================

__metaclass__ = type

DOCUMENTATION = r"""
---
module: precheck_bundle
short_description: 수집 전 대상 호스트 연결 상태 4단계 진단
description:
  - ping(TCP) → port → protocol → auth 순서로 대상 호스트를 진단합니다.
  - 각 단계의 성공/실패 여부와 실패 사유를 반환합니다.
  - controller 노드에서 실행됩니다 (delegate_to: localhost).
options:
  host:
    description: 대상 호스트 IP 또는 hostname
    required: true
    type: str
  channel:
    description: 수집 채널
    required: true
    type: str
    choices: [redfish, os, esxi]
  ports:
    description: 확인할 포트 목록 (순서대로 시도, 첫 번째 성공 포트 사용)
    type: list
    elements: int
    default: []
  timeout_port:
    description: 포트 연결 타임아웃 (초)
    type: float
    default: 3.0
  timeout_protocol:
    description: 프로토콜 핸드셰이크 타임아웃 (초)
    type: float
    default: 6.0
  timeout_auth:
    description: 인증 시도 타임아웃 (초)
    type: float
    default: 8.0
  username:
    description: 인증 사용자명 (선택)
    type: str
  password:
    description: 인증 비밀번호 (선택)
    type: str
  verify_ssl:
    description: SSL 인증서 검증 여부
    type: bool
    default: false
author:
  - ClovierOne Portal Team
"""

from ansible.module_utils.basic import AnsibleModule
import socket
import ssl
import json

# requests는 선택적 의존성
try:
    import requests
    from requests.auth import HTTPBasicAuth
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


# =============================================================================
# 채널별 기본 포트 정의
# =============================================================================
CHANNEL_DEFAULT_PORTS = {
    "redfish": [443],
    "os": [5986, 5985, 22],
    "esxi": [443],
}

# 채널별 프로토콜 진단 실패 메시지
CHANNEL_PROTOCOL_MESSAGES = {
    "redfish": "이 장비는 Redfish를 지원하지 않습니다.",
    "os": "SSH 또는 WinRM 서비스가 응답하지 않습니다.",
    "esxi": "vSphere API endpoint가 응답하지 않습니다.",
}


def tcp_check(host, port, timeout):
    """TCP 포트 연결 가능 여부 확인"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((host, port))
        return True, None
    except socket.timeout:
        return False, "연결 시간 초과 (timeout={0}s)".format(timeout)
    except ConnectionRefusedError:
        return False, "연결 거부됨 (port={0})".format(port)
    except OSError as e:
        return False, str(e)
    finally:
        try:
            sock.close()
        except Exception:
            pass


def http_get(url, timeout, verify=False, auth=None):
    """HTTP GET 요청 수행"""
    if not HAS_REQUESTS:
        # requests 없을 때 기본 urllib 사용
        try:
            import urllib.request
            import urllib.error

            ctx = ssl.create_default_context()
            if not verify:
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE

            req = urllib.request.Request(url)
            if auth:
                import base64
                credentials = base64.b64encode(
                    "{0}:{1}".format(auth[0], auth[1]).encode()
                ).decode()
                req.add_header("Authorization", "Basic " + credentials)

            resp = urllib.request.urlopen(req, timeout=timeout, context=ctx)
            body = resp.read().decode("utf-8", errors="replace")
            status_code = resp.getcode()

            try:
                json_body = json.loads(body)
            except (ValueError, json.JSONDecodeError):
                json_body = None

            return True, None, {
                "status_code": status_code,
                "json": json_body,
            }
        except urllib.error.HTTPError as e:
            return False, "HTTP {0}".format(e.code), {
                "status_code": e.code,
                "json": None,
            }
        except Exception as e:
            return False, str(e), None
    else:
        try:
            auth_obj = HTTPBasicAuth(auth[0], auth[1]) if auth else None
            resp = requests.get(
                url,
                timeout=timeout,
                verify=verify,
                auth=auth_obj,
            )
            try:
                json_body = resp.json()
            except (ValueError, json.JSONDecodeError):
                json_body = None

            if resp.status_code >= 400:
                return False, "HTTP {0}".format(resp.status_code), {
                    "status_code": resp.status_code,
                    "json": json_body,
                }

            return True, None, {
                "status_code": resp.status_code,
                "json": json_body,
            }
        except requests.exceptions.Timeout:
            return False, "요청 시간 초과 (timeout={0}s)".format(timeout), None
        except requests.exceptions.ConnectionError as e:
            return False, "연결 실패: {0}".format(str(e)[:200]), None
        except Exception as e:
            return False, str(e)[:200], None


def ssh_banner_check(host, port, timeout):
    """SSH 배너 확인으로 SSH 서비스 동작 여부 검증"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((host, port))
        banner = sock.recv(256).decode("utf-8", errors="replace").strip()
        if banner.startswith("SSH-"):
            return True, None, {"ssh_banner": banner}
        return False, "SSH 배너가 아닙니다: {0}".format(banner[:50]), None
    except Exception as e:
        return False, str(e), None
    finally:
        try:
            sock.close()
        except Exception:
            pass


def probe_redfish(host, port, timeout, verify=False):
    """Redfish ServiceRoot 프로브"""
    url = "https://{0}:{1}/redfish/v1/".format(host, port)
    ok, err, payload = http_get(url, timeout, verify=verify)
    if not ok:
        return False, err, None

    json_data = payload.get("json") if payload else None
    probe_facts = {}

    if json_data:
        probe_facts["redfish_version"] = json_data.get("RedfishVersion")
        probe_facts["product"] = json_data.get("Product")
        # Systems 링크에서 벤더 정보 탐색 시도
        systems_uri = None
        systems = json_data.get("Systems")
        if isinstance(systems, dict):
            systems_uri = systems.get("@odata.id")
        probe_facts["systems_uri"] = systems_uri

    return True, None, probe_facts


def probe_os(host, port, timeout):
    """OS 채널 프로토콜 프로브 (SSH banner 또는 WinRM endpoint)"""
    if port == 22:
        return ssh_banner_check(host, port, timeout)
    elif port in (5985, 5986):
        scheme = "https" if port == 5986 else "http"
        url = "{0}://{1}:{2}/wsman".format(scheme, host, port)
        ok, err, payload = http_get(url, timeout, verify=False)
        if ok or (payload and payload.get("status_code") in (200, 401, 405)):
            return True, None, {
                "transport": "winrm",
                "scheme": scheme,
                "port": port,
            }
        return False, err, None
    else:
        return False, "지원하지 않는 OS 포트: {0}".format(port), None


def probe_esxi(host, port, timeout, verify=False):
    """vSphere API endpoint 프로브"""
    url = "https://{0}:{1}/sdk".format(host, port)
    ok, err, payload = http_get(url, timeout, verify=verify)
    # /sdk는 보통 200 또는 SOAP fault를 반환 — 둘 다 "서비스 있음"으로 판단
    if ok:
        return True, None, {"vsphere_endpoint": url}
    # 일부 ESXi는 /sdk에 POST만 허용하므로, 연결만 되면 성공으로 봄
    # 404도 포함: ESXi 7+에서 GET /sdk → 404이지만 POST(SOAP)는 정상 응답
    if payload and payload.get("status_code") in (200, 301, 302, 404, 405, 500):
        return True, None, {"vsphere_endpoint": url}
    return False, err, None


def run_module():
    module = AnsibleModule(
        argument_spec=dict(
            host=dict(type="str", required=True),
            channel=dict(
                type="str", required=True, choices=["redfish", "os", "esxi"]
            ),
            ports=dict(type="list", elements="int", default=[]),
            timeout_port=dict(type="float", default=3.0),
            timeout_protocol=dict(type="float", default=6.0),
            timeout_auth=dict(type="float", default=8.0),
            username=dict(type="str", required=False, no_log=True),
            password=dict(type="str", required=False, no_log=True),
            verify_ssl=dict(type="bool", default=False),
        ),
        supports_check_mode=True,
    )

    host = module.params["host"]
    channel = module.params["channel"]
    ports = module.params["ports"] or CHANNEL_DEFAULT_PORTS.get(channel, [])
    verify_ssl = module.params["verify_ssl"]

    result = {
        "changed": False,
        "reachable": False,
        "port_open": False,
        "protocol_supported": False,
        "auth_success": None,
        "failure_stage": None,
        "failure_reason": None,
        "detail": None,
        "checked_ports": ports,
        "selected_port": None,
        "probe_facts": {},
    }

    # OS 채널 추가 정보
    if channel == "os":
        result["detected_os"] = None
        result["detected_port"] = None
        result["winrm_scheme"] = None

    # =========================================================================
    # Stage 1: reachable (TCP 포트 연결로 확인)
    # =========================================================================
    any_port_open = False
    open_port = None

    for port in ports:
        ok, err = tcp_check(host, port, module.params["timeout_port"])
        if ok:
            any_port_open = True
            open_port = port
            break

    if not any_port_open:
        result["reachable"] = False
        result["port_open"] = False
        result["failure_stage"] = "reachable"
        result["failure_reason"] = (
            "대상 호스트에 연결할 수 없습니다. "
            "네트워크 도달 불가 또는 호스트가 꺼져 있습니다."
        )
        result["detail"] = "ports={0}, host={1}".format(ports, host)
        module.exit_json(**result)

    result["reachable"] = True
    result["port_open"] = True
    result["selected_port"] = open_port

    # OS 채널: 포트 기반 OS 유형 판별
    if channel == "os":
        if open_port == 22:
            result["detected_os"] = "linux"
        elif open_port in (5985, 5986):
            result["detected_os"] = "windows"
            result["winrm_scheme"] = "https" if open_port == 5986 else "http"
        result["detected_port"] = open_port

    # =========================================================================
    # Stage 3: protocol_supported (프로토콜 핸드셰이크)
    # =========================================================================
    timeout_proto = module.params["timeout_protocol"]

    if channel == "redfish":
        ok, err, facts = probe_redfish(
            host, open_port, timeout_proto, verify=verify_ssl
        )
    elif channel == "os":
        ok, err, facts = probe_os(host, open_port, timeout_proto)
    elif channel == "esxi":
        ok, err, facts = probe_esxi(
            host, open_port, timeout_proto, verify=verify_ssl
        )
    else:
        ok, err, facts = False, "알 수 없는 채널: {0}".format(channel), None

    if not ok:
        result["protocol_supported"] = False
        result["failure_stage"] = "protocol"
        result["failure_reason"] = CHANNEL_PROTOCOL_MESSAGES.get(
            channel, "프로토콜 확인 실패"
        )
        result["detail"] = err
        module.exit_json(**result)

    result["protocol_supported"] = True
    if facts:
        result["probe_facts"].update(facts)

    # =========================================================================
    # Stage 4: auth_success (인증 시도 — 선택적)
    # =========================================================================
    username = module.params.get("username")
    password = module.params.get("password")
    timeout_auth = module.params["timeout_auth"]

    if username and password:
        if channel == "redfish":
            # Redfish: Systems 목록 접근으로 인증 확인
            url = "https://{0}:{1}/redfish/v1/Systems".format(host, open_port)
            ok, err, payload = http_get(
                url,
                timeout_auth,
                verify=verify_ssl,
                auth=(username, password),
            )
            if ok:
                result["auth_success"] = True
                # Systems 응답에서 벤더 힌트 추출 시도
                json_data = payload.get("json") if payload else None
                if json_data:
                    members = json_data.get("Members", [])
                    if members:
                        first_uri = members[0].get("@odata.id", "")
                        result["probe_facts"]["first_system_uri"] = first_uri
            else:
                result["auth_success"] = False
                result["failure_stage"] = "auth"
                result["failure_reason"] = (
                    "BMC 인증 실패: 사용자명 또는 비밀번호를 확인하세요."
                )
                result["detail"] = err
                module.exit_json(**result)

        elif channel == "esxi":
            # ESXi: SOAP endpoint에 인증 시도
            result["auth_success"] = None  # vSphere 모듈이 별도 처리

        elif channel == "os":
            # OS: SSH/WinRM 인증은 Ansible 자체가 처리
            result["auth_success"] = None
    else:
        # 인증 정보 없으면 스킵
        result["auth_success"] = None

    module.exit_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()
