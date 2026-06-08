"""tests/integration 공용 pytest 설정.

- emulator_harness 가 import 되도록 본 디렉터리를 sys.path 에 보장.
- integration / live 마커 등록 (PytestUnknownMarkWarning 제거).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "integration: 외부 시스템 연동/에뮬레이터 재생 회귀 테스트 (오프라인)",
    )
    config.addinivalue_line(
        "markers",
        "live: 실행 중인 에뮬레이터/실장비 필요 (기본 skip — env gating)",
    )
