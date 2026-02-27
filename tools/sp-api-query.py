#!/usr/bin/env python3
"""Amazon SP-API Query Tool

Lightweight wrapper for Amazon Selling Partner API calls.
Handles authentication (LWA token exchange) and common queries.
All new subcommands use file-based caching via cache.py.

Usage:
    python3 sp-api-query.py inventory [--asin ASIN]
    python3 sp-api-query.py orders [--days N]
    python3 sp-api-query.py pricing --asin ASIN
    python3 sp-api-query.py fees --asin ASIN
    python3 sp-api-query.py catalog --asin ASIN
    python3 sp-api-query.py health
    python3 sp-api-query.py catalog-full <ASIN>
    python3 sp-api-query.py fees-estimate <ASIN> <price>
    python3 sp-api-query.py competitive-summary <ASIN>
    python3 sp-api-query.py restrictions <ASIN>
"""

import json
import os
import sys
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Import cache module (same directory)
sys.path.insert(0, str(Path(__file__).parent))
try:
    import cache as _cache
except ImportError:
    _cache = None


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

LWA_APP_ID = os.environ.get("SP_API_LWA_APP_ID", "")
LWA_CLIENT_SECRET = os.environ.get("SP_API_LWA_CLIENT_SECRET", "")
REFRESH_TOKEN = os.environ.get("SP_API_REFRESH_TOKEN", "")
SELLER_ID = os.environ.get("AMAZON_SELLER_ID", "")
MARKETPLACE_ID = os.environ.get("AMAZON_MARKETPLACE_ID", "ATVPDKIKX0DER")

SP_API_BASE = "https://sellingpartnerapi-na.amazon.com"
LWA_TOKEN_URL = "https://api.amazon.com/auth/o2/token"


def get_access_token():
    """Exchange refresh token for access token via LWA."""
    if not all([LWA_APP_ID, LWA_CLIENT_SECRET, REFRESH_TOKEN]):
        print(json.dumps({"error": "SP-API credentials not configured. Set SP_API_LWA_APP_ID, SP_API_LWA_CLIENT_SECRET, and SP_API_REFRESH_TOKEN in tools/.env"}))
        sys.exit(1)

    data = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": REFRESH_TOKEN,
        "client_id": LWA_APP_ID,
        "client_secret": LWA_CLIENT_SECRET,
    }).encode()

    req = urllib.request.Request(LWA_TOKEN_URL, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            return result["access_token"]
    except Exception as e:
        print(json.dumps({"error": f"Failed to get access token: {str(e)}"}))
        sys.exit(1)


def sp_api_request(path, params=None, method="GET", body=None):
    """Make an authenticated SP-API request."""
    token = get_access_token()

    url = f"{SP_API_BASE}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params, doseq=True)

    if body:
        req = urllib.request.Request(url, data=json.dumps(body).encode(), method=method)
    else:
        req = urllib.request.Request(url, method=method)

    req.add_header("x-amz-access-token", token)
    req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode() if e.fp else ""
        return {"error": f"HTTP {e.code}: {body_text[:500]}"}
    except Exception as e:
        return {"error": str(e)}


# --- Cache helpers ---

def cache_get(prefix, item_id):
    """Get from cache, returns None on miss."""
    if _cache:
        return _cache.get(prefix, item_id)
    return None


def cache_put(prefix, item_id, data):
    """Store in cache."""
    if _cache:
        _cache.put(prefix, item_id, data)


# --- Original commands ---

def cmd_inventory(asin=None):
    """Get FBA inventory summary."""
    params = {
        "granularityType": "Marketplace",
        "granularityId": MARKETPLACE_ID,
        "marketplaceIds": MARKETPLACE_ID,
    }
    if asin:
        params["sellerSkus"] = asin

    result = sp_api_request("/fba/inventory/v1/summaries", params)
    print(json.dumps(result, indent=2))


def cmd_orders(days=7):
    """Get recent orders."""
    after = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    params = {
        "MarketplaceIds": MARKETPLACE_ID,
        "CreatedAfter": after,
    }
    result = sp_api_request("/orders/v0/orders", params)
    print(json.dumps(result, indent=2))


def cmd_pricing(asin):
    """Get competitive pricing for an ASIN."""
    params = {
        "MarketplaceId": MARKETPLACE_ID,
        "Asins": asin,
        "ItemType": "Asin",
    }
    result = sp_api_request("/products/pricing/v0/competitivePrice", params)
    print(json.dumps(result, indent=2))


def cmd_fees(asin):
    """Estimate FBA fees for an ASIN."""
    result = sp_api_request(f"/products/fees/v0/items/{asin}/feesEstimate")
    print(json.dumps(result, indent=2))


def cmd_catalog(asin):
    """Get catalog item details."""
    params = {
        "marketplaceIds": MARKETPLACE_ID,
        "includedData": "summaries,attributes,dimensions,identifiers",
    }
    result = sp_api_request(f"/catalog/2022-04-01/items/{asin}", params)
    print(json.dumps(result, indent=2))


def cmd_health():
    """Account health summary."""
    print(json.dumps({
        "note": "Account health endpoint requires additional authorization. Check Seller Central directly.",
        "seller_central_url": "https://sellercentral.amazon.com/performance/dashboard"
    }, indent=2))


# --- New commands with caching ---

def cmd_catalog_full(asin):
    """Full catalog data with BSR, dimensions, images."""
    cached = cache_get("catalog", asin)
    if cached:
        print(json.dumps(cached))
        return

    params = {
        "marketplaceIds": MARKETPLACE_ID,
        "includedData": "summaries,dimensions,images,identifiers,salesRanks",
    }
    raw = sp_api_request(f"/catalog/2022-04-01/items/{asin}", params)

    if "error" in raw:
        print(json.dumps(raw))
        return

    # Parse response
    summaries = raw.get("summaries", [{}])
    summary = summaries[0] if summaries else {}

    # BSR
    sales_ranks = raw.get("salesRanks", [])
    bsr = None
    bsr_category = None
    for sr in sales_ranks:
        ranks = sr.get("classificationRanks", []) or sr.get("displayGroupRanks", [])
        for rank in ranks:
            if rank.get("rank"):
                bsr = rank["rank"]
                bsr_category = rank.get("title", rank.get("displayGroupName", "Unknown"))
                break
        if bsr:
            break

    # Dimensions
    dims_data = raw.get("dimensions", [{}])
    dims = dims_data[0] if dims_data else {}
    item_dims = dims.get("item", {})
    package_dims = dims.get("package", {})
    # Prefer package dimensions for FBA sizing
    use_dims = package_dims if package_dims else item_dims

    def parse_dim(dim_obj, key):
        v = dim_obj.get(key, {})
        if isinstance(v, dict):
            v = v.get("value")
        if v is not None:
            try:
                return round(float(v), 1)
            except (ValueError, TypeError):
                pass
        return v

    # Images
    images_data = raw.get("images", [{}])
    images = images_data[0].get("images", []) if images_data else []
    main_image = None
    for img in images:
        if img.get("variant") == "MAIN":
            main_image = img.get("link")
            break
    if not main_image and images:
        main_image = images[0].get("link")

    # UPC/EAN from identifiers
    identifiers_data = raw.get("identifiers", [{}])
    upc = None
    for id_group in identifiers_data:
        for ident in id_group.get("identifiers", []):
            if ident.get("identifierType") in ("EAN", "UPC"):
                upc = ident.get("identifier")
                break

    result = {
        "asin": asin,
        "title": summary.get("itemName", "Unknown"),
        "brand": summary.get("brand", "Unknown"),
        "bsr": bsr,
        "bsr_category": bsr_category,
        "upc": upc,
        "dimensions": {
            "length": parse_dim(use_dims, "length"),
            "width": parse_dim(use_dims, "width"),
            "height": parse_dim(use_dims, "height"),
            "weight": parse_dim(use_dims, "weight"),
        },
        "main_image_url": main_image,
        "amazon_link": f"https://amazon.com/dp/{asin}",
    }

    cache_put("catalog", asin, result)
    print(json.dumps(result))


def cmd_fees_estimate(asin, price):
    """FBA fee estimate for an ASIN at a given price."""
    cache_key = f"{asin}_{price}"
    cached = cache_get("fees", cache_key)
    if cached:
        print(json.dumps(cached))
        return

    price_float = float(price)

    body = {
        "FeesEstimateRequest": {
            "MarketplaceId": MARKETPLACE_ID,
            "IsAmazonFulfilled": True,
            "PriceToEstimateFees": {
                "ListingPrice": {
                    "CurrencyCode": "USD",
                    "Amount": price_float,
                },
            },
            "Identifier": asin,
        }
    }

    raw = sp_api_request(
        f"/products/fees/v0/items/{asin}/feesEstimate",
        method="POST",
        body=body,
    )

    if "error" in raw:
        print(json.dumps(raw))
        return

    # Parse fees response
    payload = raw.get("payload", raw)
    fees_result = payload.get("FeesEstimateResult", payload)
    estimate = fees_result.get("FeesEstimate", {})
    fee_details = estimate.get("FeeDetailList", [])

    referral_fee = 0.0
    fba_fee = 0.0

    for fd in fee_details:
        fee_type = fd.get("FeeType", "")
        amount = fd.get("FinalFee", {}).get("Amount", 0)
        if fee_type == "ReferralFee":
            referral_fee = float(amount)
        elif fee_type == "FBAFees":
            fba_fee = float(amount)

    total_fees = float(estimate.get("TotalFeesEstimate", {}).get("Amount", referral_fee + fba_fee))
    referral_pct = round((referral_fee / price_float * 100), 1) if price_float > 0 else 0

    # Estimate monthly storage from dimensions (approximate)
    # Small standard: $0.87/mo, Large standard: $0.56/cu.ft/mo
    storage_monthly = 0.87  # default small standard estimate

    result = {
        "asin": asin,
        "price": price_float,
        "referral_fee": round(referral_fee, 2),
        "fba_fulfillment_fee": round(fba_fee, 2),
        "total_fees": round(total_fees, 2),
        "referral_pct": referral_pct,
        "estimated_storage_monthly": storage_monthly,
    }

    cache_put("fees", cache_key, result)
    print(json.dumps(result))


def cmd_competitive_summary(asin):
    """Competitive pricing summary: buy box, offer counts, Amazon as seller."""
    cached = cache_get("pricing", asin)
    if cached:
        print(json.dumps(cached))
        return

    # Get competitive pricing
    params = {
        "MarketplaceId": MARKETPLACE_ID,
        "Asins": asin,
        "ItemType": "Asin",
    }
    comp_raw = sp_api_request("/products/pricing/v0/competitivePrice", params)

    # Get item offers
    offer_params = {
        "MarketplaceId": MARKETPLACE_ID,
        "ItemCondition": "New",
    }
    offers_raw = sp_api_request(f"/products/pricing/v0/items/{asin}/offers", offer_params)

    # Parse competitive pricing
    buy_box_price = None
    comp_payload = comp_raw.get("payload", [])
    if isinstance(comp_payload, list):
        for item in comp_payload:
            product = item.get("Product", {})
            comp_prices = product.get("CompetitivePricing", {}).get("CompetitivePrices", [])
            for cp in comp_prices:
                if cp.get("belongsToRequester", False) or cp.get("CompetitivePriceId") == "1":
                    landed = cp.get("Price", {}).get("LandedPrice", {})
                    buy_box_price = float(landed.get("Amount", 0))
                    break
            if buy_box_price:
                break

    # Parse offers
    new_offer_count = 0
    fba_offer_count = 0
    fbm_offer_count = 0
    amazon_is_seller = False

    offers_payload = offers_raw.get("payload", {})
    offer_list = offers_payload.get("Offers", [])

    for offer in offer_list:
        new_offer_count += 1
        fulfillment = offer.get("FulfillmentChannel", "")
        if fulfillment == "Amazon":
            fba_offer_count += 1
        else:
            fbm_offer_count += 1
        if offer.get("IsBuyBoxWinner") and fulfillment == "Amazon":
            # Check if it's Amazon itself
            if offer.get("SellerFeedbackRating", {}).get("SellerPositiveFeedbackRating") is None:
                pass  # Can't determine from this alone

    # Check number of offers summary
    summary = offers_payload.get("Summary", {})
    offer_counts = summary.get("NumberOfOffers", [])
    buybox_prices = summary.get("BuyBoxPrices", [])

    for oc in offer_counts:
        if oc.get("condition") == "new":
            channel = oc.get("fulfillmentChannel", "")
            count = oc.get("OfferCount", 0)
            if channel == "Amazon":
                fba_offer_count = count
            elif channel == "Merchant":
                fbm_offer_count = count

    new_offer_count = fba_offer_count + fbm_offer_count

    # Buy box price from summary if not found above
    if not buy_box_price:
        for bp in buybox_prices:
            if bp.get("condition") == "new":
                landed = bp.get("LandedPrice", {})
                buy_box_price = float(landed.get("Amount", 0))
                break

    # Amazon as seller check
    amazon_offer = summary.get("BuyBoxEligibleOffers", [])
    for ao in amazon_offer:
        if ao.get("fulfillmentChannel") == "Amazon" and ao.get("OfferCount", 0) > 0:
            pass  # FBA offers exist

    result = {
        "asin": asin,
        "buy_box_price": round(buy_box_price, 2) if buy_box_price else None,
        "new_offer_count": new_offer_count,
        "fba_offer_count": fba_offer_count,
        "fbm_offer_count": fbm_offer_count,
        "amazon_is_seller": amazon_is_seller,
    }

    cache_put("pricing", asin, result)
    print(json.dumps(result))


def cmd_restrictions(asin):
    """Check listing restrictions/gating for an ASIN."""
    cached = cache_get("restrictions", asin)
    if cached:
        print(json.dumps(cached))
        return

    params = {
        "asin": asin,
        "sellerId": SELLER_ID,
        "marketplaceIds": MARKETPLACE_ID,
        "conditionType": "new_new",
    }
    raw = sp_api_request("/listings/2021-08-01/restrictions", params)

    if "error" in raw:
        print(json.dumps(raw))
        return

    restrictions = raw.get("restrictions", [])
    restricted = len(restrictions) > 0

    reasons = []
    for r in restrictions:
        reason_list = r.get("reasons", [])
        for reason in reason_list:
            reasons.append({
                "code": reason.get("reasonCode", "UNKNOWN"),
                "message": reason.get("message", ""),
                "approval_url": reason.get("links", [{}])[0].get("resource") if reason.get("links") else None,
            })

    result = {
        "asin": asin,
        "restricted": restricted,
        "reasons": reasons,
    }

    cache_put("restrictions", asin, result)
    print(json.dumps(result))


def cmd_catalog_search(keywords):
    """Search Amazon catalog by keywords, return ASINs."""
    cached = cache_get("search", keywords.replace(" ", "_"))
    if cached:
        print(json.dumps(cached))
        return

    result = sp_api_request(
        "/catalog/2022-04-01/items",
        params={
            "keywords": keywords,
            "marketplaceIds": MARKETPLACE_ID,
            "includedData": "summaries,salesRanks",
            "pageSize": 10,
        }
    )

    if "error" in result:
        print(json.dumps(result))
        return

    items = result.get("items", [])
    output = []
    for item in items:
        asin = item.get("asin", "")
        summary = (item.get("summaries") or [{}])[0] if item.get("summaries") else {}
        ranks = item.get("salesRanks", [])
        bsr = None
        bsr_cat = None
        for rank_list in ranks:
            for r in rank_list.get("classificationRanks", []):
                bsr = r.get("rank")
                bsr_cat = r.get("title", "")
                break
            if not bsr:
                for r in rank_list.get("displayGroupRanks", []):
                    bsr = r.get("rank")
                    bsr_cat = r.get("title", "")
                    break
        output.append({
            "asin": asin,
            "title": summary.get("itemName", ""),
            "brand": summary.get("brand", ""),
            "bsr": bsr,
            "bsr_category": bsr_cat,
        })

    cache_put("search", keywords.replace(" ", "_"), output)
    print(json.dumps(output, indent=2))


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 sp-api-query.py <command> [args]")
        print("Commands: inventory, orders, pricing, fees, catalog, health,")
        print("          catalog-full, fees-estimate, competitive-summary, restrictions")
        sys.exit(1)

    cmd = sys.argv[1].lower()

    if cmd == "inventory":
        asin = None
        if "--asin" in sys.argv:
            asin = sys.argv[sys.argv.index("--asin") + 1]
        cmd_inventory(asin)
    elif cmd == "orders":
        days = 7
        if "--days" in sys.argv:
            days = int(sys.argv[sys.argv.index("--days") + 1])
        cmd_orders(days)
    elif cmd == "pricing":
        if "--asin" not in sys.argv:
            print("Usage: python3 sp-api-query.py pricing --asin ASIN")
            sys.exit(1)
        cmd_pricing(sys.argv[sys.argv.index("--asin") + 1])
    elif cmd == "fees":
        if "--asin" not in sys.argv:
            print("Usage: python3 sp-api-query.py fees --asin ASIN")
            sys.exit(1)
        cmd_fees(sys.argv[sys.argv.index("--asin") + 1])
    elif cmd == "catalog":
        if "--asin" not in sys.argv:
            print("Usage: python3 sp-api-query.py catalog --asin ASIN")
            sys.exit(1)
        cmd_catalog(sys.argv[sys.argv.index("--asin") + 1])
    elif cmd == "health":
        cmd_health()

    # --- New subcommands ---
    elif cmd == "catalog-full":
        if len(sys.argv) < 3:
            print("Usage: python3 sp-api-query.py catalog-full <ASIN>")
            sys.exit(1)
        cmd_catalog_full(sys.argv[2])
    elif cmd == "fees-estimate":
        if len(sys.argv) < 4:
            print("Usage: python3 sp-api-query.py fees-estimate <ASIN> <price>")
            sys.exit(1)
        cmd_fees_estimate(sys.argv[2], sys.argv[3])
    elif cmd == "competitive-summary":
        if len(sys.argv) < 3:
            print("Usage: python3 sp-api-query.py competitive-summary <ASIN>")
            sys.exit(1)
        cmd_competitive_summary(sys.argv[2])
    elif cmd == "restrictions":
        if len(sys.argv) < 3:
            print("Usage: python3 sp-api-query.py restrictions <ASIN>")
            sys.exit(1)
        cmd_restrictions(sys.argv[2])
    elif cmd == "catalog-search":
        if len(sys.argv) < 3:
            print("Usage: python3 sp-api-query.py catalog-search <keywords>")
            sys.exit(1)
        cmd_catalog_search(" ".join(sys.argv[2:]))
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
