"""APScheduler job definitions for all workflow triggers."""
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

    # WF7: Finance - Daily snapshot
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
