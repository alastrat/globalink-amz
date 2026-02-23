"""Application configuration."""
import os
from pathlib import Path
from dataclasses import dataclass
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
