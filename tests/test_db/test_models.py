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
