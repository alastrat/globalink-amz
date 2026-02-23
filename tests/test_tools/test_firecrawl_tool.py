import pytest
from unittest.mock import patch, MagicMock
from tools.firecrawl_tool import scrape_supplier_catalog, scrape_product_price


class TestScrapeSupplierCatalog:
    @patch("tools.firecrawl_tool.FirecrawlApp")
    def test_scrape_catalog(self, MockApp):
        mock_app = MagicMock()
        mock_app.scrape_url.return_value = {
            "extract": {
                "supplier_name": "ABC Dist",
                "products": [
                    {"product_name": "Widget A", "wholesale_price": "$8.50", "sku": "WA-001"},
                    {"product_name": "Widget B", "wholesale_price": "$12.00", "sku": "WB-002"},
                ],
            }
        }
        MockApp.return_value = mock_app

        result = scrape_supplier_catalog("https://abcdist.com/catalog")
        assert result["supplier_name"] == "ABC Dist"
        assert len(result["products"]) == 2
        assert result["products"][0]["product_name"] == "Widget A"


class TestScrapeProductPrice:
    @patch("tools.firecrawl_tool.FirecrawlApp")
    def test_scrape_price(self, MockApp):
        mock_app = MagicMock()
        mock_app.scrape_url.return_value = {
            "extract": {
                "product_name": "Kitchen Tool",
                "price": "$19.99",
                "in_stock": True,
            }
        }
        MockApp.return_value = mock_app

        result = scrape_product_price("https://walmart.com/product/123")
        assert result["price"] == "$19.99"
