# Test Inventory

## baseline vs supplemental 분리 원칙

### Baseline 장비 (기준선)
기존 `redfish-gather/inventory.sh` + `vault/redfish/{vendor}.yml`(ansible-vault encrypted)로 관리.
baseline credential 변경 금지.

| 벤더 | vault 파일 | 비고 |
|---|---|---|
| Lenovo | vault/redfish/lenovo.yml | baseline 고정 |
| HPE | vault/redfish/hpe.yml | baseline 고정 |
| Dell | vault/redfish/dell.yml | baseline 고정 (R740 기준) |
| Cisco | vault/redfish/cisco.yml | baseline 고정 |

### Supplemental 장비 (추가 검증)
추가 evidence 수집 전용. baseline 정책을 변경하는 근거로 사용하면 안 됨.

credential은 다음 방식으로만 관리:
1. `tests/inventory/local/supplemental.ini` (gitignored, 로컬 전용)
2. `tests/vault/supplemental.yml` (ansible-vault encrypted)
3. 일회성 `--extra-vars` (디버깅 용도 한정)

### 사용 방법
```bash
# 1. 샘플 파일을 local/로 복사
cp tests/inventory/supplemental.sample.ini tests/inventory/local/supplemental.ini

# 2. 실제 credential 입력 (에디터로 편집)
vi tests/inventory/local/supplemental.ini

# 3. 실행
ansible-playbook redfish-gather/site.yml -i tests/inventory/local/supplemental.ini
```

### 주의사항
- repo tracked 파일에 평문 credential을 넣지 말 것
- Dell R760 credential이 Dell baseline과 다르다고 해서 세대별 vault 분리를 채택하면 안 됨
- supplemental 장비는 baseline 정책을 변경하는 근거가 아닌, 추가 evidence 수집용
