import pandas as pd

from src.generate_data import generate_dataset


DATASET = generate_dataset()
DATASET["date"] = pd.to_datetime(DATASET["date"])

PREVIOUS_PERIOD = DATASET[
    (DATASET["date"] >= "2026-08-05")
    & (DATASET["date"] <= "2026-08-11")
]

CURRENT_PERIOD = DATASET[
    (DATASET["date"] >= "2026-08-12")
    & (DATASET["date"] <= "2026-08-18")
]

REQUIRED_COLUMNS = {
    "date",
    "category",
    "channel",
    "user_segment",
    "impressions",
    "clicks",
    "paid_orders",
    "buyers",
    "gmv",
    "refund_amount",
}

NUMERIC_COLUMNS = [
    "impressions",
    "clicks",
    "paid_orders",
    "buyers",
    "gmv",
    "refund_amount",
]


def calculate_ratio(data: pd.DataFrame, numerator: str, denominator: str) -> float:
    """Calculate an aggregated ratio from two columns."""
    denominator_sum = data[denominator].sum()

    if denominator_sum == 0:
        return 0.0

    return float(data[numerator].sum() / denominator_sum)


def test_dataset_shape() -> None:
    assert len(DATASET) == 2700
    assert DATASET["date"].nunique() == 60
    assert DATASET["category"].nunique() == 5
    assert DATASET["channel"].nunique() == 3
    assert DATASET["user_segment"].nunique() == 3


def test_required_columns_exist() -> None:
    assert REQUIRED_COLUMNS == set(DATASET.columns)


def test_numeric_values_are_not_negative() -> None:
    assert (DATASET[NUMERIC_COLUMNS] >= 0).all().all()


def test_beauty_livestream_decline() -> None:
    previous = PREVIOUS_PERIOD[
        (PREVIOUS_PERIOD["category"] == "Beauty")
        & (PREVIOUS_PERIOD["channel"] == "Livestream")
    ]

    current = CURRENT_PERIOD[
        (CURRENT_PERIOD["category"] == "Beauty")
        & (CURRENT_PERIOD["channel"] == "Livestream")
    ]

    previous_ctr = calculate_ratio(previous, "clicks", "impressions")
    current_ctr = calculate_ratio(current, "clicks", "impressions")

    assert current["gmv"].sum() < previous["gmv"].sum()
    assert current["impressions"].sum() < previous["impressions"].sum()
    assert current_ctr < previous_ctr


def test_electronics_aov_growth() -> None:
    previous = PREVIOUS_PERIOD[
        PREVIOUS_PERIOD["category"] == "Electronics"
    ]

    current = CURRENT_PERIOD[
        CURRENT_PERIOD["category"] == "Electronics"
    ]

    previous_aov = calculate_ratio(previous, "gmv", "paid_orders")
    current_aov = calculate_ratio(current, "gmv", "paid_orders")

    assert current_aov > previous_aov * 1.15


def test_home_refund_rate_growth() -> None:
    previous = PREVIOUS_PERIOD[
        PREVIOUS_PERIOD["category"] == "Home"
    ]

    current = CURRENT_PERIOD[
        CURRENT_PERIOD["category"] == "Home"
    ]

    previous_rate = calculate_ratio(previous, "refund_amount", "gmv")
    current_rate = calculate_ratio(current, "refund_amount", "gmv")

    assert current_rate > previous_rate * 1.80


def test_short_video_cvr_decline() -> None:
    previous = PREVIOUS_PERIOD[
        PREVIOUS_PERIOD["channel"] == "Short Video"
    ]

    current = CURRENT_PERIOD[
        CURRENT_PERIOD["channel"] == "Short Video"
    ]

    previous_cvr = calculate_ratio(previous, "paid_orders", "clicks")
    current_cvr = calculate_ratio(current, "paid_orders", "clicks")

    assert current_cvr < previous_cvr * 0.80


def test_new_user_traffic_share_growth() -> None:
    previous_new_impressions = PREVIOUS_PERIOD[
        PREVIOUS_PERIOD["user_segment"] == "New"
    ]["impressions"].sum()

    current_new_impressions = CURRENT_PERIOD[
        CURRENT_PERIOD["user_segment"] == "New"
    ]["impressions"].sum()

    previous_share = (
        previous_new_impressions / PREVIOUS_PERIOD["impressions"].sum()
    )
    current_share = (
        current_new_impressions / CURRENT_PERIOD["impressions"].sum()
    )

    assert current_share > previous_share