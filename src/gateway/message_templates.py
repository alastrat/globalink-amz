"""WhatsApp message formatting templates."""


def format_product_briefing(products: list[dict], date: str) -> str:
    """Format the daily product research briefing."""
    if not products:
        return f"Daily FBA Opportunities - {date}\n\nNo new opportunities found today."

    lines = [f"Daily FBA Opportunities - {date}\n"]
    for i, p in enumerate(products[:10], 1):
        lines.append(f"{i}. {p.get('title', 'Unknown')[:50]}")
        bsr = p.get("bsr")
        bsr_str = f"{bsr:,}" if isinstance(bsr, (int, float)) else "N/A"
        lines.append(f"   ASIN: {p.get('asin', 'N/A')} | BSR: {bsr_str}")
        lines.append(f"   Wholesale: ${p.get('wholesale_cost', 0):.2f} | Amazon: ${p.get('amazon_price', 0):.2f}")
        lines.append(f"   Fees: ${p.get('total_fees', 0):.2f} | Profit: ${p.get('profit_per_unit', 0):.2f}/unit")
        lines.append(f"   ROI: {p.get('roi_percent', 0):.0f}% | Sellers: {p.get('fba_sellers', 'N/A')} FBA")
        lines.append(f"   {'UNGATED' if not p.get('restricted') else 'GATED'} | {p.get('supplier_name', 'N/A')}")
        lines.append("")

    lines.append("Reply:")
    lines.append('- "details N" - full product breakdown')
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
