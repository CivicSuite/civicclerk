from __future__ import annotations

from pathlib import Path
import subprocess

from civicclerk.vendor_live_sync import (
    VendorLiveSyncConfig,
    VendorSyncRunResult,
    VendorSyncState,
    apply_vendor_sync_result,
    compute_health_status,
    operator_status,
    source_status,
    validate_live_sync_config,
)


ROOT = Path(__file__).resolve().parents[1]


def test_live_sync_config_validation_uses_civiccore_url_guards_without_network() -> None:
    checks = validate_live_sync_config(
        VendorLiveSyncConfig(
            connector="legistar",
            source_url="http://127.0.0.1/api/meetings",
            auth_method="bearer_token",
        )
    )

    assert any(check.name == "supported connector" and check.status == "PASS" for check in checks)
    source_url = next(check for check in checks if check.name == "source URL")
    assert source_url.status == "FAIL"
    assert "blocked range" in source_url.message
    assert "vendor HTTPS host" in source_url.fix


def test_live_sync_config_validation_rejects_credentials_in_url() -> None:
    checks = validate_live_sync_config(
        VendorLiveSyncConfig(
            connector="granicus",
            source_url="https://vendor.example.gov/api/meetings?api_key=secret",
            auth_method="api_key",
        )
    )

    credential_check = next(check for check in checks if check.name == "credential location")
    assert credential_check.status == "FAIL"
    assert "credentials" in credential_check.message
    assert "deployment secrets" in credential_check.fix


def test_circuit_opens_after_five_consecutive_full_run_failures() -> None:
    state = VendorSyncState(connector="legistar", source_name="Legistar")

    for _ in range(5):
        state = apply_vendor_sync_result(
            state,
            VendorSyncRunResult(records_discovered=1, records_succeeded=0, records_failed=1),
        )

    assert state.consecutive_failure_count == 5
    assert state.sync_paused is True
    assert compute_health_status(state) == "circuit_open"
    assert "unpause" in operator_status(state)["fix"]


def test_source_status_uses_shared_civiccore_projection_for_source_lists() -> None:
    state = VendorSyncState(
        connector="legistar",
        source_name="Legistar production",
        active_failure_count=2,
        last_sync_status="partial",
    )

    status = source_status(state)

    assert status["health_status"] == "degraded"
    assert status["active_failure_count"] == 2
    assert status["last_sync_status"] == "partial"
    assert status["next_sync_at"] is None
    assert "live sync is degraded" in str(status["message"])


def test_circuit_stays_degraded_before_threshold() -> None:
    state = VendorSyncState(connector="primegov", source_name="PrimeGov")

    for _ in range(4):
        state = apply_vendor_sync_result(
            state,
            VendorSyncRunResult(records_discovered=1, records_succeeded=0, records_failed=1),
        )

    assert state.consecutive_failure_count == 4
    assert state.sync_paused is False
    assert compute_health_status(state) == "degraded"


def test_success_resets_failure_count_and_grace_period() -> None:
    state = VendorSyncState(
        connector="novusagenda",
        source_name="NovusAGENDA",
        consecutive_failure_count=1,
        sync_paused_reason="grace_period",
    )

    state = apply_vendor_sync_result(
        state,
        VendorSyncRunResult(records_discovered=1, records_succeeded=1, records_failed=0),
    )

    assert state.consecutive_failure_count == 0
    assert state.sync_paused is False
    assert state.sync_paused_reason is None
    assert state.last_sync_status == "success"
    assert compute_health_status(state) == "healthy"


def test_grace_period_reopens_after_two_failures() -> None:
    state = VendorSyncState(connector="granicus", sync_paused_reason="grace_period")

    for _ in range(2):
        state = apply_vendor_sync_result(
            state,
            VendorSyncRunResult(records_discovered=1, records_succeeded=0, records_failed=1),
        )

    assert state.consecutive_failure_count == 2
    assert state.sync_paused is True
    assert compute_health_status(state) == "circuit_open"


def test_zero_work_run_does_not_increment_failure_count() -> None:
    state = VendorSyncState(connector="legistar", consecutive_failure_count=3)

    state = apply_vendor_sync_result(
        state,
        VendorSyncRunResult(records_discovered=0, records_succeeded=0, records_failed=0),
    )

    assert state.consecutive_failure_count == 3
    assert state.last_sync_status == "success"
    assert compute_health_status(state) == "degraded"


def test_vendor_live_sync_readiness_script_reports_circuit_open_without_network() -> None:
    result = subprocess.run(
        [
            "python",
            "scripts/check_vendor_live_sync_readiness.py",
            "--connector",
            "legistar",
            "--source-url",
            "https://vendor.example.gov/api/meetings",
            "--auth-method",
            "bearer_token",
            "--simulate-consecutive-failures",
            "5",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "live_sync_ready=true" in result.stdout
    assert "network_calls=false" in result.stdout
    assert "health_status=circuit_open" in result.stdout
    assert "sync_paused=true" in result.stdout
    assert "VENDOR-LIVE-SYNC-READINESS: PASSED" in result.stdout


def test_vendor_live_sync_readiness_script_blocks_private_source_url() -> None:
    result = subprocess.run(
        [
            "python",
            "scripts/check_vendor_live_sync_readiness.py",
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
    assert "live_sync_ready=false" in result.stdout
    assert "[FAIL] source URL" in result.stdout
    assert "VENDOR-LIVE-SYNC-READINESS: FAILED" in result.stdout


def test_vendor_live_sync_readiness_print_only_is_honest() -> None:
    result = subprocess.run(
        ["python", "scripts/check_vendor_live_sync_readiness.py", "--print-only"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Network calls: disabled" in result.stdout
    assert "opens after 5 consecutive full-run failures" in result.stdout
    assert "Not a vendor pull" in result.stdout
