#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
field_dictionary.yml validator

검증 항목:
  1. YAML 파싱 성공
  2. 모든 entry에 help_ko, help_en 존재
  3. priority 값이 must/nice/skip 중 하나
  4. channel 값이 [redfish, os, esxi] 범위
  5. 중복 key 없음 (YAML 특성상 자동 덮어쓰기 — 파일 원문으로 검증)
  6. path가 실제 output 구조와 대응 가능한 형태인지

사용법:
  python3 tests/validate_field_dictionary.py

  또는 프로젝트 루트에서:
  python3 tests/validate_field_dictionary.py --schema schema/examples/redfish_success.json
"""

import yaml
import json
import sys
import os
import re
from collections import Counter

DICT_PATH = os.path.join(os.path.dirname(__file__), '..', 'schema', 'field_dictionary.yml')
SCHEMA_EXAMPLES = [
    os.path.join(os.path.dirname(__file__), '..', 'schema', 'examples', 'redfish_success.json'),
    os.path.join(os.path.dirname(__file__), '..', 'schema', 'examples', 'os_partial.json'),
]

VALID_PRIORITIES = {'must', 'nice', 'skip'}
VALID_CHANNELS = {'redfish', 'os', 'esxi'}

def load_dictionary(path):
    """YAML 파싱 + 중복 key 검출"""
    with open(path, 'r', encoding='utf-8') as f:
        raw_text = f.read()

    # 중복 key 검출: fields: 하위의 top-level key를 정규식으로 추출
    field_keys = re.findall(r'^  (["\']?[\w\.\[\]\*]+["\']?):', raw_text, re.MULTILINE)
    # 따옴표 제거
    clean_keys = [k.strip('"').strip("'") for k in field_keys]
    duplicates = [k for k, count in Counter(clean_keys).items() if count > 1]

    # YAML 파싱
    data = yaml.safe_load(raw_text)
    return data, duplicates, clean_keys


def extract_output_paths(json_data, prefix=''):
    """JSON 구조에서 가능한 field path를 추출"""
    paths = set()
    if isinstance(json_data, dict):
        for k, v in json_data.items():
            if k.startswith('@') or k.startswith('_'):
                continue
            full = f"{prefix}.{k}" if prefix else k
            paths.add(full)
            if isinstance(v, dict):
                paths.update(extract_output_paths(v, full))
            elif isinstance(v, list) and v:
                # 배열: path[]와 path[].subkey 형태
                paths.add(f"{full}[]")
                if isinstance(v[0], dict):
                    for sub_path in extract_output_paths(v[0], ''):
                        paths.add(f"{full}[].{sub_path}")
    return paths


def validate():
    errors = []
    warnings = []
    checks = []

    # ── Check 1: YAML 파싱 ──
    try:
        data, duplicates, raw_keys = load_dictionary(DICT_PATH)
        checks.append(('YAML parse', 'PASS', f'{len(raw_keys)} keys found'))
    except Exception as e:
        checks.append(('YAML parse', 'FAIL', str(e)))
        print_results(checks, errors, warnings)
        return 1

    fields = data.get('fields', {})
    if not fields:
        errors.append('No "fields" section found in dictionary')
        checks.append(('fields section', 'FAIL', 'missing'))
        print_results(checks, errors, warnings)
        return 1
    checks.append(('fields section', 'PASS', f'{len(fields)} entries'))

    # ── Check 2: 중복 key ──
    if duplicates:
        errors.append(f'Duplicate keys: {duplicates}')
        checks.append(('duplicate keys', 'FAIL', str(duplicates)))
    else:
        checks.append(('duplicate keys', 'PASS', 'no duplicates'))

    # ── Check 3-5: Entry-level validation ──
    missing_ko = []
    missing_en = []
    bad_priority = []
    bad_channel = []

    for path, entry in fields.items():
        if not isinstance(entry, dict):
            errors.append(f'{path}: entry is not a dict')
            continue

        # help_ko
        if 'help_ko' not in entry or not entry['help_ko']:
            missing_ko.append(path)
        # help_en
        if 'help_en' not in entry or not entry['help_en']:
            missing_en.append(path)
        # priority
        pri = entry.get('priority', '')
        if pri not in VALID_PRIORITIES:
            bad_priority.append(f'{path}: {pri}')
        # channel
        channels = entry.get('channel', [])
        if not isinstance(channels, list):
            bad_channel.append(f'{path}: channel is not a list')
        else:
            for ch in channels:
                if ch not in VALID_CHANNELS:
                    bad_channel.append(f'{path}: invalid channel "{ch}"')

    if missing_ko:
        errors.append(f'Missing help_ko: {missing_ko}')
        checks.append(('help_ko presence', 'FAIL', f'{len(missing_ko)} missing'))
    else:
        checks.append(('help_ko presence', 'PASS', f'all {len(fields)} have help_ko'))

    if missing_en:
        errors.append(f'Missing help_en: {missing_en}')
        checks.append(('help_en presence', 'FAIL', f'{len(missing_en)} missing'))
    else:
        checks.append(('help_en presence', 'PASS', f'all {len(fields)} have help_en'))

    if bad_priority:
        errors.append(f'Invalid priority: {bad_priority}')
        checks.append(('priority values', 'FAIL', str(bad_priority)))
    else:
        checks.append(('priority values', 'PASS', f'all valid (must/nice/skip)'))

    if bad_channel:
        errors.append(f'Invalid channel: {bad_channel}')
        checks.append(('channel values', 'FAIL', str(bad_channel)))
    else:
        checks.append(('channel values', 'PASS', f'all valid (redfish/os/esxi)'))

    # ── Check 6: Path vs schema/examples ──
    all_output_paths = set()
    schema_files_checked = 0
    for schema_path in SCHEMA_EXAMPLES:
        if os.path.exists(schema_path):
            try:
                with open(schema_path) as f:
                    schema_data = json.load(f)
                paths = extract_output_paths(schema_data)
                all_output_paths.update(paths)
                schema_files_checked += 1
            except Exception:
                pass

    if all_output_paths:
        # Normalize dictionary paths for comparison
        unmatched = []
        for dict_path in fields.keys():
            # Skip wildcard paths — they match by convention
            if '*' in dict_path:
                continue
            # Normalize: remove data. prefix, handle [] notation
            # Dictionary paths are relative (e.g., "hardware.health" = "data.hardware.health")
            # Check if any output path ends with the dictionary path
            normalized = dict_path.replace('[]', '')
            found = False
            for op in all_output_paths:
                # Strip "data." prefix for comparison
                op_norm = op.replace('data.', '', 1) if op.startswith('data.') else op
                op_norm = op_norm.replace('[]', '')
                if op_norm == normalized or op_norm.endswith('.' + normalized) or normalized.endswith('.' + op_norm):
                    found = True
                    break
            if not found:
                # Not necessarily an error — could be a valid field not in examples
                warnings.append(f'{dict_path}: no match in schema examples (may be valid)')

        checks.append(('path vs schema', 'PASS' if not unmatched else 'WARN',
                       f'{schema_files_checked} schema files, {len(warnings)} unmatched'))
    else:
        checks.append(('path vs schema', 'SKIP', 'no schema examples found'))

    # ── Summary ──
    # Priority distribution
    pri_counts = Counter(entry.get('priority', 'unknown') for entry in fields.values())
    checks.append(('priority distribution', 'INFO',
                   f"must={pri_counts.get('must',0)}, nice={pri_counts.get('nice',0)}, skip={pri_counts.get('skip',0)}"))

    # Channel distribution
    ch_counts = Counter()
    for entry in fields.values():
        for ch in entry.get('channel', []):
            ch_counts[ch] += 1
    checks.append(('channel distribution', 'INFO',
                   f"redfish={ch_counts.get('redfish',0)}, os={ch_counts.get('os',0)}, esxi={ch_counts.get('esxi',0)}"))

    print_results(checks, errors, warnings)
    return 1 if errors else 0


def print_results(checks, errors, warnings):
    print('=' * 80)
    print('field_dictionary.yml VALIDATION RESULTS')
    print('=' * 80)
    print()

    for name, status, detail in checks:
        icon = '[OK]' if status == 'PASS' else '[FAIL]' if status == 'FAIL' else '[WARN]' if status == 'WARN' else '[INFO]'
        print(f'  {icon} {name}: {detail}')

    if warnings:
        print()
        print('WARNINGS:')
        for w in warnings:
            print(f'  [WARN] {w}')

    if errors:
        print()
        print('ERRORS:')
        for e in errors:
            print(f'  [FAIL] {e}')

    print()
    total = len(checks)
    passed = sum(1 for _, s, _ in checks if s == 'PASS')
    failed = sum(1 for _, s, _ in checks if s == 'FAIL')
    print(f'Total: {total} checks, {passed} passed, {failed} failed, {len(warnings)} warnings')
    print('RESULT:', 'PASS' if not errors else 'FAIL')


if __name__ == '__main__':
    sys.exit(validate())
