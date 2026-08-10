# Project Map — server-exporter

> 디렉터리 구조 요약. 정본은 `CLAUDE.md` "파일 구조" 섹션 + `docs/06_gather-structure.md` 참조.

## 최상위 구조

```
server-exporter/
├── CLAUDE.md, GUIDE_FOR_AI.md, REQUIREMENTS.md, README.md  (정본)
├── ansible.cfg, Jenkinsfile, Jenkinsfile_grafana, Jenkinsfile_portal  (운영)
├── adapters/        # 벤더/세대별 YAML adapter (25개)
│   ├── redfish/     # 14개 (generic + dell×3 + hpe×4 + lenovo×2 + supermicro×3 + cisco)
│   ├── os/          # 7개 (linux_*/windows_*)
│   └── esxi/        # 4개 (generic + 6x/7x/8x)
├── callback_plugins/    # json_only.py — stdout callback (OUTPUT 태스크만 JSON)
├── common/
│   ├── library/         # precheck_bundle.py (4단계 진단)
│   ├── tasks/normalize/ # init_fragments / merge_fragment / build_*.yml (10개)
│   └── vars/            # vendor_aliases.yml + supported_sections.yml
├── filter_plugins/      # diagnosis_mapper.py + field_mapper.py
├── lookup_plugins/      # adapter_loader.py (adapter 동적 선택)
├── module_utils/        # adapter_common.py (점수 계산 + 벤더 정규화)
├── os-gather/           # site.yml (4-Play) + tasks/{linux,windows}/
├── esxi-gather/         # site.yml + tasks/
├── redfish-gather/      # site.yml + library/redfish_gather.py + tasks/vendors/{vendor}/
├── schema/              # sections.yml + field_dictionary.yml + baseline_v1/ + examples/
├── tests/               # redfish-probe/ + fixtures/ + evidence/ + scripts/
├── tools/               # 운영 도우미
├── vault/               # linux/windows/esxi.yml + redfish/{vendor}.yml
├── docs/                # 01~19 운영 문서 + ai/ + superpowers/
├── scripts/             # ai/hooks/ + ai/*.py
└── .claude/             # rules / skills / agents / role / ai-context / policy / templates / commands
```

## 채널 흐름 (호출자 → 결과)

```
호출자 (HTTP POST)
  ├─ loc: ich|chj|yi
  ├─ target_type: os|esxi|redfish
  └─ inventory_json: [{service_ip|bmc_ip|ip}]
         ↓
    Jenkins Job (Jenkinsfile, 4-Stage)
    ├─ [1 Validate] 입력값 검증
    ├─ [2 Gather] ansible-playbook
    │   ├─ os-gather/site.yml (4-Play)
    │   ├─ esxi-gather/site.yml
    │   └─ redfish-gather/site.yml
    ├─ [3 Validate Schema] field_dictionary 정합 (FAIL 게이트)
    ├─ [4 E2E Regression] pytest baseline (FAIL 게이트)
    └─ [Post] json_only callback → JSON 출력
```

## Fragment 변수 패턴

각 gather가 만드는 fragment (Fragment 철학) — 5 공통 변수 (변수 이름 동일, 값으로 자기 섹션을 채움):
- `_data_fragment` — 섹션별 raw 데이터 dict
- `_sections_supported_fragment` — 지원 섹션 list
- `_sections_collected_fragment` — 수집 성공 섹션 list
- `_sections_failed_fragment` — 수집 실패 섹션 list
- `_errors_fragment` — 수집 오류 list

`merge_fragment.yml`이 누적 병합 → 공통 builder 5종이 최종 JSON 조립.

## 정본 reference

- `CLAUDE.md` "파일 구조" 섹션 — 가장 상세
- `docs/06_gather-structure.md` — gather 구조
- `docs/07_normalize-flow.md` — Fragment 정규화 흐름
- `docs/10_adapter-system.md` — Adapter 시스템

## fingerprint

`scripts/ai/check_project_map_drift.py`가 watched dirs 의 SHA-1 비교. baseline은 `.claude/policy/project-map-fingerprint.yaml`.
