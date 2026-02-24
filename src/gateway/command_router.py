"""Route parsed WhatsApp commands to handler functions."""
from datetime import datetime, timedelta
from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from db.database import get_session_factory
from db.models import (
    Product, AmazonListing, Profitability, Supplier, SupplierProduct,
    PurchaseOrder, FBAShipment, PrepCenter, Inventory, PriceHistory,
    BuyBoxHistory, Return, FinancialTransaction,
)
from gateway.message_templates import (
    format_product_detail, format_draft_po, format_supplier_info,
    format_order_list, format_order_tracking, format_shipment_list,
    format_prep_status, format_prep_costs, format_inventory_report,
    format_buybox_report, format_restock_report, format_returns_report,
    format_health_report, format_profit_snapshot, format_pnl_snapshot,
    format_roi_detail, format_cashflow, format_price_comparison,
    format_price_history,
)
from gateway.openclaw_client import send_whatsapp_message

SessionFactory = get_session_factory()


def _get_db() -> Session:
    return SessionFactory()


# -- WF1: Product Research --

async def handle_product_details(args: list[str], to: str):
    index = int(args[0]) if args else 1
    db = _get_db()
    try:
        row = (
            db.query(Profitability, AmazonListing, Product)
            .join(Product, Profitability.product_id == Product.id)
            .outerjoin(AmazonListing, AmazonListing.product_id == Product.id)
            .order_by(desc(Profitability.calculated_at))
            .offset(index - 1)
            .first()
        )
        if not row:
            await send_whatsapp_message(to, f"No product found at position {index}.")
            return
        prof, listing, product = row
        data = {
            "index": index,
            "title": (listing.title if listing else None) or product.name,
            "asin": prof.asin or (listing.asin if listing else "N/A"),
            "upc": product.upc,
            "category": (listing.category if listing else None) or product.category,
            "brand": product.brand,
            "bsr": listing.bsr if listing else None,
            "wholesale_cost": prof.wholesale_cost,
            "amazon_price": prof.amazon_price,
            "referral_fee": prof.referral_fee,
            "fba_fee": prof.fba_fee,
            "prep_cost": prof.prep_cost,
            "shipping_cost": prof.shipping_cost,
            "profit_per_unit": prof.profit_per_unit,
            "roi_percent": prof.roi_percent,
            "fba_seller_count": listing.fba_seller_count if listing else None,
            "fbm_seller_count": listing.fbm_seller_count if listing else None,
            "has_amazon_offer": listing.has_amazon_offer if listing else None,
            "monthly_estimated_sales": prof.monthly_estimated_sales,
        }
        await send_whatsapp_message(to, format_product_detail(data))
    finally:
        db.close()


async def handle_create_po(args: list[str], to: str):
    index = int(args[0]) if args else 1
    db = _get_db()
    try:
        row = (
            db.query(Profitability, Product)
            .join(Product, Profitability.product_id == Product.id)
            .order_by(desc(Profitability.calculated_at))
            .offset(index - 1)
            .first()
        )
        if not row:
            await send_whatsapp_message(to, f"No product found at position {index}.")
            return
        prof, product = row
        # Find a supplier for this product
        sp = (
            db.query(SupplierProduct, Supplier)
            .join(Supplier, SupplierProduct.supplier_id == Supplier.id)
            .filter(SupplierProduct.product_id == product.id)
            .first()
        )
        supplier_name = sp[1].name if sp else "N/A"
        data = {
            "title": product.name,
            "asin": prof.asin,
            "supplier_name": supplier_name,
            "wholesale_cost": prof.wholesale_cost,
            "moq": product.moq,
            "case_pack": product.case_pack,
            "profit_per_unit": prof.profit_per_unit,
        }
        await send_whatsapp_message(to, format_draft_po(data))
    finally:
        db.close()


async def handle_add_supplier(args: list[str], to: str):
    url = args[0] if args else ""
    if not url:
        await send_whatsapp_message(to, "Please provide a supplier URL: add supplier [url]")
        return
    # For now, save a placeholder supplier. Full CrewAI scraping is a future workflow.
    db = _get_db()
    try:
        supplier = Supplier(name=f"New supplier from {url[:50]}", url=url, status="prospect")
        db.add(supplier)
        db.commit()
        await send_whatsapp_message(
            to,
            f"Supplier added (ID: {supplier.id})\nURL: {url}\n\n"
            f"Full catalog scraping will run in the next workflow cycle.",
        )
    finally:
        db.close()


# -- WF2: Supplier Mgmt --

async def handle_supplier_info(args: list[str], to: str):
    supplier_id = int(args[0]) if args else 1
    db = _get_db()
    try:
        supplier = db.query(Supplier).get(supplier_id)
        if not supplier:
            await send_whatsapp_message(to, f"Supplier #{supplier_id} not found.")
            return
        product_count = (
            db.query(func.count(SupplierProduct.id))
            .filter(SupplierProduct.supplier_id == supplier.id)
            .scalar()
        )
        data = {
            "name": supplier.name,
            "url": supplier.url,
            "contact_email": supplier.contact_email,
            "contact_phone": supplier.contact_phone,
            "payment_terms": supplier.payment_terms,
            "minimum_order": supplier.minimum_order,
            "status": supplier.status,
            "categories": supplier.categories,
            "product_count": product_count,
        }
        await send_whatsapp_message(to, format_supplier_info(data))
    finally:
        db.close()


# -- WF3: Orders --

async def handle_order_status(args: list[str], to: str):
    db = _get_db()
    try:
        orders = (
            db.query(PurchaseOrder, Supplier)
            .outerjoin(Supplier, PurchaseOrder.supplier_id == Supplier.id)
            .filter(PurchaseOrder.status != "delivered")
            .order_by(desc(PurchaseOrder.created_at))
            .all()
        )
        order_dicts = []
        for po, supplier in orders:
            order_dicts.append({
                "id": po.id,
                "status": po.status,
                "supplier_name": supplier.name if supplier else "N/A",
                "total_units": po.total_units,
                "total_cost": po.total_cost,
                "order_date": po.order_date.strftime("%m/%d/%Y") if po.order_date else None,
            })
        await send_whatsapp_message(to, format_order_list(order_dicts))
    finally:
        db.close()


async def handle_track_order(args: list[str], to: str):
    po_id = args[0] if args else ""
    db = _get_db()
    try:
        query = db.query(PurchaseOrder, Supplier).outerjoin(
            Supplier, PurchaseOrder.supplier_id == Supplier.id
        )
        if po_id.isdigit():
            query = query.filter(PurchaseOrder.id == int(po_id))
        else:
            query = query.filter(PurchaseOrder.tracking_number == po_id)
        row = query.first()
        if not row:
            await send_whatsapp_message(to, f"Order not found: {po_id}")
            return
        po, supplier = row
        data = {
            "id": po.id,
            "status": po.status,
            "supplier_name": supplier.name if supplier else "N/A",
            "total_units": po.total_units,
            "total_cost": po.total_cost,
            "order_date": po.order_date.strftime("%m/%d/%Y") if po.order_date else "N/A",
            "ship_date": po.ship_date.strftime("%m/%d/%Y") if po.ship_date else "N/A",
            "delivery_date": po.delivery_date.strftime("%m/%d/%Y") if po.delivery_date else "N/A",
            "tracking_number": po.tracking_number or "N/A",
        }
        await send_whatsapp_message(to, format_order_tracking(data))
    finally:
        db.close()


# -- WF4: Prep/Ship --

async def handle_inbound_status(args: list[str], to: str):
    db = _get_db()
    try:
        shipments = (
            db.query(FBAShipment)
            .order_by(desc(FBAShipment.updated_at))
            .limit(20)
            .all()
        )
        shipment_dicts = [
            {
                "shipment_id": s.shipment_id,
                "status": s.status,
                "destination_fc": s.destination_fc,
                "total_units": s.total_units,
                "tracking_number": s.tracking_number,
            }
            for s in shipments
        ]
        await send_whatsapp_message(to, format_shipment_list(shipment_dicts))
    finally:
        db.close()


async def handle_prep_status(args: list[str], to: str):
    db = _get_db()
    try:
        centers = db.query(PrepCenter).all()
        pending = (
            db.query(func.count(FBAShipment.id))
            .filter(FBAShipment.status.in_(["WORKING", "SHIPPED"]))
            .scalar()
        )
        data = {
            "centers": [
                {
                    "name": c.name,
                    "location": c.location,
                    "turnaround_days": c.turnaround_days,
                }
                for c in centers
            ],
            "pending_shipments": pending,
        }
        await send_whatsapp_message(to, format_prep_status(data))
    finally:
        db.close()


async def handle_prep_costs(args: list[str], to: str):
    db = _get_db()
    try:
        centers = db.query(PrepCenter).all()
        data = {
            "centers": [
                {
                    "name": c.name,
                    "label_fee": c.label_fee,
                    "polybag_fee": c.polybag_fee,
                    "inspection_fee": c.inspection_fee,
                    "bundle_fee": c.bundle_fee,
                    "storage_fee_monthly": c.storage_fee_monthly,
                }
                for c in centers
            ]
        }
        await send_whatsapp_message(to, format_prep_costs(data))
    finally:
        db.close()


# -- WF5: Inventory --

async def handle_inventory_report(args: list[str], to: str):
    db = _get_db()
    try:
        items = db.query(Inventory).order_by(Inventory.asin).all()
        item_dicts = [
            {
                "asin": i.asin,
                "fulfillable_qty": i.fulfillable_qty,
                "inbound_qty": i.inbound_qty,
                "restock_threshold": i.restock_threshold,
            }
            for i in items
        ]
        await send_whatsapp_message(to, format_inventory_report(item_dicts))
    finally:
        db.close()


async def handle_buybox_report(args: list[str], to: str):
    db = _get_db()
    try:
        # Latest entry per ASIN
        subq = (
            db.query(
                BuyBoxHistory.asin,
                func.max(BuyBoxHistory.id).label("max_id"),
            )
            .group_by(BuyBoxHistory.asin)
            .subquery()
        )
        entries = (
            db.query(BuyBoxHistory)
            .join(subq, BuyBoxHistory.id == subq.c.max_id)
            .all()
        )
        entry_dicts = [
            {
                "asin": e.asin,
                "is_ours": e.is_ours,
                "price": e.price,
                "winner_seller_id": e.winner_seller_id,
            }
            for e in entries
        ]
        await send_whatsapp_message(to, format_buybox_report(entry_dicts))
    finally:
        db.close()


async def handle_restock_report(args: list[str], to: str):
    db = _get_db()
    try:
        items = (
            db.query(Inventory)
            .filter(Inventory.fulfillable_qty < Inventory.restock_threshold)
            .order_by(Inventory.fulfillable_qty)
            .all()
        )
        item_dicts = [
            {
                "asin": i.asin,
                "fulfillable_qty": i.fulfillable_qty,
                "inbound_qty": i.inbound_qty,
                "restock_threshold": i.restock_threshold,
            }
            for i in items
        ]
        await send_whatsapp_message(to, format_restock_report(item_dicts))
    finally:
        db.close()


# -- WF6: Returns/Health --

async def handle_returns_report(args: list[str], to: str):
    db = _get_db()
    try:
        results = (
            db.query(
                Return.asin,
                func.sum(Return.quantity).label("total_qty"),
                Return.reason,
            )
            .group_by(Return.asin)
            .order_by(desc("total_qty"))
            .all()
        )
        return_dicts = [
            {"asin": r.asin, "total_qty": r.total_qty, "top_reason": r.reason}
            for r in results
        ]
        await send_whatsapp_message(to, format_returns_report(return_dicts))
    finally:
        db.close()


async def handle_health_report(args: list[str], to: str):
    db = _get_db()
    try:
        listing_count = db.query(func.count(AmazonListing.id)).scalar()
        low_stock = (
            db.query(func.count(Inventory.id))
            .filter(Inventory.fulfillable_qty < Inventory.restock_threshold)
            .scalar()
        )
        total_returns = db.query(func.coalesce(func.sum(Return.quantity), 0)).scalar()
        total_sold = (
            db.query(func.coalesce(func.sum(FinancialTransaction.amount), 0))
            .filter(FinancialTransaction.transaction_type == "sale")
            .scalar()
        )
        return_rate = 0.0
        if total_sold and total_sold > 0:
            return_rate = (total_returns / total_sold) * 100

        data = {
            "listing_count": listing_count,
            "low_stock_count": low_stock,
            "return_rate": return_rate,
            "total_returns": total_returns,
            "total_sold": total_sold,
        }
        await send_whatsapp_message(to, format_health_report(data))
    finally:
        db.close()


async def handle_reviews(args: list[str], to: str):
    asin = args[0] if args else "N/A"
    await send_whatsapp_message(
        to,
        f"Reviews for {asin}\n\nNot yet available. SP-API review access coming soon.",
    )


# -- WF7: Finance --

async def handle_profit_snapshot(args: list[str], to: str):
    db = _get_db()
    try:
        today = datetime.utcnow().date()
        start = datetime(today.year, today.month, today.day)
        end = start + timedelta(days=1)

        txns = (
            db.query(FinancialTransaction)
            .filter(
                FinancialTransaction.transaction_date >= start,
                FinancialTransaction.transaction_date < end,
            )
            .all()
        )
        if not txns:
            data = {"has_data": False}
        else:
            revenue = sum(t.amount for t in txns if t.amount > 0)
            expenses = abs(sum(t.amount for t in txns if t.amount < 0))
            data = {
                "has_data": True,
                "revenue": revenue,
                "expenses": expenses,
                "profit": revenue - expenses,
                "count": len(txns),
            }
        await send_whatsapp_message(to, format_profit_snapshot(data))
    finally:
        db.close()


async def handle_pnl_report(args: list[str], to: str):
    db = _get_db()
    try:
        today = datetime.utcnow().date()
        start = datetime(today.year, today.month, 1)

        txns = (
            db.query(FinancialTransaction)
            .filter(FinancialTransaction.transaction_date >= start)
            .all()
        )
        revenue = sum(t.amount for t in txns if t.transaction_type == "sale")
        cogs = abs(sum(t.amount for t in txns if t.transaction_type == "cogs"))
        fees = abs(sum(t.amount for t in txns if t.transaction_type == "fee"))
        profit = revenue - cogs - fees
        margin = (profit / revenue * 100) if revenue > 0 else 0.0

        data = {
            "period": f"{today.strftime('%B %Y')}",
            "revenue": revenue,
            "cogs": cogs,
            "fees": fees,
            "profit": profit,
            "margin_percent": margin,
        }
        await send_whatsapp_message(to, format_pnl_snapshot(data))
    finally:
        db.close()


async def handle_roi_detail(args: list[str], to: str):
    asin_or_id = args[0] if args else ""
    db = _get_db()
    try:
        query = db.query(Profitability, Product).join(
            Product, Profitability.product_id == Product.id
        )
        if asin_or_id.isdigit():
            query = query.filter(Profitability.id == int(asin_or_id))
        else:
            query = query.filter(Profitability.asin == asin_or_id.upper())

        row = query.order_by(desc(Profitability.calculated_at)).first()
        if not row:
            await send_whatsapp_message(
                to,
                format_roi_detail({"has_data": False, "asin": asin_or_id}),
            )
            return
        prof, product = row
        data = {
            "has_data": True,
            "asin": prof.asin,
            "title": product.name,
            "wholesale_cost": prof.wholesale_cost,
            "amazon_price": prof.amazon_price,
            "referral_fee": prof.referral_fee,
            "fba_fee": prof.fba_fee,
            "profit_per_unit": prof.profit_per_unit,
            "roi_percent": prof.roi_percent,
            "monthly_estimated_sales": prof.monthly_estimated_sales,
            "monthly_estimated_profit": prof.monthly_estimated_profit,
        }
        await send_whatsapp_message(to, format_roi_detail(data))
    finally:
        db.close()


async def handle_cashflow_report(args: list[str], to: str):
    db = _get_db()
    try:
        today = datetime.utcnow().date()
        start = datetime(today.year, today.month, 1)

        txns = (
            db.query(FinancialTransaction)
            .filter(FinancialTransaction.transaction_date >= start)
            .all()
        )
        if not txns:
            data = {"has_data": False}
        else:
            inflows = sum(t.amount for t in txns if t.amount > 0)
            outflows = abs(sum(t.amount for t in txns if t.amount < 0))
            data = {
                "has_data": True,
                "period": today.strftime("%B %Y"),
                "inflows": inflows,
                "outflows": outflows,
                "net": inflows - outflows,
            }
        await send_whatsapp_message(to, format_cashflow(data))
    finally:
        db.close()


# -- WF8: Price Intel --

async def handle_reprice(args: list[str], to: str):
    if len(args) < 2:
        await send_whatsapp_message(to, "Usage: reprice [ASIN] [price]")
        return
    asin = args[0].upper()
    price = float(args[1])
    db = _get_db()
    try:
        entry = PriceHistory(asin=asin, source="manual_target", price=price)
        db.add(entry)
        db.commit()
        await send_whatsapp_message(
            to,
            f"Target price set for {asin}: ${price:.2f}\n\n"
            f"Repricing automation will pick this up in the next cycle.",
        )
    finally:
        db.close()


async def handle_price_comparison(args: list[str], to: str):
    db = _get_db()
    try:
        # Latest price per (asin, source)
        subq = (
            db.query(
                PriceHistory.asin,
                PriceHistory.source,
                func.max(PriceHistory.id).label("max_id"),
            )
            .group_by(PriceHistory.asin, PriceHistory.source)
            .subquery()
        )
        entries = (
            db.query(PriceHistory)
            .join(subq, PriceHistory.id == subq.c.max_id)
            .order_by(PriceHistory.asin, PriceHistory.source)
            .all()
        )
        entry_dicts = [
            {"asin": e.asin, "source": e.source, "price": e.price}
            for e in entries
        ]
        await send_whatsapp_message(to, format_price_comparison(entry_dicts))
    finally:
        db.close()


async def handle_price_history(args: list[str], to: str):
    asin = args[0].upper() if args else ""
    if not asin:
        await send_whatsapp_message(to, "Usage: price history [ASIN]")
        return
    db = _get_db()
    try:
        entries = (
            db.query(PriceHistory)
            .filter(PriceHistory.asin == asin)
            .order_by(desc(PriceHistory.recorded_at))
            .limit(7)
            .all()
        )
        entry_dicts = [
            {
                "recorded_at": e.recorded_at,
                "source": e.source,
                "price": e.price,
            }
            for e in reversed(entries)
        ]
        await send_whatsapp_message(to, format_price_history(asin, entry_dicts))
    finally:
        db.close()


# -- Command routing table --

COMMAND_HANDLERS = {
    "product_details": handle_product_details,
    "create_po": handle_create_po,
    "add_supplier": handle_add_supplier,
    "supplier_info": handle_supplier_info,
    "order_status": handle_order_status,
    "track_order": handle_track_order,
    "inbound_status": handle_inbound_status,
    "prep_status": handle_prep_status,
    "prep_costs": handle_prep_costs,
    "inventory_report": handle_inventory_report,
    "buybox_report": handle_buybox_report,
    "restock_report": handle_restock_report,
    "returns_report": handle_returns_report,
    "health_report": handle_health_report,
    "reviews": handle_reviews,
    "profit_snapshot": handle_profit_snapshot,
    "pnl_report": handle_pnl_report,
    "roi_detail": handle_roi_detail,
    "cashflow_report": handle_cashflow_report,
    "reprice": handle_reprice,
    "price_comparison": handle_price_comparison,
    "price_history": handle_price_history,
}


async def route_command(command: str, args: list[str], to: str):
    """Route a command to its handler. Returns True if handled."""
    handler = COMMAND_HANDLERS.get(command)
    if handler:
        await handler(args, to)
        return True
    return False
