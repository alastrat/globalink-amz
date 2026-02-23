import pytest
from unittest.mock import patch, MagicMock
from tools.exa_tool import search_wholesale_suppliers, find_similar_suppliers


class TestSearchWholesaleSuppliers:
    @patch("tools.exa_tool.Exa")
    def test_search_suppliers(self, MockExa):
        mock_exa = MagicMock()
        mock_result = MagicMock()
        mock_result.results = [
            MagicMock(title="ABC Wholesale", url="https://abc.com", summary="Kitchen wholesaler"),
        ]
        mock_exa.search_and_contents.return_value = mock_result
        MockExa.return_value = mock_exa

        results = search_wholesale_suppliers("kitchen products wholesale USA")
        assert len(results) == 1
        assert results[0]["title"] == "ABC Wholesale"
