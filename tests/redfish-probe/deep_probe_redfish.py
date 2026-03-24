"""Deep probe: Storage Drives/Controllers, additional endpoints"""
import urllib.request, ssl, json, base64, os

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

FIXTURE_BASE = os.path.join(os.path.expanduser('~'), 'redfish_fixtures')

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
        try: body = json.loads(e.read())
        except: body = {}
        return e.code, body
    except Exception as e:
        return 0, {'error': str(e)}

def save(vendor, name, data):
    outdir = os.path.join(FIXTURE_BASE, vendor)
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, f'{name}.json'), 'w') as f:
        json.dump(data, f, indent=2)

for vname, cfg in SERVERS.items():
    ip, user, pw = cfg['ip'], cfg['user'], cfg['pass']
    print(f"\n{'='*50} {vname.upper()} {'='*50}")

    # 1. Get system URI
    code, systems = fetch(ip, user, pw, '/redfish/v1/Systems')
    if code != 200: continue
    sys_uri = systems['Members'][0]['@odata.id']

    # 2. Storage deep dive - get all storage controllers
    code, storage_col = fetch(ip, user, pw, f'{sys_uri}/Storage')
    if code == 200:
        for mem in storage_col.get('Members', []):
            s_uri = mem['@odata.id']
            sc, sd = fetch(ip, user, pw, s_uri)
            s_name = s_uri.split('/')[-1]
            save(vname, f'storage_{s_name}', sd)
            print(f"  Storage: {s_uri} => {sc}")

            # Check for Drives
            if sc == 200:
                drives = sd.get('Drives', [])
                for i, drv in enumerate(drives[:3]):
                    drv_uri = drv.get('@odata.id', '')
                    if drv_uri:
                        dc, dd = fetch(ip, user, pw, drv_uri)
                        save(vname, f'drive_{s_name}_{i}', dd)
                        if dc == 200:
                            cap = dd.get('CapacityBytes', 'N/A')
                            model = dd.get('Model', 'N/A')
                            media = dd.get('MediaType', 'N/A')
                            print(f"    Drive: {drv_uri} => {dc} | {model} | {media} | {cap}")
                        else:
                            print(f"    Drive: {drv_uri} => {dc}")

                # StorageControllers array (inline in Storage resource)
                controllers = sd.get('StorageControllers', [])
                if controllers:
                    print(f"    StorageControllers (inline): {len(controllers)} found")
                    for ci, ctrl in enumerate(controllers):
                        print(f"      [{ci}] {ctrl.get('Name','?')} | {ctrl.get('Model','?')} | FW:{ctrl.get('FirmwareVersion','?')}")

                # Controllers link (newer Redfish)
                ctrl_link = sd.get('Controllers', {})
                if isinstance(ctrl_link, dict) and '@odata.id' in ctrl_link:
                    cc, cd = fetch(ip, user, pw, ctrl_link['@odata.id'])
                    print(f"    Controllers link: {ctrl_link['@odata.id']} => {cc}")
                    if cc == 200 and 'Members' in cd:
                        for cm in cd.get('Members', [])[:2]:
                            cm_uri = cm.get('@odata.id', '')
                            cmc, cmd = fetch(ip, user, pw, cm_uri)
                            save(vname, f'storage_controller_{cm_uri.split("/")[-1]}', cmd)
                            print(f"      Controller: {cm_uri} => {cmc}")

    # 3. All Memory DIMM summary
    code, mem_col = fetch(ip, user, pw, f'{sys_uri}/Memory')
    if code == 200:
        total_dimms = len(mem_col.get('Members', []))
        print(f"  Memory DIMMs total: {total_dimms}")
        populated = 0
        total_gb = 0
        for mem in mem_col.get('Members', []):
            mc, md = fetch(ip, user, pw, mem['@odata.id'])
            if mc == 200:
                cap = md.get('CapacityMiB', 0) or md.get('SizeMB', 0) or 0
                status = md.get('Status', {}).get('State', 'Unknown')
                if cap and cap > 0 and status not in ['Absent']:
                    populated += 1
                    total_gb += cap / 1024
        print(f"    Populated: {populated}/{total_dimms}, Total: {total_gb:.0f} GB")
        save(vname, 'memory_summary', {'total_dimms': total_dimms, 'populated': populated, 'total_gb': total_gb})

    # 4. All Processors summary
    code, proc_col = fetch(ip, user, pw, f'{sys_uri}/Processors')
    if code == 200:
        for pmem in proc_col.get('Members', []):
            pc, pd = fetch(ip, user, pw, pmem['@odata.id'])
            if pc == 200:
                model = pd.get('Model', 'N/A')
                cores = pd.get('TotalCores', 'N/A')
                threads = pd.get('TotalThreads', 'N/A')
                socket = pd.get('Socket', pd.get('Id', 'N/A'))
                speed = pd.get('MaxSpeedMHz', 'N/A')
                status = pd.get('Status', {}).get('State', 'N/A')
                print(f"  CPU {socket}: {model} | Cores:{cores} Threads:{threads} Speed:{speed}MHz | {status}")

    # 5. Manager detailed info (BMC)
    code, mgr_col = fetch(ip, user, pw, '/redfish/v1/Managers')
    if code == 200:
        mgr_uri = mgr_col['Members'][0]['@odata.id']
        mc, md = fetch(ip, user, pw, mgr_uri)
        if mc == 200:
            print(f"  BMC: {md.get('Model', 'N/A')} | FW: {md.get('FirmwareVersion', 'N/A')} | Type: {md.get('ManagerType', 'N/A')}")
            # Manager EthernetInterfaces for BMC MAC
            eth_link = md.get('EthernetInterfaces', {}).get('@odata.id', '')
            if eth_link:
                ec, ed = fetch(ip, user, pw, eth_link)
                if ec == 200:
                    for emem in ed.get('Members', [])[:2]:
                        emc, emd = fetch(ip, user, pw, emem['@odata.id'])
                        if emc == 200:
                            mac = emd.get('MACAddress', emd.get('PermanentMACAddress', 'N/A'))
                            ipv4 = emd.get('IPv4Addresses', [])
                            ip_str = ipv4[0].get('Address', 'N/A') if ipv4 else 'N/A'
                            print(f"    BMC NIC: MAC={mac} IP={ip_str}")

    # 6. System-level key fields
    code, sys_data = fetch(ip, user, pw, sys_uri)
    if code == 200:
        print(f"  System: Model={sys_data.get('Model','N/A')} | Mfr={sys_data.get('Manufacturer','N/A')}")
        print(f"    Serial={sys_data.get('SerialNumber','N/A')} | HostName={sys_data.get('HostName','N/A')}")
        print(f"    UUID={sys_data.get('UUID','N/A')} | BIOS={sys_data.get('BiosVersion','N/A')}")
        print(f"    PowerState={sys_data.get('PowerState','N/A')} | Status={sys_data.get('Status',{})}")
        ps = sys_data.get('ProcessorSummary', {})
        ms = sys_data.get('MemorySummary', {})
        print(f"    ProcessorSummary: Count={ps.get('Count','N/A')} Model={ps.get('Model','N/A')}")
        print(f"    MemorySummary: TotalGB={ms.get('TotalSystemMemoryGiB','N/A')} Status={ms.get('Status',{}).get('HealthRollup','N/A')}")
        # OEM data
        oem = sys_data.get('Oem', {})
        if oem:
            print(f"    OEM keys: {list(oem.keys())}")

    # 7. Chassis details
    code, ch_col = fetch(ip, user, pw, '/redfish/v1/Chassis')
    if code == 200:
        ch_uri = ch_col['Members'][0]['@odata.id']
        cc, cd = fetch(ip, user, pw, ch_uri)
        if cc == 200:
            print(f"  Chassis: Type={cd.get('ChassisType','N/A')} | Model={cd.get('Model','N/A')}")
            print(f"    PartNumber={cd.get('PartNumber','N/A')} | Serial={cd.get('SerialNumber','N/A')}")
            print(f"    Manufacturer={cd.get('Manufacturer','N/A')}")

    # 8. Power details
    ch_col_data = fetch(ip, user, pw, '/redfish/v1/Chassis')[1]
    ch_uri = ch_col_data['Members'][0]['@odata.id']
    power_code, power_data = fetch(ip, user, pw, f'{ch_uri}/Power')
    if power_code == 200:
        pctrl = power_data.get('PowerControl', [])
        psu = power_data.get('PowerSupplies', [])
        print(f"  Power: Controls={len(pctrl)} PSUs={len(psu)}")
        for pc in pctrl[:2]:
            watts = pc.get('PowerConsumedWatts', 'N/A')
            cap = pc.get('PowerCapacityWatts', 'N/A')
            print(f"    PowerControl: Consumed={watts}W Capacity={cap}W")
        for ps in psu[:2]:
            print(f"    PSU: {ps.get('Name','N/A')} | Model={ps.get('Model','N/A')} | Capacity={ps.get('PowerCapacityWatts','N/A')}W | Status={ps.get('Status',{}).get('State','N/A')}")

    # 9. Thermal details
    therm_code, therm_data = fetch(ip, user, pw, f'{ch_uri}/Thermal')
    if therm_code == 200:
        temps = therm_data.get('Temperatures', [])
        fans = therm_data.get('Fans', [])
        print(f"  Thermal: Temps={len(temps)} Fans={len(fans)}")

    # 10. FirmwareInventory full list
    fw_code, fw_data = fetch(ip, user, pw, '/redfish/v1/UpdateService/FirmwareInventory')
    if fw_code == 200:
        fw_members = fw_data.get('Members', [])
        print(f"  FirmwareInventory: {len(fw_members)} items")
        for fm in fw_members[:5]:
            fmc, fmd = fetch(ip, user, pw, fm['@odata.id'])
            if fmc == 200:
                print(f"    {fmd.get('Name','N/A')}: {fmd.get('Version','N/A')} | Updateable={fmd.get('Updateable','N/A')}")

print("\n\nDEEP PROBE COMPLETE")
