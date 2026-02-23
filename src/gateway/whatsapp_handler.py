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
