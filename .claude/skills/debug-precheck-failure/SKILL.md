---
name: debug-precheck-failure
description: 진단 (TCP 도달 → 프로토콜 → 인증 (ICMP 미사용)) 어디서 막혔는지 분석. precheck_bundle.py 결과의 diagnosis.details를 해석하고 구체적 해결 방향 제시. 사용자가 "포트는 열렸는데 protocol 실패", "auth 단계에서 막힘", "precheck 실패 원인" 등 요청 시. - precheck 실패 발생 / graceful degradation 했지만 일부 데이터 누락 / 새 BMC 응답 없음
---

# debug-precheck-failure

## 목적

server-exporter의 4단계 진단(`common/library/precheck_bundle.py`) 어느 단계에서 실패했는지 분석 + 구체적 디버깅 절차 안내.

## 4단계 (rule 27 R2)

| 단계 | 책임 | 일반적 실패 원인 |
|---|---|---|
| 1. ping | ICMP / TCP SYN으로 host 도달성 | 네트워크 / firewall / VLAN |
| 2. port | target_type별 포트 (SSH 22 / WinRM 5985-5986 / vSphere 443 / Redfish 443) | 서비스 미기동 / firewall |
| 3. protocol | TCP 응답 + 첫 응답 형식 (HTTPS handshake / SSH banner / Redfish JSON) | TLS 버전 / cipher suite / 잘못된 protocol |
| 4. auth | 자격증명으로 인증 | vault 자격증명 잘못 / 사용자 잠김 / privilege 부족 |

## 입력

- target_ip
- target_type (os / esxi / redfish)
- precheck 결과 JSON (envelope의 `diagnosis.precheck`)

## 출력

```markdown
## Precheck 실패 분석 — 10.x.x.1 (target_type=redfish)

### 결과
- ping: ok
- port: ok (443 응답)
- protocol: **fail** ("HTTPS handshake failed: TLS version mismatch")
- auth: skipped

### 진단
3단계 protocol 실패 — TLS 버전 불일치.
구 BMC 펌웨어가 TLS 1.0/1.1만 지원하는데 Python 3.12 default ssl context는 TLS 1.2+.

### 해결 방향
1. 펌웨어 업그레이드 권고 (BMC 운영자 확인)
2. 또는 redfish_gather.py에 TLS 버전 fallback 추가:
   ```python
   ctx = ssl.create_default_context()
   ctx.minimum_version = ssl.TLSVersion.TLSv1
   ```
   → 코드에 의도 명시 주석 (cycle-011: rule 60 보안 정책 해제) + ai-context/external/integration.md 갱신

### 다음 단계
- 펌웨어 정보 확인 (`Manufacturer` / `Model` Wikipedia spec 비교)
- `docs/ai/catalogs/EXTERNAL_CONTRACTS.md`에 drift 추가 (rule 96 R4)
```

## 절차

### Step 1: ping 실패

```bash
ping -c 3 <target_ip>
# 또는 (방화벽으로 ICMP 차단 시)
nc -zv <target_ip> <port>
```

원인:
- 네트워크 / VLAN 분리 → Agent 노드 라우팅 확인
- ICMP 차단 → TCP SYN으로 대체

### Step 2: port 실패

```bash
nc -zv <target_ip> 443       # Redfish / vSphere
nc -zv <target_ip> 22        # SSH (Linux)
nc -zv <target_ip> 5986      # WinRM HTTPS
```

원인:
- 서비스 미기동 (BMC 재시작 필요)
- 방화벽 (Agent IP 허용 규칙 확인)

### Step 3: protocol 실패

```bash
# Redfish HTTPS handshake
curl -kv https://<ip>/redfish/v1/ 2>&1 | head -30

# SSH banner
ssh -o ConnectTimeout=10 -v root@<ip> 2>&1 | head -20
```

원인:
- TLS 버전 (구 BMC = TLS 1.0/1.1)
- Cipher suite 불일치
- 잘못된 protocol (예: target_type=esxi인데 실제는 Linux host)

### Step 4: auth 실패

```bash
# Redfish Basic Auth
curl -k -u "user:pass" https://<ip>/redfish/v1/Systems

# SSH
ssh -i <key> root@<ip>

# WinRM
python -c "import winrm; s = winrm.Session('<ip>', auth=('<user>','<pass>'), transport='ntlm'); print(s.run_cmd('hostname'))"
```

원인:
- vault 자격증명 stale (rotate-vault skill로 갱신)
- 사용자 잠김 (BMC 로그인 시도 횟수 초과)
- privilege 부족 (read-only 사용자가 일부 endpoint 403)

## server-exporter 도메인 적용

- 영향 채널: 모든 채널 (precheck 공통)
- 영향 vendor: 진단 대상

## 적용 rule / 관련

- **rule 27** (precheck-guard-first) — 4단계 정본
- (cycle-011: rule 60 해제 — 자격증명 / TLS 정책은 운영 권장 수준)
- rule 96 (external-contract-integrity) — protocol drift 발견 시
- skill: `classify-precheck-layer`, `debug-external-integrated-feature`, `rotate-vault`
- agent: `precheck-engineer`
- 정본: `docs/11_precheck-module.md`, `common/library/precheck_bundle.py`
- reference: `docs/ai/references/redfish/redfish-spec.md`, `docs/ai/references/winrm/pywinrm.md`
