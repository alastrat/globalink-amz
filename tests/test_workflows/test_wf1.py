import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from workflows.wf1_product_research import run_product_research


class TestProductResearchWorkflow:
    @patch("workflows.wf1_product_research.create_product_research_crew")
    @patch("workflows.wf1_product_research.send_whatsapp_message", new_callable=AsyncMock)
    @patch("workflows.wf1_product_research.save_results_to_db")
    def test_workflow_runs_crew_and_sends_briefing(self, mock_save, mock_send, mock_crew_factory):
        mock_crew = MagicMock()
        mock_crew.kickoff.return_value.raw = '[{"asin": "B08XXX", "title": "Test", "roi_percent": 50}]'
        mock_crew_factory.return_value = mock_crew

        import asyncio
        asyncio.run(run_product_research())

        mock_crew.kickoff.assert_called_once()
        mock_save.assert_called_once()
