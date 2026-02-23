from gateway.whatsapp_handler import parse_command, get_help_message


def test_parse_help():
    cmd, args = parse_command("help")
    assert cmd == "help"


def test_parse_details():
    cmd, args = parse_command("details 5")
    assert cmd == "product_details"
    assert args == ["5"]


def test_parse_buy():
    cmd, args = parse_command("buy 3")
    assert cmd == "create_po"
    assert args == ["3"]


def test_parse_inventory():
    cmd, args = parse_command("inventory")
    assert cmd == "inventory_report"


def test_parse_add_supplier():
    cmd, args = parse_command("add supplier https://example.com")
    assert cmd == "add_supplier"
    assert args == ["https://example.com"]


def test_parse_unknown():
    cmd, args = parse_command("something random")
    assert cmd == "unknown"


def test_help_message():
    msg = get_help_message()
    assert "Available commands" in msg
    assert "inventory" in msg
    assert "profit" in msg
