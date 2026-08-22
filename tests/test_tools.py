import pytest

from src.tools import (
    breakdown_by_dimension,
    compare_periods,
    get_funnel_metrics,
    get_overview_metrics,
)


CURRENT_START = "2026-08-12"
CURRENT_END = "2026-08-18"
PREVIOUS_START = "2026-08-05"
PREVIOUS_END = "2026-08-11"


def test_overview_metrics() -> None:
    result = get_overview_metrics(
        start_date=CURRENT_START,
        end_date=CURRENT_END,
    )

    assert result["status"] == "success"
    assert result["row_count"] == 315
    assert result["metrics"]["impressions"] > 0
    assert result["metrics"]["gmv"] > 0


def test_beauty_period_comparison() -> None:
    result = compare_periods(
        current_start_date=CURRENT_START,
        current_end_date=CURRENT_END,
        previous_start_date=PREVIOUS_START,
        previous_end_date=PREVIOUS_END,
        category="Beauty",
    )

    assert result["status"] == "success"
    assert result["changes"]["gmv"]["relative_change"] < 0
    assert result["changes"]["ctr"]["relative_change"] < 0


def test_channel_breakdown() -> None:
    result = breakdown_by_dimension(
        start_date=CURRENT_START,
        end_date=CURRENT_END,
        dimension="channel",
        category="Beauty",
    )

    channel_values = {
        item["value"]
        for item in result["breakdown"]
    }

    assert result["status"] == "success"
    assert channel_values == {
        "Livestream",
        "Search",
        "Short Video",
    }


def test_funnel_metrics() -> None:
    result = get_funnel_metrics(
        start_date=CURRENT_START,
        end_date=CURRENT_END,
    )

    funnel = result["funnel"]

    assert result["status"] == "success"
    assert funnel["impressions"] >= funnel["clicks"]
    assert funnel["clicks"] >= funnel["paid_orders"]
    assert funnel["paid_orders"] >= funnel["buyers"]


def test_invalid_category_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown category"):
        get_overview_metrics(
            start_date=CURRENT_START,
            end_date=CURRENT_END,
            category="Books",
        )


def test_empty_date_range_returns_no_data() -> None:
    result = get_overview_metrics(
        start_date="2030-01-01",
        end_date="2030-01-07",
    )

    assert result["status"] == "no_data"