# -*- coding: utf-8 -*-
# ==============================================================================
# adapter_loader.py — Adapter 자동 탐색 및 선택 Lookup Plugin
# ==============================================================================
# adapters/<channel>/ 디렉토리의 YAML 파일을 스캔하고,
# probe facts와 match 조건을 비교하여 최적의 adapter를 선택합니다.
#
# 사용법 (Ansible task):
#   - set_fact:
#       _selected_adapter: >-
#         {{ lookup('adapter_loader',
#                   channel='redfish',
#                   facts=_precheck_result.probe_facts,
#                   repo_root=lookup('env','REPO_ROOT')) }}
# ==============================================================================

__metaclass__ = type

DOCUMENTATION = r"""
---
name: adapter_loader
author: ClovierOne Portal Team
short_description: Adapter 자동 탐색 및 선택
description:
  - adapters/<channel>/ 디렉토리의 YAML 파일을 스캔합니다.
  - 각 adapter의 match 조건을 probe facts와 비교합니다.
  - 가장 높은 점수의 adapter를 반환합니다.
options:
  channel:
    description: 수집 채널 (redfish/os/esxi)
    required: true
  facts:
    description: probe facts 딕셔너리
    required: false
    default: {}
  repo_root:
    description: 프로젝트 루트 경로
    required: false
"""

from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase
from ansible.utils.display import Display

import glob
import os
import yaml
import sys

display = Display()


class LookupModule(LookupBase):
    def run(self, terms, variables=None, **kwargs):
        channel = kwargs.get("channel")
        if not channel:
            raise AnsibleError("adapter_loader: 'channel' 파라미터가 필요합니다.")

        facts = kwargs.get("facts", {}) or {}

        # repo_root 결정
        repo_root = kwargs.get("repo_root", "")
        if not repo_root:
            repo_root = os.environ.get("REPO_ROOT", "")
        if not repo_root:
            # Ansible 변수에서 시도
            if variables:
                repo_root = variables.get("REPO_ROOT", "")
        if not repo_root:
            raise AnsibleError(
                "adapter_loader: REPO_ROOT를 결정할 수 없습니다. "
                "repo_root 파라미터 또는 REPO_ROOT 환경변수를 설정하세요."
            )

        # module_utils 경로를 sys.path에 추가
        module_utils_path = os.path.join(repo_root, "module_utils")
        if module_utils_path not in sys.path:
            sys.path.insert(0, module_utils_path)

        # adapter_common import
        try:
            from adapter_common import (
                load_vendor_aliases,
                normalize_vendor,
                adapter_matches,
                adapter_score,
            )
        except ImportError:
            raise AnsibleError(
                "adapter_loader: module_utils/adapter_common.py를 "
                "import할 수 없습니다. REPO_ROOT={0}".format(repo_root)
            )

        # vendor_aliases 로드
        aliases_path = os.path.join(
            repo_root, "common", "vars", "vendor_aliases.yml"
        )
        aliases = load_vendor_aliases(aliases_path)

        # adapter 디렉토리 스캔
        adapter_dir = os.path.join(repo_root, "adapters", channel)
        if not os.path.isdir(adapter_dir):
            raise AnsibleError(
                "adapter_loader: adapter 디렉토리를 찾을 수 없습니다: "
                "{0}".format(adapter_dir)
            )

        adapters = []
        for path in sorted(glob.glob(os.path.join(adapter_dir, "*.yml"))):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                data["_source_file"] = path
                data["_filename"] = os.path.basename(path)
                adapters.append(data)
            except Exception as e:
                display.warning(
                    "adapter_loader: {0} 로드 실패: {1}".format(path, str(e))
                )

        if not adapters:
            raise AnsibleError(
                "adapter_loader: {0} 디렉토리에 adapter YAML이 없습니다.".format(
                    adapter_dir
                )
            )

        # match 평가
        matched = []
        for adapter in adapters:
            if adapter_matches(adapter, facts, aliases):
                score = adapter_score(adapter, facts, aliases)
                if score > -9999:
                    matched.append((score, adapter))
                    display.vvv(
                        "adapter_loader: {0} matched (score={1})".format(
                            adapter.get("adapter_id", adapter.get("_filename")),
                            score,
                        )
                    )

        if not matched:
            # generic fallback 검색
            for adapter in adapters:
                if adapter.get("generic", False):
                    display.v(
                        "adapter_loader: generic fallback 사용: {0}".format(
                            adapter.get("adapter_id")
                        )
                    )
                    return [adapter]

            raise AnsibleError(
                "adapter_loader: channel={0}에 매칭되는 adapter가 없습니다. "
                "facts={1}".format(channel, facts)
            )

        # 점수순 정렬 (내림차순)
        matched.sort(key=lambda x: x[0], reverse=True)
        best_score, best_adapter = matched[0]

        display.v(
            "adapter_loader: 선택됨 — {0} (score={1})".format(
                best_adapter.get("adapter_id", "unknown"), best_score
            )
        )

        return [best_adapter]
