"""CrewAI agent and crew definitions for Amazon FBA workflows."""
import os
from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type

from config.settings import load_agent_config
from tools.amazon_sp_api import (
    check_restriction, estimate_fees, get_product_details,
    get_competitive_pricing, search_catalog_by_upc,
)
from tools.firecrawl_tool import scrape_supplier_catalog
from tools.exa_tool import search_wholesale_suppliers
from tools.fee_calculator import calculate_profitability


# -- CrewAI Tool Wrappers --


class SearchSuppliersInput(BaseModel):
    query: str = Field(..., description="Search query for finding wholesale suppliers")

class SearchSuppliersTool(BaseTool):
    name: str = "Search Wholesale Suppliers"
    description: str = "Search the web for wholesale suppliers and distributors using AI-powered search"
    args_schema: Type[BaseModel] = SearchSuppliersInput
    def _run(self, query: str) -> str:
        results = search_wholesale_suppliers(query)
        return str(results)


class ScrapeSupplierInput(BaseModel):
    url: str = Field(..., description="URL of the supplier catalog page to scrape")

class ScrapeSupplierTool(BaseTool):
    name: str = "Scrape Supplier Catalog"
    description: str = "Scrape a wholesale supplier website to extract product catalog data"
    args_schema: Type[BaseModel] = ScrapeSupplierInput
    def _run(self, url: str) -> str:
        result = scrape_supplier_catalog(url)
        return str(result)


class UPCLookupInput(BaseModel):
    upc: str = Field(..., description="UPC barcode to search on Amazon")

class UPCLookupTool(BaseTool):
    name: str = "UPC to ASIN Lookup"
    description: str = "Search Amazon catalog by UPC code to find matching ASINs"
    args_schema: Type[BaseModel] = UPCLookupInput
    def _run(self, upc: str) -> str:
        results = search_catalog_by_upc(upc)
        return str(results)


class ProductDetailInput(BaseModel):
    asin: str = Field(..., description="Amazon ASIN to look up")

class ProductDetailTool(BaseTool):
    name: str = "Get Amazon Product Details"
    description: str = "Get product details from Amazon catalog including title, brand, BSR"
    args_schema: Type[BaseModel] = ProductDetailInput
    def _run(self, asin: str) -> str:
        result = get_product_details(asin)
        return str(result)


class RestrictionCheckInput(BaseModel):
    asin: str = Field(..., description="Amazon ASIN to check restrictions for")

class RestrictionCheckTool(BaseTool):
    name: str = "Check Amazon Selling Restriction"
    description: str = "Check if our seller account is allowed to sell a specific ASIN on Amazon"
    args_schema: Type[BaseModel] = RestrictionCheckInput
    def _run(self, asin: str) -> str:
        seller_id = os.getenv("AMAZON_SELLER_ID", "")
        result = check_restriction(asin, seller_id)
        return str(result)


class FeeEstimateInput(BaseModel):
    asin: str = Field(..., description="Amazon ASIN")
    price: float = Field(..., description="Selling price in USD")

class FeeEstimateTool(BaseTool):
    name: str = "Estimate Amazon FBA Fees"
    description: str = "Get estimated FBA fees (referral fee + fulfillment fee) for an ASIN at a given price"
    args_schema: Type[BaseModel] = FeeEstimateInput
    def _run(self, asin: str, price: float) -> str:
        result = estimate_fees(asin, price)
        return str(result)


class PricingInput(BaseModel):
    asins: str = Field(..., description="Comma-separated list of ASINs (max 20)")

class CompetitivePricingTool(BaseTool):
    name: str = "Get Competitive Pricing"
    description: str = "Get Buy Box price, seller count, and BSR for Amazon ASINs"
    args_schema: Type[BaseModel] = PricingInput
    def _run(self, asins: str) -> str:
        asin_list = [a.strip() for a in asins.split(",")]
        result = get_competitive_pricing(asin_list)
        return str(result)


class ProfitCalcInput(BaseModel):
    wholesale_cost: float = Field(..., description="Wholesale cost per unit")
    amazon_price: float = Field(..., description="Amazon selling price")
    referral_fee: float = Field(..., description="Amazon referral fee")
    fba_fee: float = Field(..., description="FBA fulfillment fee")

class ProfitCalculatorTool(BaseTool):
    name: str = "Calculate Profitability"
    description: str = "Calculate ROI and profit per unit for a product"
    args_schema: Type[BaseModel] = ProfitCalcInput
    def _run(self, wholesale_cost: float, amazon_price: float, referral_fee: float, fba_fee: float) -> str:
        result = calculate_profitability(wholesale_cost, amazon_price, referral_fee, fba_fee)
        return str(result)


# -- Agent Factory --


def _make_agent(config: dict, tools: list = None) -> Agent:
    return Agent(
        role=config["role"],
        goal=config["goal"],
        backstory=config["backstory"],
        llm=config["llm"],
        tools=tools or [],
        verbose=True,
        memory=True,
        max_iter=config.get("max_iter", 5),
        allow_delegation=config.get("allow_delegation", False),
    )


# -- Crew Builders --


def create_product_research_crew(supplier_data: str = "") -> Crew:
    """Create the WF1 Product Research crew."""
    agent_config = load_agent_config()

    scout = _make_agent(agent_config["product_scout"], [SearchSuppliersTool(), ScrapeSupplierTool()])
    matcher = _make_agent(agent_config["asin_matcher"], [UPCLookupTool(), ProductDetailTool()])
    checker = _make_agent(agent_config["restriction_checker"], [RestrictionCheckTool()])
    finance = _make_agent(agent_config["financial_analyst"], [FeeEstimateTool(), ProfitCalculatorTool()])
    market = _make_agent(agent_config["market_analyst"], [CompetitivePricingTool()])

    scout_task = Task(
        description=(
            "Discover wholesale products to analyze. "
            f"Supplier data provided: {supplier_data or 'None - search for new suppliers'}. "
            "Find products with UPC codes and wholesale prices. "
            "Focus on: home & kitchen, toys, pet supplies, office products. "
            "Avoid: hazmat, supplements, clothing, electronics. "
            "Return a list of products with: name, UPC, wholesale price, category, supplier."
        ),
        expected_output="JSON list of products with name, upc, wholesale_price, category, supplier_name, supplier_url",
        agent=scout,
    )

    match_task = Task(
        description=(
            "For each product from the scout, find matching Amazon ASINs. "
            "Use UPC codes to look up ASINs. For each match, get the product title, brand, and BSR. "
            "Skip products that have no Amazon match."
        ),
        expected_output="JSON list of matched products with: name, upc, asin, title, brand, bsr, wholesale_price",
        agent=matcher,
        context=[scout_task],
    )

    restrict_task = Task(
        description=(
            "For each matched ASIN, check if our seller account is restricted from selling it. "
            "Filter out all restricted ASINs. "
            "Flag ASINs that require approval but could potentially be unlocked."
        ),
        expected_output="JSON list of UNRESTRICTED products with: asin, title, wholesale_price, restriction_status",
        agent=checker,
        context=[match_task],
    )

    finance_task = Task(
        description=(
            "For each unrestricted product, calculate profitability: "
            "1. Get FBA fee estimate from Amazon. "
            "2. Calculate: profit = amazon_price - wholesale_cost - fba_fees - prep($1.50) - shipping($0.80). "
            "3. Calculate ROI% = profit / total_cost * 100. "
            "4. Filter: keep only products with ROI >= 30% AND profit >= $3/unit. "
            "Rank by ROI descending."
        ),
        expected_output="JSON list of profitable products ranked by ROI with full financial breakdown",
        agent=finance,
        context=[restrict_task],
    )

    market_task = Task(
        description=(
            "For each profitable product, evaluate market dynamics: "
            "1. Check BSR (lower = better demand, ideal < 100,000). "
            "2. Count FBA sellers (fewer = less competition, max 20). "
            "3. Check if Amazon itself sells the product (avoid if yes). "
            "4. Score each product: demand_score (1-10) and competition_score (1-10). "
            "5. Final rank = ROI * demand_score / competition_score. "
            "Return top 20 products."
        ),
        expected_output="JSON list of top 20 products with full analysis: financials, market scores, final rank",
        agent=market,
        context=[finance_task],
    )

    return Crew(
        agents=[scout, matcher, checker, finance, market],
        tasks=[scout_task, match_task, restrict_task, finance_task, market_task],
        process=Process.sequential,
        memory=True,
        verbose=True,
    )
