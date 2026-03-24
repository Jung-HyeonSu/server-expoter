# -*- coding: utf-8 -*-
"""
Ansible Callback Plugin — json_only  v2
========================================
OUTPUT 태스크의 결과만 JSON 으로 stdout 에 출력한다.
나머지 모든 Ansible 로그(play/task 헤더, ok/changed 메시지 등)는 억제한다.

포털은 이 JSON 출력만 파싱한다.

환경변수:
  ANSIBLE_JSON_OUTPUT_TASK  — 캡처할 태스크 이름 (기본값: OUTPUT)
"""
# 단일 복사본 — 채널별 복사본(os-gather/, esxi-gather/, redfish-gather/)은 제거됨.
# 프로젝트 루트의 ansible.cfg가 callback_plugins = ./callback_plugins 로 이 파일을 참조한다.
__metaclass__ = type

import json
import os
import sys

from ansible.plugins.callback import CallbackBase

DOCUMENTATION = r'''
    name: json_only
    type: stdout
    short_description: Print only OUTPUT task result as JSON
    description:
      - Suppresses all Ansible output except the task named OUTPUT (configurable).
      - The OUTPUT task's msg field is printed as compact JSON to stdout.
      - Errors are written to stderr as structured JSON.
    options:
      output_task_name:
        description: Name of the task whose result will be printed.
        env:
          - name: ANSIBLE_JSON_OUTPUT_TASK
        default: OUTPUT
'''


class CallbackModule(CallbackBase):

    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE    = 'stdout'
    CALLBACK_NAME    = 'json_only'
    CALLBACK_NEEDS_ENABLED = False

    def __init__(self):
        super(CallbackModule, self).__init__()
        self._output_task = os.getenv('ANSIBLE_JSON_OUTPUT_TASK', 'OUTPUT')

    # ── 내부 유틸 ────────────────────────────────────────────────────────────

    def _emit(self, data, file=None):
        """dict/list/str → compact JSON → stdout (또는 file)"""
        target = file or sys.stdout
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except (json.JSONDecodeError, ValueError):
                pass  # 그냥 문자열로 출력
        print(json.dumps(data, ensure_ascii=False, separators=(',', ':')),
              file=target, flush=True)

    def _emit_error(self, error_type, message, host=None, task=None):
        payload = {
            'error_type': error_type,
            'message':    str(message),
        }
        if host:
            payload['host'] = host
        if task:
            payload['task'] = task
        self._emit(payload, file=sys.stderr)

    # ── 캡처 대상 태스크 처리 ────────────────────────────────────────────────

    def v2_runner_on_ok(self, result):
        if result._task.name != self._output_task:
            return
        res = result._result
        if 'msg' in res:
            self._emit(res['msg'])
        elif 'ansible_facts' in res:
            # set_fact 결과가 OUTPUT 태스크에 연결된 경우
            self._emit(res['ansible_facts'])

    def v2_runner_on_failed(self, result, ignore_errors=False):
        if result._task.name != self._output_task:
            return
        msg = (result._result.get('msg')
               or result._result.get('stderr')
               or 'task failed')
        self._emit_error(
            error_type='task_failed',
            message=msg,
            host=result._host.get_name(),
            task=result._task.name,
        )

    def v2_runner_on_unreachable(self, result):
        if result._task.name != self._output_task:
            return
        msg = result._result.get('msg', 'host unreachable')
        self._emit_error(
            error_type='host_unreachable',
            message=msg,
            host=result._host.get_name(),
        )

    # ── 억제할 이벤트 (아무것도 출력하지 않음) ──────────────────────────────

    def v2_playbook_on_start(self, playbook):             pass
    def v2_playbook_on_play_start(self, play):            pass
    def v2_playbook_on_task_start(self, task, is_conditional): pass
    def v2_runner_on_skipped(self, result):               pass
    def v2_runner_on_no_hosts(self, pattern):             pass
    def v2_playbook_on_no_hosts_matched(self):            pass
    def v2_playbook_on_no_hosts_remaining(self):          pass
    def v2_playbook_on_stats(self, stats):                pass
    def v2_runner_item_on_ok(self, result):               pass
    def v2_runner_item_on_failed(self, result):           pass
    def v2_runner_item_on_skipped(self, result):          pass
    def v2_runner_retry(self, result):                    pass
    def v2_runner_on_async_ok(self, result):              pass
    def v2_runner_on_async_failed(self, result):          pass
    def v2_playbook_on_handler_task_start(self, task):    pass
    def v2_on_any(self, *args, **kwargs):                 pass
