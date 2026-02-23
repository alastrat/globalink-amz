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
    moq = Column(Integer)
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
    bsr = Column(Integer)
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
    categories = Column(Text)
    payment_terms = Column(String(100))
    minimum_order = Column(Float)
    notes = Column(Text)
    status = Column(String(50), default="prospect")
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
    label_fee = Column(Float)
    polybag_fee = Column(Float)
    inspection_fee = Column(Float)
    bundle_fee = Column(Float)
    storage_fee_monthly = Column(Float)
    turnaround_days = Column(Integer)
    contact_email = Column(String(300))
    notes = Column(Text)
    status = Column(String(50), default="prospect")


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"))
    status = Column(String(50), default="draft")
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
    shipment_id = Column(String(100), unique=True)
    status = Column(String(50))
    destination_fc = Column(String(20))
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
    source = Column(String(50), nullable=False)
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
    report_type = Column(String(50), nullable=False)
    content = Column(Text)
    products_analyzed = Column(Integer)
    opportunities_found = Column(Integer)
    sent_at = Column(DateTime, default=datetime.utcnow)


class FinancialTransaction(Base):
    __tablename__ = "financial_transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_type = Column(String(50), nullable=False)
    asin = Column(String(20))
    amount = Column(Float, nullable=False)
    description = Column(Text)
    reference_id = Column(String(200))
    transaction_date = Column(DateTime, default=datetime.utcnow)
