# Python Redfish Clients — 비교 + server-exporter 선택 근거

> Source: HPE python-ilorest-library, OpenStack Sushy, DMTF python-redfish, server-exporter stdlib 자체구현 비교.
> Fetched: 2026-04-27.

## 비교 매트릭스

| 라이브러리 | 의존성 | vendor 호환 | 인증 | server-exporter 선택? |
|---|---|---|---|---|
| **stdlib만** (urllib + ssl + json) | 없음 | DMTF 표준만 (vendor OEM은 adapter로) | Basic + X-Auth-Token | **YES** (rule 10 R2) |
| `python-ilorest-library` (HPE) | requests + 보조 | iLO 4/5/6 + 일반 Redfish | Basic + Session | NO (HPE 종속 + 외부 라이브러리) |
| Sushy (OpenStack) | requests | DMTF 표준 (Ironic 사용) | Basic + Session | NO (외부 라이브러리, 의존성 추가) |
| python-redfish (DMTF) | requests | DMTF 공식 | Basic + Session | NO (외부 라이브러리) |

## server-exporter 선택: stdlib 자체구현

`redfish-gather/library/redfish_gather.py` (약 3,430줄, 2026-05-29 재실측) — `urllib + ssl + json + base64`만 사용 (rule 10 R2).

### 선택 근거

1. **의존성 최소화**: Agent 환경에 추가 pip 설치 부담 없음
2. **server-exporter 도메인 적합**: vendor OEM은 adapter YAML + tasks/vendors/로 분리 (rule 12)
3. **stdlib 충분**: Redfish는 HTTP+JSON. urllib + ssl로 100% 처리 가능
4. **Robust**: 네트워크 / 인증 / TLS 모두 표준 라이브러리로

### 단점 / 트레이드오프

- vendor-specific 편의 API 없음 → adapter 시스템으로 보완
- Session-based auth는 직접 구현 필요 (현재 server-exporter는 Basic 우선)

## stdlib 구현 패턴 (server-exporter)

```python
import urllib.request
import urllib.error
import ssl
import json
import base64

def get(url, user, pwd, timeout=30, verify=False):
    ctx = ssl.create_default_context()
    if not verify:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    
    req = urllib.request.Request(url)
    if user:
        token = base64.b64encode(f"{user}:{pwd}".encode()).decode()
        req.add_header('Authorization', f'Basic {token}')
    req.add_header('Accept', 'application/json')
    
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return {'error': str(e), 'code': e.code}
    except (urllib.error.URLError, OSError) as e:
        return {'error': str(e)}
```

### TLS 버전 fallback (구 BMC)

```python
ctx = ssl.create_default_context()
ctx.minimum_version = ssl.TLSVersion.TLSv1  # 구 펌웨어 지원
```

(rule 96 — adapter origin 주석 / drift 기록 / cycle-011: rule 60 해제, TLS 정책 운영자 결정)

### Session-based auth (필요 시 추가)

```python
# POST /redfish/v1/SessionService/Sessions
data = json.dumps({"UserName": user, "Password": pwd}).encode()
req = urllib.request.Request(f"{base_url}/redfish/v1/SessionService/Sessions",
                              data=data, method='POST')
req.add_header('Content-Type', 'application/json')
with urllib.request.urlopen(req, context=ctx) as r:
    token = r.headers.get('X-Auth-Token')
# 후속 요청 시
req.add_header('X-Auth-Token', token)
```

## 라이브러리 도입 시 고려사항

만약 향후 server-exporter가 Sushy / ilorest / python-redfish 도입을 검토한다면:

1. **rule 10 R2 (stdlib 우선) 예외 명시** — 명시적 ADR 필요
2. **agent 환경 의존성 갱신** — REQUIREMENTS.md + ansible.cfg
3. **벤더 종속** 최소화 — Sushy 또는 python-redfish (DMTF 표준)이 ilorest보다 적합
4. **현재 stdlib 구현 한계** 명확히 — Session-based / batch 요청 / 비동기 등이 약점일 때만

## 적용 rule / 관련

- **rule 10 R2 (stdlib 우선)** — 핵심 결정 근거
- rule 30 (integration-redfish-vmware-os)
- (cycle-011: rule 60 해제 — TLS verify 정책은 운영자 결정)
- rule 96 (external-contract-integrity)
- 정본: `redfish-gather/library/redfish_gather.py`
- reference: `docs/ai/references/redfish/redfish-spec.md`
