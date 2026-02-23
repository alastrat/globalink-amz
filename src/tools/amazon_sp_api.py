"""Amazon SP-API client wrapper for all Amazon operations."""
import os
import time
from sp_api.api import CatalogItems, ListingsRestrictions, ProductFees, Products
from sp_api.base import Marketplaces
from sp_api.base.exceptions import SellingApiRequestThrottledException


def _get_credentials() -> dict:
    return {
        "lwa_app_id": os.getenv("SP_API_LWA_APP_ID", ""),
        "lwa_client_secret": os.getenv("SP_API_LWA_CLIENT_SECRET", ""),
        "refresh_token": os.getenv("SP_API_REFRESH_TOKEN", ""),
    }


def _retry_on_throttle(func, *args, max_retries=5, **kwargs):
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except SellingApiRequestThrottledException:
            wait = 2 ** attempt
            time.sleep(wait)
    raise Exception(f"SP-API throttled after {max_retries} retries")


def check_restriction(asin: str, seller_id: str, condition: str = "new_new") -> dict:
    """Check if seller is restricted from listing an ASIN."""
    client = ListingsRestrictions(
        marketplace=Marketplaces.US,
        credentials=_get_credentials(),
    )
    response = _retry_on_throttle(
        client.get_listings_restrictions,
        asin=asin,
        sellerId=seller_id,
        marketplaceIds=[Marketplaces.US.marketplace_id],
        conditionType=condition,
    )
    restrictions = response.payload.get("restrictions", [])

    if not restrictions:
        return {"asin": asin, "restricted": False, "reason_code": None, "reason_message": None}

    first_reason = restrictions[0].get("reasons", [{}])[0]
    return {
        "asin": asin,
        "restricted": True,
        "reason_code": first_reason.get("reasonCode"),
        "reason_message": first_reason.get("message"),
        "approval_url": next(
            (link.get("resource") for link in first_reason.get("links", [])), None
        ),
    }


def estimate_fees(asin: str, price: float) -> dict:
    """Get FBA fee estimate for an ASIN at a given price."""
    client = ProductFees(
        marketplace=Marketplaces.US,
        credentials=_get_credentials(),
    )
    response = _retry_on_throttle(
        client.get_my_fees_estimate_for_asin,
        asin=asin,
        price=price,
        currency_code="USD",
        shipping_price=0,
        is_fba=True,
    )
    result = response.payload.get("FeesEstimateResult", {})

    if result.get("Status") != "Success":
        error = result.get("Error", {})
        return {"error": f"{error.get('Code')}: {error.get('Message')}"}

    estimate = result.get("FeesEstimate", {})
    total = estimate.get("TotalFeesEstimate", {}).get("Amount", 0)
    fees = {f.get("FeeType"): f.get("FeeAmount", {}).get("Amount", 0)
            for f in estimate.get("FeeDetailList", [])}

    return {
        "asin": asin,
        "total_fees": total,
        "referral_fee": fees.get("ReferralFee", 0),
        "fba_fee": fees.get("FBAFees", 0),
        "variable_closing_fee": fees.get("VariableClosingFee", 0),
    }


def get_product_details(asin: str) -> dict:
    """Get catalog details for an ASIN."""
    client = CatalogItems(
        marketplace=Marketplaces.US,
        credentials=_get_credentials(),
    )
    response = _retry_on_throttle(
        client.get_catalog_item,
        asin=asin,
        marketplaceIds=[Marketplaces.US.marketplace_id],
        includedData="summaries,salesRanks,dimensions,identifiers,images",
    )
    payload = response.payload
    summaries = payload.get("summaries", [{}])
    summary = summaries[0] if summaries else {}

    bsr = None
    for rank_group in payload.get("salesRanks", []):
        for rank in rank_group.get("displayGroupRanks", []):
            bsr = rank.get("rank")
            break
        if bsr:
            break

    upc = None
    for id_group in payload.get("identifiers", []):
        for ident in id_group.get("identifiers", []):
            if ident.get("identifierType") == "UPC":
                upc = ident.get("identifier")
                break

    return {
        "asin": asin,
        "title": summary.get("itemName"),
        "brand": summary.get("brand"),
        "manufacturer": summary.get("manufacturer"),
        "bsr": bsr,
        "upc": upc,
    }


def get_competitive_pricing(asins: list[str]) -> list[dict]:
    """Get competitive pricing for up to 20 ASINs."""
    client = Products(
        marketplace=Marketplaces.US,
        credentials=_get_credentials(),
    )
    response = _retry_on_throttle(
        client.get_competitive_pricing_for_asins,
        asin_list=asins[:20],
    )
    results = []
    for product in response.payload:
        asin = product.get("ASIN")
        comp = product.get("Product", {}).get("CompetitivePricing", {})

        landed_price = None
        for cp in comp.get("CompetitivePrices", []):
            if cp.get("CompetitivePriceId") == "1":
                landed_price = cp.get("Price", {}).get("LandedPrice", {}).get("Amount")
                break

        offer_count = 0
        for ol in comp.get("NumberOfOfferListings", []):
            if ol.get("condition") == "New":
                offer_count = int(ol.get("Count", 0))

        bsr = None
        for sr in product.get("Product", {}).get("SalesRankings", []):
            bsr = sr.get("Rank")
            break

        results.append({
            "asin": asin,
            "buy_box_price": landed_price,
            "new_offer_count": offer_count,
            "bsr": bsr,
        })
    return results


def search_catalog_by_upc(upc: str) -> list[dict]:
    """Search Amazon catalog by UPC to find matching ASINs."""
    client = CatalogItems(
        marketplace=Marketplaces.US,
        credentials=_get_credentials(),
    )
    response = _retry_on_throttle(
        client.search_catalog_items,
        marketplaceIds=[Marketplaces.US.marketplace_id],
        identifiers=[upc],
        identifiersType="UPC",
        includedData="summaries,salesRanks",
    )
    items = response.payload.get("items", [])
    return [
        {
            "asin": item.get("asin"),
            "title": item.get("summaries", [{}])[0].get("itemName"),
        }
        for item in items
    ]
