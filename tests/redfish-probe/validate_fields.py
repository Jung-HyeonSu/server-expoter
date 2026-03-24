"""Validate code field mappings against actual BMC payloads"""
import json, os

BASE = os.path.join(os.path.expanduser('~'), 'redfish_fixtures')

def load(vendor, name):
    path = os.path.join(BASE, vendor, f'{name}.json')
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None

def safe(d, *keys):
    for k in keys:
        if not isinstance(d, dict): return None
        d = d.get(k)
        if d is None: return None
    return d

VENDORS = ['lenovo', 'hpe', 'dell']

# ===== SYSTEM SECTION =====
print("=" * 80)
print("SYSTEM SECTION FIELD VALIDATION")
print("=" * 80)
sys_fields = [
    ('Manufacturer', ['Manufacturer']),
    ('Model', ['Model']),
    ('SerialNumber', ['SerialNumber']),
    ('SKU', ['SKU']),
    ('UUID', ['UUID']),
    ('HostName', ['HostName']),
    ('PowerState', ['PowerState']),
    ('Status.Health', ['Status', 'Health']),
    ('Status.State', ['Status', 'State']),
    ('IndicatorLED', ['IndicatorLED']),
    ('BiosVersion', ['BiosVersion']),
    ('ProcessorSummary.Count', ['ProcessorSummary', 'Count']),
    ('ProcessorSummary.Model', ['ProcessorSummary', 'Model']),
    ('ProcessorSummary.Status.Health', ['ProcessorSummary', 'Status', 'Health']),
    ('MemorySummary.TotalSystemMemoryGiB', ['MemorySummary', 'TotalSystemMemoryGiB']),
    ('MemorySummary.Status.Health', ['MemorySummary', 'Status', 'Health']),
    ('MemorySummary.Status.HealthRollup', ['MemorySummary', 'Status', 'HealthRollup']),
]

print(f"{'Field':<45} {'Lenovo':<20} {'HPE':<20} {'Dell':<20}")
print("-" * 105)
for field_name, keys in sys_fields:
    vals = []
    for v in VENDORS:
        d = load(v, 'system')
        if d:
            val = safe(d, *keys)
            if val is None:
                vals.append('MISSING')
            elif val == '':
                vals.append('EMPTY')
            else:
                s = str(val)[:18]
                vals.append(s)
        else:
            vals.append('NO FILE')
    print(f"{field_name:<45} {vals[0]:<20} {vals[1]:<20} {vals[2]:<20}")

# OEM
print("\nOEM KEYS:")
for v in VENDORS:
    d = load(v, 'system')
    if d:
        oem = d.get('Oem', {})
        print(f"  {v}: {list(oem.keys()) if oem else 'None'}")
        for ok, ov in oem.items():
            if isinstance(ov, dict):
                print(f"    {ok} sub-keys: {list(ov.keys())[:10]}")

# ===== BMC/MANAGER SECTION =====
print("\n" + "=" * 80)
print("BMC/MANAGER SECTION FIELD VALIDATION")
print("=" * 80)
bmc_fields = [
    ('FirmwareVersion', ['FirmwareVersion']),
    ('Model', ['Model']),
    ('ManagerType', ['ManagerType']),
    ('Status.Health', ['Status', 'Health']),
    ('Status.State', ['Status', 'State']),
    ('UUID', ['UUID']),
    ('DateTime', ['DateTime']),
]

print(f"{'Field':<45} {'Lenovo':<20} {'HPE':<20} {'Dell':<20}")
print("-" * 105)
for field_name, keys in bmc_fields:
    vals = []
    for v in VENDORS:
        d = load(v, 'manager')
        if d:
            val = safe(d, *keys)
            if val is None: vals.append('MISSING')
            elif val == '': vals.append('EMPTY')
            else: vals.append(str(val)[:18])
        else:
            vals.append('NO FILE')
    print(f"{field_name:<45} {vals[0]:<20} {vals[1]:<20} {vals[2]:<20}")

# ===== PROCESSOR SECTION =====
print("\n" + "=" * 80)
print("PROCESSOR SECTION FIELD VALIDATION")
print("=" * 80)
proc_fields = [
    ('Id', ['Id']),
    ('Name', ['Name']),
    ('Model', ['Model']),
    ('Manufacturer', ['Manufacturer']),
    ('Socket', ['Socket']),
    ('TotalCores', ['TotalCores']),
    ('TotalThreads', ['TotalThreads']),
    ('MaxSpeedMHz', ['MaxSpeedMHz']),
    ('Status.Health', ['Status', 'Health']),
    ('Status.State', ['Status', 'State']),
    ('InstructionSet', ['InstructionSet']),
    ('ProcessorArchitecture', ['ProcessorArchitecture']),
]

print(f"{'Field':<45} {'Lenovo':<20} {'HPE':<20} {'Dell':<20}")
print("-" * 105)
for field_name, keys in proc_fields:
    vals = []
    for v in VENDORS:
        d = load(v, 'system_processors_0')
        if d:
            val = safe(d, *keys)
            if val is None: vals.append('MISSING')
            elif val == '': vals.append('EMPTY')
            else: vals.append(str(val)[:18])
        else:
            vals.append('NO FILE')
    print(f"{field_name:<45} {vals[0]:<20} {vals[1]:<20} {vals[2]:<20}")

# ===== MEMORY SECTION =====
print("\n" + "=" * 80)
print("MEMORY SECTION FIELD VALIDATION")
print("=" * 80)
mem_fields = [
    ('Id', ['Id']),
    ('Name', ['Name']),
    ('CapacityMiB', ['CapacityMiB']),
    ('MemoryDeviceType', ['MemoryDeviceType']),
    ('OperatingSpeedMhz', ['OperatingSpeedMhz']),
    ('Manufacturer', ['Manufacturer']),
    ('SerialNumber', ['SerialNumber']),
    ('PartNumber', ['PartNumber']),
    ('Status.Health', ['Status', 'Health']),
    ('Status.State', ['Status', 'State']),
    ('DataWidthBits', ['DataWidthBits']),
    ('BusWidthBits', ['BusWidthBits']),
    ('RankCount', ['RankCount']),
    ('BaseModuleType', ['BaseModuleType']),
    ('MemoryType', ['MemoryType']),
]

print(f"{'Field':<45} {'Lenovo':<20} {'HPE':<20} {'Dell':<20}")
print("-" * 105)
for field_name, keys in mem_fields:
    vals = []
    for v in VENDORS:
        d = load(v, 'system_memory_0')
        if d:
            val = safe(d, *keys)
            if val is None: vals.append('MISSING')
            elif val == '': vals.append('EMPTY')
            else: vals.append(str(val)[:18])
        else:
            vals.append('NO FILE')
    print(f"{field_name:<45} {vals[0]:<20} {vals[1]:<20} {vals[2]:<20}")

# ===== STORAGE SECTION =====
print("\n" + "=" * 80)
print("STORAGE SECTION FIELD VALIDATION")
print("=" * 80)
# Check storage controller structure
for v in VENDORS:
    d = load(v, 'system_storage_0')
    if d:
        print(f"\n  [{v.upper()}] Storage top-level keys: {list(d.keys())[:15]}")
        ctrls = d.get('StorageControllers', [])
        if ctrls:
            print(f"    StorageControllers: {len(ctrls)} items")
            for c in ctrls[:1]:
                print(f"      Keys: {list(c.keys())[:12]}")
                print(f"      Name={c.get('Name')} Model={c.get('Model')} FW={c.get('FirmwareVersion')}")
        else:
            print(f"    StorageControllers: MISSING (check Controllers link)")
            ctrl_link = d.get('Controllers', {})
            if isinstance(ctrl_link, dict) and '@odata.id' in ctrl_link:
                print(f"    Controllers link: {ctrl_link['@odata.id']}")

        drives = d.get('Drives', [])
        print(f"    Drives links: {len(drives)}")

# Drive fields
drive_fields = [
    ('Name', ['Name']),
    ('Model', ['Model']),
    ('SerialNumber', ['SerialNumber']),
    ('Manufacturer', ['Manufacturer']),
    ('MediaType', ['MediaType']),
    ('Protocol', ['Protocol']),
    ('CapacityBytes', ['CapacityBytes']),
    ('Status.Health', ['Status', 'Health']),
    ('RotationSpeedRPM', ['RotationSpeedRPM']),
    ('BlockSizeBytes', ['BlockSizeBytes']),
    ('CapableSpeedGbs', ['CapableSpeedGbs']),
]

# Find first drive fixture per vendor
print(f"\n{'Field':<45} {'Lenovo':<20} {'HPE':<20} {'Dell':<20}")
print("-" * 105)
drive_files = {
    'lenovo': 'drive_RAID_Slot3_0',
    'hpe': 'drive_DE00C000_0',
    'dell': 'drive_RAID.Slot.6-1_0',
}
for field_name, keys in drive_fields:
    vals = []
    for v in VENDORS:
        d = load(v, drive_files.get(v, ''))
        if d:
            val = safe(d, *keys)
            if val is None: vals.append('MISSING')
            elif val == '': vals.append('EMPTY')
            else: vals.append(str(val)[:18])
        else:
            vals.append('NO FILE')
    print(f"{field_name:<45} {vals[0]:<20} {vals[1]:<20} {vals[2]:<20}")

# ===== NETWORK SECTION =====
print("\n" + "=" * 80)
print("NETWORK/ETHERNET SECTION FIELD VALIDATION")
print("=" * 80)
net_fields = [
    ('Id', ['Id']),
    ('Name', ['Name']),
    ('MACAddress', ['MACAddress']),
    ('SpeedMbps', ['SpeedMbps']),
    ('LinkStatus', ['LinkStatus']),
    ('Status.Health', ['Status', 'Health']),
    ('Status.State', ['Status', 'State']),
    ('IPv4Addresses', ['IPv4Addresses']),
    ('IPv6Addresses', ['IPv6Addresses']),
    ('InterfaceEnabled', ['InterfaceEnabled']),
    ('FQDN', ['FQDN']),
    ('HostName', ['HostName']),
    ('PermanentMACAddress', ['PermanentMACAddress']),
    ('AutoNeg', ['AutoNeg']),
    ('FullDuplex', ['FullDuplex']),
]

print(f"{'Field':<45} {'Lenovo':<20} {'HPE':<20} {'Dell':<20}")
print("-" * 105)
for field_name, keys in net_fields:
    vals = []
    for v in VENDORS:
        d = load(v, 'system_ethernetinterfaces_0')
        if d:
            val = safe(d, *keys)
            if val is None:
                vals.append('MISSING')
            elif val == '':
                vals.append('EMPTY')
            elif isinstance(val, list):
                vals.append(f'[{len(val)} items]')
            else:
                vals.append(str(val)[:18])
        else:
            vals.append('NO FILE')
    print(f"{field_name:<45} {vals[0]:<20} {vals[1]:<20} {vals[2]:<20}")

# ===== POWER SECTION =====
print("\n" + "=" * 80)
print("POWER SECTION FIELD VALIDATION")
print("=" * 80)
for v in VENDORS:
    d = load(v, 'chassis_power')
    if d:
        print(f"\n  [{v.upper()}] Power top-level keys: {list(d.keys())[:10]}")
        pc = d.get('PowerControl', [])
        print(f"    PowerControl: {len(pc)} items")
        if pc:
            p0 = pc[0]
            print(f"      Keys: {list(p0.keys())[:10]}")
            print(f"      ConsumedWatts={p0.get('PowerConsumedWatts')} CapacityWatts={p0.get('PowerCapacityWatts')}")

        psu = d.get('PowerSupplies', [])
        print(f"    PowerSupplies: {len(psu)} items")
        if psu:
            p0 = psu[0]
            print(f"      Keys: {list(p0.keys())[:12]}")
            print(f"      Name={p0.get('Name')} Model={p0.get('Model')} Capacity={p0.get('PowerCapacityWatts')}W")
            print(f"      Serial={p0.get('SerialNumber')} FW={p0.get('FirmwareVersion')} Health={safe(p0, 'Status', 'Health')}")
            print(f"      Manufacturer={p0.get('Manufacturer')} State={safe(p0, 'Status', 'State')}")

# ===== FIRMWARE SECTION =====
print("\n" + "=" * 80)
print("FIRMWARE SECTION FIELD VALIDATION")
print("=" * 80)
fw_fields = [
    ('Id', ['Id']),
    ('Name', ['Name']),
    ('Version', ['Version']),
    ('Updateable', ['Updateable']),
    ('SoftwareId', ['SoftwareId']),
    ('Description', ['Description']),
    ('ReleaseDate', ['ReleaseDate']),
    ('Manufacturer', ['Manufacturer']),
]

print(f"{'Field':<45} {'Lenovo':<20} {'HPE':<20} {'Dell':<20}")
print("-" * 105)
for field_name, keys in fw_fields:
    vals = []
    for v in VENDORS:
        d = load(v, 'firmware_0')
        if d:
            val = safe(d, *keys)
            if val is None: vals.append('MISSING')
            elif val == '': vals.append('EMPTY')
            else: vals.append(str(val)[:18])
        else:
            vals.append('NO FILE')
    print(f"{field_name:<45} {vals[0]:<20} {vals[1]:<20} {vals[2]:<20}")

# ===== CHASSIS SECTION =====
print("\n" + "=" * 80)
print("CHASSIS SECTION FIELD VALIDATION")
print("=" * 80)
ch_fields = [
    ('ChassisType', ['ChassisType']),
    ('Model', ['Model']),
    ('Manufacturer', ['Manufacturer']),
    ('SerialNumber', ['SerialNumber']),
    ('PartNumber', ['PartNumber']),
    ('SKU', ['SKU']),
    ('AssetTag', ['AssetTag']),
    ('IndicatorLED', ['IndicatorLED']),
    ('Status.Health', ['Status', 'Health']),
    ('Status.State', ['Status', 'State']),
]

print(f"{'Field':<45} {'Lenovo':<20} {'HPE':<20} {'Dell':<20}")
print("-" * 105)
for field_name, keys in ch_fields:
    vals = []
    for v in VENDORS:
        d = load(v, 'chassis')
        if d:
            val = safe(d, *keys)
            if val is None: vals.append('MISSING')
            elif val == '': vals.append('EMPTY')
            else: vals.append(str(val)[:18])
        else:
            vals.append('NO FILE')
    print(f"{field_name:<45} {vals[0]:<20} {vals[1]:<20} {vals[2]:<20}")

# ===== DETECT VENDOR VALIDATION =====
print("\n" + "=" * 80)
print("VENDOR DETECTION VALIDATION")
print("=" * 80)
for v in VENDORS:
    sr = load(v, 'service_root')
    sys = load(v, 'system')
    mgr = load(v, 'manager')
    if sr:
        print(f"\n  [{v.upper()}]")
        print(f"    ServiceRoot.Vendor = {sr.get('Vendor', 'MISSING')}")
        print(f"    ServiceRoot.Oem keys = {list(sr.get('Oem', {}).keys()) if sr.get('Oem') else 'None'}")
    if sys:
        print(f"    System.Manufacturer = {sys.get('Manufacturer', 'MISSING')}")
        print(f"    System.Model = {sys.get('Model', 'MISSING')}")
    if mgr:
        print(f"    Manager.Model = {mgr.get('Model', 'MISSING')}")
        print(f"    Manager.FirmwareVersion = {mgr.get('FirmwareVersion', 'MISSING')}")
        print(f"    Manager.ManagerType = {mgr.get('ManagerType', 'MISSING')}")

# ===== URI PATTERN VALIDATION =====
print("\n" + "=" * 80)
print("URI PATTERN VALIDATION (Systems/Managers/Chassis member IDs)")
print("=" * 80)
for v in VENDORS:
    sc = load(v, 'systems_collection')
    mc = load(v, 'managers_collection')
    cc = load(v, 'chassis_collection')
    print(f"\n  [{v.upper()}]")
    if sc:
        members = [m['@odata.id'] for m in sc.get('Members', [])]
        print(f"    Systems members: {members}")
    if mc:
        members = [m['@odata.id'] for m in mc.get('Members', [])]
        print(f"    Managers members: {members}")
    if cc:
        members = [m['@odata.id'] for m in cc.get('Members', [])]
        print(f"    Chassis members: {members}")

print("\n\nFIELD VALIDATION COMPLETE")
