from __future__ import annotations

import asyncio
import sys
import warnings
from pathlib import Path

import pytest

SIBLING_CIVICCORE = Path(__file__).resolve().parents[1].parent / "civiccore"
if SIBLING_CIVICCORE.is_dir() and str(SIBLING_CIVICCORE) not in sys.path:
    sys.path.insert(0, str(SIBLING_CIVICCORE))
if SIBLING_CIVICCORE.is_dir():
    import civiccore
    import civiccore.auth

    civiccore_path = str(SIBLING_CIVICCORE / "civiccore")
    civiccore_auth_path = str(SIBLING_CIVICCORE / "civiccore" / "auth")
    if civiccore_path not in civiccore.__path__:
        civiccore.__path__.append(civiccore_path)
    if civiccore_auth_path not in civiccore.auth.__path__:
        civiccore.auth.__path__.append(civiccore_auth_path)

from civicclerk.main import STAFF_AUTH_MODE_ENV_VAR, STAFF_OPEN_MODE


if sys.platform == "win32":
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


@pytest.fixture(autouse=True)
def explicit_open_mode_for_legacy_feature_tests(
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
) -> None:
    if request.node.get_closest_marker("uses_civicclerk_default_staff_mode"):
        monkeypatch.delenv(STAFF_AUTH_MODE_ENV_VAR, raising=False)
        return
    monkeypatch.setenv(STAFF_AUTH_MODE_ENV_VAR, STAFF_OPEN_MODE)
