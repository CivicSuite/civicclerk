from __future__ import annotations

from datetime import UTC, datetime, timezone, timedelta

from civicclerk.vendor_delta import plan_vendor_delta_request


def test_legistar_delta_request_uses_last_modified_date() -> None:
    plan = plan_vendor_delta_request(
        connector="Legistar",
        source_url="https://vendor.example.gov/api/meetings?department=clerk",
        changed_since=datetime(2026, 5, 1, 12, 30, 15, tzinfo=UTC),
    )

    assert plan.delta_enabled is True
    assert plan.cursor_param == "LastModifiedDate"
    assert plan.cursor_value == "2026-05-01T12:30:15Z"
    assert plan.request_url == (
        "https://vendor.example.gov/api/meetings?department=clerk&LastModifiedDate=2026-05-01T12%3A30%3A15Z"
    )
    assert "reset the cursor" in plan.fix


def test_delta_request_replaces_existing_cursor_without_dropping_other_filters() -> None:
    plan = plan_vendor_delta_request(
        connector="primegov",
        source_url="https://vendor.example.gov/api/meetings?updated_since=old&page_size=100",
        changed_since=datetime(2026, 5, 1, 8, 0, tzinfo=timezone(timedelta(hours=-4))),
    )

    assert plan.cursor_param == "updated_since"
    assert plan.cursor_value == "2026-05-01T12:00:00Z"
    assert plan.request_url == (
        "https://vendor.example.gov/api/meetings?page_size=100&updated_since=2026-05-01T12%3A00%3A00Z"
    )


def test_delta_request_falls_back_to_full_pull_without_cursor() -> None:
    plan = plan_vendor_delta_request(
        connector="granicus",
        source_url="https://vendor.example.gov/api/meetings",
        changed_since=None,
    )

    assert plan.delta_enabled is False
    assert plan.request_url == "https://vendor.example.gov/api/meetings"
    assert "successful run cursor" in plan.fix


def test_delta_request_handles_unknown_connector_as_full_pull() -> None:
    plan = plan_vendor_delta_request(
        connector="futurevendor",
        source_url="https://vendor.example.gov/api/meetings",
        changed_since=datetime(2026, 5, 1, tzinfo=UTC),
    )

    assert plan.delta_enabled is False
    assert plan.cursor_param is None
    assert plan.request_url == "https://vendor.example.gov/api/meetings"
