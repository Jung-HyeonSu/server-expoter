# Project Map — server-exporter

> 디렉터리 구조 요약. 정본은 `CLAUDE.md` "파일 구조" 섹션 + `docs/develop/01-gather-structure.md` 참조.

## 최상위 구조

```
server-exporter/
├── CLAUDE.md, GUIDE_FOR_AI.md, REQUIREMENTS.md, README.md  (정본)
├── ansible.cfg, Jenkinsfile, Jenkinsfile_portal, Jenkinsfile_portal_test  (운영 경로는 _portal)
├── adapters/        # 벤더/세대별 YAML adapter
│   ├── redfish/     # vendor × 세대
│   ├── os/          # linux_* / windows_*
│   └── esxi/        # generic + 6x/7x/8x (9.x 어댑터는 없다)
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
├── vault/               # vault/common/redfish/standard.yml + <loc>/{esxi.yml,os/,redfish/}
├── docs/                # 사람용 문서 + ai/ (하네스 전용)
├── scripts/             # ai/hooks/ + ai/*.py
└── .claude/             # rules / skills / agents / role / ai-context / policy / templates / commands
```

## 채널 흐름 (호출자 → 결과)

```
호출자 (HTTP POST)
  ├─ loc: locations.yml 의 키 (현재 ich|chj|yi|git)
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
- `docs/develop/01-gather-structure.md` — gather 구조
- `docs/develop/02-normalize-flow.md` — Fragment 정규화 흐름
- `docs/develop/03-adapter-system.md` — Adapter 시스템

## fingerprint

`scripts/ai/check_project_map_drift.py`가 watched dirs 의 SHA-1 비교. baseline은 `.claude/policy/project-map-fingerprint.yaml`.
