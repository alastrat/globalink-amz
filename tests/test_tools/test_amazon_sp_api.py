import pytest
from unittest.mock import patch, MagicMock
from tools.amazon_sp_api import (
    check_restriction,
    estimate_fees,
    get_product_details,
    get_competitive_pricing,
    search_catalog_by_upc,
)


@pytest.fixture
def mock_credentials():
    return {
        "lwa_app_id": "test-app-id",
        "lwa_client_secret": "test-secret",
        "refresh_token": "test-token",
    }


class TestCheckRestriction:
    @patch("tools.amazon_sp_api.ListingsRestrictions")
    def test_unrestricted_product(self, MockRestrictions):
        mock_client = MagicMock()
        mock_client.get_listings_restrictions.return_value.payload = {
            "restrictions": []
        }
        MockRestrictions.return_value = mock_client

        result = check_restriction("B08XXXXXXXX", "SELLER123")
        assert result["restricted"] is False
        assert result["asin"] == "B08XXXXXXXX"

    @patch("tools.amazon_sp_api.ListingsRestrictions")
    def test_restricted_product(self, MockRestrictions):
        mock_client = MagicMock()
        mock_client.get_listings_restrictions.return_value.payload = {
            "restrictions": [{
                "conditionType": "new_new",
                "reasons": [{"message": "Approval required", "reasonCode": "APPROVAL_REQUIRED"}]
            }]
        }
        MockRestrictions.return_value = mock_client

        result = check_restriction("B08YYYYYYYY", "SELLER123")
        assert result["restricted"] is True
        assert result["reason_code"] == "APPROVAL_REQUIRED"


class TestEstimateFees:
    @patch("tools.amazon_sp_api.ProductFees")
    def test_fee_estimate(self, MockFees):
        mock_client = MagicMock()
        mock_client.get_my_fees_estimate_for_asin.return_value.payload = {
            "FeesEstimateResult": {
                "Status": "Success",
                "FeesEstimate": {
                    "TotalFeesEstimate": {"CurrencyCode": "USD", "Amount": 9.12},
                    "FeeDetailList": [
                        {"FeeType": "ReferralFee", "FeeAmount": {"Amount": 3.75}},
                        {"FeeType": "FBAFees", "FeeAmount": {"Amount": 5.37}},
                    ]
                }
            }
        }
        MockFees.return_value = mock_client

        result = estimate_fees("B08XXXXXXXX", 24.99)
        assert result["total_fees"] == 9.12
        assert result["referral_fee"] == 3.75
        assert result["fba_fee"] == 5.37


class TestGetProductDetails:
    @patch("tools.amazon_sp_api.CatalogItems")
    def test_product_details(self, MockCatalog):
        mock_client = MagicMock()
        mock_client.get_catalog_item.return_value.payload = {
            "summaries": [{"itemName": "Test Product", "brand": "TestBrand"}],
            "salesRanks": [{"displayGroupRanks": [{"rank": 5000, "title": "Kitchen"}]}],
            "identifiers": [{"identifiers": [{"identifierType": "UPC", "identifier": "012345678901"}]}],
        }
        MockCatalog.return_value = mock_client

        result = get_product_details("B08XXXXXXXX")
        assert result["title"] == "Test Product"
        assert result["brand"] == "TestBrand"
        assert result["bsr"] == 5000


class TestSearchByUPC:
    @patch("tools.amazon_sp_api.CatalogItems")
    def test_upc_search(self, MockCatalog):
        mock_client = MagicMock()
        mock_client.search_catalog_items.return_value.payload = {
            "items": [{"asin": "B08XXXXXXXX", "summaries": [{"itemName": "Found Product"}]}]
        }
        MockCatalog.return_value = mock_client

        result = search_catalog_by_upc("012345678901")
        assert result[0]["asin"] == "B08XXXXXXXX"
