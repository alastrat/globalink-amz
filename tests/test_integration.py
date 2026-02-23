"""Smoke test that verifies the entire system can start up."""
import pytest
from fastapi.testclient import TestClient
from gateway.api import app
from db.database import Base, get_engine
from config.settings import Settings


@pytest.fixture(autouse=True)
def setup_db():
    engine = get_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield


def test_full_system_health():
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200


def test_settings_load():
    s = Settings()
    assert s.min_roi_percent == 30.0


def test_incoming_message_help():
    client = TestClient(app)
    r = client.post("/webhook/incoming", json={
        "from_number": "573001234567",
        "message": "help",
    })
    assert r.status_code == 200


def test_openai_proxy_integration():
    client = TestClient(app)
    r = client.post("/v1/chat/completions", json={
        "model": "fba-agent",
        "messages": [{"role": "user", "content": "inventory"}],
    })
    assert r.status_code == 200
    data = r.json()
    assert "Processing" in data["choices"][0]["message"]["content"]


def test_all_workflow_imports():
    from workflows.wf1_product_research import run_product_research
    from workflows.wf2_supplier_management import run_supplier_management
    from workflows.wf3_order_management import run_order_management
    from workflows.wf4_prep_shipping import run_prep_shipping
    from workflows.wf5_inventory_buybox import run_inventory_buybox
    from workflows.wf6_returns_health import run_returns_health
    from workflows.wf7_finance import run_finance_daily
    from workflows.wf8_price_intelligence import run_price_intelligence
    assert callable(run_product_research)
    assert callable(run_supplier_management)


def test_scheduler_creates_jobs():
    from scheduler.jobs import create_scheduler
    scheduler = create_scheduler()
    jobs = scheduler.get_jobs()
    assert len(jobs) >= 3
