from config.settings import Settings, load_agent_config, load_filter_config, load_schedule_config


def test_settings_defaults():
    s = Settings()
    assert s.min_roi_percent == 30.0
    assert s.min_profit_per_unit == 3.0
    assert s.max_fba_sellers == 20
    assert s.timezone == "America/Bogota"


def test_load_agent_config():
    config = load_agent_config()
    assert "product_scout" in config
    assert "restriction_checker" in config
    assert config["product_scout"]["llm"] == "anthropic/claude-haiku-4-5-20251001"


def test_load_filter_config():
    config = load_filter_config()
    assert "excluded_categories" in config
    assert "hazmat" in [c.lower() for c in config["excluded_categories"]]


def test_load_schedule_config():
    config = load_schedule_config()
    assert "wf1_product_research" in config
