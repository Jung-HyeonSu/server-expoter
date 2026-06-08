"""HPE iLO 에뮬레이터 record/replay 하네스 (공용 모듈).

배경 (rule 21 R1 / rule 25 R7-B):
    server-exporter 의 본질적 제약은 lab 부재다. 실측 HPE 장비는 1 대뿐
    (DL380 Gen11, iLO6 v1.73). 본 하네스는 HPE 공식 iLO Redfish 에뮬레이터
    (BSD-3, v1.7.0) 를 **고품질 테스트 타깃** 으로 써서 redfish_gather.py 의
    파싱/정규화 엔진에 오프라인·결정적 회귀 안전망을 건다.

    **에뮬레이터 != 실장비.** 본 하네스가 만든 fixture / golden 은
    schema/baseline_v1/ 실측 baseline 으로 승격하지 않는다. 전부
    tests/fixtures/redfish/hpe_emulator_* 아래 "emulator-derived" 로 라벨링.

설계:
    - record (capture): rg._get / rg._get_noauth 를 실 에뮬레이터로 passthrough
      하면서 (path -> 응답) 을 기록 → recording.json.
    - replay (test): 기록된 recording.json 을 (path -> 응답) lookup 으로 주입해
      **실제** detect_vendor → _collect_all_sections → _compute_final_status 를
      오프라인에서 구동 → golden(expected_output.json) 과 비교.

    두 경로 모두 main() gather mode 흐름을 1:1 미러링 (redfish_gather.py L3816~).
"""
from __future__ import annotations

import sys
import types
from pathlib import Path

# ---------------------------------------------------------------------------
# redfish_gather 모듈 import (기존 unit test 와 동일 패턴 — ansible stub)
#   tests/unit/test_redfish_storage_controller.py L14~27 참조.
# ---------------------------------------------------------------------------
REPO = Path(__file__).resolve().parents[2]
_LIB = str(REPO / "redfish-gather" / "library")
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

_stub_basic = types.ModuleType("ansible.module_utils.basic")
_stub_basic.AnsibleModule = object
_stub_module_utils = types.ModuleType("ansible.module_utils")
_stub_module_utils.basic = _stub_basic
_stub_ansible = types.ModuleType("ansible")
_stub_ansible.module_utils = _stub_module_utils
sys.modules.setdefault("ansible", _stub_ansible)
sys.modules.setdefault("ansible.module_utils", _stub_module_utils)
sys.modules.setdefault("ansible.module_utils.basic", _stub_basic)

import redfish_gather as rg  # noqa: E402

# import 시점의 "진짜" 네트워크 transport (swap 전 원본 보존).
_REAL_GET = rg._get
_REAL_GET_NOAUTH = rg._get_noauth

# replay 시 기록에 없는 path 응답 (graceful — 코드의 404 처리 경로 그대로 탐).
_REPLAY_MISS = (404, {}, "replay-miss: path not in recording")


def run_gather(get_impl, noauth_impl, ip="127.0.0.1",
               user="root", pw="root_password", timeout=30, verify_ssl=False):
    """main() gather mode 흐름을 1:1 미러링해 모듈 산출 snapshot 을 반환.

    get_impl / noauth_impl: rg._get / rg._get_noauth 를 대체할 transport.
        (record 시 passthrough+기록, replay 시 lookup)

    Returns: dict — main() exit_json 의 gather 산출 필드 부분집합.
        list 필드는 정렬해 결정적(deterministic) 비교 가능.
    """
    saved_get, saved_noauth = rg._get, rg._get_noauth
    rg._get, rg._get_noauth = get_impl, noauth_impl
    try:
        vendor, system_uri, manager_uri, chassis_uri, det_errors, service_root = \
            rg.detect_vendor(ip, user, pw, timeout, verify_ssl)
        probe_facts = rg._extract_probe_facts(service_root, vendor)

        all_errors = list(det_errors)
        collected, failed, unsupported = [], [], []

        if not system_uri:
            return {
                "vendor": vendor,
                "status": "failed",
                "collected": [],
                "failed_sections": ["all"],
                "unsupported_sections": [],
                "data": {},
                "multi_node": None,
                "probe_facts": probe_facts,
                "error_count": len(all_errors),
            }

        data = rg._collect_all_sections(
            ip, vendor, system_uri, manager_uri, chassis_uri,
            user, pw, timeout, verify_ssl,
            all_errors, collected, failed, unsupported,
            manager_layout=None,
            product_hint=rg._safe(service_root, "Product"),
        )
        multi_node = rg._collect_multi_node_topology(
            ip, vendor, service_root, user, pw, timeout, verify_ssl,
            manager_layout=None,
        )
        final_status, clean = rg._compute_final_status(collected, failed, all_errors)

        return {
            "vendor": vendor,
            "status": final_status,
            "collected": sorted(clean),
            "failed_sections": sorted(set(failed)),
            "unsupported_sections": sorted(set(unsupported)),
            "data": data,
            "multi_node": multi_node,
            "probe_facts": probe_facts,
            "error_count": len(all_errors),
        }
    finally:
        rg._get, rg._get_noauth = saved_get, saved_noauth


def make_recorder():
    """실 에뮬레이터로 passthrough 하며 (path -> 응답) 을 기록.

    Returns: (get_impl, noauth_impl, recording: dict[str, list])
        recording key: 'get::<path>' / 'noauth::<path>'
        recording value: [status, data, err] (JSON 직렬화 가능)
    """
    recording: dict[str, list] = {}

    def get_impl(bmc_ip, path, username, password, timeout, verify_ssl):
        status, data, err = _REAL_GET(bmc_ip, path, username, password, timeout, verify_ssl)
        recording[f"get::{path}"] = [status, data, err]
        return status, data, err

    def noauth_impl(bmc_ip, path, timeout, verify_ssl):
        status, data, err = _REAL_GET_NOAUTH(bmc_ip, path, timeout, verify_ssl)
        recording[f"noauth::{path}"] = [status, data, err]
        return status, data, err

    return get_impl, noauth_impl, recording


def make_replayer(recording):
    """기록된 recording 을 (path -> 응답) lookup 으로 주입 (오프라인).

    Returns: (get_impl, noauth_impl)
    """
    def get_impl(bmc_ip, path, username, password, timeout, verify_ssl):
        rec = recording.get(f"get::{path}")
        if rec is None:
            return _REPLAY_MISS
        return rec[0], rec[1], rec[2]

    def noauth_impl(bmc_ip, path, timeout, verify_ssl):
        rec = recording.get(f"noauth::{path}")
        if rec is None:
            return _REPLAY_MISS
        return rec[0], rec[1], rec[2]

    return get_impl, noauth_impl


# golden 비교에서 strict equality 대상 (errors 는 count 만 — 메시지 verbose 회피).
GOLDEN_KEYS = (
    "vendor", "status", "collected", "failed_sections",
    "unsupported_sections", "data", "multi_node", "probe_facts",
)
