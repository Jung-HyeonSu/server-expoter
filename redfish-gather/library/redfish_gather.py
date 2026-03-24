#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Ansible Custom Module: redfish_gather  v4
------------------------------------------
검증된 벤더별 URI 구조 (공식 문서 기반):

  HPE iLO 5/6  : Systems/1               / Managers/1   (Oem.Hpe / Oem.Hp fallback)
  Dell iDRAC 9 : Systems/System.Embedded.1 / Managers/iDRAC.Embedded.1  (Oem.Dell)
  Lenovo XCC   : Systems/1               / Managers/1   (Oem.Lenovo)
  Supermicro   : Systems/1               / Managers/1   (Oem.Supermicro)
    Manufacturer = "Super Micro Computer, Inc."

외부 라이브러리 불필요 — Python stdlib(urllib, ssl, socket) 만 사용
"""

__metaclass__ = type

DOCUMENTATION = r'''
module: redfish_gather
short_description: Gather hardware info via Redfish API (Dell/HPE/Lenovo/Supermicro)
options:
  bmc_ip:     required, str
  username:   required, str
  password:   required, str, no_log
  timeout:    optional, int, default 30
  verify_ssl: optional, bool, default false
'''

import json, socket, sys, traceback

def _removeprefix(s, prefix):
    """str.removeprefix() 호환 (Python 3.8 이하 지원)"""
    if s.startswith(prefix):
        return s[len(prefix):]
    return s

try:
    import urllib.request as urlreq
    import urllib.error as urlerr
    import ssl, base64
    HAS_URLLIB = True
except ImportError:
    HAS_URLLIB = False

from ansible.module_utils.basic import AnsibleModule


# ── HTTP 유틸 ────────────────────────────────────────────────────────────────

def _ctx(verify_ssl):
    ctx = ssl.create_default_context()
    if not verify_ssl:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx

def _auth(username, password):
    return 'Basic ' + base64.b64encode(f'{username}:{password}'.encode()).decode()

def _get(bmc_ip, path, username, password, timeout, verify_ssl):
    url = f'https://{bmc_ip}/redfish/v1/{path.lstrip("/")}'
    req = urlreq.Request(url, headers={
        'Authorization': _auth(username, password),
        'Accept': 'application/json',
        'OData-Version': '4.0',
    })
    try:
        with urlreq.urlopen(req, context=_ctx(verify_ssl), timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode('utf-8', errors='replace')), None
    except urlerr.HTTPError as e:
        try:    body = json.loads(e.read().decode('utf-8', errors='replace'))
        except (json.JSONDecodeError, ValueError, UnicodeDecodeError): body = {}
        return e.code, body, f'HTTP {e.code}: {e.reason}'
    except urlerr.URLError as e:
        return 0, {}, f'URLError: {e.reason}'
    except socket.timeout:
        return 0, {}, f'Timeout after {timeout}s'
    except (OSError, ValueError) as e:
        return 0, {}, f'Unexpected: {type(e).__name__}: {e}'

def _p(uri):
    """@odata.id URI → _get() path 인수"""
    return _removeprefix(_removeprefix(uri.lstrip('/'), 'redfish/v1/'), 'redfish/v1').rstrip('/')

def _safe(d, *keys, default=None):
    for k in keys:
        if not isinstance(d, dict): return default
        d = d.get(k, default)
        if d is None: return default
    return d

def _err(section, message, detail=None):
    return {'section': section, 'message': str(message), 'detail': detail}


# ── 벤더 정규화 ──────────────────────────────────────────────────────────────

# 내장 벤더 매핑 (vendor_aliases.yml 로드 불가 시 fallback)
# ※ common/vars/vendor_aliases.yml과 동기화 필요 — 변경 시 양쪽 모두 수정할 것
# canonical vendors: dell, hpe, lenovo, supermicro, cisco
_BUILTIN_VENDOR_MAP = {
    'dell': 'dell', 'dell inc.': 'dell',
    'hpe': 'hpe', 'hewlett packard enterprise': 'hpe', 'hp enterprise': 'hpe', 'hp': 'hpe',
    'lenovo': 'lenovo',
    'supermicro': 'supermicro', 'super micro computer, inc.': 'supermicro',
    'super micro computer': 'supermicro',
    'cisco': 'cisco', 'cisco systems inc': 'cisco', 'cisco systems inc.': 'cisco',
    'cisco systems': 'cisco',
}

def _load_vendor_aliases_file():
    """vendor_aliases.yml을 로드합니다. 실패 시 빈 dict 반환."""
    import os
    try:
        import yaml
    except ImportError:
        return {}
    # yaml 사용 시작
    # REPO_ROOT 기반 경로
    repo_root = os.environ.get('REPO_ROOT', '')
    if not repo_root:
        return {}
    path = os.path.join(repo_root, 'common', 'vars', 'vendor_aliases.yml')
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
        mapping = {}
        for canonical, alias_list in data.get('vendor_aliases', {}).items():
            for alias in alias_list:
                mapping[alias.strip().lower()] = canonical
        return mapping
    except (IOError, OSError, yaml.YAMLError, AttributeError, TypeError):
        return {}

def _normalize_vendor_from_aliases(mfr_lower):
    """
    Manufacturer 문자열(소문자)을 정규화된 벤더명으로 변환합니다.
    1차: vendor_aliases.yml (REPO_ROOT 기반)
    2차: 내장 fallback 맵
    3차: 부분 매칭 (substring)
    """
    # vendor_aliases.yml 시도
    aliases = _load_vendor_aliases_file()
    merged = {**_BUILTIN_VENDOR_MAP, **aliases}  # aliases 우선

    # 정확 매칭
    if mfr_lower in merged:
        return merged[mfr_lower]

    # 부분 매칭 (기존 로직 호환)
    for key, canon in merged.items():
        if key in mfr_lower or mfr_lower in key:
            return canon

    return 'unknown'


# ── 벤더 감지 ────────────────────────────────────────────────────────────────

def _get_noauth(bmc_ip, path, timeout, verify_ssl):
    """인증 없이 GET 요청 (ServiceRoot 등 무인증 엔드포인트용)"""
    url = f'https://{bmc_ip}/redfish/v1/{path.lstrip("/")}'
    req = urlreq.Request(url, headers={
        'Accept': 'application/json',
        'OData-Version': '4.0',
    })
    try:
        with urlreq.urlopen(req, context=_ctx(verify_ssl), timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode('utf-8', errors='replace')), None
    except urlerr.HTTPError as e:
        try:    body = json.loads(e.read().decode('utf-8', errors='replace'))
        except (json.JSONDecodeError, ValueError, UnicodeDecodeError): body = {}
        return e.code, body, f'HTTP {e.code}: {e.reason}'
    except urlerr.URLError as e:
        return 0, {}, f'URLError: {e.reason}'
    except socket.timeout:
        return 0, {}, f'Timeout after {timeout}s'
    except (OSError, ValueError) as e:
        return 0, {}, f'Unexpected: {type(e).__name__}: {e}'


def _detect_vendor_from_service_root(root):
    """
    ServiceRoot 응답에서 벤더를 식별합니다 (무인증).

    식별 알고리즘 (대소문자 무시):
      1. Oem 객체의 키 이름 확인
      2. Vendor 필드 확인
      3. Product 필드에 벤더명 포함 확인
      4. Name 필드에 벤더명 포함 확인
      5. 모두 해당 없으면 None 반환

    Returns: vendor 문자열 ('dell', 'hpe', 'lenovo', 'supermicro') 또는 None
    """
    # _BUILTIN_VENDOR_MAP 기반 통합 감지 — 하드코딩 분기 대신 map 사용
    vm = _BUILTIN_VENDOR_MAP

    # 1. Oem 객체의 키 이름 확인
    oem = _safe(root, 'Oem')
    if isinstance(oem, dict):
        for key in oem:
            k = key.lower()
            if k in vm:
                return vm[k]

    # 2. Vendor 필드 확인 (정확 매칭)
    vendor_field = _safe(root, 'Vendor')
    if vendor_field and isinstance(vendor_field, str):
        v = vendor_field.lower().strip().rstrip('.')
        if v in vm:
            return vm[v]

    # 3. Product 필드에 벤더명 포함 확인
    product = _safe(root, 'Product')
    if product and isinstance(product, str):
        p = product.lower()
        for alias, canonical in vm.items():
            if alias in p:
                return canonical
        if 'ilo' in p or 'proliant' in p:
            return 'hpe'

    # 4. Name 필드에 벤더명 포함 확인
    name = _safe(root, 'Name')
    if name and isinstance(name, str):
        n = name.lower()
        for alias, canonical in vm.items():
            if alias in n:
                return canonical

    # 5. 해당 없음
    return None


def detect_vendor(bmc_ip, username, password, timeout, verify_ssl):
    """
    ServiceRoot(무인증)에서 벤더를 식별하고,
    인증된 요청으로 Systems/Managers/Chassis URI를 해석합니다.

    Returns: (vendor, system_uri, manager_uri, chassis_uri, errors)
    """
    errors = []

    # ServiceRoot는 무인증으로 접근 (대부분의 BMC에서 인증 불필요)
    st, root, err = _get_noauth(bmc_ip, '', timeout, verify_ssl)
    if err or st != 200:
        # 무인증 실패 시 인증으로 재시도 (일부 BMC는 ServiceRoot도 인증 필요)
        st, root, err = _get(bmc_ip, '', username, password, timeout, verify_ssl)
        if err or st != 200:
            errors.append(_err('vendor_detect', f'ServiceRoot 실패: {err or st}'))
            return 'unknown', None, None, None, errors

    # ServiceRoot에서 벤더 식별
    vendor = _detect_vendor_from_service_root(root)
    if vendor is None:
        vendor = 'unknown'
        errors.append(_err('vendor_detect', 'ServiceRoot에서 벤더 식별 불가'))

    systems_uri  = _safe(root, 'Systems',  '@odata.id')
    managers_uri = _safe(root, 'Managers', '@odata.id')
    chassis_coll_uri = _safe(root, 'Chassis', '@odata.id')

    if not systems_uri:
        errors.append(_err('vendor_detect', 'ServiceRoot 에 Systems 링크 없음'))
        return vendor, None, None, None, errors

    # Systems 컬렉션에서 첫 번째 System URI 해석 (인증 필요)
    st, sys_coll, err = _get(bmc_ip, _p(systems_uri), username, password, timeout, verify_ssl)
    if err or st != 200:
        errors.append(_err('vendor_detect', f'Systems 컬렉션 실패: {err or st}'))
        return vendor, None, None, None, errors

    members = _safe(sys_coll, 'Members') or []
    if not members:
        errors.append(_err('vendor_detect', 'Systems 컬렉션 멤버 없음'))
        return vendor, None, None, None, errors

    system_uri = _safe(members[0], '@odata.id')

    # Managers URI 해석
    manager_uri = None
    if managers_uri:
        st, mgr_coll, err = _get(bmc_ip, _p(managers_uri), username, password, timeout, verify_ssl)
        if not err and st == 200:
            mgr_members = _safe(mgr_coll, 'Members') or []
            if mgr_members:
                manager_uri = _safe(mgr_members[0], '@odata.id')

    # Chassis 첫 번째 멤버 URI (Power/Thermal 수집에 필요)
    chassis_uri = None
    if chassis_coll_uri:
        st, ch_coll, cerr = _get(bmc_ip, _p(chassis_coll_uri), username, password, timeout, verify_ssl)
        if not cerr and st == 200:
            ch_members = _safe(ch_coll, 'Members') or []
            if ch_members:
                chassis_uri = _safe(ch_members[0], '@odata.id')

    return vendor, system_uri, manager_uri, chassis_uri, errors


# ── 섹션별 수집 ───────────────────────────────────────────────────────────────

def gather_system(bmc_ip, system_uri, vendor, username, password, timeout, verify_ssl):
    st, data, err = _get(bmc_ip, _p(system_uri), username, password, timeout, verify_ssl)
    errors = []
    if err or st != 200:
        errors.append(_err('system', f'System 수집 실패: {err or st}'))
        return {}, errors

    # HostName: HPE는 빈 문자열("") 반환 가능 → None으로 변환
    hostname = _safe(data, 'HostName')
    if isinstance(hostname, str) and not hostname.strip():
        hostname = None

    # IndicatorLED fallback: HPE Gen11은 IndicatorLED 미제공, LocationIndicatorActive 사용
    led_state = _safe(data, 'IndicatorLED')
    if led_state is None:
        loc_active = _safe(data, 'LocationIndicatorActive')
        if loc_active is not None:
            led_state = 'Blinking' if loc_active else 'Off'

    # MemorySummary.Status: HPE는 Health 미제공, HealthRollup만 제공
    mem_health = _safe(data, 'MemorySummary', 'Status', 'Health')
    if mem_health is None:
        mem_health = _safe(data, 'MemorySummary', 'Status', 'HealthRollup')

    result = {
        'manufacturer':   _safe(data, 'Manufacturer'),
        'model':          _safe(data, 'Model'),
        'serial':         _safe(data, 'SerialNumber'),
        'sku':            _safe(data, 'SKU'),
        'uuid':           _safe(data, 'UUID'),
        'hostname':       hostname,
        'power_state':    _safe(data, 'PowerState'),
        'health':         _safe(data, 'Status', 'Health'),
        'state':          _safe(data, 'Status', 'State'),
        'led_state':      led_state,
        'bios_version':   _safe(data, 'BiosVersion'),
        'cpu_summary': {
            'count':  _safe(data, 'ProcessorSummary', 'Count'),
            'model':  _safe(data, 'ProcessorSummary', 'Model'),
            'health': _safe(data, 'ProcessorSummary', 'Status', 'Health'),
        },
        'memory_summary': {
            'total_gib': _safe(data, 'MemorySummary', 'TotalSystemMemoryGiB'),
            'health':    mem_health,
        },
        'oem': {},
    }

    # 벤더별 OEM 확장
    if vendor == 'hpe':
        # iLO 5/6 = Oem.Hpe, iLO 4 이하 = Oem.Hp
        oem = _safe(data, 'Oem', 'Hpe') or _safe(data, 'Oem', 'Hp') or {}
        ahs = _safe(oem, 'AggregateHealthStatus') or {}
        result['oem'] = {
            'post_state':              _safe(oem, 'PostState'),
            'server_signature':        _safe(oem, 'ServerSignature'),
            'aggregate_server_health': _safe(ahs, 'AggregateServerHealth'),
            'fan_redundancy':          _safe(ahs, 'FanRedundancy'),
            'psu_redundancy':          _safe(ahs, 'PowerSupplyRedundancy'),
            'subsystem_health': {
                'fans':         _safe(ahs, 'Fans', 'Status', 'Health'),
                'memory':       _safe(ahs, 'Memory', 'Status', 'Health'),
                'network':      _safe(ahs, 'Network', 'Status', 'Health'),
                'power':        _safe(ahs, 'PowerSupplies', 'Status', 'Health'),
                'processors':   _safe(ahs, 'Processors', 'Status', 'Health'),
                'storage':      _safe(ahs, 'Storage', 'Status', 'Health'),
                'temperatures': _safe(ahs, 'Temperatures', 'Status', 'Health'),
            },
        }
    elif vendor == 'dell':
        oem = _safe(data, 'Oem', 'Dell', 'DellSystem') or {}
        result['oem'] = {
            'lifecycle_version':       _safe(oem, 'LifecycleControllerVersion'),
            'bios_release_date':       _safe(oem, 'BIOSReleaseDate'),
            'current_rollup_status':   _safe(oem, 'CurrentRollupStatus'),
            'cpu_rollup_status':       _safe(oem, 'CPURollupStatus'),
            'fan_rollup_status':       _safe(oem, 'FanRollupStatus'),
            'battery_rollup_status':   _safe(oem, 'BatteryRollupStatus'),
            'intrusion_rollup_status': _safe(oem, 'IntrusionRollupStatus'),
            'storage_rollup_status':   _safe(oem, 'StorageRollupStatus'),
            'chassis_service_tag':     _safe(oem, 'ChassisServiceTag'),
            'express_service_code':    _safe(oem, 'ExpressServiceCode'),
            'estimated_exhaust_temp':  _safe(oem, 'EstimatedExhaustTemperatureCel'),
        }
    elif vendor == 'lenovo':
        oem = _safe(data, 'Oem', 'Lenovo') or {}
        result['oem'] = {'product_name': _safe(oem, 'ProductName')}
    elif vendor == 'supermicro':
        oem = _safe(data, 'Oem', 'Supermicro') or {}
        result['oem'] = {
            'board_id':   _safe(oem, 'BoardID'),
            'node_id':    _safe(oem, 'NodeID'),
        }

    # 주요 필드 누락은 경고 수준 — 수집 자체는 성공으로 처리
    # errors에 추가하지 않아 _run()에서 failed로 분류되지 않음
    # 필요 시 별도 warnings 반환으로 확장 가능

    return result, errors


def gather_bmc(bmc_ip, manager_uri, vendor, username, password, timeout, verify_ssl):
    if not manager_uri:
        return {}, [_err('bmc', 'manager_uri 없음')]

    st, data, err = _get(bmc_ip, _p(manager_uri), username, password, timeout, verify_ssl)
    errors = []
    if err or st != 200:
        errors.append(_err('bmc', f'BMC 수집 실패: {err or st}'))
        return {}, errors

    bmc_names = {'dell': 'iDRAC', 'hpe': 'iLO', 'lenovo': 'XCC', 'supermicro': 'BMC'}
    result = {
        'name':             bmc_names.get(vendor, 'BMC'),
        'firmware_version': _safe(data, 'FirmwareVersion'),
        'model':            _safe(data, 'Model'),
        'manager_type':     _safe(data, 'ManagerType'),
        'health':           _safe(data, 'Status', 'Health'),
        'ip':               None,
        'oem': {},
    }

    # Manager EthernetInterfaces에서 BMC IP 추출
    nic_link = _safe(data, 'EthernetInterfaces', '@odata.id')
    if nic_link:
        nst, ncoll, nerr = _get(bmc_ip, _p(nic_link), username, password, timeout, verify_ssl)
        if not nerr and nst == 200:
            for nm in (_safe(ncoll, 'Members') or []):
                nuri = _safe(nm, '@odata.id')
                if not nuri:
                    continue
                nst2, ndata, nerr2 = _get(bmc_ip, _p(nuri), username, password, timeout, verify_ssl)
                if nerr2 or nst2 != 200:
                    continue
                for addr in (_safe(ndata, 'IPv4Addresses') or []):
                    ip = _safe(addr, 'Address')
                    if ip and ip not in ('0.0.0.0', ''):
                        result['ip'] = ip
                        break
                if result['ip']:
                    break

    if vendor == 'hpe':
        oem = _safe(data, 'Oem', 'Hpe') or _safe(data, 'Oem', 'Hp') or {}
        result['oem'] = {'ilo_version': _safe(oem, 'Type')}
    elif vendor == 'supermicro':
        oem = _safe(data, 'Oem', 'Supermicro') or {}
        result['oem'] = {'bmc_ip': _safe(oem, 'BMCIPv4Address')}
        if not result['ip'] and result['oem'].get('bmc_ip'):
            result['ip'] = result['oem']['bmc_ip']

    return result, errors


def gather_processors(bmc_ip, system_uri, username, password, timeout, verify_ssl):
    path = _p(system_uri) + '/Processors'
    st, coll, err = _get(bmc_ip, path, username, password, timeout, verify_ssl)
    errors = []
    if err or st != 200:
        errors.append(_err('processors', f'Processor 컬렉션 실패: {err or st}'))
        return [], errors

    processors = []
    for member in (_safe(coll, 'Members') or []):
        uri = _safe(member, '@odata.id')
        if not uri: continue
        st, pdata, perr = _get(bmc_ip, _p(uri), username, password, timeout, verify_ssl)
        if perr or st != 200:
            errors.append(_err('processors', f'Processor {uri} 실패: {perr or st}'))
            continue
        if _safe(pdata, 'Status', 'State') in ('Absent', 'Disabled'):
            continue
        processors.append({
            'id':            _safe(pdata, 'Id'),
            'name':          _safe(pdata, 'Name'),
            'model':         _safe(pdata, 'Model'),
            'manufacturer':  _safe(pdata, 'Manufacturer'),
            'socket':        _safe(pdata, 'Socket'),
            'total_cores':   _safe(pdata, 'TotalCores'),
            'total_threads': _safe(pdata, 'TotalThreads'),
            'speed_mhz':     _safe(pdata, 'MaxSpeedMHz'),
            'health':        _safe(pdata, 'Status', 'Health'),
        })
    return processors, errors


def gather_memory(bmc_ip, system_uri, username, password, timeout, verify_ssl):
    path = _p(system_uri) + '/Memory'
    st, coll, err = _get(bmc_ip, path, username, password, timeout, verify_ssl)
    errors = []
    if err or st != 200:
        errors.append(_err('memory', f'Memory 컬렉션 실패: {err or st}'))
        return {'total_mib': None, 'slots': []}, errors

    slots, total_mib = [], 0
    for member in (_safe(coll, 'Members') or []):
        uri = _safe(member, '@odata.id')
        if not uri: continue
        st, mdata, merr = _get(bmc_ip, _p(uri), username, password, timeout, verify_ssl)
        if merr or st != 200:
            errors.append(_err('memory', f'Memory {uri} 실패: {merr or st}'))
            continue
        if _safe(mdata, 'Status', 'State') == 'Absent':
            continue
        cap = _safe(mdata, 'CapacityMiB') or 0
        if cap: total_mib += int(cap)
        slots.append({
            'id':           _safe(mdata, 'Id'),
            'name':         _safe(mdata, 'Name'),
            'capacity_mib': int(cap) if cap else None,
            'type':         _safe(mdata, 'MemoryDeviceType'),
            'speed_mhz':    _safe(mdata, 'OperatingSpeedMhz'),
            'manufacturer': _safe(mdata, 'Manufacturer'),
            'serial':       _safe(mdata, 'SerialNumber'),
            'part_number':  _safe(mdata, 'PartNumber'),
            'health':       _safe(mdata, 'Status', 'Health'),
        })
    return {'total_mib': total_mib or None, 'slots': slots}, errors


def gather_storage(bmc_ip, system_uri, username, password, timeout, verify_ssl):
    path = _p(system_uri) + '/Storage'
    st, coll, err = _get(bmc_ip, path, username, password, timeout, verify_ssl)
    errors = []

    # Storage 실패 시 SimpleStorage fallback (구형 BMC 호환)
    use_simple = False
    if err or st != 200:
        simple_path = _p(system_uri) + '/SimpleStorage'
        st2, coll2, err2 = _get(bmc_ip, simple_path, username, password, timeout, verify_ssl)
        if not err2 and st2 == 200:
            use_simple = True
            coll = coll2
            errors.append(_err('storage', f'Storage 미지원, SimpleStorage fallback 사용'))
        else:
            errors.append(_err('storage', f'Storage/SimpleStorage 모두 실패: {err or st}'))
            return [], errors

    controllers = []

    if use_simple:
        # SimpleStorage: 플랫 디바이스 목록 (컨트롤러/드라이브 분리 없음)
        for member in (_safe(coll, 'Members') or []):
            uri = _safe(member, '@odata.id')
            if not uri: continue
            st, sdata, serr = _get(bmc_ip, _p(uri), username, password, timeout, verify_ssl)
            if serr or st != 200:
                errors.append(_err('storage', f'SimpleStorage {uri} 실패: {serr or st}'))
                continue
            drives = []
            for dev in (_safe(sdata, 'Devices') or []):
                cap = _safe(dev, 'CapacityBytes')
                drives.append({
                    'name':           _safe(dev, 'Name'),
                    'model':          _safe(dev, 'Model'),
                    'serial':         None,
                    'manufacturer':   _safe(dev, 'Manufacturer'),
                    'media_type':     None,
                    'protocol':       None,
                    'capacity_bytes': int(cap) if cap else None,
                    'capacity_gb':    round(int(cap) / 1e9, 2) if cap else None,
                    'health':         _safe(dev, 'Status', 'Health'),
                })
            controllers.append({
                'id': _safe(sdata, 'Id'), 'name': _safe(sdata, 'Name'),
                'health': _safe(sdata, 'Status', 'Health'), 'drives': drives,
            })
    else:
        # Storage: 컨트롤러 → 드라이브 계층 구조
        for member in (_safe(coll, 'Members') or []):
            uri = _safe(member, '@odata.id')
            if not uri: continue
            st, sdata, serr = _get(bmc_ip, _p(uri), username, password, timeout, verify_ssl)
            if serr or st != 200:
                errors.append(_err('storage', f'Storage {uri} 실패: {serr or st}'))
                continue

            # 컨트롤러 상세 정보 추출
            # 1차: StorageControllers 인라인 배열 (Dell, Lenovo 등)
            # 2차: Controllers 서브링크 (HPE Gen11 등 — 인라인 배열 없음)
            ctrl_info = {}
            inline_ctrls = _safe(sdata, 'StorageControllers') or []
            if inline_ctrls:
                c = inline_ctrls[0]
                ctrl_info = {
                    'controller_model':    _safe(c, 'Model'),
                    'controller_firmware': _safe(c, 'FirmwareVersion'),
                    'controller_manufacturer': _safe(c, 'Manufacturer'),
                    'controller_health':   _safe(c, 'Status', 'Health'),
                }
            else:
                ctrl_link = _safe(sdata, 'Controllers', '@odata.id')
                if ctrl_link:
                    cst, ctrl_coll, cerr = _get(bmc_ip, _p(ctrl_link), username, password, timeout, verify_ssl)
                    if not cerr and cst == 200:
                        ctrl_members = _safe(ctrl_coll, 'Members') or []
                        if ctrl_members:
                            c_uri = _safe(ctrl_members[0], '@odata.id')
                            if c_uri:
                                cst2, cdata, cerr2 = _get(bmc_ip, _p(c_uri), username, password, timeout, verify_ssl)
                                if not cerr2 and cst2 == 200:
                                    ctrl_info = {
                                        'controller_model':    _safe(cdata, 'Model'),
                                        'controller_firmware': _safe(cdata, 'FirmwareVersion'),
                                        'controller_manufacturer': _safe(cdata, 'Manufacturer'),
                                        'controller_health':   _safe(cdata, 'Status', 'Health'),
                                    }

            drives = []
            for d_member in (_safe(sdata, 'Drives') or []):
                d_uri = _safe(d_member, '@odata.id')
                if not d_uri: continue
                dst, ddata, derr = _get(bmc_ip, _p(d_uri), username, password, timeout, verify_ssl)
                if derr or dst != 200:
                    errors.append(_err('storage', f'Drive {d_uri} 실패: {derr or dst}'))
                    continue
                # Q-09: HPE Empty Bay 필터 — CapacityBytes가 없거나 Name에 "Empty" 포함 시 스킵
                cap = _safe(ddata, 'CapacityBytes')
                drive_name = _safe(ddata, 'Name') or ''
                if not cap or int(cap) == 0:
                    continue
                if 'empty' in drive_name.lower():
                    continue
                # PredictedMediaLifeLeftPercent: HPE returns float, others int → normalize to int
                life_pct = _safe(ddata, 'PredictedMediaLifeLeftPercent')
                if life_pct is not None:
                    life_pct = int(life_pct)
                drives.append({
                    'name':           _safe(ddata, 'Name'),
                    'model':          _safe(ddata, 'Model'),
                    'serial':         _safe(ddata, 'SerialNumber'),
                    'manufacturer':   _safe(ddata, 'Manufacturer'),
                    'media_type':     _safe(ddata, 'MediaType'),
                    'protocol':       _safe(ddata, 'Protocol'),
                    'capacity_bytes': int(cap) if cap else None,
                    'capacity_gb':    round(int(cap) / 1e9, 2) if cap else None,
                    'health':         _safe(ddata, 'Status', 'Health') or _safe(ddata, 'Status', 'HealthRollup'),
                    'failure_predicted':       _safe(ddata, 'FailurePredicted'),
                    'predicted_life_percent':  life_pct,
                })
            ctrl_entry = {
                'id': _safe(sdata, 'Id'), 'name': _safe(sdata, 'Name'),
                'health': _safe(sdata, 'Status', 'Health') or _safe(sdata, 'Status', 'HealthRollup'),
                'drives': drives,
            }
            ctrl_entry.update(ctrl_info)
            controllers.append(ctrl_entry)
    return controllers, errors


def gather_network(bmc_ip, system_uri, username, password, timeout, verify_ssl):
    """Systems/{id}/EthernetInterfaces — 호스트 서버 NIC"""
    path = _p(system_uri) + '/EthernetInterfaces'
    st, coll, err = _get(bmc_ip, path, username, password, timeout, verify_ssl)
    errors = []
    if err or st != 200:
        errors.append(_err('network', f'EthernetInterfaces 실패: {err or st}'))
        return [], errors

    nics = []
    for member in (_safe(coll, 'Members') or []):
        uri = _safe(member, '@odata.id')
        if not uri: continue
        st, ndata, nerr = _get(bmc_ip, _p(uri), username, password, timeout, verify_ssl)
        if nerr or st != 200:
            errors.append(_err('network', f'NIC {uri} 실패: {nerr or st}'))
            continue
        ipv4_addrs = [
            {'address': a.get('Address'), 'subnet_mask': a.get('SubnetMask'),
             'gateway': a.get('Gateway'), 'address_origin': a.get('AddressOrigin')}
            for a in (_safe(ndata, 'IPv4Addresses') or [])
            if a.get('Address') not in (None, '0.0.0.0', '')
        ]
        nics.append({
            'id': _safe(ndata, 'Id'), 'name': _safe(ndata, 'Name') or _safe(ndata, 'Id') or '',
            'mac': _safe(ndata, 'MACAddress'), 'speed_mbps': _safe(ndata, 'SpeedMbps'),
            'mtu': _safe(ndata, 'MTUSize'),
            'link_status': _safe(ndata, 'LinkStatus'), 'health': _safe(ndata, 'Status', 'Health'),
            'ipv4': ipv4_addrs,
        })
    return nics, errors


def gather_firmware(bmc_ip, username, password, timeout, verify_ssl):
    """
    UpdateService/FirmwareInventory — 벤더 공통
    Members 에 상세 필드 없으면 개별 URI 조회 (Dell/HPE/Supermicro 모두 해당)
    """
    path = 'UpdateService/FirmwareInventory'
    st, coll, err = _get(bmc_ip, path, username, password, timeout, verify_ssl)
    errors = []
    if err or st != 200:
        errors.append(_err('firmware', f'FirmwareInventory 실패: {err or st}'))
        return [], errors

    fw_list = []
    for member in (_safe(coll, 'Members') or []):
        member_uri = _safe(member, '@odata.id')
        # Members 에 Name/Version 없으면 개별 URI 조회 (벤더 공통)
        if not _safe(member, 'Name') and member_uri:
            st2, fw_data, ferr = _get(bmc_ip, _p(member_uri), username, password, timeout, verify_ssl)
            if not ferr and st2 == 200:
                member = fw_data
        fw_id = _safe(member, 'Id') or (member_uri.split('/')[-1] if member_uri else None)
        # Q-14: Dell Previous- 항목 스킵 (비활성 이전 버전)
        if fw_id and isinstance(fw_id, str) and fw_id.startswith('Previous-'):
            continue
        # Q-13: SoftwareId가 문자열 "null"이면 Python None으로 변환
        component = _safe(member, 'SoftwareId')
        if isinstance(component, str) and component.lower() == 'null':
            component = None
        fw_list.append({
            'id':         fw_id,
            'name':       _safe(member, 'Name'),
            'version':    _safe(member, 'Version'),
            'updateable': _safe(member, 'Updateable'),
            'component':  component or fw_id,
        })
    return fw_list, errors


def gather_power(bmc_ip, chassis_uri, username, password, timeout, verify_ssl):
    """Chassis/{id}/Power — PSU 정보. chassis_uri는 detect_vendor()에서 전달."""
    errors = []
    if not chassis_uri:
        errors.append(_err('power', 'chassis_uri 없음 (detect_vendor 에서 Chassis 미발견)'))
        return {}, errors

    power_path = _p(chassis_uri) + '/Power'
    st, pdata, perr = _get(bmc_ip, power_path, username, password, timeout, verify_ssl)
    if perr or st != 200:
        errors.append(_err('power', f'Power 정보 실패: {perr or st}'))
        return {}, errors

    psus = [
        {
            'name':             _safe(psu, 'Name'),
            'model':            _safe(psu, 'Model'),
            'serial':           _safe(psu, 'SerialNumber'),
            'manufacturer':     _safe(psu, 'Manufacturer'),
            'power_capacity_w': _safe(psu, 'PowerCapacityWatts'),
            'firmware_version': _safe(psu, 'FirmwareVersion'),
            'health':           _safe(psu, 'Status', 'Health'),
            'state':            _safe(psu, 'Status', 'State'),
        }
        for psu in (_safe(pdata, 'PowerSupplies') or [])
    ]

    # PowerControl — system-level power consumption (Safe Common: 3 vendors verified)
    pc_list = pdata.get('PowerControl') or []
    pc0 = pc_list[0] if pc_list else {}
    pm = pc0.get('PowerMetrics') or {}
    power_control = {
        'power_consumed_watts':  _safe(pc0, 'PowerConsumedWatts'),
        'power_capacity_watts':  _safe(pc0, 'PowerCapacityWatts'),
        'interval_in_min':       _safe(pm, 'IntervalInMin'),
        'min_consumed_watts':    _safe(pm, 'MinConsumedWatts'),
        'avg_consumed_watts':    _safe(pm, 'AverageConsumedWatts'),
        'max_consumed_watts':    _safe(pm, 'MaxConsumedWatts'),
    } if pc0 else None

    return {'power_supplies': psus, 'power_control': power_control}, errors


# ── 메인 ─────────────────────────────────────────────────────────────────────

def main():
    module = AnsibleModule(
        argument_spec=dict(
            bmc_ip     = dict(type='str',  required=True),
            username   = dict(type='str',  required=True),
            password   = dict(type='str',  required=True, no_log=True),
            timeout    = dict(type='int',  default=30),
            verify_ssl = dict(type='bool', default=False),
        ),
        supports_check_mode=True,
    )

    if not HAS_URLLIB:
        module.fail_json(msg='Python urllib 를 import 할 수 없습니다')

    p = module.params
    bmc_ip, username, password = p['bmc_ip'], p['username'], p['password']
    timeout, verify_ssl = p['timeout'], p['verify_ssl']

    all_errors, collected, failed = [], [], []

    vendor, system_uri, manager_uri, chassis_uri, det_errors = detect_vendor(
        bmc_ip, username, password, timeout, verify_ssl
    )
    all_errors.extend(det_errors)

    if not system_uri:
        module.exit_json(
            changed=False, status='failed', vendor=vendor,
            collected=[], failed_sections=['all'], errors=all_errors, data={},
        )

    result_data = {}

    def _run(section, fn, *args):
        try:
            val, errs = fn(*args)
            all_errors.extend(errs)
            collected.append(section)
            if errs: failed.append(section)
            return val
        except Exception:
            all_errors.append(_err(section, '예외 발생', traceback.format_exc(limit=3)))
            failed.append(section)
            return None

    result_data['system']     = _run('system',    gather_system,     bmc_ip, system_uri,  vendor, username, password, timeout, verify_ssl)
    result_data['bmc']        = _run('bmc',        gather_bmc,        bmc_ip, manager_uri, vendor, username, password, timeout, verify_ssl)
    result_data['processors'] = _run('processors', gather_processors, bmc_ip, system_uri,         username, password, timeout, verify_ssl)
    result_data['memory']     = _run('memory',     gather_memory,     bmc_ip, system_uri,         username, password, timeout, verify_ssl)
    result_data['storage']    = _run('storage',    gather_storage,    bmc_ip, system_uri,         username, password, timeout, verify_ssl)
    result_data['network']    = _run('network',    gather_network,    bmc_ip, system_uri,         username, password, timeout, verify_ssl)
    result_data['firmware']   = _run('firmware',   gather_firmware,   bmc_ip,                     username, password, timeout, verify_ssl)
    result_data['power']      = _run('power',      gather_power,      bmc_ip, chassis_uri,            username, password, timeout, verify_ssl)

    clean = [s for s in collected if s not in failed]
    if not clean:         final_status = 'failed'
    elif failed:          final_status = 'partial'
    else:                 final_status = 'success'

    module.exit_json(
        changed=False, status=final_status, vendor=vendor,
        collected=clean, failed_sections=list(set(failed)),
        errors=all_errors, data=result_data,
    )


if __name__ == '__main__':
    main()
