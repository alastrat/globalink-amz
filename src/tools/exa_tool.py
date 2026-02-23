"""Exa tool for AI-powered web search and supplier discovery."""
import os
from exa_py import Exa


def _get_client() -> Exa:
    return Exa(api_key=os.getenv("EXA_API_KEY"))


def search_wholesale_suppliers(query: str, num_results: int = 10) -> list[dict]:
    """Search for wholesale suppliers using AI-powered search."""
    exa = _get_client()
    results = exa.search_and_contents(
        query,
        num_results=num_results,
        type="neural",
        use_autoprompt=True,
        text={"max_characters": 1500},
        summary=True,
    )
    return [
        {
            "title": r.title,
            "url": r.url,
            "summary": getattr(r, "summary", None),
            "score": r.score,
        }
        for r in results.results
    ]


def find_similar_suppliers(supplier_url: str, num_results: int = 10) -> list[dict]:
    """Find suppliers similar to a known one."""
    exa = _get_client()
    results = exa.find_similar_and_contents(
        url=supplier_url,
        num_results=num_results,
        text={"max_characters": 1000},
        summary=True,
        exclude_source_domain=True,
    )
    return [
        {
            "title": r.title,
            "url": r.url,
            "summary": getattr(r, "summary", None),
        }
        for r in results.results
    ]


def search_product_market(query: str, num_results: int = 10) -> list[dict]:
    """Search for market intelligence on a product category."""
    exa = _get_client()
    results = exa.search_and_contents(
        query,
        num_results=num_results,
        type="neural",
        text={"max_characters": 2000},
        summary=True,
    )
    return [
        {
            "title": r.title,
            "url": r.url,
            "summary": getattr(r, "summary", None),
        }
        for r in results.results
    ]
