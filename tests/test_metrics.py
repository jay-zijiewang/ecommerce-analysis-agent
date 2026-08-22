import pytest

from src.metrics import calculate_metrics


def test_calculate_metrics() -> None:
    result = calculate_metrics(
        impressions=100_000,
        clicks=8_000,
        paid_orders=400,
        gmv=48_000,
        refund_amount=2_400,
    )

    assert result["gmv"] == 48_000
    assert result["net_gmv"] == 45_600
    assert result["ctr"] == pytest.approx(0.08)
    assert result["cvr"] == pytest.approx(0.05)
    assert result["aov"] == pytest.approx(120.0)
    assert result["refund_rate"] == pytest.approx(0.05)


def test_zero_denominators() -> None:
    result = calculate_metrics(
        impressions=0,
        clicks=0,
        paid_orders=0,
        gmv=0,
        refund_amount=0,
    )

    assert result["ctr"] == 0.0
    assert result["cvr"] == 0.0
    assert result["aov"] == 0.0
    assert result["refund_rate"] == 0.0


def test_negative_value_is_rejected() -> None:
    with pytest.raises(ValueError):
        calculate_metrics(
            impressions=-1,
            clicks=0,
            paid_orders=0,
            gmv=0,
            refund_amount=0,
        )