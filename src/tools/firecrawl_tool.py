"""Firecrawl tool for scraping supplier catalogs and retail prices."""
import os
from firecrawl import FirecrawlApp


def _get_app() -> FirecrawlApp:
    return FirecrawlApp(api_key=os.getenv("FIRECRAWL_API_KEY"))


CATALOG_SCHEMA = {
    "type": "object",
    "properties": {
        "supplier_name": {"type": "string"},
        "products": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "product_name": {"type": "string"},
                    "sku": {"type": "string"},
                    "upc": {"type": "string"},
                    "wholesale_price": {"type": "string"},
                    "retail_price": {"type": "string"},
                    "minimum_order_quantity": {"type": "string"},
                    "case_pack": {"type": "string"},
                    "brand": {"type": "string"},
                    "category": {"type": "string"},
                    "in_stock": {"type": "boolean"},
                },
            },
        },
    },
}

PRICE_SCHEMA = {
    "type": "object",
    "properties": {
        "product_name": {"type": "string"},
        "price": {"type": "string"},
        "in_stock": {"type": "boolean"},
        "seller": {"type": "string"},
    },
}


def scrape_supplier_catalog(url: str) -> dict:
    """Scrape a wholesale supplier catalog page and extract structured product data."""
    app = _get_app()
    result = app.scrape_url(
        url,
        params={
            "formats": ["extract", "markdown"],
            "extract": {
                "schema": CATALOG_SCHEMA,
                "prompt": (
                    "Extract all wholesale products from this catalog page. "
                    "Include product names, SKUs, UPC codes, wholesale prices, "
                    "minimum order quantities, case pack sizes, brands, and stock status."
                ),
            },
            "onlyMainContent": True,
            "waitFor": 5000,
        },
    )
    return result.get("extract", {})


def scrape_product_price(url: str) -> dict:
    """Scrape a retail product page to get current price."""
    app = _get_app()
    result = app.scrape_url(
        url,
        params={
            "formats": ["extract"],
            "extract": {
                "schema": PRICE_SCHEMA,
                "prompt": "Extract the product name, current price, stock status, and seller.",
            },
            "onlyMainContent": True,
            "waitFor": 3000,
        },
    )
    return result.get("extract", {})


def crawl_supplier_site(base_url: str, max_pages: int = 20) -> list[dict]:
    """Crawl a supplier's catalog across multiple pages."""
    app = _get_app()
    result = app.crawl_url(
        base_url,
        params={
            "limit": max_pages,
            "maxDepth": 2,
            "scrapeOptions": {
                "formats": ["extract"],
                "extract": {
                    "schema": CATALOG_SCHEMA,
                    "prompt": "Extract all wholesale products from this catalog page.",
                },
                "onlyMainContent": True,
            },
        },
        poll_interval=5,
    )
    all_products = []
    for page in result.get("data", []):
        extracted = page.get("extract", {})
        if extracted and extracted.get("products"):
            all_products.extend(extracted["products"])
    return all_products
