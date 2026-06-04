# Repo Facts — server-exporter

> 검증 기준 Agent (10.100.64.154) 에서 2026-03-27 확인. 최소 요구사항은 `REQUIREMENTS.md` 4절 참조.

## 핵심 기술 스택

| 카테고리 | 기술 | 검증 기준 버전 | 용도 |
|---------|------|--------------|------|
| Orchestration | ansible-core | 2.20.3 | 플레이북 실행 |
| | ansible (package) | 13.4.0 | core + bundled collections |
| Language | Python | 3.12.3 | 커스텀 모듈 / 필터 / 플러그인 (venv: /opt/ansible-env/) |
| Runtime | Java (OpenJDK) | 21.0.10 | Jenkins Agent 실행 |
| Template | Jinja2 | 3.1.6 | Ansible 템플릿 엔진 |
| Protocol | SSH, WinRM, Redfish API | — | 정보 수집 |
| CI/CD | Jenkins | — | 파이프라인 (Java 21 필수) |
| Secrets | Ansible Vault | — | 인증 정보 관리 |
| Utils | Python stdlib | — | Redfish HTTP, XML, JSON (외부 라이브러리 없음) |

## Collections

- `ansible.windows` 3.3.0 — Windows gather
- `community.vmware` 6.2.0 — ESXi gather
- `community.windows` 3.1.0 — Windows 보조
- `ansible.posix` 2.1.0
- `community.general` 12.4.0
- `ansible.utils` 6.0.1

## pip 패키지

- `pywinrm` 0.5.0 — Windows WinRM
- `pyvmomi` 9.0.0 — ESXi vSphere API
- `redis` 7.3.0 — Ansible fact caching
- `jmespath` 1.1.0 — json_query 필터
- `netaddr` 1.3.0 — ipaddr 필터
- `lxml` 6.0.2 — VMware XML 파싱
- Redfish는 stdlib only (urllib / ssl / json)

## 모듈 / 채널

| 채널 | 디렉터리 | 핵심 파일 |
|---|---|---|
| OS gather | `os-gather/` | site.yml (3-Play: 포트감지 → Linux → Play3 Windows), tasks/{linux,windows}/gather_*.yml |
| ESXi gather | `esxi-gather/` | site.yml (1-Play), tasks/collect_facts/config/datastores + normalize_*.yml |
| Redfish gather | `redfish-gather/` | site.yml (1-Play: precheck → detect → adapter → collect → normalize), library/redfish_gather.py (약 3,830줄) |
| 공통 | `common/` | library/precheck_bundle.py (4단계 진단), tasks/normalize/init_fragments/merge_fragment/build_*.yml |
| 어댑터 | `adapters/{redfish,os,esxi}/` | 27 YAML + registry.yml — Redfish 16 + OS 7 + ESXi 4 |
| Schema | `schema/` | sections.yml (10), field_dictionary.yml (39 Must / 38 Nice / 6 Skip = 83), baseline_v1/ (9 baseline: redfish 5 + esxi/ubuntu/windows + rhel810_raw_fallback) |
| Vault | `vault/` | linux/windows/esxi.yml + redfish/{vendor}.yml |

## 테스트

- `tests/redfish-probe/` — probe_redfish.py + deep_probe_redfish.py
- `tests/fixtures/` — 145+ 실장비 JSON 응답
- `tests/baseline_v1/` — 7+ 벤더 baseline JSON
- `tests/evidence/` — Round 7-10 조건부 검토
- `tests/scripts/` — conditional_review.py, os_esxi_verify.sh

## 정본 reference (덮어쓰지 말 것)

- `REQUIREMENTS.md` — 벤더/버전별 최소 요구사항 (정본)
- `README.md` — 프로젝트 정체성, 3-channel 개요
- `GUIDE_FOR_AI.md` — Fragment 철학, 새 gather 템플릿
- `CLAUDE.md` — Tier 0 정본
- `docs/01~19` — 운영 문서
