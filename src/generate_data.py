from pathlib import Path

import numpy as np
import pandas as pd


RANDOM_SEED = 42
START_DATE = "2026-06-20"
NUMBER_OF_DAYS = 60
CURRENT_PERIOD_START = pd.Timestamp("2026-08-12")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = PROJECT_ROOT / "data" / "ecommerce_metrics.csv"

CATEGORIES = ["Beauty", "Electronics", "Home", "Apparel", "Food"]
CHANNELS = ["Livestream", "Short Video", "Search"]
USER_SEGMENTS = ["New", "Returning", "High Value"]

BASE_IMPRESSIONS = {
    "Beauty": 18_000,
    "Electronics": 12_000,
    "Home": 10_000,
    "Apparel": 16_000,
    "Food": 20_000,
}

BASE_AOV = {
    "Beauty": 120.0,
    "Electronics": 480.0,
    "Home": 260.0,
    "Apparel": 150.0,
    "Food": 75.0,
}

BASE_REFUND_RATE = {
    "Beauty": 0.06,
    "Electronics": 0.04,
    "Home": 0.05,
    "Apparel": 0.08,
    "Food": 0.02,
}

CHANNEL_VOLUME_MULTIPLIER = {
    "Livestream": 1.25,
    "Short Video": 1.00,
    "Search": 0.70,
}

CHANNEL_CTR = {
    "Livestream": 0.10,
    "Short Video": 0.075,
    "Search": 0.12,
}

SEGMENT_VOLUME_MULTIPLIER = {
    "New": 1.25,
    "Returning": 0.90,
    "High Value": 0.35,
}

SEGMENT_CVR = {
    "New": 0.028,
    "Returning": 0.052,
    "High Value": 0.075,
}


def apply_current_period_anomalies(
    date: pd.Timestamp,
    category: str,
    channel: str,
    user_segment: str,
    impressions: int,
    ctr: float,
    cvr: float,
    aov: float,
    refund_rate: float,
) -> tuple[int, float, float, float, float]:
    """Apply predefined business anomalies to the current period."""

    if date < CURRENT_PERIOD_START:
        return impressions, ctr, cvr, aov, refund_rate

    if user_segment == "New":
        impressions = int(impressions * 1.40)

    if category == "Beauty" and channel == "Livestream":
        impressions = int(impressions * 0.65)
        ctr *= 0.72

    if category == "Electronics":
        aov *= 1.22

    if category == "Home":
        refund_rate *= 2.20

    if channel == "Short Video":
        cvr *= 0.72

    return impressions, ctr, cvr, aov, refund_rate


def generate_dataset() -> pd.DataFrame:
    """Generate a reproducible e-commerce dataset."""

    rng = np.random.default_rng(RANDOM_SEED)
    dates = pd.date_range(START_DATE, periods=NUMBER_OF_DAYS, freq="D")
    records = []

    for date in dates:
        for category in CATEGORIES:
            for channel in CHANNELS:
                for user_segment in USER_SEGMENTS:
                    impressions = int(
                        BASE_IMPRESSIONS[category]
                        * CHANNEL_VOLUME_MULTIPLIER[channel]
                        * SEGMENT_VOLUME_MULTIPLIER[user_segment]
                        * rng.normal(1.0, 0.08)
                    )

                    ctr = CHANNEL_CTR[channel] * rng.normal(1.0, 0.05)
                    cvr = SEGMENT_CVR[user_segment] * rng.normal(1.0, 0.06)
                    aov = BASE_AOV[category] * rng.normal(1.0, 0.04)
                    refund_rate = BASE_REFUND_RATE[category] * rng.normal(1.0, 0.08)

                    (
                        impressions,
                        ctr,
                        cvr,
                        aov,
                        refund_rate,
                    ) = apply_current_period_anomalies(
                        date=date,
                        category=category,
                        channel=channel,
                        user_segment=user_segment,
                        impressions=impressions,
                        ctr=ctr,
                        cvr=cvr,
                        aov=aov,
                        refund_rate=refund_rate,
                    )

                    ctr = float(np.clip(ctr, 0.001, 0.50))
                    cvr = float(np.clip(cvr, 0.001, 0.50))
                    refund_rate = float(np.clip(refund_rate, 0.0, 0.90))

                    clicks = int(round(impressions * ctr))
                    paid_orders = int(round(clicks * cvr))
                    buyers = int(round(paid_orders * rng.uniform(0.82, 0.95)))
                    gmv = round(paid_orders * aov, 2)
                    refund_amount = round(gmv * refund_rate, 2)

                    records.append(
                        {
                            "date": date.date().isoformat(),
                            "category": category,
                            "channel": channel,
                            "user_segment": user_segment,
                            "impressions": impressions,
                            "clicks": clicks,
                            "paid_orders": paid_orders,
                            "buyers": buyers,
                            "gmv": gmv,
                            "refund_amount": refund_amount,
                        }
                    )

    return pd.DataFrame(records)


def main() -> None:
    """Generate and save the dataset."""

    dataset = generate_dataset()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    dataset.to_csv(OUTPUT_PATH, index=False)

    print(f"Generated rows: {len(dataset)}")
    print(f"Start date: {dataset['date'].min()}")
    print(f"End date: {dataset['date'].max()}")
    print(f"Output path: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()