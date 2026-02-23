"""WF7: Finance - Daily P&L snapshots and weekly financial reports."""
import os
from gateway.openclaw_client import send_whatsapp_message


async def run_finance_daily():
    """Execute daily financial snapshot."""
    owner = os.getenv("OWNER_WHATSAPP_NUMBER", "")
    # TODO: Implement full workflow
    # - Calculate daily revenue, COGS, fees, profit
    # - Save to financial_transactions table
    # - Send P&L snapshot via WhatsApp
    await send_whatsapp_message(owner, "Daily finance snapshot completed.")


async def run_finance_weekly():
    """Execute weekly P&L report."""
    owner = os.getenv("OWNER_WHATSAPP_NUMBER", "")
    # TODO: Implement full workflow
    # - Aggregate weekly financials
    # - Compare to previous week
    # - Send detailed P&L report
    await send_whatsapp_message(owner, "Weekly P&L report completed.")
