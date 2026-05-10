from __future__ import annotations

import asyncio
import sys
import warnings

import pytest

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
