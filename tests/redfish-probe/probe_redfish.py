import urllib.request, ssl, json, base64, sys, os, time

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# ⚠ 운영 환경에서는 환경변수를 사용하세요:
#   BMC_LENOVO_IP, BMC_LENOVO_USER, BMC_LENOVO_PASS 등
# 아래는 격리된 테스트 환경 전용 기본값입니다.
SERVERS = {
    'lenovo': {
        'ip':   os.environ.get('BMC_LENOVO_IP',   '10.50.11.232'),
        'user': os.environ.get('BMC_LENOVO_USER', 'USERID'),
        'pass': os.environ.get('BMC_LENOVO_PASS', 'CHANGE_ME'),
    },
    'hpe': {
        'ip':   os.environ.get('BMC_HPE_IP',   '10.50.11.231'),
        'user': os.environ.get('BMC_HPE_USER', 'admin'),
        'pass': os.environ.get('BMC_HPE_PASS', 'CHANGE_ME'),
    },
    'dell': {
        'ip':   os.environ.get('BMC_DELL_IP',   '10.50.11.162'),
        'user': os.environ.get('BMC_DELL_USER', 'root'),
        'pass': os.environ.get('BMC_DELL_PASS', 'CHANGE_ME'),
    },
}

FIXTURE_BASE = os.path.join(os.path.dirname(__file__), 'redfish_fixtures')

def fetch(ip, user, pw, path, timeout=20):
    url = f'https://{ip}{path}'
    creds = base64.b64encode(f'{user}:{pw}'.encode()).decode()
    req = urllib.request.Request(url, headers={
        'Authorization': f'Basic {creds}',
        'Accept': 'application/json'
    })
    try:
        resp = urllib.request.urlopen(req, context=ctx, timeout=timeout)
        return resp.getcode(), json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read())
        except:
            body = {}
        return e.code, body
    except Exception as e:
        return 0, {'error': str(e)}

def probe_vendor(name, cfg):
    ip, user, pw = cfg['ip'], cfg['user'], cfg['pass']
    results = {}

    print(f"\n{'='*60}")
    print(f"  PROBING: {name.upper()} ({ip})")
    print(f"{'='*60}")

    # 1. Service Root
    code, data = fetch(ip, user, pw, '/redfish/v1/')
    results['service_root'] = {'code': code, 'data': data}
    print(f"  /redfish/v1/ => {code}")

    # 2. Systems collection
    code, data = fetch(ip, user, pw, '/redfish/v1/Systems')
    results['systems_collection'] = {'code': code, 'data': data}
    sys_members = [m['@odata.id'] for m in data.get('Members', [])] if code == 200 else []
    print(f"  /redfish/v1/Systems => {code} (members: {len(sys_members)})")

    # 3. Systems member (first)
    sys_uri = ''
    if sys_members:
        sys_uri = sys_members[0]
        code, data = fetch(ip, user, pw, sys_uri)
        results['system'] = {'code': code, 'data': data, 'uri': sys_uri}
        print(f"  {sys_uri} => {code}")

        # Sub-resources from system
        for sub in ['Processors', 'Memory', 'Storage', 'SimpleStorage', 'EthernetInterfaces', 'NetworkInterfaces', 'Bios']:
            sub_link = ''
            if code == 200:
                sub_obj = data.get(sub, {})
                if isinstance(sub_obj, dict):
                    sub_link = sub_obj.get('@odata.id', '')

            if sub_link:
                sc, sd = fetch(ip, user, pw, sub_link)
                results[f'system_{sub.lower()}'] = {'code': sc, 'data': sd, 'uri': sub_link}
                print(f"  {sub_link} => {sc}")

                # Drill into collection members (first 2)
                if sc == 200 and 'Members' in sd:
                    for i, mem in enumerate(sd.get('Members', [])[:2]):
                        mem_uri = mem.get('@odata.id', '')
                        if mem_uri:
                            mc, md = fetch(ip, user, pw, mem_uri)
                            results[f'system_{sub.lower()}_{i}'] = {'code': mc, 'data': md, 'uri': mem_uri}
                            print(f"    {mem_uri} => {mc}")
            else:
                # Try constructing path
                constructed = f"{sys_uri}/{sub}"
                sc, sd = fetch(ip, user, pw, constructed)
                results[f'system_{sub.lower()}'] = {'code': sc, 'data': sd, 'uri': constructed}
                tag = 'constructed' if sc == 200 else 'not found'
                print(f"  {constructed} => {sc} ({tag})")

    # 4. Managers collection + member
    code, data = fetch(ip, user, pw, '/redfish/v1/Managers')
    results['managers_collection'] = {'code': code, 'data': data}
    mgr_members = [m['@odata.id'] for m in data.get('Members', [])] if code == 200 else []
    print(f"  /redfish/v1/Managers => {code} (members: {len(mgr_members)})")

    if mgr_members:
        mgr_uri = mgr_members[0]
        code, data = fetch(ip, user, pw, mgr_uri)
        results['manager'] = {'code': code, 'data': data, 'uri': mgr_uri}
        print(f"  {mgr_uri} => {code}")

        # Manager sub-resources
        if code == 200:
            for sub in ['EthernetInterfaces', 'VirtualMedia', 'LogServices', 'NetworkProtocol']:
                sub_obj = data.get(sub, {})
                sub_link = sub_obj.get('@odata.id', '') if isinstance(sub_obj, dict) else ''
                if sub_link:
                    sc, sd = fetch(ip, user, pw, sub_link)
                    results[f'manager_{sub.lower()}'] = {'code': sc, 'data': sd, 'uri': sub_link}
                    print(f"  {sub_link} => {sc}")
                    # Drill into first member
                    if sc == 200 and 'Members' in sd:
                        for i, mem in enumerate(sd.get('Members', [])[:1]):
                            mem_uri = mem.get('@odata.id', '')
                            if mem_uri:
                                mc, md = fetch(ip, user, pw, mem_uri)
                                results[f'manager_{sub.lower()}_{i}'] = {'code': mc, 'data': md, 'uri': mem_uri}
                                print(f"    {mem_uri} => {mc}")

    # 5. Chassis collection + member
    code, data = fetch(ip, user, pw, '/redfish/v1/Chassis')
    results['chassis_collection'] = {'code': code, 'data': data}
    ch_members = [m['@odata.id'] for m in data.get('Members', [])] if code == 200 else []
    print(f"  /redfish/v1/Chassis => {code} (members: {len(ch_members)})")

    ch_uri = ''
    if ch_members:
        ch_uri = ch_members[0]
        code, data = fetch(ip, user, pw, ch_uri)
        results['chassis'] = {'code': code, 'data': data, 'uri': ch_uri}
        print(f"  {ch_uri} => {code}")

        # Power, Thermal, and subsystems
        if code == 200:
            for sub in ['Power', 'Thermal', 'PowerSubsystem', 'ThermalSubsystem', 'NetworkAdapters']:
                sub_obj = data.get(sub, {})
                sub_link = sub_obj.get('@odata.id', '') if isinstance(sub_obj, dict) else ''
                if sub_link:
                    sc, sd = fetch(ip, user, pw, sub_link)
                    results[f'chassis_{sub.lower()}'] = {'code': sc, 'data': sd, 'uri': sub_link}
                    print(f"  {sub_link} => {sc}")
                else:
                    constructed = f"{ch_uri}/{sub}"
                    sc, sd = fetch(ip, user, pw, constructed)
                    results[f'chassis_{sub.lower()}'] = {'code': sc, 'data': sd, 'uri': constructed}
                    tag = 'found' if sc == 200 else 'not found'
                    print(f"  {constructed} => {sc} ({tag})")

    # 6. UpdateService + FirmwareInventory
    code, data = fetch(ip, user, pw, '/redfish/v1/UpdateService')
    results['update_service'] = {'code': code, 'data': data}
    print(f"  /redfish/v1/UpdateService => {code}")

    if code == 200:
        fw_link = data.get('FirmwareInventory', {}).get('@odata.id', '')
        if fw_link:
            sc, sd = fetch(ip, user, pw, fw_link)
            results['firmware_inventory'] = {'code': sc, 'data': sd, 'uri': fw_link}
            mem_count = len(sd.get('Members', [])) if sc == 200 else 0
            print(f"  {fw_link} => {sc} (members: {mem_count})")
            if sc == 200 and 'Members' in sd:
                for i, mem in enumerate(sd.get('Members', [])[:3]):
                    mem_uri = mem.get('@odata.id', '')
                    if mem_uri:
                        mc, md = fetch(ip, user, pw, mem_uri)
                        results[f'firmware_{i}'] = {'code': mc, 'data': md, 'uri': mem_uri}
                        print(f"    {mem_uri} => {mc}")

        sw_link = data.get('SoftwareInventory', {}).get('@odata.id', '')
        if sw_link:
            sc, sd = fetch(ip, user, pw, sw_link)
            results['software_inventory'] = {'code': sc, 'data': sd, 'uri': sw_link}
            print(f"  {sw_link} => {sc}")

    # 7. Negative tests
    for neg_path in ['/redfish/v1/Systems/NONEXISTENT', '/redfish/v1/Chassis/BOGUS/Power']:
        code, data = fetch(ip, user, pw, neg_path)
        results[f'negative_{neg_path}'] = {'code': code}
        print(f"  [NEG] {neg_path} => {code}")

    return results


# Run all vendors
all_results = {}
for name, cfg in SERVERS.items():
    all_results[name] = probe_vendor(name, cfg)

# Save results
for vendor, results in all_results.items():
    outdir = os.path.join(FIXTURE_BASE, vendor)
    os.makedirs(outdir, exist_ok=True)
    for key, val in results.items():
        if 'data' in val:
            fpath = os.path.join(outdir, f'{key}.json')
            with open(fpath, 'w') as f:
                json.dump(val['data'], f, indent=2)

# Summary
print(f"\n{'='*60}")
print("  SUMMARY")
print(f"{'='*60}")
for vendor in ['lenovo', 'hpe', 'dell']:
    r = all_results[vendor]
    total = len(r)
    ok = sum(1 for v in r.values() if v.get('code') == 200)
    fail = total - ok
    print(f"\n  [{vendor.upper()}] total={total}, OK={ok}, FAIL={fail}")
    for key, val in r.items():
        code = val.get('code', '?')
        uri = val.get('uri', key)
        status = 'OK' if code == 200 else f'FAIL({code})'
        print(f"    {uri:65s} {status}")

print(f"\nAll fixtures saved to {FIXTURE_BASE}")
