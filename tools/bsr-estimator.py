#!/usr/bin/env python3
"""BSR to estimated monthly sales using category-specific power law.

Formula: sales = A * BSR^(-B)

Usage:
    python3 bsr-estimator.py <bsr> <category>

Returns JSON: { bsr, category, estimated_monthly_sales, demand_indicator }
"""

import json
import math
import sys

# Category coefficients: (A, B)
# Based on industry estimates for Amazon US marketplace
CATEGORY_COEFFICIENTS = {
    "baby": (45000, 0.80),
    "baby products": (45000, 0.80),
    "beauty": (60000, 0.82),
    "beauty & personal care": (60000, 0.82),
    "electronics": (50000, 0.85),
    "grocery": (55000, 0.78),
    "grocery & gourmet food": (55000, 0.78),
    "health": (65000, 0.80),
    "health & household": (65000, 0.80),
    "health, household & baby care": (65000, 0.80),
    "home": (50000, 0.80),
    "home & kitchen": (50000, 0.80),
    "kitchen": (50000, 0.80),
    "kitchen & dining": (50000, 0.80),
    "office": (35000, 0.78),
    "office products": (35000, 0.78),
    "pet": (40000, 0.78),
    "pet supplies": (40000, 0.78),
    "sports": (45000, 0.82),
    "sports & outdoors": (45000, 0.82),
    "toys": (55000, 0.85),
    "toys & games": (55000, 0.85),
    "tools": (35000, 0.80),
    "tools & home improvement": (35000, 0.80),
    "clothing": (70000, 0.85),
    "clothing, shoes & jewelry": (70000, 0.85),
    "automotive": (30000, 0.78),
    "automotive parts & accessories": (30000, 0.78),
    "garden": (40000, 0.80),
    "patio, lawn & garden": (40000, 0.80),
    "industrial": (25000, 0.75),
    "industrial & scientific": (25000, 0.75),
    "arts": (30000, 0.78),
    "arts, crafts & sewing": (30000, 0.78),
}

# Default for unknown categories
DEFAULT_COEFFICIENTS = (45000, 0.80)


def estimate_monthly_sales(bsr, category):
    """Estimate monthly sales from BSR and category."""
    cat_lower = category.lower().strip()
    a, b = CATEGORY_COEFFICIENTS.get(cat_lower, DEFAULT_COEFFICIENTS)

    if bsr <= 0:
        return 0

    sales = a * math.pow(bsr, -b)
    return max(1, round(sales))


def get_demand_indicator(monthly_sales):
    """Classify demand level."""
    if monthly_sales >= 300:
        return "HIGH"
    elif monthly_sales >= 100:
        return "MEDIUM"
    elif monthly_sales >= 30:
        return "LOW"
    else:
        return "VERY LOW"


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 bsr-estimator.py <bsr> <category>")
        sys.exit(1)

    try:
        bsr = int(sys.argv[1])
    except ValueError:
        print(json.dumps({"error": f"Invalid BSR: {sys.argv[1]}"}))
        sys.exit(1)

    category = " ".join(sys.argv[2:])
    monthly_sales = estimate_monthly_sales(bsr, category)
    demand = get_demand_indicator(monthly_sales)

    result = {
        "bsr": bsr,
        "category": category,
        "estimated_monthly_sales": monthly_sales,
        "demand_indicator": demand,
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
