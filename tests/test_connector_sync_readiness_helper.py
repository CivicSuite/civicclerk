from __future__ import annotations

import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def test_connector_sync_readiness_passes_builtin_payloads_without_network() -> None:
    result = subprocess.run(
        ["python", "scripts/check_connector_sync_readiness.py"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "sync_ready=true" in result.stdout
    assert "network_calls=false" in result.stdout
    for connector in ["granicus", "legistar", "novusagenda", "primegov"]:
        assert f"[PASS] {connector} local payload" in result.stdout
    assert "CONNECTOR-SYNC-READINESS: PASSED" in result.stdout


def test_connector_sync_readiness_rejects_bad_payload_dir(tmp_path: Path) -> None:
    (tmp_path / "granicus.json").write_text(
        json.dumps({"id": "gr-100", "agenda": []}),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            "python",
            "scripts/check_connector_sync_readiness.py",
            "--connector",
            "granicus",
            "--payload-dir",
            str(tmp_path),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "sync_ready=false" in result.stdout
    assert "[FAIL] granicus local payload" in result.stdout
    assert "CONNECTOR-SYNC-READINESS: FAILED" in result.stdout


def test_connector_sync_readiness_validates_future_source_guards() -> None:
    result = subprocess.run(
        [
            "python",
            "scripts/check_connector_sync_readiness.py",
            "--connector",
            "legistar",
            "--source-url",
            "http://127.0.0.1/api",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "[FAIL] source URL" in result.stdout
    assert "blocked range" in result.stdout


def test_connector_sync_readiness_print_only_documents_no_live_sync_claim() -> None:
    result = subprocess.run(
        ["python", "scripts/check_connector_sync_readiness.py", "--print-only"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    for expected in [
        "CivicClerk connector sync readiness",
        "Network calls: disabled",
        "Not live sync",
        "do not wire scheduled live sync until this passes",
    ]:
        assert expected in result.stdout
