import pytest
from tools.fee_calculator import calculate_profitability


def test_profitable_product():
    result = calculate_profitability(
        wholesale_cost=8.50,
        amazon_price=24.99,
        referral_fee=3.75,
        fba_fee=5.37,
        prep_cost=1.50,
        shipping_to_prep=0.80,
    )
    assert result["profit_per_unit"] == pytest.approx(5.07, abs=0.01)
    assert result["roi_percent"] == pytest.approx(46.9, abs=0.5)
    assert result["is_profitable"] is True


def test_unprofitable_product():
    result = calculate_profitability(
        wholesale_cost=20.00,
        amazon_price=24.99,
        referral_fee=3.75,
        fba_fee=5.37,
        prep_cost=1.50,
        shipping_to_prep=0.80,
    )
    assert result["profit_per_unit"] < 0
    assert result["is_profitable"] is False


def test_monthly_profit_estimate():
    result = calculate_profitability(
        wholesale_cost=8.50,
        amazon_price=24.99,
        referral_fee=3.75,
        fba_fee=5.37,
        prep_cost=1.50,
        shipping_to_prep=0.80,
        estimated_monthly_sales=100,
    )
    assert result["monthly_profit"] == pytest.approx(507, abs=5)
