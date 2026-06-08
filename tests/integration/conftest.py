"""tests/integration 공용 pytest 설정.

- emulator_harness 가 import 되도록 본 디렉터리를 sys.path 에 보장.
- integration / live 마커 등록 (PytestUnknownMarkWarning 제거).
- hermetic 가드: 비-live 테스트 중 실 네트워크 호출을 차단해 "오프라인 / 네트워크
  호출 0" 불변식을 convention → enforced assertion 으로 격상.
"""
import sys
from pathlib import Path

import pytest

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


@pytest.fixture(autouse=True)
def _hermetic_network_guard(request, monkeypatch):
    """비-live integration 테스트 동안 redfish_gather 의 실 네트워크 호출을 차단.

    replay 는 rg._get/_get_noauth seam swap 으로 네트워크 0 이어야 한다(테스트
    docstring 의 명시 불변식). 그러나 _probe_realm_hint(redfish_gather.py)는 seam 을
    우회해 urlreq.urlopen 을 직접 호출하므로, 미래에 vendor=unknown fixture 가 추가돼
    그 경로가 활성화되면 'offline' 테스트가 조용히 실 네트워크를 탈 수 있다. 본 가드는
    urlreq.urlopen 을 raise 로 바꿔, seam 우회 누출을 즉시 명확한 실패로 표면화한다.

    live 마커(test_live_emulator_smoke)는 실 네트워크가 필요하므로 면제.
    capture_emulator.py 는 pytest 가 아니라 스크립트라 영향 없음.
    """
    if request.node.get_closest_marker("live"):
        return
    import emulator_harness as H  # rg import + ansible stub 보장

    def _blocked(req, *args, **kwargs):
        url = getattr(req, "full_url", req)
        raise RuntimeError(
            f"hermetic guard: 비-live integration 테스트가 네트워크 시도 ({url}). "
            f"replay seam(_get/_get_noauth) 우회 — _probe_realm_hint 등 직접 urlopen "
            f"경로가 활성화됐거나 replay 누출. fixture/회귀 점검 필요."
        )

    monkeypatch.setattr(H.rg.urlreq, "urlopen", _blocked)
