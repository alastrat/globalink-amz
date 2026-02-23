# Amazon FBA Agent Crew - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a multi-agent AI system that autonomously manages an Amazon FBA wholesale business, communicating with the owner via WhatsApp.

**Architecture:** CrewAI (Python) orchestrates 7 specialized AI agents that discover wholesale products, validate Amazon selling eligibility, analyze profitability, and manage the full business lifecycle. OpenClaw (Node.js) provides the WhatsApp gateway. Both run on a single VPS via Docker Compose, communicating over a local HTTP API.

**Tech Stack:** Python 3.12, CrewAI, Anthropic Claude API (Haiku + Sonnet), Amazon SP-API (python-amazon-sp-api), Firecrawl, Exa, SQLite + SQLAlchemy, APScheduler, OpenClaw (Node.js), Docker Compose

---

## Phase 1: Project Foundation

### Task 1: Initialize Python Project

**Files:**
- Create: `pyproject.toml`
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `src/__init__.py`
- Create: `src/main.py`
- Create: `tests/__init__.py`

**Step 1: Create pyproject.toml**

```toml
[project]
name = "amazon-fba-agent"
version = "0.1.0"
description = "AI-powered Amazon FBA wholesale business management system"
requires-python = ">=3.12"

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

**Step 2: Create requirements.txt**

```
crewai>=0.80
crewai[tools]
anthropic
python-amazon-sp-api
firecrawl-py
exa-py
sqlalchemy>=2.0
alembic
apscheduler>=3.10
httpx
pydantic>=2.0
python-dotenv
uvicorn
fastapi
pytest
pytest-asyncio
```

**Step 3: Create .env.example**

```bash
# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Amazon SP-API
SP_API_LWA_APP_ID=amzn1.application-oa2-client.xxx
SP_API_LWA_CLIENT_SECRET=your-secret
SP_API_REFRESH_TOKEN=Atzr|your-token
AMAZON_SELLER_ID=AXXXXXXXXXXXXX
AMAZON_MARKETPLACE_ID=ATVPDKIKX0DER

# Firecrawl
FIRECRAWL_API_KEY=fc-...

# Exa
EXA_API_KEY=...

# WhatsApp Gateway
GATEWAY_URL=http://localhost:3000
GATEWAY_API_KEY=your-gateway-key

# App Settings
TIMEZONE=America/Bogota
MIN_ROI_PERCENT=30
MIN_PROFIT_PER_UNIT=3.0
MAX_FBA_SELLERS=20
DAILY_BRIEFING_HOUR=7
```

**Step 4: Create .gitignore**

```
__pycache__/
*.pyc
.env
*.db
.venv/
dist/
*.egg-info/
.pytest_cache/
node_modules/
```

**Step 5: Create src/__init__.py (empty) and src/main.py**

```python
"""Amazon FBA Agent Crew - Entry Point"""
import os
from dotenv import load_dotenv

load_dotenv()


def main():
    print("Amazon FBA Agent Crew starting...")
    # Will be filled in later tasks


if __name__ == "__main__":
    main()
```

**Step 6: Create virtual environment and install dependencies**

Run: `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`

**Step 7: Verify installation**

Run: `python -c "import crewai; from sp_api.api import CatalogItems; from firecrawl import FirecrawlApp; from exa_py import Exa; print('All imports OK')"`
Expected: `All imports OK`

**Step 8: Commit**

```bash
git add pyproject.toml requirements.txt .env.example .gitignore src/ tests/
git commit -m "feat: initialize project with dependencies and structure"
```

---

### Task 2: Database Models

**Files:**
- Create: `src/db/__init__.py`
- Create: `src/db/models.py`
- Create: `src/db/database.py`
- Create: `tests/test_db/__init__.py`
- Create: `tests/test_db/test_models.py`

**Step 1: Write the failing test**

```python
# tests/test_db/test_models.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from db.database import Base, get_engine
from db.models import (
    Product, AmazonListing, Restriction, Profitability,
    Supplier, SupplierProduct, PrepCenter, PurchaseOrder,
    FBAShipment, Inventory, PriceHistory, BuyBoxHistory,
    Return, DailyReport, FinancialTransaction,
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_create_supplier(db_session):
    supplier = Supplier(
        name="ABC Distributors",
        url="https://abcdist.com",
        contact_email="sales@abcdist.com",
        categories="kitchen,home",
        payment_terms="NET30",
    )
    db_session.add(supplier)
    db_session.commit()
    assert supplier.id is not None
    assert supplier.name == "ABC Distributors"


def test_create_product_with_amazon_listing(db_session):
    product = Product(
        name="Kitchen Gadget XYZ",
        upc="012345678901",
        wholesale_price=8.50,
        category="kitchen",
    )
    db_session.add(product)
    db_session.commit()

    listing = AmazonListing(
        product_id=product.id,
        asin="B08XXXXXXXX",
        title="Kitchen Gadget XYZ - Premium Edition",
        current_price=24.99,
        bsr=4200,
        category="Kitchen & Dining",
        fba_seller_count=4,
    )
    db_session.add(listing)
    db_session.commit()

    assert listing.product_id == product.id
    assert listing.asin == "B08XXXXXXXX"


def test_create_restriction(db_session):
    restriction = Restriction(
        asin="B08XXXXXXXX",
        condition_type="new_new",
        is_restricted=False,
    )
    db_session.add(restriction)
    db_session.commit()
    assert restriction.is_restricted is False


def test_create_profitability(db_session):
    product = Product(name="Test Product", wholesale_price=10.0)
    db_session.add(product)
    db_session.commit()

    prof = Profitability(
        product_id=product.id,
        asin="B08XXXXXXXX",
        wholesale_cost=10.0,
        amazon_price=29.99,
        referral_fee=4.50,
        fba_fee=5.20,
        prep_cost=1.50,
        shipping_cost=0.80,
        profit_per_unit=8.0,
        roi_percent=80.0,
        monthly_estimated_sales=120,
    )
    db_session.add(prof)
    db_session.commit()
    assert prof.roi_percent == 80.0


def test_create_purchase_order(db_session):
    supplier = Supplier(name="Test Supplier")
    db_session.add(supplier)
    db_session.commit()

    po = PurchaseOrder(
        supplier_id=supplier.id,
        status="draft",
        total_cost=250.0,
        total_units=30,
    )
    db_session.add(po)
    db_session.commit()
    assert po.status == "draft"


def test_price_history(db_session):
    ph = PriceHistory(
        asin="B08XXXXXXXX",
        source="amazon",
        price=24.99,
    )
    db_session.add(ph)
    db_session.commit()
    assert ph.source == "amazon"
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_db/test_models.py -v`
Expected: FAIL (modules not found)

**Step 3: Create src/db/database.py**

```python
"""Database engine and session management."""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///fba_agent.db")


class Base(DeclarativeBase):
    pass


def get_engine(url: str | None = None):
    return create_engine(url or DATABASE_URL)


def get_session_factory(engine=None):
    if engine is None:
        engine = get_engine()
    return sessionmaker(bind=engine)
```

**Step 4: Create src/db/models.py**

```python
"""SQLAlchemy models for all business entities."""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text,
    ForeignKey, Index,
)
from sqlalchemy.orm import relationship
from db.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(500), nullable=False)
    upc = Column(String(20), index=True)
    wholesale_price = Column(Float)
    category = Column(String(200))
    brand = Column(String(200))
    moq = Column(Integer)  # minimum order quantity
    case_pack = Column(Integer)
    source_url = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    amazon_listings = relationship("AmazonListing", back_populates="product")
    profitabilities = relationship("Profitability", back_populates="product")
    supplier_products = relationship("SupplierProduct", back_populates="product")


class AmazonListing(Base):
    __tablename__ = "amazon_listings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    asin = Column(String(20), unique=True, index=True, nullable=False)
    title = Column(String(500))
    current_price = Column(Float)
    bsr = Column(Integer)  # best seller rank
    category = Column(String(200))
    fba_seller_count = Column(Integer)
    fbm_seller_count = Column(Integer)
    has_amazon_offer = Column(Boolean, default=False)
    main_image_url = Column(Text)
    weight_lb = Column(Float)
    length_in = Column(Float)
    width_in = Column(Float)
    height_in = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    product = relationship("Product", back_populates="amazon_listings")

    __table_args__ = (
        Index("ix_asin_bsr", "asin", "bsr"),
    )


class Restriction(Base):
    __tablename__ = "restrictions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    asin = Column(String(20), index=True, nullable=False)
    condition_type = Column(String(50), default="new_new")
    is_restricted = Column(Boolean, nullable=False)
    reason_code = Column(String(100))
    reason_message = Column(Text)
    approval_url = Column(Text)
    checked_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_restriction_asin_condition", "asin", "condition_type"),
    )


class Profitability(Base):
    __tablename__ = "profitability"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    asin = Column(String(20), index=True)
    wholesale_cost = Column(Float, nullable=False)
    amazon_price = Column(Float, nullable=False)
    referral_fee = Column(Float)
    fba_fee = Column(Float)
    prep_cost = Column(Float, default=1.50)
    shipping_cost = Column(Float, default=0.80)
    profit_per_unit = Column(Float)
    roi_percent = Column(Float)
    monthly_estimated_sales = Column(Integer)
    monthly_estimated_profit = Column(Float)
    calculated_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product", back_populates="profitabilities")


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(300), nullable=False)
    url = Column(Text)
    contact_email = Column(String(300))
    contact_phone = Column(String(50))
    categories = Column(Text)  # comma-separated
    payment_terms = Column(String(100))
    minimum_order = Column(Float)
    notes = Column(Text)
    status = Column(String(50), default="prospect")  # prospect, applied, approved, active
    created_at = Column(DateTime, default=datetime.utcnow)

    supplier_products = relationship("SupplierProduct", back_populates="supplier")
    purchase_orders = relationship("PurchaseOrder", back_populates="supplier")


class SupplierProduct(Base):
    __tablename__ = "supplier_products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    supplier_sku = Column(String(100))
    wholesale_price = Column(Float)
    moq = Column(Integer)
    last_checked = Column(DateTime, default=datetime.utcnow)

    supplier = relationship("Supplier", back_populates="supplier_products")
    product = relationship("Product", back_populates="supplier_products")


class PrepCenter(Base):
    __tablename__ = "prep_centers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(300), nullable=False)
    location = Column(String(200))
    label_fee = Column(Float)  # per unit
    polybag_fee = Column(Float)
    inspection_fee = Column(Float)
    bundle_fee = Column(Float)
    storage_fee_monthly = Column(Float)  # per cubic foot
    turnaround_days = Column(Integer)
    contact_email = Column(String(300))
    notes = Column(Text)
    status = Column(String(50), default="prospect")


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"))
    status = Column(String(50), default="draft")  # draft, submitted, shipped, delivered, received
    total_cost = Column(Float)
    total_units = Column(Integer)
    tracking_number = Column(String(200))
    order_date = Column(DateTime)
    ship_date = Column(DateTime)
    delivery_date = Column(DateTime)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    supplier = relationship("Supplier", back_populates="purchase_orders")


class FBAShipment(Base):
    __tablename__ = "fba_shipments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    shipment_id = Column(String(100), unique=True)  # Amazon's shipment ID
    status = Column(String(50))  # WORKING, SHIPPED, RECEIVING, CLOSED
    destination_fc = Column(String(20))  # fulfillment center code
    total_units = Column(Integer)
    tracking_number = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, autoincrement=True)
    asin = Column(String(20), index=True, nullable=False)
    sku = Column(String(100))
    fulfillable_qty = Column(Integer, default=0)
    inbound_qty = Column(Integer, default=0)
    reserved_qty = Column(Integer, default=0)
    restock_threshold = Column(Integer, default=10)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PriceHistory(Base):
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    asin = Column(String(20), index=True, nullable=False)
    source = Column(String(50), nullable=False)  # amazon, walmart, target
    price = Column(Float, nullable=False)
    recorded_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_price_history_asin_source", "asin", "source"),
    )


class BuyBoxHistory(Base):
    __tablename__ = "buybox_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    asin = Column(String(20), index=True, nullable=False)
    winner_seller_id = Column(String(50))
    is_ours = Column(Boolean, default=False)
    price = Column(Float)
    recorded_at = Column(DateTime, default=datetime.utcnow)


class Return(Base):
    __tablename__ = "returns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    asin = Column(String(20), index=True, nullable=False)
    order_id = Column(String(100))
    reason = Column(Text)
    quantity = Column(Integer, default=1)
    returned_at = Column(DateTime, default=datetime.utcnow)


class DailyReport(Base):
    __tablename__ = "daily_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_type = Column(String(50), nullable=False)  # product_research, inventory, pnl
    content = Column(Text)
    products_analyzed = Column(Integer)
    opportunities_found = Column(Integer)
    sent_at = Column(DateTime, default=datetime.utcnow)


class FinancialTransaction(Base):
    __tablename__ = "financial_transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_type = Column(String(50), nullable=False)  # purchase, sale, fee, refund, prep
    asin = Column(String(20))
    amount = Column(Float, nullable=False)
    description = Column(Text)
    reference_id = Column(String(200))  # PO number, order ID, etc.
    transaction_date = Column(DateTime, default=datetime.utcnow)
```

**Step 5: Create src/db/__init__.py**

```python
from db.database import Base, get_engine, get_session_factory
from db.models import *
```

**Step 6: Run tests to verify they pass**

Run: `python -m pytest tests/test_db/test_models.py -v`
Expected: All 6 tests PASS

**Step 7: Commit**

```bash
git add src/db/ tests/test_db/
git commit -m "feat: add database models for all business entities"
```

---

### Task 3: Configuration System

**Files:**
- Create: `src/config/__init__.py`
- Create: `src/config/settings.py`
- Create: `config/agents.yaml`
- Create: `config/filters.yaml`
- Create: `config/schedules.yaml`
- Create: `tests/test_config.py`

**Step 1: Write the failing test**

```python
# tests/test_config.py
from config.settings import Settings, load_agent_config, load_filter_config, load_schedule_config


def test_settings_defaults():
    s = Settings()
    assert s.min_roi_percent == 30.0
    assert s.min_profit_per_unit == 3.0
    assert s.max_fba_sellers == 20
    assert s.timezone == "America/Bogota"


def test_load_agent_config():
    config = load_agent_config()
    assert "product_scout" in config
    assert "restriction_checker" in config
    assert config["product_scout"]["llm"] == "anthropic/claude-haiku-4-5-20251001"


def test_load_filter_config():
    config = load_filter_config()
    assert "excluded_categories" in config
    assert "hazmat" in [c.lower() for c in config["excluded_categories"]]


def test_load_schedule_config():
    config = load_schedule_config()
    assert "wf1_product_research" in config
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_config.py -v`
Expected: FAIL

**Step 3: Create config/agents.yaml**

```yaml
product_scout:
  role: "Wholesale Product Scout"
  goal: "Discover wholesale products from supplier catalogs and directories that could be profitable on Amazon FBA"
  backstory: "You are an expert wholesale product researcher who knows how to find profitable products from US distributors. You focus on high-demand, low-competition products and avoid hazmat and high-return categories."
  llm: "anthropic/claude-haiku-4-5-20251001"
  max_iter: 10
  allow_delegation: false

asin_matcher:
  role: "Amazon ASIN Matcher"
  goal: "Match wholesale products to their corresponding Amazon ASINs using UPC codes and product names"
  backstory: "You are an expert at cross-referencing product identifiers. You use UPC codes, product names, and brand information to find exact Amazon ASIN matches."
  llm: "anthropic/claude-haiku-4-5-20251001"
  max_iter: 5
  allow_delegation: false

restriction_checker:
  role: "Amazon Restriction Checker"
  goal: "Determine which Amazon ASINs the seller is allowed to list and sell"
  backstory: "You check product selling eligibility on Amazon. You understand brand gating, category restrictions, and approval requirements."
  llm: "anthropic/claude-haiku-4-5-20251001"
  max_iter: 3
  allow_delegation: false

financial_analyst:
  role: "FBA Financial Analyst"
  goal: "Calculate precise profitability for every ungated product including all fees and costs"
  backstory: "You are an expert in Amazon FBA economics. You calculate referral fees, FBA fulfillment fees, prep costs, and shipping to determine true ROI. You only recommend products with minimum 30% ROI and $3 profit per unit."
  llm: "anthropic/claude-sonnet-4-20250514"
  max_iter: 5
  allow_delegation: false

market_analyst:
  role: "Amazon Market Analyst"
  goal: "Evaluate product demand, competition level, and market dynamics"
  backstory: "You analyze Amazon marketplace data to assess demand (via BSR), competition (seller count), and market stability. You flag risks like Amazon selling the product directly or too many FBA sellers."
  llm: "anthropic/claude-sonnet-4-20250514"
  max_iter: 5
  allow_delegation: false

supply_chain:
  role: "Supply Chain Coordinator"
  goal: "Manage supplier relationships, prep center operations, and logistics"
  backstory: "You coordinate the wholesale supply chain from supplier to Amazon FBA warehouse. You track orders, manage prep center relationships, and optimize logistics costs."
  llm: "anthropic/claude-haiku-4-5-20251001"
  max_iter: 5
  allow_delegation: false

briefing_agent:
  role: "Daily Business Briefing Agent"
  goal: "Compile analysis results into clear, actionable WhatsApp briefings for the business owner"
  backstory: "You synthesize data from all other agents into concise daily reports. You rank opportunities, highlight alerts, and format messages for WhatsApp readability."
  llm: "anthropic/claude-sonnet-4-20250514"
  max_iter: 3
  allow_delegation: false
```

**Step 4: Create config/filters.yaml**

```yaml
excluded_categories:
  - "Hazmat"
  - "Dangerous Goods"
  - "Supplements"
  - "Dietary Supplements"
  - "Topical Products"
  - "Pesticides"

high_return_categories:
  - "Clothing"
  - "Shoes"
  - "Electronics"

min_roi_percent: 30.0
min_profit_per_unit: 3.0
max_fba_sellers: 20
min_bsr: 1           # ignore BSR 0 (no sales data)
max_bsr: 200000      # ignore very slow movers
min_amazon_price: 15.0  # avoid low-price items with thin margins
```

**Step 5: Create config/schedules.yaml**

```yaml
wf1_product_research:
  cron: "0 6 * * *"    # 6:00 AM daily
  timezone: "America/Bogota"

wf2_supplier_management:
  cron: "0 5 * * 1"    # 5:00 AM every Monday
  timezone: "America/Bogota"

wf3_order_management:
  interval_hours: 6

wf4_prep_shipping:
  cron: "0 9 * * *"    # 9:00 AM daily
  timezone: "America/Bogota"

wf5_inventory_buybox:
  interval_hours: 2

wf6_returns_health:
  cron: "0 10 * * *"   # 10:00 AM daily
  timezone: "America/Bogota"

wf7_finance:
  cron: "0 18 * * *"   # 6:00 PM daily snapshot
  timezone: "America/Bogota"
  weekly_pnl_cron: "0 8 * * 0"  # 8:00 AM every Sunday

wf8_price_intelligence:
  cron: "0 */4 * * *"  # every 4 hours
  timezone: "America/Bogota"
```

**Step 6: Create src/config/settings.py**

```python
"""Application configuration."""
import os
from pathlib import Path
from dataclasses import dataclass, field
import yaml

PROJECT_ROOT = Path(__file__).parent.parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"


@dataclass
class Settings:
    # Amazon
    seller_id: str = ""
    marketplace_id: str = "ATVPDKIKX0DER"

    # Filters
    min_roi_percent: float = 30.0
    min_profit_per_unit: float = 3.0
    max_fba_sellers: int = 20
    min_bsr: int = 1
    max_bsr: int = 200000
    min_amazon_price: float = 15.0

    # App
    timezone: str = "America/Bogota"
    daily_briefing_hour: int = 7
    database_url: str = "sqlite:///fba_agent.db"

    def __post_init__(self):
        self.seller_id = os.getenv("AMAZON_SELLER_ID", self.seller_id)
        self.marketplace_id = os.getenv("AMAZON_MARKETPLACE_ID", self.marketplace_id)
        self.timezone = os.getenv("TIMEZONE", self.timezone)
        db = os.getenv("DATABASE_URL")
        if db:
            self.database_url = db


def _load_yaml(filename: str) -> dict:
    path = CONFIG_DIR / filename
    with open(path) as f:
        return yaml.safe_load(f)


def load_agent_config() -> dict:
    return _load_yaml("agents.yaml")


def load_filter_config() -> dict:
    return _load_yaml("filters.yaml")


def load_schedule_config() -> dict:
    return _load_yaml("schedules.yaml")
```

**Step 7: Create src/config/__init__.py**

```python
from config.settings import Settings, load_agent_config, load_filter_config, load_schedule_config
```

**Step 8: Run tests**

Run: `python -m pytest tests/test_config.py -v`
Expected: All 4 tests PASS

**Step 9: Commit**

```bash
git add src/config/ config/ tests/test_config.py
git commit -m "feat: add configuration system with YAML-based agent, filter, and schedule configs"
```

---

## Phase 2: API Tool Wrappers

### Task 4: Amazon SP-API Client

**Files:**
- Create: `src/tools/__init__.py`
- Create: `src/tools/amazon_sp_api.py`
- Create: `tests/test_tools/__init__.py`
- Create: `tests/test_tools/test_amazon_sp_api.py`

**Step 1: Write the failing test (with mocked SP-API)**

```python
# tests/test_tools/test_amazon_sp_api.py
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
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_tools/test_amazon_sp_api.py -v`
Expected: FAIL

**Step 3: Implement src/tools/amazon_sp_api.py**

```python
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
            if cp.get("CompetitivePriceId") == "1":  # New Buy Box
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
```

**Step 4: Run tests**

Run: `python -m pytest tests/test_tools/test_amazon_sp_api.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/tools/ tests/test_tools/
git commit -m "feat: add Amazon SP-API client wrapper with restriction check, fees, catalog, and pricing"
```

---

### Task 5: Firecrawl and Exa Tool Wrappers

**Files:**
- Create: `src/tools/firecrawl_tool.py`
- Create: `src/tools/exa_tool.py`
- Create: `tests/test_tools/test_firecrawl_tool.py`
- Create: `tests/test_tools/test_exa_tool.py`

**Step 1: Write failing tests**

```python
# tests/test_tools/test_firecrawl_tool.py
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
```

```python
# tests/test_tools/test_exa_tool.py
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
```

**Step 2: Run tests to verify failure**

Run: `python -m pytest tests/test_tools/test_firecrawl_tool.py tests/test_tools/test_exa_tool.py -v`
Expected: FAIL

**Step 3: Implement src/tools/firecrawl_tool.py**

```python
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
```

**Step 4: Implement src/tools/exa_tool.py**

```python
"""Exa tool for AI-powered web search and supplier discovery."""
import os
from exa_py import Exa


def _get_client() -> Exa:
    return Exa(api_key=os.getenv("EXA_API_KEY"))


def search_wholesale_suppliers(query: str, num_results: int = 10) -> list[dict]:
    """Search for wholesale suppliers using AI-powered search."""
    exa = _get_client()
    results = exa.search_and_contents(
        query,
        num_results=num_results,
        type="neural",
        use_autoprompt=True,
        text={"max_characters": 1500},
        summary=True,
    )
    return [
        {
            "title": r.title,
            "url": r.url,
            "summary": getattr(r, "summary", None),
            "score": r.score,
        }
        for r in results.results
    ]


def find_similar_suppliers(supplier_url: str, num_results: int = 10) -> list[dict]:
    """Find suppliers similar to a known one."""
    exa = _get_client()
    results = exa.find_similar_and_contents(
        url=supplier_url,
        num_results=num_results,
        text={"max_characters": 1000},
        summary=True,
        exclude_source_domain=True,
    )
    return [
        {
            "title": r.title,
            "url": r.url,
            "summary": getattr(r, "summary", None),
        }
        for r in results.results
    ]


def search_product_market(query: str, num_results: int = 10) -> list[dict]:
    """Search for market intelligence on a product category."""
    exa = _get_client()
    results = exa.search_and_contents(
        query,
        num_results=num_results,
        type="neural",
        text={"max_characters": 2000},
        summary=True,
    )
    return [
        {
            "title": r.title,
            "url": r.url,
            "summary": getattr(r, "summary", None),
        }
        for r in results.results
    ]
```

**Step 5: Run tests**

Run: `python -m pytest tests/test_tools/ -v`
Expected: All tests PASS

**Step 6: Commit**

```bash
git add src/tools/firecrawl_tool.py src/tools/exa_tool.py tests/test_tools/test_firecrawl_tool.py tests/test_tools/test_exa_tool.py
git commit -m "feat: add Firecrawl and Exa tool wrappers for supplier scraping and discovery"
```

---

### Task 6: Offline Fee Calculator

**Files:**
- Create: `src/tools/fee_calculator.py`
- Create: `tests/test_tools/test_fee_calculator.py`

**Step 1: Write failing test**

```python
# tests/test_tools/test_fee_calculator.py
from tools.fee_calculator import calculate_profitability


def test_profitable_product():
    result = calculate_profitability(
        wholesale_cost=8.50,
        amazon_price=24.99,
        referral_fee=3.75,
        fba_fee=5.37,
        prep_cost=1.50,
        shipping_to_prep=0.80,
    )
    assert result["profit_per_unit"] == pytest.approx(5.07, abs=0.01)
    assert result["roi_percent"] == pytest.approx(59.6, abs=0.5)
    assert result["is_profitable"] is True


def test_unprofitable_product():
    result = calculate_profitability(
        wholesale_cost=20.00,
        amazon_price=24.99,
        referral_fee=3.75,
        fba_fee=5.37,
        prep_cost=1.50,
        shipping_to_prep=0.80,
    )
    assert result["profit_per_unit"] < 0
    assert result["is_profitable"] is False


def test_monthly_profit_estimate():
    result = calculate_profitability(
        wholesale_cost=8.50,
        amazon_price=24.99,
        referral_fee=3.75,
        fba_fee=5.37,
        prep_cost=1.50,
        shipping_to_prep=0.80,
        estimated_monthly_sales=100,
    )
    assert result["monthly_profit"] == pytest.approx(507, abs=5)


import pytest
```

**Step 2: Run to verify failure**

Run: `python -m pytest tests/test_tools/test_fee_calculator.py -v`

**Step 3: Implement**

```python
"""Offline FBA profitability calculator."""


def calculate_profitability(
    wholesale_cost: float,
    amazon_price: float,
    referral_fee: float,
    fba_fee: float,
    prep_cost: float = 1.50,
    shipping_to_prep: float = 0.80,
    estimated_monthly_sales: int | None = None,
    min_roi_percent: float = 30.0,
    min_profit: float = 3.0,
) -> dict:
    """Calculate full profitability for a product."""
    total_cost = wholesale_cost + prep_cost + shipping_to_prep
    total_fees = referral_fee + fba_fee
    profit_per_unit = amazon_price - total_cost - total_fees

    roi_percent = (profit_per_unit / total_cost * 100) if total_cost > 0 else 0

    monthly_profit = None
    if estimated_monthly_sales is not None:
        monthly_profit = profit_per_unit * estimated_monthly_sales

    is_profitable = profit_per_unit >= min_profit and roi_percent >= min_roi_percent

    return {
        "wholesale_cost": wholesale_cost,
        "amazon_price": amazon_price,
        "total_cost_per_unit": total_cost,
        "total_fees": total_fees,
        "referral_fee": referral_fee,
        "fba_fee": fba_fee,
        "prep_cost": prep_cost,
        "shipping_cost": shipping_to_prep,
        "profit_per_unit": round(profit_per_unit, 2),
        "roi_percent": round(roi_percent, 1),
        "is_profitable": is_profitable,
        "monthly_profit": round(monthly_profit, 2) if monthly_profit is not None else None,
        "estimated_monthly_sales": estimated_monthly_sales,
    }
```

**Step 4: Run tests**

Run: `python -m pytest tests/test_tools/test_fee_calculator.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/tools/fee_calculator.py tests/test_tools/test_fee_calculator.py
git commit -m "feat: add offline FBA profitability calculator"
```

---

## Phase 3: CrewAI Agent Definitions

### Task 7: Define All CrewAI Agents

**Files:**
- Create: `src/agents/__init__.py`
- Create: `src/agents/crew.py`
- Create: `tests/test_agents/__init__.py`
- Create: `tests/test_agents/test_crew.py`

**Step 1: Write the failing test**

```python
# tests/test_agents/test_crew.py
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
        assert len(crew.tasks) == 5  # scout, match, restrict, finance, market
```

**Step 2: Run to verify failure**

Run: `python -m pytest tests/test_agents/test_crew.py -v`

**Step 3: Implement src/agents/crew.py**

```python
"""CrewAI agent and crew definitions for Amazon FBA workflows."""
import os
from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type

from config.settings import load_agent_config
from tools.amazon_sp_api import (
    check_restriction, estimate_fees, get_product_details,
    get_competitive_pricing, search_catalog_by_upc,
)
from tools.firecrawl_tool import scrape_supplier_catalog
from tools.exa_tool import search_wholesale_suppliers
from tools.fee_calculator import calculate_profitability


# ── CrewAI Tool Wrappers ────────────────────────────────


class SearchSuppliersInput(BaseModel):
    query: str = Field(..., description="Search query for finding wholesale suppliers")

class SearchSuppliersTool(BaseTool):
    name: str = "Search Wholesale Suppliers"
    description: str = "Search the web for wholesale suppliers and distributors using AI-powered search"
    args_schema: Type[BaseModel] = SearchSuppliersInput
    def _run(self, query: str) -> str:
        results = search_wholesale_suppliers(query)
        return str(results)


class ScrapeSupplierInput(BaseModel):
    url: str = Field(..., description="URL of the supplier catalog page to scrape")

class ScrapeSupplierTool(BaseTool):
    name: str = "Scrape Supplier Catalog"
    description: str = "Scrape a wholesale supplier website to extract product catalog data"
    args_schema: Type[BaseModel] = ScrapeSupplierInput
    def _run(self, url: str) -> str:
        result = scrape_supplier_catalog(url)
        return str(result)


class UPCLookupInput(BaseModel):
    upc: str = Field(..., description="UPC barcode to search on Amazon")

class UPCLookupTool(BaseTool):
    name: str = "UPC to ASIN Lookup"
    description: str = "Search Amazon catalog by UPC code to find matching ASINs"
    args_schema: Type[BaseModel] = UPCLookupInput
    def _run(self, upc: str) -> str:
        results = search_catalog_by_upc(upc)
        return str(results)


class ProductDetailInput(BaseModel):
    asin: str = Field(..., description="Amazon ASIN to look up")

class ProductDetailTool(BaseTool):
    name: str = "Get Amazon Product Details"
    description: str = "Get product details from Amazon catalog including title, brand, BSR"
    args_schema: Type[BaseModel] = ProductDetailInput
    def _run(self, asin: str) -> str:
        result = get_product_details(asin)
        return str(result)


class RestrictionCheckInput(BaseModel):
    asin: str = Field(..., description="Amazon ASIN to check restrictions for")

class RestrictionCheckTool(BaseTool):
    name: str = "Check Amazon Selling Restriction"
    description: str = "Check if our seller account is allowed to sell a specific ASIN on Amazon"
    args_schema: Type[BaseModel] = RestrictionCheckInput
    def _run(self, asin: str) -> str:
        seller_id = os.getenv("AMAZON_SELLER_ID", "")
        result = check_restriction(asin, seller_id)
        return str(result)


class FeeEstimateInput(BaseModel):
    asin: str = Field(..., description="Amazon ASIN")
    price: float = Field(..., description="Selling price in USD")

class FeeEstimateTool(BaseTool):
    name: str = "Estimate Amazon FBA Fees"
    description: str = "Get estimated FBA fees (referral fee + fulfillment fee) for an ASIN at a given price"
    args_schema: Type[BaseModel] = FeeEstimateInput
    def _run(self, asin: str, price: float) -> str:
        result = estimate_fees(asin, price)
        return str(result)


class PricingInput(BaseModel):
    asins: str = Field(..., description="Comma-separated list of ASINs (max 20)")

class CompetitivePricingTool(BaseTool):
    name: str = "Get Competitive Pricing"
    description: str = "Get Buy Box price, seller count, and BSR for Amazon ASINs"
    args_schema: Type[BaseModel] = PricingInput
    def _run(self, asins: str) -> str:
        asin_list = [a.strip() for a in asins.split(",")]
        result = get_competitive_pricing(asin_list)
        return str(result)


class ProfitCalcInput(BaseModel):
    wholesale_cost: float = Field(..., description="Wholesale cost per unit")
    amazon_price: float = Field(..., description="Amazon selling price")
    referral_fee: float = Field(..., description="Amazon referral fee")
    fba_fee: float = Field(..., description="FBA fulfillment fee")

class ProfitCalculatorTool(BaseTool):
    name: str = "Calculate Profitability"
    description: str = "Calculate ROI and profit per unit for a product"
    args_schema: Type[BaseModel] = ProfitCalcInput
    def _run(self, wholesale_cost: float, amazon_price: float, referral_fee: float, fba_fee: float) -> str:
        result = calculate_profitability(wholesale_cost, amazon_price, referral_fee, fba_fee)
        return str(result)


# ── Agent Factory ────────────────────────────────────────


def _make_agent(config: dict, tools: list = None) -> Agent:
    return Agent(
        role=config["role"],
        goal=config["goal"],
        backstory=config["backstory"],
        llm=config["llm"],
        tools=tools or [],
        verbose=True,
        memory=True,
        max_iter=config.get("max_iter", 5),
        allow_delegation=config.get("allow_delegation", False),
    )


# ── Crew Builders ────────────────────────────────────────


def create_product_research_crew(supplier_data: str = "") -> Crew:
    """Create the WF1 Product Research crew."""
    agent_config = load_agent_config()

    scout = _make_agent(agent_config["product_scout"], [SearchSuppliersTool(), ScrapeSupplierTool()])
    matcher = _make_agent(agent_config["asin_matcher"], [UPCLookupTool(), ProductDetailTool()])
    checker = _make_agent(agent_config["restriction_checker"], [RestrictionCheckTool()])
    finance = _make_agent(agent_config["financial_analyst"], [FeeEstimateTool(), ProfitCalculatorTool()])
    market = _make_agent(agent_config["market_analyst"], [CompetitivePricingTool()])

    scout_task = Task(
        description=(
            "Discover wholesale products to analyze. "
            f"Supplier data provided: {supplier_data or 'None - search for new suppliers'}. "
            "Find products with UPC codes and wholesale prices. "
            "Focus on: home & kitchen, toys, pet supplies, office products. "
            "Avoid: hazmat, supplements, clothing, electronics. "
            "Return a list of products with: name, UPC, wholesale price, category, supplier."
        ),
        expected_output="JSON list of products with name, upc, wholesale_price, category, supplier_name, supplier_url",
        agent=scout,
    )

    match_task = Task(
        description=(
            "For each product from the scout, find matching Amazon ASINs. "
            "Use UPC codes to look up ASINs. For each match, get the product title, brand, and BSR. "
            "Skip products that have no Amazon match."
        ),
        expected_output="JSON list of matched products with: name, upc, asin, title, brand, bsr, wholesale_price",
        agent=matcher,
        context=[scout_task],
    )

    restrict_task = Task(
        description=(
            "For each matched ASIN, check if our seller account is restricted from selling it. "
            "Filter out all restricted ASINs. "
            "Flag ASINs that require approval but could potentially be unlocked."
        ),
        expected_output="JSON list of UNRESTRICTED products with: asin, title, wholesale_price, restriction_status",
        agent=checker,
        context=[match_task],
    )

    finance_task = Task(
        description=(
            "For each unrestricted product, calculate profitability: "
            "1. Get FBA fee estimate from Amazon. "
            "2. Calculate: profit = amazon_price - wholesale_cost - fba_fees - prep($1.50) - shipping($0.80). "
            "3. Calculate ROI% = profit / total_cost * 100. "
            "4. Filter: keep only products with ROI >= 30% AND profit >= $3/unit. "
            "Rank by ROI descending."
        ),
        expected_output="JSON list of profitable products ranked by ROI with full financial breakdown",
        agent=finance,
        context=[restrict_task],
    )

    market_task = Task(
        description=(
            "For each profitable product, evaluate market dynamics: "
            "1. Check BSR (lower = better demand, ideal < 100,000). "
            "2. Count FBA sellers (fewer = less competition, max 20). "
            "3. Check if Amazon itself sells the product (avoid if yes). "
            "4. Score each product: demand_score (1-10) and competition_score (1-10). "
            "5. Final rank = ROI * demand_score / competition_score. "
            "Return top 20 products."
        ),
        expected_output="JSON list of top 20 products with full analysis: financials, market scores, final rank",
        agent=market,
        context=[finance_task],
    )

    return Crew(
        agents=[scout, matcher, checker, finance, market],
        tasks=[scout_task, match_task, restrict_task, finance_task, market_task],
        process=Process.sequential,
        memory=True,
        verbose=True,
    )
```

**Step 4: Run tests**

Run: `python -m pytest tests/test_agents/test_crew.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/agents/ tests/test_agents/
git commit -m "feat: define CrewAI agents and product research crew with all tool wrappers"
```

---

## Phase 4: WhatsApp Gateway Bridge

### Task 8: HTTP API for WhatsApp Communication

**Files:**
- Create: `src/gateway/__init__.py`
- Create: `src/gateway/api.py`
- Create: `src/gateway/message_templates.py`
- Create: `src/gateway/whatsapp_handler.py`
- Create: `tests/test_gateway/__init__.py`
- Create: `tests/test_gateway/test_api.py`

**Step 1: Write failing test**

```python
# tests/test_gateway/test_api.py
import pytest
from fastapi.testclient import TestClient
from gateway.api import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_incoming_message_route(client):
    response = client.post("/webhook/incoming", json={
        "from": "573001234567",
        "message": "inventory",
    })
    assert response.status_code == 200


def test_send_message_endpoint(client):
    # This tests the outbound endpoint our system uses to send messages
    response = client.post("/api/send", json={
        "to": "573001234567",
        "message": "Test message",
    })
    assert response.status_code == 200
```

**Step 2: Run to verify failure**

Run: `python -m pytest tests/test_gateway/test_api.py -v`

**Step 3: Implement src/gateway/message_templates.py**

```python
"""WhatsApp message formatting templates."""


def format_product_briefing(products: list[dict], date: str) -> str:
    """Format the daily product research briefing."""
    if not products:
        return f"Daily FBA Opportunities - {date}\n\nNo new opportunities found today."

    lines = [f"Daily FBA Opportunities - {date}\n"]
    for i, p in enumerate(products[:10], 1):
        lines.append(f"{i}. {p.get('title', 'Unknown')[:50]}")
        lines.append(f"   ASIN: {p.get('asin', 'N/A')} | BSR: {p.get('bsr', 'N/A'):,}")
        lines.append(f"   Wholesale: ${p.get('wholesale_cost', 0):.2f} | Amazon: ${p.get('amazon_price', 0):.2f}")
        lines.append(f"   Fees: ${p.get('total_fees', 0):.2f} | Profit: ${p.get('profit_per_unit', 0):.2f}/unit")
        lines.append(f"   ROI: {p.get('roi_percent', 0):.0f}% | Sellers: {p.get('fba_sellers', 'N/A')} FBA")
        lines.append(f"   {'UNGATED' if not p.get('restricted') else 'GATED'} | {p.get('supplier_name', 'N/A')}")
        lines.append("")

    lines.append("Reply:")
    lines.append('- "details N" - full breakdown')
    lines.append('- "buy N" - draft purchase order')
    lines.append('- "skip" - no action today')
    lines.append('- "add supplier [url]" - add new supplier')

    return "\n".join(lines)


def format_inventory_report(items: list[dict]) -> str:
    """Format inventory status report."""
    if not items:
        return "Inventory Report\n\nNo active inventory."

    lines = ["Inventory Report\n"]
    for item in items:
        status = "LOW" if item.get("fulfillable_qty", 0) < item.get("restock_threshold", 10) else "OK"
        lines.append(f"- {item.get('asin', 'N/A')}: {item.get('fulfillable_qty', 0)} units [{status}]")
        if item.get("inbound_qty", 0) > 0:
            lines.append(f"  Inbound: {item['inbound_qty']} units")
    return "\n".join(lines)


def format_pnl_snapshot(data: dict) -> str:
    """Format P&L snapshot."""
    lines = [
        f"P&L Snapshot - {data.get('period', 'Today')}\n",
        f"Revenue: ${data.get('revenue', 0):,.2f}",
        f"COGS:    ${data.get('cogs', 0):,.2f}",
        f"Fees:    ${data.get('fees', 0):,.2f}",
        f"Profit:  ${data.get('profit', 0):,.2f}",
        f"Margin:  {data.get('margin_percent', 0):.1f}%",
    ]
    return "\n".join(lines)
```

**Step 4: Implement src/gateway/whatsapp_handler.py**

```python
"""Handle incoming WhatsApp messages and route to appropriate workflow."""
import re


COMMANDS = {
    r"^details\s+(\d+)$": "product_details",
    r"^buy\s+(\d+)$": "create_po",
    r"^supplier\s+(\d+)$": "supplier_info",
    r"^add supplier\s+(.+)$": "add_supplier",
    r"^inventory$": "inventory_report",
    r"^buybox$": "buybox_report",
    r"^reprice\s+(\w+)\s+([\d.]+)$": "reprice",
    r"^restock$": "restock_report",
    r"^orders$": "order_status",
    r"^track\s+(.+)$": "track_order",
    r"^inbound$": "inbound_status",
    r"^prep status$": "prep_status",
    r"^prep costs$": "prep_costs",
    r"^returns$": "returns_report",
    r"^health$": "health_report",
    r"^reviews\s+(\w+)$": "reviews",
    r"^profit$": "profit_snapshot",
    r"^pnl$": "pnl_report",
    r"^roi\s+(.+)$": "roi_detail",
    r"^cashflow$": "cashflow_report",
    r"^prices$": "price_comparison",
    r"^price history\s+(\w+)$": "price_history",
    r"^skip$": "skip",
    r"^help$": "help",
}


def parse_command(message: str) -> tuple[str, list[str]]:
    """Parse a WhatsApp message into a command and arguments."""
    text = message.strip().lower()
    for pattern, command in COMMANDS.items():
        match = re.match(pattern, text, re.IGNORECASE)
        if match:
            return command, list(match.groups())
    return "unknown", [text]


def get_help_message() -> str:
    return (
        "Available commands:\n\n"
        "Product Research:\n"
        "- details N - full product breakdown\n"
        "- buy N - draft purchase order\n"
        "- add supplier [url] - add new supplier\n\n"
        "Inventory:\n"
        "- inventory - stock levels\n"
        "- buybox - Buy Box status\n"
        "- restock - reorder suggestions\n\n"
        "Orders:\n"
        "- orders - active order status\n"
        "- track [PO#] - shipment tracking\n"
        "- inbound - FBA inbound status\n\n"
        "Finance:\n"
        "- profit - today's profit\n"
        "- pnl - monthly P&L\n"
        "- cashflow - money in/out\n\n"
        "Other:\n"
        "- health - account health\n"
        "- returns - return rates\n"
        "- prices - price comparison\n"
        "- help - this message"
    )
```

**Step 5: Implement src/gateway/api.py**

```python
"""FastAPI HTTP server bridging WhatsApp (OpenClaw) and CrewAI agents."""
import os
import httpx
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel

from gateway.whatsapp_handler import parse_command, get_help_message

app = FastAPI(title="FBA Agent Gateway")

GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:3000")
OWNER_PHONE = os.getenv("OWNER_WHATSAPP_NUMBER", "")


class IncomingMessage(BaseModel):
    from_number: str = ""
    message: str = ""


class OutgoingMessage(BaseModel):
    to: str = ""
    message: str = ""


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/webhook/incoming")
async def handle_incoming(msg: IncomingMessage, background_tasks: BackgroundTasks):
    """Receive messages from OpenClaw webhook and process them."""
    command, args = parse_command(msg.message)

    if command == "help":
        await send_whatsapp_message(msg.from_number, get_help_message())
    elif command == "unknown":
        await send_whatsapp_message(
            msg.from_number,
            f'Command not recognized: "{msg.message}". Send "help" for available commands.'
        )
    else:
        # Queue for async processing by the appropriate workflow
        background_tasks.add_task(process_command, command, args, msg.from_number)
        await send_whatsapp_message(msg.from_number, f"Processing: {command}...")

    return {"status": "received"}


@app.post("/api/send")
async def send_message(msg: OutgoingMessage):
    """API endpoint for internal services to send WhatsApp messages."""
    await send_whatsapp_message(msg.to or OWNER_PHONE, msg.message)
    return {"status": "sent"}


async def send_whatsapp_message(to: str, message: str):
    """Send a message via OpenClaw's WhatsApp gateway."""
    async with httpx.AsyncClient() as client:
        try:
            await client.post(
                f"{GATEWAY_URL}/api/send",
                json={"to": to, "message": message},
                headers={"Authorization": f"Bearer {os.getenv('GATEWAY_API_KEY', '')}"},
                timeout=10,
            )
        except httpx.RequestError:
            # Gateway not available - log but don't crash
            print(f"[Gateway] Failed to send message to {to}: {message[:100]}...")


async def process_command(command: str, args: list[str], from_number: str):
    """Process a parsed command by invoking the appropriate workflow."""
    # This will be filled in by workflow implementations
    # For now, just echo back
    await send_whatsapp_message(from_number, f"Processed command: {command} with args: {args}")
```

**Step 6: Run tests**

Run: `python -m pytest tests/test_gateway/ -v`
Expected: PASS

**Step 7: Commit**

```bash
git add src/gateway/ tests/test_gateway/
git commit -m "feat: add FastAPI gateway with WhatsApp message routing and templates"
```

---

## Phase 5: Workflow Orchestration

### Task 9: WF1 Product Research Workflow

**Files:**
- Create: `src/workflows/__init__.py`
- Create: `src/workflows/wf1_product_research.py`
- Create: `tests/test_workflows/__init__.py`
- Create: `tests/test_workflows/test_wf1.py`

**Step 1: Write failing test**

```python
# tests/test_workflows/test_wf1.py
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
```

**Step 2: Implement src/workflows/wf1_product_research.py**

```python
"""WF1: Product Research - Daily product discovery and analysis pipeline."""
import json
from datetime import datetime

from agents.crew import create_product_research_crew
from gateway.api import send_whatsapp_message
from gateway.message_templates import format_product_briefing
from db.database import get_engine, get_session_factory, Base
from db.models import Product, AmazonListing, Restriction, Profitability, DailyReport

import os


def save_results_to_db(products: list[dict]):
    """Persist analysis results to the database."""
    engine = get_engine()
    Base.metadata.create_all(engine)
    SessionFactory = get_session_factory(engine)

    with SessionFactory() as session:
        for p in products:
            product = Product(
                name=p.get("title", "Unknown"),
                upc=p.get("upc"),
                wholesale_price=p.get("wholesale_cost"),
                category=p.get("category"),
                brand=p.get("brand"),
            )
            session.add(product)
            session.flush()

            if p.get("asin"):
                listing = AmazonListing(
                    product_id=product.id,
                    asin=p["asin"],
                    title=p.get("title"),
                    current_price=p.get("amazon_price"),
                    bsr=p.get("bsr"),
                    fba_seller_count=p.get("fba_sellers"),
                )
                session.add(listing)

                restriction = Restriction(
                    asin=p["asin"],
                    is_restricted=p.get("restricted", False),
                )
                session.add(restriction)

                if p.get("profit_per_unit") is not None:
                    prof = Profitability(
                        product_id=product.id,
                        asin=p["asin"],
                        wholesale_cost=p.get("wholesale_cost", 0),
                        amazon_price=p.get("amazon_price", 0),
                        referral_fee=p.get("referral_fee", 0),
                        fba_fee=p.get("fba_fee", 0),
                        profit_per_unit=p.get("profit_per_unit", 0),
                        roi_percent=p.get("roi_percent", 0),
                    )
                    session.add(prof)

        report = DailyReport(
            report_type="product_research",
            products_analyzed=len(products),
            opportunities_found=len([p for p in products if p.get("roi_percent", 0) >= 30]),
        )
        session.add(report)
        session.commit()


async def run_product_research(supplier_data: str = ""):
    """Execute the full product research pipeline."""
    crew = create_product_research_crew(supplier_data)
    result = crew.kickoff()

    try:
        products = json.loads(result.raw)
    except (json.JSONDecodeError, AttributeError):
        products = []

    save_results_to_db(products)

    today = datetime.now().strftime("%b %d")
    briefing = format_product_briefing(products, today)

    owner_phone = os.getenv("OWNER_WHATSAPP_NUMBER", "")
    await send_whatsapp_message(owner_phone, briefing)

    return products
```

**Step 3: Run tests**

Run: `python -m pytest tests/test_workflows/test_wf1.py -v`
Expected: PASS

**Step 4: Commit**

```bash
git add src/workflows/ tests/test_workflows/
git commit -m "feat: add WF1 product research workflow with crew execution and DB persistence"
```

---

### Task 10: Scheduler Setup

**Files:**
- Create: `src/scheduler/__init__.py`
- Create: `src/scheduler/jobs.py`

**Step 1: Implement src/scheduler/jobs.py**

```python
"""APScheduler job definitions for all workflow triggers."""
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from config.settings import load_schedule_config


def create_scheduler() -> AsyncIOScheduler:
    """Create and configure the scheduler with all workflow jobs."""
    scheduler = AsyncIOScheduler()
    config = load_schedule_config()

    # WF1: Product Research - Daily
    wf1 = config.get("wf1_product_research", {})
    if wf1.get("cron"):
        scheduler.add_job(
            _run_wf1,
            CronTrigger.from_crontab(wf1["cron"], timezone=wf1.get("timezone", "UTC")),
            id="wf1_product_research",
            name="Daily Product Research",
        )

    # WF5: Inventory & Buy Box - Every 2 hours
    wf5 = config.get("wf5_inventory_buybox", {})
    if wf5.get("interval_hours"):
        scheduler.add_job(
            _run_wf5,
            IntervalTrigger(hours=wf5["interval_hours"]),
            id="wf5_inventory_buybox",
            name="Inventory & Buy Box Check",
        )

    # WF7: Finance - Daily snapshot + Weekly P&L
    wf7 = config.get("wf7_finance", {})
    if wf7.get("cron"):
        scheduler.add_job(
            _run_wf7_daily,
            CronTrigger.from_crontab(wf7["cron"], timezone=wf7.get("timezone", "UTC")),
            id="wf7_finance_daily",
            name="Daily P&L Snapshot",
        )

    # WF8: Price Intelligence - Every 4 hours
    wf8 = config.get("wf8_price_intelligence", {})
    if wf8.get("cron"):
        scheduler.add_job(
            _run_wf8,
            CronTrigger.from_crontab(wf8["cron"], timezone=wf8.get("timezone", "UTC")),
            id="wf8_price_intelligence",
            name="Price Intelligence",
        )

    return scheduler


async def _run_wf1():
    from workflows.wf1_product_research import run_product_research
    await run_product_research()


async def _run_wf5():
    # Will be implemented in future task
    pass


async def _run_wf7_daily():
    # Will be implemented in future task
    pass


async def _run_wf8():
    # Will be implemented in future task
    pass
```

**Step 2: Commit**

```bash
git add src/scheduler/
git commit -m "feat: add APScheduler with cron triggers for all workflows"
```

---

### Task 11: Application Entry Point

**Files:**
- Modify: `src/main.py`

**Step 1: Update src/main.py**

```python
"""Amazon FBA Agent Crew - Application Entry Point."""
import asyncio
import uvicorn
from dotenv import load_dotenv

load_dotenv()

from db.database import Base, get_engine
from gateway.api import app as fastapi_app
from scheduler.jobs import create_scheduler


def init_db():
    """Create all database tables."""
    engine = get_engine()
    Base.metadata.create_all(engine)
    print("[DB] Tables created.")


async def start():
    """Start the application: API server + scheduler."""
    init_db()

    scheduler = create_scheduler()
    scheduler.start()
    print("[Scheduler] Started with scheduled jobs.")

    config = uvicorn.Config(
        fastapi_app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )
    server = uvicorn.Server(config)
    print("[API] Starting on port 8000...")
    await server.serve()


def main():
    asyncio.run(start())


if __name__ == "__main__":
    main()
```

**Step 2: Commit**

```bash
git add src/main.py
git commit -m "feat: wire up main entry point with DB init, scheduler, and API server"
```

---

## Phase 6: Docker Deployment

### Task 12: Dockerfile and Docker Compose

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `gateway/Dockerfile` (for OpenClaw)
- Create: `gateway/openclaw-config.json`

**Step 1: Create Dockerfile (Python app)**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY config/ config/
COPY pyproject.toml .

ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["python", "src/main.py"]
```

**Step 2: Create docker-compose.yml**

```yaml
version: "3.8"

services:
  fba-agent:
    build: .
    container_name: fba-agent
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./data:/app/data
      - ./config:/app/config
    restart: unless-stopped
    depends_on:
      - openclaw

  openclaw:
    image: ghcr.io/openclaw/openclaw:latest
    container_name: openclaw-gateway
    ports:
      - "3000:3000"
    environment:
      - WEBHOOK_URL=http://fba-agent:8000/webhook/incoming
    volumes:
      - ./gateway/openclaw-config.json:/app/config.json
      - openclaw-data:/app/data
    restart: unless-stopped

volumes:
  openclaw-data:
```

**Step 3: Create gateway/openclaw-config.json**

```json
{
  "channels": {
    "whatsapp": {
      "enabled": true
    }
  },
  "webhook": {
    "url": "http://fba-agent:8000/webhook/incoming",
    "events": ["message.received"]
  },
  "ai": {
    "enabled": false
  }
}
```

> **Note:** The exact OpenClaw configuration may need adjustment based on its actual API. This is a starting template - verify against OpenClaw's documentation during deployment.

**Step 4: Commit**

```bash
git add Dockerfile docker-compose.yml gateway/
git commit -m "feat: add Docker Compose deployment with Python app and OpenClaw gateway"
```

---

## Phase 7: Remaining Workflows (Stubs + Implementation)

### Task 13: Implement Remaining Workflow Stubs

For workflows WF2-WF8, create stub files that follow the same pattern as WF1 but with placeholder logic. Each can be fleshed out incrementally as the business grows.

**Files to create:**
- `src/workflows/wf2_supplier_management.py`
- `src/workflows/wf3_order_management.py`
- `src/workflows/wf4_prep_shipping.py`
- `src/workflows/wf5_inventory_buybox.py`
- `src/workflows/wf6_returns_health.py`
- `src/workflows/wf7_finance.py`
- `src/workflows/wf8_price_intelligence.py`

Each file follows this pattern:

```python
"""WF[N]: [Name] - [Description]."""
import os
from gateway.api import send_whatsapp_message


async def run_[workflow_name]():
    """Execute the [workflow name] pipeline."""
    owner = os.getenv("OWNER_WHATSAPP_NUMBER", "")
    # TODO: Implement full workflow
    await send_whatsapp_message(owner, "[Workflow Name] check completed - no issues.")
```

Wire each into `scheduler/jobs.py` and `gateway/whatsapp_handler.py` command routing.

**Commit:**

```bash
git add src/workflows/
git commit -m "feat: add workflow stubs for WF2-WF8 with scheduler and command routing"
```

---

### Task 14: Integration Test & Documentation

**Files:**
- Create: `tests/test_integration.py`
- Create: `scripts/setup.sh`

**Step 1: Integration test**

```python
# tests/test_integration.py
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
```

**Step 2: Create scripts/setup.sh**

```bash
#!/bin/bash
# Setup script for Amazon FBA Agent Crew
set -e

echo "=== Amazon FBA Agent Crew Setup ==="

# Check Python version
python3 --version

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy env template
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env from template. Please fill in your API keys."
fi

# Run tests
python -m pytest tests/ -v

echo ""
echo "=== Setup Complete ==="
echo "Next steps:"
echo "1. Edit .env with your API keys (SP-API, Anthropic, Firecrawl, Exa)"
echo "2. Run: python src/main.py"
echo "3. Or deploy with: docker compose up -d"
```

**Step 3: Run all tests**

Run: `python -m pytest tests/ -v`
Expected: All tests PASS

**Step 4: Commit**

```bash
chmod +x scripts/setup.sh
git add tests/test_integration.py scripts/
git commit -m "feat: add integration tests and setup script"
```

---

## Summary: Build Order

| Phase | Tasks | What It Delivers |
|-------|-------|-----------------|
| 1 | 1-3 | Project structure, DB, config |
| 2 | 4-6 | SP-API, Firecrawl, Exa, fee calculator |
| 3 | 7 | CrewAI agents and WF1 crew |
| 4 | 8 | WhatsApp gateway bridge |
| 5 | 9-11 | WF1 workflow, scheduler, main.py |
| 6 | 12 | Docker deployment |
| 7 | 13-14 | Remaining workflows, integration tests |

**Total: 14 implementation tasks, ~3-4 weeks to complete.**

After Task 12, you will have a deployable system that can:
- Discover wholesale products via Exa + Firecrawl
- Match products to Amazon ASINs
- Check selling restrictions via SP-API
- Calculate profitability
- Send daily WhatsApp briefings
- Accept commands via WhatsApp

Workflows WF2-WF8 (Task 13) can be implemented incrementally as the business grows and you start actually purchasing inventory.
