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


def format_product_detail(p: dict) -> str:
    """Format a single product deep-dive card."""
    bsr = p.get("bsr")
    bsr_str = f"{bsr:,}" if isinstance(bsr, (int, float)) else "N/A"
    total_fees = (p.get("referral_fee", 0) or 0) + (p.get("fba_fee", 0) or 0)
    lines = [
        f"Product Detail\n",
        f"{p.get('title', 'Unknown')}\n",
        f"ASIN: {p.get('asin', 'N/A')}",
        f"UPC:  {p.get('upc', 'N/A')}",
        f"BSR:  {bsr_str} in {p.get('category', 'N/A')}",
        f"Brand: {p.get('brand', 'N/A')}",
        f"",
        f"Wholesale: ${p.get('wholesale_cost', 0):.2f}",
        f"Amazon:    ${p.get('amazon_price', 0):.2f}",
        f"Referral:  ${p.get('referral_fee', 0) or 0:.2f}",
        f"FBA Fee:   ${p.get('fba_fee', 0) or 0:.2f}",
        f"Prep:      ${p.get('prep_cost', 0) or 0:.2f}",
        f"Shipping:  ${p.get('shipping_cost', 0) or 0:.2f}",
        f"Profit:    ${p.get('profit_per_unit', 0) or 0:.2f}/unit",
        f"ROI:       {p.get('roi_percent', 0) or 0:.0f}%",
        f"",
        f"FBA Sellers: {p.get('fba_seller_count', 'N/A')}",
        f"FBM Sellers: {p.get('fbm_seller_count', 'N/A')}",
        f"Amazon Offer: {'Yes' if p.get('has_amazon_offer') else 'No'}",
        f"Est. Sales: {p.get('monthly_estimated_sales', 'N/A')}/mo",
        f"",
        f'Reply "buy {p.get("index", "N")}" to draft a PO',
    ]
    return "\n".join(lines)


def format_draft_po(p: dict) -> str:
    """Format a draft purchase order preview."""
    lines = [
        f"Draft Purchase Order\n",
        f"Product: {p.get('title', 'Unknown')[:60]}",
        f"ASIN:    {p.get('asin', 'N/A')}",
        f"",
        f"Supplier:  {p.get('supplier_name', 'N/A')}",
        f"Unit Cost: ${p.get('wholesale_cost', 0):.2f}",
        f"MOQ:       {p.get('moq', 'N/A')} units",
        f"Case Pack: {p.get('case_pack', 'N/A')}",
        f"",
        f"Est. Total: ${(p.get('wholesale_cost', 0) or 0) * (p.get('moq', 0) or 0):.2f}",
        f"Est. Profit: ${(p.get('profit_per_unit', 0) or 0) * (p.get('moq', 0) or 0):.2f}",
        f"",
        f"This is a preview only. Full PO workflow coming soon.",
    ]
    return "\n".join(lines)


def format_supplier_info(s: dict) -> str:
    """Format a supplier info card."""
    lines = [
        f"Supplier: {s.get('name', 'Unknown')}\n",
        f"URL:      {s.get('url', 'N/A')}",
        f"Email:    {s.get('contact_email', 'N/A')}",
        f"Phone:    {s.get('contact_phone', 'N/A')}",
        f"Payment:  {s.get('payment_terms', 'N/A')}",
        f"Min Order: ${s.get('minimum_order', 0) or 0:,.2f}",
        f"Status:   {s.get('status', 'N/A')}",
        f"Products: {s.get('product_count', 0)}",
    ]
    if s.get("categories"):
        lines.append(f"Categories: {s['categories']}")
    return "\n".join(lines)


def format_order_list(orders: list[dict]) -> str:
    """Format active purchase orders."""
    if not orders:
        return "Active Orders\n\nNo active orders."

    lines = ["Active Orders\n"]
    for o in orders:
        lines.append(f"PO #{o.get('id', '?')} - {o.get('status', 'unknown')}")
        lines.append(f"  Supplier: {o.get('supplier_name', 'N/A')}")
        lines.append(f"  Units: {o.get('total_units', 0)} | Cost: ${o.get('total_cost', 0) or 0:,.2f}")
        if o.get("order_date"):
            lines.append(f"  Ordered: {o['order_date']}")
        lines.append("")
    lines.append('Reply "track [PO#]" for tracking details')
    return "\n".join(lines)


def format_order_tracking(o: dict) -> str:
    """Format single order tracking details."""
    lines = [
        f"Order Tracking - PO #{o.get('id', '?')}\n",
        f"Status:   {o.get('status', 'unknown')}",
        f"Supplier: {o.get('supplier_name', 'N/A')}",
        f"Units:    {o.get('total_units', 0)}",
        f"Cost:     ${o.get('total_cost', 0) or 0:,.2f}",
        f"",
        f"Ordered:    {o.get('order_date', 'N/A')}",
        f"Shipped:    {o.get('ship_date', 'N/A')}",
        f"Delivery:   {o.get('delivery_date', 'N/A')}",
        f"Tracking #: {o.get('tracking_number', 'N/A')}",
    ]
    return "\n".join(lines)


def format_shipment_list(shipments: list[dict]) -> str:
    """Format FBA inbound shipments."""
    if not shipments:
        return "FBA Inbound Shipments\n\nNo inbound shipments."

    lines = ["FBA Inbound Shipments\n"]
    for s in shipments:
        lines.append(f"- {s.get('shipment_id', '?')} [{s.get('status', '?')}]")
        lines.append(f"  FC: {s.get('destination_fc', 'N/A')} | Units: {s.get('total_units', 0)}")
        if s.get("tracking_number"):
            lines.append(f"  Tracking: {s['tracking_number']}")
    return "\n".join(lines)


def format_prep_status(prep: dict) -> str:
    """Format prep center queue status."""
    if not prep.get("centers"):
        return "Prep Status\n\nNo prep center configured."

    lines = ["Prep Status\n"]
    for c in prep["centers"]:
        lines.append(f"{c.get('name', 'Unknown')} ({c.get('location', '?')})")
        lines.append(f"  Turnaround: {c.get('turnaround_days', '?')} days")
    if prep.get("pending_shipments"):
        lines.append(f"\nPending Shipments: {prep['pending_shipments']}")
    else:
        lines.append("\nNo pending shipments in prep.")
    return "\n".join(lines)


def format_prep_costs(costs: dict) -> str:
    """Format prep cost breakdown."""
    if not costs.get("centers"):
        return "Prep Costs\n\nNo prep center configured."

    lines = ["Prep Cost Breakdown\n"]
    for c in costs["centers"]:
        lines.append(f"{c.get('name', 'Unknown')}:")
        lines.append(f"  Label:      ${c.get('label_fee', 0) or 0:.2f}/unit")
        lines.append(f"  Polybag:    ${c.get('polybag_fee', 0) or 0:.2f}/unit")
        lines.append(f"  Inspection: ${c.get('inspection_fee', 0) or 0:.2f}/unit")
        lines.append(f"  Bundle:     ${c.get('bundle_fee', 0) or 0:.2f}/unit")
        lines.append(f"  Storage:    ${c.get('storage_fee_monthly', 0) or 0:.2f}/mo")
        lines.append("")
    return "\n".join(lines)


def format_buybox_report(entries: list[dict]) -> str:
    """Format Buy Box win/loss per ASIN."""
    if not entries:
        return "Buy Box Report\n\nNo Buy Box data recorded."

    lines = ["Buy Box Report\n"]
    for e in entries:
        status = "WON" if e.get("is_ours") else "LOST"
        lines.append(f"- {e.get('asin', 'N/A')}: [{status}] ${e.get('price', 0) or 0:.2f}")
        if not e.get("is_ours") and e.get("winner_seller_id"):
            lines.append(f"  Winner: {e['winner_seller_id']}")
    return "\n".join(lines)


def format_restock_report(items: list[dict]) -> str:
    """Format reorder suggestions for low-stock ASINs."""
    if not items:
        return "Restock Report\n\nAll inventory levels OK."

    lines = ["Restock Report - Low Stock\n"]
    for item in items:
        lines.append(f"- {item.get('asin', 'N/A')}: {item.get('fulfillable_qty', 0)} units")
        lines.append(f"  Threshold: {item.get('restock_threshold', 10)} | Inbound: {item.get('inbound_qty', 0)}")
    return "\n".join(lines)


def format_returns_report(returns: list[dict]) -> str:
    """Format return rates grouped by ASIN."""
    if not returns:
        return "Returns Report\n\nNo returns recorded."

    lines = ["Returns Report\n"]
    for r in returns:
        lines.append(f"- {r.get('asin', 'N/A')}: {r.get('total_qty', 0)} units returned")
        if r.get("top_reason"):
            lines.append(f"  Top reason: {r['top_reason']}")
    return "\n".join(lines)


def format_health_report(data: dict) -> str:
    """Format account health summary."""
    lines = [
        "Account Health Summary\n",
        f"Active Listings: {data.get('listing_count', 0)}",
        f"Low Stock ASINs: {data.get('low_stock_count', 0)}",
        f"Return Rate:     {data.get('return_rate', 0):.1f}%",
        f"Total Returns:   {data.get('total_returns', 0)}",
        f"Total Sold:      {data.get('total_sold', 0)}",
    ]
    return "\n".join(lines)


def format_profit_snapshot(data: dict) -> str:
    """Format today's profit summary."""
    if not data.get("has_data"):
        return "Today's Profit\n\nNo transactions recorded today."

    lines = [
        "Today's Profit\n",
        f"Revenue:  ${data.get('revenue', 0):,.2f}",
        f"Expenses: ${data.get('expenses', 0):,.2f}",
        f"Profit:   ${data.get('profit', 0):,.2f}",
        f"Transactions: {data.get('count', 0)}",
    ]
    return "\n".join(lines)


def format_roi_detail(data: dict) -> str:
    """Format single product ROI breakdown."""
    if not data.get("has_data"):
        return f"ROI Detail\n\nNo profitability data for {data.get('asin', 'this ASIN')}."

    lines = [
        f"ROI Detail - {data.get('asin', 'N/A')}\n",
        f"Product:   {data.get('title', 'N/A')}",
        f"Wholesale: ${data.get('wholesale_cost', 0):.2f}",
        f"Amazon:    ${data.get('amazon_price', 0):.2f}",
        f"Fees:      ${(data.get('referral_fee', 0) or 0) + (data.get('fba_fee', 0) or 0):.2f}",
        f"Profit:    ${data.get('profit_per_unit', 0) or 0:.2f}/unit",
        f"ROI:       {data.get('roi_percent', 0) or 0:.0f}%",
        f"Est. Monthly Sales:  {data.get('monthly_estimated_sales', 'N/A')}",
        f"Est. Monthly Profit: ${data.get('monthly_estimated_profit', 0) or 0:,.2f}",
    ]
    return "\n".join(lines)


def format_cashflow(data: dict) -> str:
    """Format money in/out summary."""
    if not data.get("has_data"):
        return "Cash Flow Report\n\nNo transactions this month."

    lines = [
        f"Cash Flow - {data.get('period', 'This Month')}\n",
        f"Inflows:  ${data.get('inflows', 0):,.2f}",
        f"Outflows: ${data.get('outflows', 0):,.2f}",
        f"Net:      ${data.get('net', 0):,.2f}",
    ]
    return "\n".join(lines)


def format_price_comparison(entries: list[dict]) -> str:
    """Format multi-source price table."""
    if not entries:
        return "Price Comparison\n\nNo price data recorded."

    lines = ["Price Comparison\n"]
    current_asin = None
    for e in entries:
        if e.get("asin") != current_asin:
            current_asin = e.get("asin")
            lines.append(f"\n{current_asin}:")
        lines.append(f"  {e.get('source', '?'):12s} ${e.get('price', 0):.2f}")
    return "\n".join(lines)


def format_price_history(asin: str, entries: list[dict]) -> str:
    """Format ASIN price trend (last 7 entries)."""
    if not entries:
        return f"Price History - {asin}\n\nNo price data for this ASIN."

    lines = [f"Price History - {asin}\n"]
    for e in entries:
        date_str = e.get("recorded_at", "?")
        if hasattr(date_str, "strftime"):
            date_str = date_str.strftime("%m/%d %H:%M")
        lines.append(f"  {date_str}  {e.get('source', '?'):10s}  ${e.get('price', 0):.2f}")
    return "\n".join(lines)
