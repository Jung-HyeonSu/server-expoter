# tests/reference/redfish/ — Redfish 종합 endpoint reference

## 수집 도구

`tests/reference/scripts/crawl_redfish_full.py` — ServiceRoot부터 모든 link 재귀 follow.

## 디렉터리 컨벤션

```text
tests/reference/redfish/<vendor>/<ip-with-underscore>/
├── _manifest.json     ← 전체 endpoint list / status / timing
├── _summary.txt       ← 사람이 읽는 요약
└── <path-derived>.json ← 각 endpoint raw 응답
```

`<path-derived>.json` 명명 규칙:
- 원본 path: `/redfish/v1/Systems/System.Embedded.1/Memory/DIMM.Socket.A1`
- 파일명: `redfish_v1_systems_system.embedded.1_memory_dimm.socket.a1.json` (lowercase + `/` → `_`)
- 130 자 초과 시 끝 부분에 sha1 hash 10자 추가 (Windows MAX_PATH 260 우회)

각 파일은 wrapper format:
```json
{
  "_meta": {
    "uri": "/redfish/v1/...",
    "code": 200,
    "depth": 3,
    "elapsed_ms": 234.5,
    "fetched_at": "2026-04-28T..."
  },
  "_data": { ... 실제 응답 ... }
}
```

## 수집 대상 (2026-04-28 1차)

| Vendor | IP | 상태 | 비고 |
|---|---|---|---|
| Dell | 10.100.15.27 | OK | iDRAC9 — 1624 endpoint (2417 파일) / 15MB / 17.5s (`_manifest.json` 기준) |
| Dell | 10.100.15.28 | OK | iDRAC9 |
| Dell | 10.100.15.31 | OK | iDRAC9 |
| Dell | 10.100.15.33 | OK | iDRAC9 (10.100.64.96 OS의 BMC) |
| Dell | 10.100.15.34 | OK | iDRAC9 |
| HPE | 10.50.11.231 | OK | iLO6 (ProLiant DL380 Gen11, FW 1.73) |
| Lenovo | 10.50.11.232 | OK | XCC |
| Cisco | 10.100.15.1 | **SKIP** | HTTP 503 (장비 다운 의심) |
| Cisco | 10.100.15.2 | OK | TA-UNODE-G1 (CIMC) |
| Cisco | 10.100.15.3 | **SKIP** | 연결 timeout |

## 활용

1. **새 펌웨어 / 새 모델 확인**: probe → diff against existing _manifest.json
2. **OEM 차이 비교**: `redfish/dell/*/redfish_v1_systems_system.embedded.1_oem_dell_*` vs `redfish/hpe/*/redfish_v1_systems_1_oem_hpe_*`
3. **JsonSchemas 활용**: `redfish/<vendor>/<ip>/redfish_v1_jsonschemas_*` — 그 vendor가 노출하는 schema 정의 — adapter `tested_against` 검증 자료
4. **Vault 2단계 검증**: ServiceRoot (`redfish_v1.json`)는 무인증으로도 OK — vendor detection 가능 확인

## 재실행

```bash
# 전체
python tests/reference/scripts/crawl_redfish_full.py --skip-existing

# 단일 장비
python tests/reference/scripts/crawl_redfish_full.py --target dell-10.100.15.27

# vendor 전수
python tests/reference/scripts/crawl_redfish_full.py --vendor dell

# 깊이 제한
python tests/reference/scripts/crawl_redfish_full.py --max-depth 6
```

## SKIP 처리되는 path (collection root는 1회 수집)

- `/redfish/v1/EventService/Subscriptions/*` — dynamic
- `/redfish/v1/SessionService/Sessions/*` — dynamic
- `/redfish/v1/TaskService/Tasks/*` — dynamic
- `/redfish/v1/Systems/*/LogServices/Sel/Entries` — SEL 매우 큼
- `/redfish/v1/Managers/*/LogServices/Lclog/Entries` — Dell LC log 매우 큼
- `/redfish/v1/Managers/1/LogServices/IML/Entries` — HPE IML log 매우 큼

추가/제외는 `crawl_redfish_full.py`의 `SKIP_PATH_PREFIXES` 수정.
