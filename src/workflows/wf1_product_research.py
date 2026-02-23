"""WF1: Product Research - Daily product discovery and analysis pipeline."""
import json
import os
from datetime import datetime

from agents.crew import create_product_research_crew
from gateway.openclaw_client import send_whatsapp_message
from gateway.message_templates import format_product_briefing
from db.database import get_engine, get_session_factory, Base
from db.models import Product, AmazonListing, Restriction, Profitability, DailyReport


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
