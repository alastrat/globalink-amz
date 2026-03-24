#!/usr/bin/env python3
"""
ASIN Hunter - Wholesale FBA Product Research Tool
Connects to Amazon SP-API for competitive analysis and profitability scoring

Credentials are read from environment variables (matching sp-api-query.py):
  SP_API_REFRESH_TOKEN, SP_API_LWA_APP_ID, SP_API_LWA_CLIENT_SECRET,
  AMAZON_SELLER_ID, AMAZON_MARKETPLACE_ID
Falls back to config.json sp_api/seller_id fields if env vars are not set.
"""

import json
import os
import sys
import csv
import time
import hashlib
import argparse
import math
import requests
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote


def load_env():
    """Load .env file from same directory as this script."""
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip("'\"")
                if key and value and key not in os.environ:
                    os.environ[key] = value


load_env()


class AmazonSPAPI:
    """Amazon Selling Partner API client"""

    BASE_URL = "https://sellingpartnerapi-na.amazon.com"
    TOKEN_URL = "https://api.amazon.com/auth/o2/token"

    def __init__(self, refresh_token=None, lwa_app_id=None, lwa_client_secret=None, region="US"):
        self.refresh_token = refresh_token or os.environ.get("SP_API_REFRESH_TOKEN", "")
        self.lwa_app_id = lwa_app_id or os.environ.get("SP_API_LWA_APP_ID", "")
        self.lwa_client_secret = lwa_client_secret or os.environ.get("SP_API_LWA_CLIENT_SECRET", "")
        self.region = region
        self.access_token = None
        self.token_expiry = None

    def _get_access_token(self):
        """Get LWA OAuth token from refresh_token"""
        if self.access_token and self.token_expiry and datetime.now() < self.token_expiry:
            return self.access_token

        payload = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "client_id": self.lwa_app_id,
            "client_secret": self.lwa_client_secret
        }

        try:
            response = requests.post(self.TOKEN_URL, data=payload, timeout=10)
            response.raise_for_status()
            data = response.json()
            self.access_token = data["access_token"]
            expires_in = data.get("expires_in", 3600)
            self.token_expiry = datetime.now() + timedelta(seconds=expires_in - 60)
            return self.access_token
        except Exception as e:
            print(f"Error getting access token: {e}")
            return None

    def _headers(self):
        """Returns x-amz-access-token header"""
        token = self._get_access_token()
        if not token:
            return None
        return {"x-amz-access-token": token}

    def search_catalog(self, keywords, max_results=20):
        """Search catalog/2022-04-01/items"""
        headers = self._headers()
        if not headers:
            return []

        params = {
            "keywords": keywords,
            "marketplaceIds": "ATVPDKIKX0DER",
            "pageSize": min(max_results, 20)
        }

        try:
            response = requests.get(
                f"{self.BASE_URL}/catalog/2022-04-01/items",
                headers=headers,
                params=params,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            return data.get("items", [])
        except Exception as e:
            print(f"Error searching catalog: {e}")
            return []

    def get_competitive_pricing(self, asin_list):
        """Get batch pricing for ASINs in groups of 20"""
        if not asin_list:
            return []

        headers = self._headers()
        if not headers:
            return []

        results = []
        for i in range(0, len(asin_list), 20):
            batch = asin_list[i:i+20]
            params = {
                "MarketplaceId": "ATVPDKIKX0DER",
                "Asins": batch
            }

            try:
                response = requests.get(
                    f"{self.BASE_URL}/products/pricing/v0/competitivePrice",
                    headers=headers,
                    params=params,
                    timeout=10
                )
                response.raise_for_status()
                data = response.json()
                results.extend(data.get("payload", []))
                time.sleep(0.5)
            except Exception as e:
                print(f"Error getting competitive pricing: {e}")

        return results

    def get_item_offers(self, asin):
        """Get single ASIN offers"""
        headers = self._headers()
        if not headers:
            return None

        params = {
            "MarketplaceId": "ATVPDKIKX0DER",
            "Sku": asin,
            "ItemCondition": "New"
        }

        try:
            response = requests.get(
                f"{self.BASE_URL}/products/pricing/v0/offers",
                headers=headers,
                params=params,
                timeout=10
            )
            response.raise_for_status()
            return response.json().get("payload", {})
        except Exception as e:
            print(f"Error getting item offers for {asin}: {e}")
            return None

    def check_restrictions(self, asin, seller_id):
        """Check listing restrictions - returns {restricted: bool, reasons: list, approval: str}"""
        headers = self._headers()
        if not headers:
            return {"restricted": True, "reasons": ["Auth failed"], "approval": "error"}

        params = {
            "asin": asin,
            "sellerId": seller_id,
            "marketplaceIds": "ATVPDKIKX0DER",
            "conditionType": "new_new"
        }

        try:
            response = requests.get(
                f"{self.BASE_URL}/listings/2021-08-01/restrictions",
                headers=headers,
                params=params,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()

            restrictions = data.get("restrictions", [])
            if restrictions:
                reasons = []
                for r in restrictions:
                    for link in r.get("reasons", []):
                        reasons.append(link.get("message", "Unknown restriction"))
                return {
                    "restricted": True,
                    "reasons": reasons if reasons else ["Restricted"],
                    "approval": "restricted"
                }
            return {"restricted": False, "reasons": [], "approval": "approved"}
        except requests.exceptions.HTTPError as e:
            # Some 4xx errors contain restriction info in the body
            try:
                body = e.response.json()
                errors = body.get("errors", [])
                if errors:
                    return {"restricted": True, "reasons": [err.get("message", str(e)) for err in errors], "approval": "error"}
            except Exception:
                pass
            return {"restricted": True, "reasons": [str(e)], "approval": "error"}
        except Exception as e:
            return {"restricted": True, "reasons": [str(e)], "approval": "error"}

    def check_restrictions_batch(self, asins, seller_id):
        """Batch check restrictions with rate limiting (0.2s between requests)"""
        results = {}
        for asin in asins:
            results[asin] = self.check_restrictions(asin, seller_id)
            time.sleep(0.2)
        return results

    def get_item_offers_batch(self, asins):
        """Batch get offers, extracts fba_seller_count, buy_box_price, total_sellers"""
        results = []
        for asin in asins:
            offers = self.get_item_offers(asin)
            if offers:
                fba_sellers = len([o for o in offers.get("Offers", [])
                                 if o.get("FulfillmentChannel") == "AMAZON"])
                buy_box = None
                for offer in offers.get("Offers", []):
                    if offer.get("IsBuyBoxWinner"):
                        buy_box = offer.get("Price", {}).get("ListingPrice", {}).get("Amount")
                        break

                results.append({
                    "asin": asin,
                    "fba_seller_count": fba_sellers,
                    "buy_box_price": float(buy_box) if buy_box else None,
                    "total_sellers": len(offers.get("Offers", []))
                })
            time.sleep(0.5)

        return results

    def get_catalog_item(self, asin):
        """Get single catalog item with summaries, salesRanks, dimensions, attributes"""
        headers = self._headers()
        if not headers:
            return None

        params = {
            "marketplaceIds": "ATVPDKIKX0DER",
            "includedData": "summaries,salesRanks,dimensions,attributes"
        }

        try:
            response = requests.get(
                f"{self.BASE_URL}/catalog/2022-04-01/items/{asin}",
                headers=headers,
                params=params,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error getting catalog item {asin}: {e}")
            return None

    def get_catalog_items_batch(self, asins):
        """Batch get catalog items"""
        results = []
        for asin in asins:
            item = self.get_catalog_item(asin)
            if item:
                results.append(item)
            time.sleep(0.5)
        return results


class ProductAnalyzer:
    """Product profitability and scoring analysis"""

    REFERRAL_FEES = {
        "Electronics": 0.08,
        "Appliances": 0.08,
        "Home & Kitchen": 0.15,
        "Sports & Outdoors": 0.15,
        "Clothing": 0.17,
        "Shoes": 0.17,
        "Jewelry": 0.14,
        "Default": 0.15
    }

    FBA_FEES = {
        "Small Standard": {"base": 3.22, "per_lb": 0.00},
        "Large Standard": {"base": 3.86, "per_lb": 0.00},
        "Small Oversize": {"base": 5.81, "per_lb": 0.00},
        "Medium Oversize": {"base": 9.78, "per_lb": 0.00},
        "Large Oversize": {"base": 12.87, "per_lb": 0.00},
        "Special Oversize": {"base": 0.00, "per_lb": 0.87}
    }

    def __init__(self, config=None):
        self.config = config or {}

    def estimate_size_tier(self, weight_lb):
        """Estimate FBA size tier from weight"""
        if weight_lb < 1:
            return "Small Standard"
        elif weight_lb < 2:
            return "Large Standard"
        elif weight_lb < 20:
            return "Small Oversize"
        elif weight_lb < 70:
            return "Medium Oversize"
        else:
            return "Large Oversize"

    def estimate_fba_fee(self, weight_lb, size_tier=None):
        """Estimate FBA fee for product"""
        if not size_tier:
            size_tier = self.estimate_size_tier(weight_lb)

        fee_info = self.FBA_FEES.get(size_tier, self.FBA_FEES["Large Standard"])
        base = fee_info["base"]
        per_lb = fee_info.get("per_lb", 0) * weight_lb
        return base + per_lb

    def estimate_referral_fee(self, price, category="Default"):
        """Estimate referral fee percentage"""
        rate = self.REFERRAL_FEES.get(category, self.REFERRAL_FEES["Default"])
        return price * rate

    def calculate_profitability(self, product):
        """Calculate all fees, profit, ROI, margin"""
        price = product.get("price", 0)
        cost = product.get("cost", 0)
        weight_lb = product.get("weight_lb", 1)
        category = product.get("category", "Default")

        prep_cost = self.config.get("prep_cost_per_unit", 0.50)
        inbound_cost = self.config.get("inbound_cost_per_unit", 0.25)

        referral_fee = self.estimate_referral_fee(price, category)
        fba_fee = self.estimate_fba_fee(weight_lb)

        total_cost = cost + referral_fee + fba_fee + prep_cost + inbound_cost
        profit = price - total_cost
        roi = (profit / cost * 100) if cost > 0 else 0
        margin = (profit / price * 100) if price > 0 else 0

        product.update({
            "referral_fee": referral_fee,
            "fba_fee": fba_fee,
            "prep_cost": prep_cost,
            "inbound_cost": inbound_cost,
            "total_cost": total_cost,
            "profit": profit,
            "roi": roi,
            "margin": margin
        })

        return product

    def score_product(self, product):
        """Score product 0-100: ROI (0-30), BSR (0-20), Competition (0-15),
        Price stability (0-15), Sales velocity (0-10), Size/weight (0-10)"""

        score = 0

        # ROI scoring (0-30 points)
        roi = product.get("roi", 0)
        roi_score = min(30, max(0, roi / 5))
        score += roi_score

        # BSR scoring (0-20 points) - lower is better
        bsr = product.get("bsr", 1000000)
        if bsr < 1000:
            bsr_score = 20
        elif bsr < 10000:
            bsr_score = 15
        elif bsr < 50000:
            bsr_score = 10
        elif bsr < 100000:
            bsr_score = 5
        else:
            bsr_score = 0
        score += bsr_score

        # Competition scoring (0-15 points) - fewer sellers is better
        fba_sellers = product.get("fba_seller_count", 10)
        if fba_sellers <= 3:
            comp_score = 15
        elif fba_sellers <= 5:
            comp_score = 12
        elif fba_sellers <= 10:
            comp_score = 8
        elif fba_sellers <= 20:
            comp_score = 4
        else:
            comp_score = 0
        score += comp_score

        # Price stability (0-15 points)
        price_stability = product.get("price_stability", 0.8)
        stability_score = min(15, max(0, price_stability * 18))
        score += stability_score

        # Sales velocity (0-10 points) - monthly sales
        monthly_sales = product.get("monthly_sales", 0)
        if monthly_sales > 1000:
            sales_score = 10
        elif monthly_sales > 500:
            sales_score = 8
        elif monthly_sales > 100:
            sales_score = 5
        elif monthly_sales > 20:
            sales_score = 2
        else:
            sales_score = 0
        score += sales_score

        # Size/weight (0-10 points) - lighter and smaller is better
        weight = product.get("weight_lb", 5)
        if weight < 1:
            weight_score = 10
        elif weight < 3:
            weight_score = 8
        elif weight < 10:
            weight_score = 5
        elif weight < 20:
            weight_score = 2
        else:
            weight_score = 0
        score += weight_score

        # Determine grade
        if score >= 80:
            grade = "A"
        elif score >= 65:
            grade = "B"
        elif score >= 50:
            grade = "C"
        elif score >= 35:
            grade = "D"
        else:
            grade = "F"

        product["score"] = round(score, 1)
        product["grade"] = grade

        return product

    def passes_filters(self, product, filters=None):
        """Check if product passes all config filters"""
        if not filters:
            filters = self.config.get("filters", {})

        if product.get("roi", 0) < filters.get("min_roi", 0):
            return False
        if product.get("bsr", 1000000) > filters.get("max_bsr", 1000000):
            return False
        if product.get("price", 0) < filters.get("min_price", 0):
            return False
        if product.get("price", 0) > filters.get("max_price", 999999):
            return False
        if product.get("fba_seller_count", 0) < filters.get("min_fba_sellers", 0):
            return False

        return True

    def analyze_batch(self, products):
        """Run profitability + scoring on all products, sort by score desc"""
        for product in products:
            self.calculate_profitability(product)
            self.score_product(product)

        return sorted(products, key=lambda p: p.get("score", 0), reverse=True)


def import_seller_assistant_csv(filepath):
    """Import Seller Assistant CSV export"""
    products = []

    column_mapping = {
        "ASIN": "asin",
        "Title": "title",
        "Price": "price",
        "Your Price": "price",
        "Buy Box Price": "price",
        "Category": "category",
        "Sales Rank": "bsr",
        "Sales Rank (Category)": "bsr",
        "Estimated Monthly Sales": "monthly_sales",
        "Estimated Sales": "monthly_sales",
        "Your Offer Count": "fba_seller_count",
        "FBA Offer Count": "fba_seller_count",
        "Total Offer Count": "total_sellers",
        "All Offers (including your)": "total_sellers",
        "Weight": "weight_lb",
        "Weight (lbs)": "weight_lb",
        "Product Cost": "cost",
        "Cost": "cost"
    }

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                product = {}
                for csv_col, product_field in column_mapping.items():
                    if csv_col in row and row[csv_col]:
                        value = row[csv_col].strip()

                        if product_field in ["price", "cost", "weight_lb"]:
                            try:
                                product[product_field] = float(value.replace("$", "").replace(",", ""))
                            except:
                                pass
                        elif product_field in ["bsr", "monthly_sales", "fba_seller_count", "total_sellers"]:
                            try:
                                product[product_field] = int(value.replace(",", ""))
                            except:
                                pass
                        else:
                            product[product_field] = value

                if "asin" in product:
                    products.append(product)
    except Exception as e:
        print(f"Error importing CSV: {e}")

    return products


def generate_demo_data():
    """Generate 40 realistic demo products"""
    brands = ["TechPro", "HomeSelect", "SportMax", "EliteGear", "Premium+",
              "ProTools", "SmartLiving", "PerformanceX", "QualityFirst", "NextGen"]
    categories = ["Electronics", "Home & Kitchen", "Sports & Outdoors",
                 "Tools", "Appliances", "Automotive"]

    products = []
    for i in range(40):
        asin = f"B0{hashlib.md5(str(i).encode()).hexdigest()[:8].upper()}"
        price = round(15 + (i % 30) * 3.5 + 12 * (i // 10), 2)
        cost = round(price * (0.35 + (i % 5) * 0.05), 2)
        bsr = 5000 + i * 1200 + (i % 7) * 15000
        monthly_sales = max(5, 200 - i * 3 + (i % 5) * 50)
        weight = 0.5 + (i % 12) * 0.8
        fba_sellers = 2 + (i % 8)

        product = {
            "asin": asin,
            "title": f"{brands[i % len(brands)]} {categories[i % len(categories)]} #{i+1}",
            "brand": brands[i % len(brands)],
            "category": categories[i % len(categories)],
            "price": price,
            "cost": cost,
            "bsr": bsr,
            "monthly_sales": monthly_sales,
            "weight_lb": round(weight, 2),
            "fba_seller_count": fba_sellers,
            "total_sellers": fba_sellers + 2 + (i % 3),
            "price_stability": round(0.85 + (i % 5) * 0.03, 2)
        }
        products.append(product)

    return products


def load_asin_list(filepath):
    """Load ASIN list from file - handles URLs, comma-separated, comments, deduplicates"""
    asins = set()

    try:
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()

                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    continue

                # Extract ASIN from URL
                if 'amazon.com' in line or 'dp/' in line:
                    if '/dp/' in line:
                        asin = line.split('/dp/')[1].split('/')[0].split('?')[0]
                        asins.add(asin)
                    elif '/gp/product/' in line:
                        asin = line.split('/gp/product/')[1].split('/')[0].split('?')[0]
                        asins.add(asin)
                else:
                    # Handle comma-separated values
                    for item in line.split(','):
                        item = item.strip()
                        if item and len(item) == 10 and item[0] == 'B':
                            asins.add(item)
    except Exception as e:
        print(f"Error loading ASIN list: {e}")

    return list(asins)


def generate_csv_template(asins, output_path):
    """Generate CSV template for ASIN list with helper row"""
    try:
        with open(output_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                "asin", "title", "brand", "category", "price", "cost",
                "bsr", "monthly_sales", "weight_lb", "fba_seller_count", "total_sellers"
            ])
            writer.writeheader()

            # Helper row with examples
            writer.writerow({
                "asin": "B000EXAMPLE",
                "title": "Product Name Here",
                "brand": "Brand Name",
                "category": "Home & Kitchen",
                "price": "29.99",
                "cost": "8.50",
                "bsr": "15000",
                "monthly_sales": "150",
                "weight_lb": "2.5",
                "fba_seller_count": "5",
                "total_sellers": "8"
            })

            # Add ASIN rows
            for asin in asins:
                writer.writerow({"asin": asin})
    except Exception as e:
        print(f"Error generating CSV template: {e}")


def fetch_asins_via_api(asins, sp_config):
    """Fetch catalog + pricing for ASIN list via API"""
    api = AmazonSPAPI(
        sp_config.get("refresh_token"),
        sp_config.get("lwa_app_id"),
        sp_config.get("lwa_client_secret")
    )

    products = []

    # Get catalog items
    for asin in asins:
        catalog = api.get_catalog_item(asin)
        if catalog:
            item = catalog.get("item", {})
            summaries = item.get("summaries", [{}])[0]

            product = {
                "asin": asin,
                "title": summaries.get("title", ""),
                "category": item.get("attributes", {}).get("product_type", "Unknown"),
                "bsr": 50000,
                "weight_lb": 2.0
            }
            products.append(product)

    # Get offers and pricing
    offers_batch = api.get_item_offers_batch(asins)
    for offer in offers_batch:
        for product in products:
            if product["asin"] == offer["asin"]:
                product.update(offer)

    return products


def generate_dashboard(products, all_products, config, output_path):
    """Generate self-contained HTML dashboard with charts and filters"""

    # Calculate KPIs
    found_count = len(products)
    avg_roi = sum(p.get("roi", 0) for p in products) / len(products) if products else 0
    avg_score = sum(p.get("score", 0) for p in products) / len(products) if products else 0
    avg_profit = sum(p.get("profit", 0) for p in products) / len(products) if products else 0
    avg_price = sum(p.get("price", 0) for p in products) / len(products) if products else 0

    # Budget simulator - pick top products fitting $1000 budget
    budget = 1000
    selected = []
    total_cost = 0
    for p in products:
        cost = p.get("cost", 0)
        if total_cost + cost <= budget:
            selected.append(p)
            total_cost += cost

    budget_projected_revenue = sum(p.get("price", 0) for p in selected)
    budget_projected_profit = sum(p.get("profit", 0) for p in selected)
    budget_projected_roi = (budget_projected_profit / total_cost * 100) if total_cost > 0 else 0

    # Prepare chart data
    roi_price_data = [[p.get("roi", 0), p.get("price", 0), p.get("asin", "")] for p in products[:100]]

    category_counts = {}
    for p in products:
        cat = p.get("category", "Other")
        category_counts[cat] = category_counts.get(cat, 0) + 1

    score_distribution = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
    for p in products:
        grade = p.get("grade", "F")
        score_distribution[grade] += 1

    profit_sales_data = [[p.get("profit", 0), p.get("monthly_sales", 0)] for p in products[:100]]

    # Generate HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ASIN Hunter Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #0f1117;
            color: #c9d1d9;
            line-height: 1.6;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }}

        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 1px solid #30363d;
        }}

        h1 {{
            font-size: 28px;
            color: #f0f6fc;
        }}

        .export-btn {{
            background: #6366f1;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            transition: background 0.2s;
        }}

        .export-btn:hover {{
            background: #4f46e5;
        }}

        .filters {{
            background: #1a1d29;
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 30px;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
        }}

        .filter-group {{
            display: flex;
            flex-direction: column;
        }}

        .filter-group label {{
            font-size: 12px;
            text-transform: uppercase;
            color: #8b949e;
            margin-bottom: 5px;
            font-weight: 600;
        }}

        .filter-group input,
        .filter-group select {{
            background: #0f1117;
            border: 1px solid #30363d;
            color: #c9d1d9;
            padding: 8px;
            border-radius: 4px;
            font-size: 14px;
        }}

        .filter-group input:focus,
        .filter-group select:focus {{
            outline: none;
            border-color: #6366f1;
            box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
        }}

        .filter-buttons {{
            display: flex;
            gap: 10px;
            grid-column: 1 / -1;
        }}

        .filter-btn {{
            background: #6366f1;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
        }}

        .filter-btn:hover {{
            background: #4f46e5;
        }}

        .filter-btn.reset {{
            background: #30363d;
        }}

        .filter-btn.reset:hover {{
            background: #484f58;
        }}

        .kpi-cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }}

        .kpi-card {{
            background: #1a1d29;
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
        }}

        .kpi-label {{
            font-size: 12px;
            text-transform: uppercase;
            color: #8b949e;
            margin-bottom: 10px;
            font-weight: 600;
        }}

        .kpi-value {{
            font-size: 28px;
            font-weight: 700;
            color: #58a6ff;
        }}

        .charts-container {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}

        .chart-wrapper {{
            background: #1a1d29;
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 20px;
            position: relative;
            height: 400px;
        }}

        .chart-title {{
            position: absolute;
            top: 20px;
            left: 20px;
            font-size: 16px;
            font-weight: 600;
            color: #f0f6fc;
            z-index: 10;
        }}

        canvas {{
            max-height: 350px;
        }}

        .budget-simulator {{
            background: #1a1d29;
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 30px;
        }}

        .budget-title {{
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 15px;
            color: #f0f6fc;
        }}

        .budget-stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }}

        .budget-stat {{
            background: #0f1117;
            padding: 15px;
            border-radius: 4px;
            border-left: 3px solid #6366f1;
        }}

        .budget-stat-label {{
            font-size: 12px;
            color: #8b949e;
            text-transform: uppercase;
            font-weight: 600;
        }}

        .budget-stat-value {{
            font-size: 20px;
            font-weight: 700;
            color: #58a6ff;
            margin-top: 5px;
        }}

        .table-wrapper {{
            overflow-x: auto;
            margin-bottom: 30px;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            background: #1a1d29;
            border: 1px solid #30363d;
            border-radius: 8px;
            overflow: hidden;
        }}

        thead {{
            background: #0f1117;
            border-bottom: 2px solid #30363d;
        }}

        th {{
            padding: 15px;
            text-align: left;
            font-size: 12px;
            text-transform: uppercase;
            color: #8b949e;
            font-weight: 600;
            cursor: pointer;
            user-select: none;
        }}

        th:hover {{
            background: #161b22;
        }}

        td {{
            padding: 12px 15px;
            border-bottom: 1px solid #30363d;
            font-size: 14px;
        }}

        tbody tr:hover {{
            background: #0d1117;
        }}

        .grade-badge {{
            display: inline-block;
            width: 32px;
            height: 32px;
            border-radius: 50%;
            text-align: center;
            line-height: 32px;
            font-weight: 700;
            font-size: 14px;
        }}

        .grade-a {{
            background: #238636;
            color: white;
        }}

        .grade-b {{
            background: #388bfd;
            color: white;
        }}

        .grade-c {{
            background: #d29922;
            color: white;
        }}

        .grade-d {{
            background: #da3633;
            color: white;
        }}

        .grade-f {{
            background: #6e40aa;
            color: white;
        }}

        .score-bar {{
            height: 8px;
            background: #30363d;
            border-radius: 4px;
            overflow: hidden;
            margin: 5px 0;
        }}

        .score-fill {{
            height: 100%;
            background: linear-gradient(90deg, #da3633 0%, #d29922 50%, #238636 100%);
            transition: width 0.3s ease;
        }}

        .positive {{
            color: #3fb950;
        }}

        .negative {{
            color: #da3633;
        }}

        .warning {{
            color: #d29922;
        }}

        .asin-link {{
            color: #58a6ff;
            text-decoration: none;
            font-family: 'Courier New', monospace;
        }}

        .asin-link:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>ASIN Hunter Dashboard</h1>
            <button class="export-btn" onclick="exportToCSV()">Export CSV</button>
        </div>

        <div class="filters">
            <div class="filter-group">
                <label>Category</label>
                <select id="filterCategory" onchange="applyFilters()">
                    <option value="">All Categories</option>
                </select>
            </div>
            <div class="filter-group">
                <label>Grade</label>
                <select id="filterGrade" onchange="applyFilters()">
                    <option value="">All Grades</option>
                    <option value="A">A</option>
                    <option value="B">B</option>
                    <option value="C">C</option>
                    <option value="D">D</option>
                    <option value="F">F</option>
                </select>
            </div>
            <div class="filter-group">
                <label>Min ROI (%)</label>
                <input type="number" id="filterMinROI" placeholder="0" onchange="applyFilters()">
            </div>
            <div class="filter-group">
                <label>Max BSR</label>
                <input type="number" id="filterMaxBSR" placeholder="1000000" onchange="applyFilters()">
            </div>
            <div class="filter-group">
                <label>Price Range</label>
                <input type="text" id="filterPrice" placeholder="0-100" onchange="applyFilters()">
            </div>
            <div class="filter-group">
                <label>Size Tier</label>
                <select id="filterSizeTier" onchange="applyFilters()">
                    <option value="">All Sizes</option>
                    <option value="small">Small (< 1 lb)</option>
                    <option value="medium">Medium (1-10 lb)</option>
                    <option value="large">Large (10+ lb)</option>
                </select>
            </div>
            <div class="filter-group">
                <label>Min Stability</label>
                <input type="number" id="filterMinStability" placeholder="0" min="0" max="1" step="0.1" onchange="applyFilters()">
            </div>
            <div class="filter-group">
                <label>Search Title</label>
                <input type="text" id="filterSearch" placeholder="Search..." onchange="applyFilters()">
            </div>
            <div class="filter-buttons">
                <button class="filter-btn" onclick="applyFilters()">Filter</button>
                <button class="filter-btn reset" onclick="resetFilters()">Reset</button>
            </div>
        </div>

        <div class="kpi-cards">
            <div class="kpi-card">
                <div class="kpi-label">Products Found</div>
                <div class="kpi-value" id="kpiCount">{found_count}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Average ROI</div>
                <div class="kpi-value positive" id="kpiROI">{avg_roi:.1f}%</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Average Score</div>
                <div class="kpi-value" id="kpiScore">{avg_score:.1f}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Avg Profit/Unit</div>
                <div class="kpi-value positive" id="kpiProfit">${avg_profit:.2f}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Average Price</div>
                <div class="kpi-value" id="kpiPrice">${avg_price:.2f}</div>
            </div>
        </div>

        <div class="budget-simulator">
            <div class="budget-title">Budget Simulator ($1000)</div>
            <div style="font-size: 14px; color: #8b949e; margin-bottom: 10px;">
                Auto-selected {len(selected)} products fitting ${total_cost:.2f} budget
            </div>
            <div class="budget-stats">
                <div class="budget-stat">
                    <div class="budget-stat-label">Items Selected</div>
                    <div class="budget-stat-value">{len(selected)}</div>
                </div>
                <div class="budget-stat">
                    <div class="budget-stat-label">Total Cost</div>
                    <div class="budget-stat-value">${total_cost:.2f}</div>
                </div>
                <div class="budget-stat">
                    <div class="budget-stat-label">Projected Revenue</div>
                    <div class="budget-stat-value positive">${budget_projected_revenue:.2f}</div>
                </div>
                <div class="budget-stat">
                    <div class="budget-stat-label">Projected Profit</div>
                    <div class="budget-stat-value positive">${budget_projected_profit:.2f}</div>
                </div>
                <div class="budget-stat">
                    <div class="budget-stat-label">Projected ROI</div>
                    <div class="budget-stat-value positive">{budget_projected_roi:.1f}%</div>
                </div>
            </div>
        </div>

        <div class="charts-container">
            <div class="chart-wrapper">
                <div class="chart-title">ROI vs Price</div>
                <canvas id="roiChart"></canvas>
            </div>
            <div class="chart-wrapper">
                <div class="chart-title">Products by Category</div>
                <canvas id="categoryChart"></canvas>
            </div>
            <div class="chart-wrapper">
                <div class="chart-title">Score Distribution</div>
                <canvas id="scoreChart"></canvas>
            </div>
            <div class="chart-wrapper">
                <div class="chart-title">Profit vs Monthly Sales</div>
                <canvas id="profitChart"></canvas>
            </div>
        </div>

        <div class="table-wrapper">
            <table id="productsTable">
                <thead>
                    <tr>
                        <th onclick="sortTable('grade')">Grade</th>
                        <th onclick="sortTable('score')">Score</th>
                        <th onclick="sortTable('asin')">ASIN</th>
                        <th onclick="sortTable('title')">Title</th>
                        <th onclick="sortTable('category')">Category</th>
                        <th onclick="sortTable('price')">Price</th>
                        <th onclick="sortTable('cost')">Cost</th>
                        <th onclick="sortTable('profit')">Profit</th>
                        <th onclick="sortTable('roi')">ROI %</th>
                        <th onclick="sortTable('bsr')">BSR</th>
                        <th onclick="sortTable('monthly_sales')">Monthly Sales</th>
                        <th onclick="sortTable('fba_seller_count')">FBA Sellers</th>
                        <th onclick="sortTable('price_stability')">Stability</th>
                        <th onclick="sortTable('total_cost')">Total Fees</th>
                    </tr>
                </thead>
                <tbody id="tableBody">
                </tbody>
            </table>
        </div>
    </div>

    <script>
        const allProducts = {json.dumps(products)};
        let filteredProducts = [...allProducts];
        let currentSort = {{'column': 'score', 'direction': 'desc'}};
        let charts = {{}};

        function renderProducts(prods) {{
            const tbody = document.getElementById('tableBody');
            tbody.innerHTML = '';

            prods.forEach(p => {{
                const gradeClass = `grade-${{p.grade.toLowerCase()}}`;
                const scorePercent = Math.min(100, (p.score / 100) * 100);
                const profitClass = p.profit >= 0 ? 'positive' : 'negative';
                const roiClass = p.roi >= 0 ? 'positive' : 'negative';

                const row = document.createElement('tr');
                row.innerHTML = `
                    <td><span class="grade-badge ${{gradeClass}}">${{p.grade}}</span></td>
                    <td>
                        <div class="score-bar">
                            <div class="score-fill" style="width: ${{scorePercent}}%"></div>
                        </div>
                        ${{p.score.toFixed(1)}}
                    </td>
                    <td><a href="https://amazon.com/dp/${{p.asin}}" target="_blank" class="asin-link">${{p.asin}}</a></td>
                    <td>${{p.title}}</td>
                    <td>${{p.category}}</td>
                    <td>${{p.price.toFixed(2)}}</td>
                    <td>${{p.cost.toFixed(2)}}</td>
                    <td class="${{profitClass}}">${{p.profit.toFixed(2)}}</td>
                    <td class="${{roiClass}}">${{(p.roi||0).toFixed(1)}}%</td>
                    <td>${{p.bsr.toLocaleString()}}</td>
                    <td>${{(p.monthly_sales||0).toLocaleString()}}</td>
                    <td>${{p.fba_seller_count||0}}</td>
                    <td>${{(p.price_stability||0).toFixed(0)}}%</td>
                    <td>${{p.total_cost.toFixed(2)}}</td>
                `;
                tbody.appendChild(row);
            }});

            updateKPIs(prods);
            renderCharts(prods);
        }}

        function updateKPIs(prods) {{
            if (prods.length === 0) {{
                document.getElementById('kpiCount').textContent = '0';
                document.getElementById('kpiROI').textContent = '0%';
                document.getElementById('kpiScore').textContent = '0';
                document.getElementById('kpiProfit').textContent = '$0.00';
                document.getElementById('kpiPrice').textContent = '$0.00';
                return;
            }}

            const avgROI = prods.reduce((s, p) => s + (p.roi || 0), 0) / prods.length;
            const avgScore = prods.reduce((s, p) => s + (p.score || 0), 0) / prods.length;
            const avgProfit = prods.reduce((s, p) => s + (p.profit || 0), 0) / prods.length;
            const avgPrice = prods.reduce((s, p) => s + (p.price || 0), 0) / prods.length;

            document.getElementById('kpiCount').textContent = prods.length;
            document.getElementById('kpiROI').textContent = avgROI.toFixed(1) + '%';
            document.getElementById('kpiScore').textContent = avgScore.toFixed(1);
            document.getElementById('kpiProfit').textContent = '$' + avgProfit.toFixed(2);
            document.getElementById('kpiPrice').textContent = '$' + avgPrice.toFixed(2);
        }}

        function renderCharts(prods) {{
            // ROI vs Price
            if (charts.roiChart) charts.roiChart.destroy();
            const roiCtx = document.getElementById('roiChart').getContext('2d');
            const roiData = prods.slice(0, 50).map(p => ({{x: p.price, y: p.roi || 0, label: p.asin}}));
            charts.roiChart = new Chart(roiCtx, {{
                type: 'scatter',
                data: {{
                    datasets: [{{
                        label: 'ROI % vs Price',
                        data: roiData,
                        backgroundColor: 'rgba(99, 102, 241, 0.5)',
                        borderColor: '#6366f1',
                        borderWidth: 1,
                        pointRadius: 4
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {{
                        x: {{
                            type: 'linear',
                            title: {{display: true, text: 'Price ($)', color: '#8b949e'}},
                            grid: {{color: '#30363d'}},
                            ticks: {{color: '#8b949e'}}
                        }},
                        y: {{
                            title: {{display: true, text: 'ROI (%)', color: '#8b949e'}},
                            grid: {{color: '#30363d'}},
                            ticks: {{color: '#8b949e'}}
                        }}
                    }},
                    plugins: {{legend: {{display: false}}}}
                }}
            }});

            // Category Distribution
            if (charts.categoryChart) charts.categoryChart.destroy();
            const catCtx = document.getElementById('categoryChart').getContext('2d');
            const categories = {{}};
            prods.forEach(p => {{
                categories[p.category] = (categories[p.category] || 0) + 1;
            }});
            charts.categoryChart = new Chart(catCtx, {{
                type: 'bar',
                data: {{
                    labels: Object.keys(categories),
                    datasets: [{{
                        label: 'Count',
                        data: Object.values(categories),
                        backgroundColor: '#6366f1',
                        borderColor: '#4f46e5',
                        borderWidth: 1
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {{
                        y: {{
                            beginAtZero: true,
                            grid: {{color: '#30363d'}},
                            ticks: {{color: '#8b949e'}}
                        }},
                        x: {{
                            grid: {{display: false}},
                            ticks: {{color: '#8b949e'}}
                        }}
                    }},
                    plugins: {{legend: {{display: false}}}}
                }}
            }});

            // Score Distribution
            if (charts.scoreChart) charts.scoreChart.destroy();
            const scoreCtx = document.getElementById('scoreChart').getContext('2d');
            const grades = {{A: 0, B: 0, C: 0, D: 0, F: 0}};
            prods.forEach(p => {{
                grades[p.grade]++;
            }});
            charts.scoreChart = new Chart(scoreCtx, {{
                type: 'doughnut',
                data: {{
                    labels: Object.keys(grades),
                    datasets: [{{
                        data: Object.values(grades),
                        backgroundColor: ['#238636', '#388bfd', '#d29922', '#da3633', '#6e40aa']
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{legend: {{position: 'bottom', labels: {{color: '#8b949e'}}}}}}
                }}
            }});

            // Profit vs Sales
            if (charts.profitChart) charts.profitChart.destroy();
            const profitCtx = document.getElementById('profitChart').getContext('2d');
            const profitData = prods.slice(0, 50).map(p => ({{x: p.monthly_sales || 0, y: p.profit || 0}}));
            charts.profitChart = new Chart(profitCtx, {{
                type: 'scatter',
                data: {{
                    datasets: [{{
                        label: 'Profit vs Monthly Sales',
                        data: profitData,
                        backgroundColor: 'rgba(88, 166, 255, 0.5)',
                        borderColor: '#58a6ff',
                        borderWidth: 1,
                        pointRadius: 4
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {{
                        x: {{
                            type: 'linear',
                            title: {{display: true, text: 'Monthly Sales', color: '#8b949e'}},
                            grid: {{color: '#30363d'}},
                            ticks: {{color: '#8b949e'}}
                        }},
                        y: {{
                            title: {{display: true, text: 'Profit per Unit ($)', color: '#8b949e'}},
                            grid: {{color: '#30363d'}},
                            ticks: {{color: '#8b949e'}}
                        }}
                    }},
                    plugins: {{legend: {{display: false}}}}
                }}
            }});
        }}

        function applyFilters() {{
            const category = document.getElementById('filterCategory').value;
            const grade = document.getElementById('filterGrade').value;
            const minROI = parseFloat(document.getElementById('filterMinROI').value) || 0;
            const maxBSR = parseFloat(document.getElementById('filterMaxBSR').value) || 1000000;
            const priceStr = document.getElementById('filterPrice').value;
            const sizeTier = document.getElementById('filterSizeTier').value;
            const minStability = parseFloat(document.getElementById('filterMinStability').value) || 0;
            const search = document.getElementById('filterSearch').value.toLowerCase();

            let [minPrice, maxPrice] = [0, 999999];
            if (priceStr) {{
                const parts = priceStr.split('-');
                minPrice = parseFloat(parts[0]) || 0;
                maxPrice = parseFloat(parts[1]) || 999999;
            }}

            filteredProducts = allProducts.filter(p => {{
                if (category && p.category !== category) return false;
                if (grade && p.grade !== grade) return false;
                if (p.roi < minROI) return false;
                if (p.bsr > maxBSR) return false;
                if (p.price < minPrice || p.price > maxPrice) return false;
                if (p.price_stability < minStability) return false;
                if (search && !p.title.toLowerCase().includes(search)) return false;

                if (sizeTier) {{
                    const weight = p.weight_lb || 0;
                    if (sizeTier === 'small' && weight >= 1) return false;
                    if (sizeTier === 'medium' && (weight < 1 || weight >= 10)) return false;
                    if (sizeTier === 'large' && weight < 10) return false;
                }}

                return true;
            }});

            sortProducts();
            renderProducts(filteredProducts);
        }}

        function resetFilters() {{
            document.getElementById('filterCategory').value = '';
            document.getElementById('filterGrade').value = '';
            document.getElementById('filterMinROI').value = '';
            document.getElementById('filterMaxBSR').value = '';
            document.getElementById('filterPrice').value = '';
            document.getElementById('filterSizeTier').value = '';
            document.getElementById('filterMinStability').value = '';
            document.getElementById('filterSearch').value = '';
            filteredProducts = [...allProducts];
            sortProducts();
            renderProducts(filteredProducts);
        }}

        function sortTable(column) {{
            if (currentSort.column === column) {{
                currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
            }} else {{
                currentSort.column = column;
                currentSort.direction = 'asc';
            }}
            sortProducts();
            renderProducts(filteredProducts);
        }}

        function sortProducts() {{
            filteredProducts.sort((a, b) => {{
                let aVal = a[currentSort.column];
                let bVal = b[currentSort.column];

                if (typeof aVal === 'string') {{
                    aVal = aVal.toLowerCase();
                    bVal = bVal.toLowerCase();
                }}

                if (aVal < bVal) return currentSort.direction === 'asc' ? -1 : 1;
                if (aVal > bVal) return currentSort.direction === 'asc' ? 1 : -1;
                return 0;
            }});
        }}

        function exportToCSV() {{
            let csv = 'Grade,Score,ASIN,Title,Category,Price,Cost,Profit,ROI%,BSR,Monthly Sales,FBA Sellers,Stability,Total Fees\\n';

            filteredProducts.forEach(p => {{
                csv += `${{p.grade}},${{p.score.toFixed(1)}},${{p.asin}},"${{p.title}}",${{p.category}},${{p.price.toFixed(2)}},${{p.cost.toFixed(2)}},${{p.profit.toFixed(2)}},${{(p.roi || 0).toFixed(1)}},${{p.bsr}},${{p.monthly_sales || 0}},${{p.fba_seller_count || 0}},${{(p.price_stability || 0).toFixed(2)}},${{p.total_cost.toFixed(2)}}\\n`;
            }});

            const blob = new Blob([csv], {{type: 'text/csv'}});
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'asin-hunter-' + new Date().toISOString().split('T')[0] + '.csv';
            a.click();
            window.URL.revokeObjectURL(url);
        }}

        function populateCategories() {{
            const categories = [...new Set(allProducts.map(p => p.category))].sort();
            const select = document.getElementById('filterCategory');
            categories.forEach(cat => {{
                const option = document.createElement('option');
                option.value = cat;
                option.textContent = cat;
                select.appendChild(option);
            }});
        }}

        // Initialize
        document.addEventListener('DOMContentLoaded', () => {{
            populateCategories();
            sortProducts();
            renderProducts(filteredProducts);
        }});
    </script>
</body>
</html>"""

    try:
        with open(output_path, 'w') as f:
            f.write(html)
        print(f"Dashboard generated: {output_path}")
    except Exception as e:
        print(f"Error generating dashboard: {e}")


def main():
    parser = argparse.ArgumentParser(description="ASIN Hunter - Wholesale FBA Research Tool")
    parser.add_argument("--demo", action="store_true", help="Demo mode with sample data")
    parser.add_argument("--csv", type=str, help="Import Seller Assistant CSV")
    parser.add_argument("--asins", type=str, help="ASIN list file")
    parser.add_argument("--auto", type=str, help="Auto pipeline: ASIN list → restrictions → offers → catalog → score → dashboard")
    parser.add_argument("--check", nargs="*", help="Check selling restrictions. Pass ASINs directly and/or use --file for a list file")
    parser.add_argument("--file", type=str, help="ASIN list file for --check mode")
    parser.add_argument("--config", type=str, default=None, help="Config file path (default: asin-hunter-config.json in script dir)")
    parser.add_argument("--output", type=str, default="dashboard.html", help="Output dashboard path")
    parser.add_argument("--json", action="store_true", help="Output results as JSON to stdout (for Inngest integration)")

    args = parser.parse_args()

    # Load config — default to config.json in script directory
    config_path = args.config or str(Path(__file__).parent / "asin-hunter-config.json")
    config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
        except Exception as e:
            print(f"Warning: Could not load config: {e}", file=sys.stderr)

    analyzer = ProductAnalyzer(config)

    # Restriction check mode
    if args.check is not None:
        seller_id = os.environ.get("AMAZON_SELLER_ID") or config.get("seller_id")
        if not seller_id:
            msg = "Error: AMAZON_SELLER_ID env var or seller_id in config required"
            if args.json:
                print(json.dumps({"error": msg}))
            else:
                print(msg)
            sys.exit(1)

        asins = set()

        # From command-line args
        for item in (args.check or []):
            item = item.strip()
            if 'amazon.com' in item or '/dp/' in item:
                if '/dp/' in item:
                    asins.add(item.split('/dp/')[1].split('/')[0].split('?')[0])
                elif '/gp/product/' in item:
                    asins.add(item.split('/gp/product/')[1].split('/')[0].split('?')[0])
            elif len(item) == 10 and item[0] == 'B':
                asins.add(item)

        # From file
        if args.file:
            asins.update(load_asin_list(args.file))

        if not asins:
            msg = "Error: No ASINs provided. Pass ASINs directly or use --file <path>"
            if args.json:
                print(json.dumps({"error": msg}))
            else:
                print(msg)
            sys.exit(1)

        asins = list(asins)
        if not args.json:
            print(f"Checking restrictions for {len(asins)} ASIN(s)...\n")

        # API client reads creds from env vars by default
        api = AmazonSPAPI()

        results = api.check_restrictions_batch(asins, seller_id)

        approved = []
        restricted = []
        for asin, r in results.items():
            if r.get("restricted"):
                restricted.append((asin, r))
            else:
                approved.append((asin, r))

        if args.json:
            print(json.dumps({
                "approved": [a for a, _ in approved],
                "restricted": {a: r for a, r in restricted},
                "summary": {
                    "total": len(asins),
                    "approved_count": len(approved),
                    "restricted_count": len(restricted)
                }
            }))
            return

        if approved:
            print(f"APPROVED ({len(approved)}):")
            for asin, _ in approved:
                print(f"  {asin}")

        if restricted:
            print(f"\nRESTRICTED ({len(restricted)}):")
            for asin, r in restricted:
                reasons = "; ".join(r.get("reasons", []))
                print(f"  {asin} — {reasons}")

        print(f"\nSummary: {len(approved)} approved, {len(restricted)} restricted out of {len(asins)} checked")
        return

    # Demo mode
    if args.demo:
        print("Generating demo data...")
        products = generate_demo_data()
        products = analyzer.analyze_batch(products)
        generate_dashboard(products, products, config, args.output)
        print(f"Dashboard saved to {args.output}")
        return

    # CSV import mode
    if args.csv:
        print(f"Importing CSV: {args.csv}")
        products = import_seller_assistant_csv(args.csv)
        products = analyzer.analyze_batch(products)
        generate_dashboard(products, products, config, args.output)
        print(f"Dashboard saved to {args.output}")
        return

    # ASIN list mode
    if args.asins:
        print(f"Loading ASIN list: {args.asins}")
        asins = load_asin_list(args.asins)
        print(f"Loaded {len(asins)} ASINs")

        # Generate template CSV
        template_path = os.path.splitext(args.asins)[0] + "_template.csv"
        generate_csv_template(asins, template_path)
        print(f"Template generated: {template_path}")

        # Try to fetch via API if configured
        if config.get("refresh_token"):
            print("Fetching data via API...")
            products = fetch_asins_via_api(asins, config)
            products = analyzer.analyze_batch(products)
            generate_dashboard(products, products, config, args.output)
            print(f"Dashboard saved to {args.output}")
        else:
            print("No API credentials configured. Fill in template manually.")
        return

    # Auto pipeline mode
    if args.auto:
        print("\n" + "="*60)
        print("ASIN HUNTER - AUTO RESEARCH PIPELINE")
        print("="*60)

        seller_id = os.environ.get("AMAZON_SELLER_ID") or config.get("seller_id")
        if not seller_id:
            print("Error: AMAZON_SELLER_ID env var or seller_id in config required")
            return

        # Step 1: Load ASINs
        print("\n[1/5] Loading ASIN list...")
        asins = load_asin_list(args.auto)
        print(f"  Loaded {len(asins)} ASINs")

        # Initialize API (reads creds from env vars)
        api = AmazonSPAPI()

        # Step 2: Check restrictions
        print("\n[2/5] Checking restrictions...")
        restrictions = api.check_restrictions_batch(asins, seller_id)
        restricted_count = sum(1 for r in restrictions.values() if r.get("restricted"))
        approved_asins = [asin for asin, r in restrictions.items() if not r.get("restricted")]
        print(f"  {restricted_count} restricted, {len(approved_asins)} approved")

        # Step 3: Get offers and seller count
        print("\n[3/5] Fetching offers and pricing...")
        offers_batch = api.get_item_offers_batch(approved_asins)
        products = []
        for offer in offers_batch:
            if offer.get("fba_seller_count", 0) >= 3 and offer.get("buy_box_price", 0) >= 20:
                products.append({
                    "asin": offer["asin"],
                    "price": offer.get("buy_box_price", 0),
                    "fba_seller_count": offer.get("fba_seller_count", 0),
                    "total_sellers": offer.get("total_sellers", 0),
                    "bsr": 50000,
                    "weight_lb": 2.0,
                    "category": "Unknown",
                    "cost": offer.get("buy_box_price", 0) * 0.4,
                    "title": offer["asin"],
                    "monthly_sales": 100
                })
        print(f"  {len(products)} products meet criteria (3+ FBA sellers, price >= $20)")

        # Step 4: Get catalog details
        print("\n[4/5] Fetching catalog details...")
        catalog_items = api.get_catalog_items_batch([p["asin"] for p in products])
        for item in catalog_items:
            asin = item.get("asin")
            for product in products:
                if product["asin"] == asin:
                    summaries = item.get("item", {}).get("summaries", [{}])[0]
                    product["title"] = summaries.get("title", product["asin"])
                    product["category"] = item.get("item", {}).get("attributes", {}).get("product_type", "Unknown")
        print(f"  Updated {len([p for p in products if p.get('title') != 'ASIN'])} product details")

        # Step 5: Score and generate dashboard
        print("\n[5/5] Scoring products and generating dashboard...")
        products = analyzer.analyze_batch(products)
        generate_dashboard(products, products, config, args.output)

        # Save restriction report
        restriction_report_path = "restriction_report.csv"
        with open(restriction_report_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["ASIN", "Restricted", "Approval Status", "Reasons"])
            for asin, r in restrictions.items():
                writer.writerow([
                    asin,
                    r.get("restricted", False),
                    r.get("approval", "unknown"),
                    "; ".join(r.get("reasons", []))
                ])

        print(f"\n" + "="*60)
        print(f"✓ Dashboard saved: {args.output}")
        print(f"✓ Restriction report: {restriction_report_path}")
        print(f"✓ Products analyzed: {len(products)}")
        print("="*60 + "\n")
        return

    # Default: keyword search mode
    print("ASIN Hunter - SP-API Keyword Search Mode")
    print("\nUsage:")
    print("  python asin_hunter.py --demo")
    print("  python asin_hunter.py --csv <file.csv>")
    print("  python asin_hunter.py --asins <asins.txt>")
    print("  python asin_hunter.py --auto <asins.txt>")
    print("\nDefault mode requires API credentials in config.json")


if __name__ == "__main__":
    main()
