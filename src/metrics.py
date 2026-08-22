def safe_divide(numerator: float, denominator: float) -> float:
    """Safely divide two numbers and avoid division by zero."""
    if denominator == 0:
        return 0.0

    return numerator / denominator


def calculate_metrics(
    impressions: int,
    clicks: int,
    paid_orders: int,
    gmv: float,
    refund_amount: float,
) -> dict[str, float]:
    """Calculate e-commerce metrics from aggregated raw values."""

    raw_values = {
        "impressions": impressions,
        "clicks": clicks,
        "paid_orders": paid_orders,
        "gmv": gmv,
        "refund_amount": refund_amount,
    }

    for field_name, value in raw_values.items():
        if value < 0:
            raise ValueError(f"{field_name} cannot be negative.")

    return {
        "gmv": float(gmv),
        "net_gmv": float(gmv - refund_amount),
        "ctr": safe_divide(clicks, impressions),
        "cvr": safe_divide(paid_orders, clicks),
        "aov": safe_divide(gmv, paid_orders),
        "refund_rate": safe_divide(refund_amount, gmv),
    }