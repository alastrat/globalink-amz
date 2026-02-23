import pytest
from unittest.mock import patch
from agents.crew import create_product_research_crew


def test_crew_has_correct_agents():
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
        crew = create_product_research_crew()
        agent_roles = [a.role for a in crew.agents]
        assert "Wholesale Product Scout" in agent_roles
        assert "Amazon ASIN Matcher" in agent_roles
        assert "Amazon Restriction Checker" in agent_roles
        assert "FBA Financial Analyst" in agent_roles
        assert "Amazon Market Analyst" in agent_roles


def test_crew_has_correct_task_count():
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
        crew = create_product_research_crew()
        assert len(crew.tasks) == 5
