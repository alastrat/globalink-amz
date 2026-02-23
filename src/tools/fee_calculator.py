"""Offline FBA profitability calculator."""


def calculate_profitability(
    wholesale_cost: float,
    amazon_price: float,
    referral_fee: float,
    fba_fee: float,
    prep_cost: float = 1.50,
    shipping_to_prep: float = 0.80,
    estimated_monthly_sales: int | None = None,
    min_roi_percent: float = 30.0,
    min_profit: float = 3.0,
) -> dict:
    """Calculate full profitability for a product."""
    total_cost = wholesale_cost + prep_cost + shipping_to_prep
    total_fees = referral_fee + fba_fee
    profit_per_unit = amazon_price - total_cost - total_fees

    roi_percent = (profit_per_unit / total_cost * 100) if total_cost > 0 else 0

    monthly_profit = None
    if estimated_monthly_sales is not None:
        monthly_profit = profit_per_unit * estimated_monthly_sales

    is_profitable = profit_per_unit >= min_profit and roi_percent >= min_roi_percent

    return {
        "wholesale_cost": wholesale_cost,
        "amazon_price": amazon_price,
        "total_cost_per_unit": total_cost,
        "total_fees": total_fees,
        "referral_fee": referral_fee,
        "fba_fee": fba_fee,
        "prep_cost": prep_cost,
        "shipping_cost": shipping_to_prep,
        "profit_per_unit": round(profit_per_unit, 2),
        "roi_percent": round(roi_percent, 1),
        "is_profitable": is_profitable,
        "monthly_profit": round(monthly_profit, 2) if monthly_profit is not None else None,
        "estimated_monthly_sales": estimated_monthly_sales,
    }
