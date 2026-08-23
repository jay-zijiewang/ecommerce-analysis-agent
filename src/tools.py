from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.metrics import calculate_metrics


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "data" / "ecommerce_metrics.csv"
VALID_DIMENSIONS = {"category", "channel", "user_segment"}


def load_data() -> pd.DataFrame:
    """Load the e-commerce dataset."""

    if not DATA_PATH.exists():
        raise FileNotFoundError(
            "Dataset not found. Run python -m src.generate_data first."
        )

    return pd.read_csv(DATA_PATH, parse_dates=["date"])


def parse_date(date_value: str) -> pd.Timestamp:
    """Convert a date string into a pandas timestamp."""

    try:
        parsed_date = datetime.strptime(date_value, "%Y-%m-%d")
    except ValueError as error:
        raise ValueError("Dates must use YYYY-MM-DD format.") from error

    return pd.Timestamp(parsed_date)


def build_filters(
    category: str | None,
    channel: str | None,
    user_segment: str | None,
) -> dict[str, str]:
    """Build a dictionary containing active filters."""

    filters = {
        "category": category,
        "channel": channel,
        "user_segment": user_segment,
    }

    return {
        field_name: field_value
        for field_name, field_value in filters.items()
        if field_value is not None
    }


def filter_data(
    data: pd.DataFrame,
    start_date: str,
    end_date: str,
    filters: dict[str, str],
) -> pd.DataFrame:
    """Filter the dataset by date and optional business dimensions."""

    start = parse_date(start_date)
    end = parse_date(end_date)

    if start > end:
        raise ValueError("Start date cannot be later than end date.")

    filtered_data = data[
        (data["date"] >= start)
        & (data["date"] <= end)
    ]

    for field_name, field_value in filters.items():
        valid_values = set(data[field_name].dropna().unique())

        if field_value not in valid_values:
            raise ValueError(
                f"Unknown {field_name}: {field_value}. "
                f"Valid values: {sorted(valid_values)}"
            )

        filtered_data = filtered_data[
            filtered_data[field_name] == field_value
        ]

    return filtered_data


def aggregate_metrics(data: pd.DataFrame) -> dict[str, int | float]:
    """Aggregate raw values and calculate derived metrics."""

    impressions = int(data["impressions"].sum())
    clicks = int(data["clicks"].sum())
    paid_orders = int(data["paid_orders"].sum())
    buyers = int(data["buyers"].sum())
    gmv = float(data["gmv"].sum())
    refund_amount = float(data["refund_amount"].sum())

    derived_metrics = calculate_metrics(
        impressions=impressions,
        clicks=clicks,
        paid_orders=paid_orders,
        gmv=gmv,
        refund_amount=refund_amount,
    )

    return {
        "impressions": impressions,
        "clicks": clicks,
        "paid_orders": paid_orders,
        "buyers": buyers,
        "gmv": round(derived_metrics["gmv"], 2),
        "refund_amount": round(refund_amount, 2),
        "net_gmv": round(derived_metrics["net_gmv"], 2),
        "ctr": round(derived_metrics["ctr"], 6),
        "cvr": round(derived_metrics["cvr"], 6),
        "aov": round(derived_metrics["aov"], 2),
        "refund_rate": round(derived_metrics["refund_rate"], 6),
    }


def calculate_change(
    current_value: int | float,
    previous_value: int | float,
) -> dict[str, float | None]:
    """Calculate absolute and relative changes."""

    absolute_change = float(current_value - previous_value)

    if previous_value == 0:
        relative_change = 0.0 if current_value == 0 else None
    else:
        relative_change = float(absolute_change / previous_value)

    return {
        "absolute_change": round(absolute_change, 6),
        "relative_change": (
            None
            if relative_change is None
            else round(relative_change, 6)
        ),
    }


def get_overview_metrics(
    start_date: str,
    end_date: str,
    category: str | None = None,
    channel: str | None = None,
    user_segment: str | None = None,
) -> dict[str, Any]:
    """Return aggregated metrics for a selected business scope."""

    data = load_data()
    filters = build_filters(category, channel, user_segment)
    filtered_data = filter_data(data, start_date, end_date, filters)

    if filtered_data.empty:
        return {
            "status": "no_data",
            "message": "No data matched the requested scope.",
            "date_range": {
                "start_date": start_date,
                "end_date": end_date,
            },
            "filters": filters,
        }

    return {
        "status": "success",
        "date_range": {
            "start_date": start_date,
            "end_date": end_date,
        },
        "filters": filters,
        "row_count": len(filtered_data),
        "metrics": aggregate_metrics(filtered_data),
    }


def compare_periods(
    current_start_date: str,
    current_end_date: str,
    previous_start_date: str,
    previous_end_date: str,
    category: str | None = None,
    channel: str | None = None,
    user_segment: str | None = None,
) -> dict[str, Any]:
    """Compare metrics between current and previous periods."""

    current_result = get_overview_metrics(
        start_date=current_start_date,
        end_date=current_end_date,
        category=category,
        channel=channel,
        user_segment=user_segment,
    )

    previous_result = get_overview_metrics(
        start_date=previous_start_date,
        end_date=previous_end_date,
        category=category,
        channel=channel,
        user_segment=user_segment,
    )

    if (
        current_result["status"] != "success"
        or previous_result["status"] != "success"
    ):
        return {
            "status": "no_data",
            "message": "Both periods must contain matching data.",
            "current_period": current_result,
            "previous_period": previous_result,
        }

    current_metrics = current_result["metrics"]
    previous_metrics = previous_result["metrics"]
    changes = {}

    for metric_name, current_value in current_metrics.items():
        previous_value = previous_metrics[metric_name]

        changes[metric_name] = {
            "current": current_value,
            "previous": previous_value,
            **calculate_change(current_value, previous_value),
        }

    return {
        "status": "success",
        "filters": current_result["filters"],
        "current_period": current_result["date_range"],
        "previous_period": previous_result["date_range"],
        "changes": changes,
    }


def breakdown_by_dimension(
    start_date: str,
    end_date: str,
    dimension: str,
    category: str | None = None,
    channel: str | None = None,
    user_segment: str | None = None,
) -> dict[str, Any]:
    """Break down business metrics by one selected dimension."""

    if dimension not in VALID_DIMENSIONS:
        raise ValueError(
            f"Invalid dimension: {dimension}. "
            f"Valid dimensions: {sorted(VALID_DIMENSIONS)}"
        )

    data = load_data()
    filters = build_filters(category, channel, user_segment)
    filtered_data = filter_data(data, start_date, end_date, filters)

    if filtered_data.empty:
        return {
            "status": "no_data",
            "message": "No data matched the requested scope.",
            "dimension": dimension,
            "filters": filters,
        }

    breakdown = []

    for dimension_value, group_data in filtered_data.groupby(
        dimension,
        sort=True,
    ):
        breakdown.append(
            {
                "value": str(dimension_value),
                "row_count": len(group_data),
                "metrics": aggregate_metrics(group_data),
            }
        )

    return {
        "status": "success",
        "date_range": {
            "start_date": start_date,
            "end_date": end_date,
        },
        "filters": filters,
        "dimension": dimension,
        "breakdown": breakdown,
    }


def get_funnel_metrics(
    start_date: str,
    end_date: str,
    category: str | None = None,
    channel: str | None = None,
    user_segment: str | None = None,
) -> dict[str, Any]:
    """Return traffic and conversion funnel metrics."""

    overview = get_overview_metrics(
        start_date=start_date,
        end_date=end_date,
        category=category,
        channel=channel,
        user_segment=user_segment,
    )

    if overview["status"] != "success":
        return overview

    metrics = overview["metrics"]

    return {
        "status": "success",
        "date_range": overview["date_range"],
        "filters": overview["filters"],
        "funnel": {
            "impressions": metrics["impressions"],
            "clicks": metrics["clicks"],
            "paid_orders": metrics["paid_orders"],
            "buyers": metrics["buyers"],
        },
        "rates": {
            "ctr": metrics["ctr"],
            "cvr": metrics["cvr"],
        },
    }

def compare_dimension_periods(
    current_start_date: str,
    current_end_date: str,
    previous_start_date: str,
    previous_end_date: str,
    dimension: str,
    category: str | None = None,
    channel: str | None = None,
    user_segment: str | None = None,
) -> dict[str, Any]:
    """Compare all values of one dimension between two periods."""

    if dimension not in VALID_DIMENSIONS:
        raise ValueError(
            f"Invalid dimension: {dimension}. "
            f"Valid dimensions: {sorted(VALID_DIMENSIONS)}"
        )

    current_result = breakdown_by_dimension(
        start_date=current_start_date,
        end_date=current_end_date,
        dimension=dimension,
        category=category,
        channel=channel,
        user_segment=user_segment,
    )

    previous_result = breakdown_by_dimension(
        start_date=previous_start_date,
        end_date=previous_end_date,
        dimension=dimension,
        category=category,
        channel=channel,
        user_segment=user_segment,
    )

    if (
        current_result["status"] != "success"
        or previous_result["status"] != "success"
    ):
        return {
            "status": "no_data",
            "message": "Both periods must contain matching data.",
            "current_period": current_result,
            "previous_period": previous_result,
        }

    current_by_value = {
        item["value"]: item["metrics"]
        for item in current_result["breakdown"]
    }

    previous_by_value = {
        item["value"]: item["metrics"]
        for item in previous_result["breakdown"]
    }

    dimension_values = sorted(
        set(current_by_value) | set(previous_by_value)
    )
    comparisons = []

    for dimension_value in dimension_values:
        current_metrics = current_by_value.get(
            dimension_value,
            {},
        )
        previous_metrics = previous_by_value.get(
            dimension_value,
            {},
        )

        metric_names = sorted(
            set(current_metrics) | set(previous_metrics)
        )
        metric_changes = {}

        for metric_name in metric_names:
            current_value = current_metrics.get(
                metric_name,
                0,
            )
            previous_value = previous_metrics.get(
                metric_name,
                0,
            )

            metric_changes[metric_name] = {
                "current": current_value,
                "previous": previous_value,
                **calculate_change(
                    current_value,
                    previous_value,
                ),
            }

        comparisons.append(
            {
                "value": dimension_value,
                "changes": metric_changes,
            }
        )

    return {
        "status": "success",
        "dimension": dimension,
        "filters": current_result["filters"],
        "current_period": current_result["date_range"],
        "previous_period": previous_result["date_range"],
        "comparisons": comparisons,
    }