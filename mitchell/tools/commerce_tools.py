"""Commerce tools for the Mitchell ToolRegistry exposing multi-platform product search, price tracking, and coupons."""

import json
from typing import Any, Dict, List, Optional

from mitchell.commerce import commerce_assistant, commerce_search, price_tracker
from mitchell.tools.registry import Tool


def tool_commerce_search_products(query: str) -> str:
    """Search for products across e-commerce marketplaces with price comparison."""
    listings = commerce_search.search_product(query=query)
    return json.dumps([l.model_dump() for l in listings], indent=2)


def tool_commerce_track_price(title: str, current_price: float, target_price: float, url: str) -> str:
    """Track a product for price drops."""
    item = price_tracker.track_product(title=title, current_price=current_price, target_price=target_price, url=url)
    return f"Tracking '{item.title}' — alert will trigger when price drops below ₹{target_price}."


def tool_commerce_find_coupons(store_name: str) -> str:
    """Find verified coupons and promo codes for an online store."""
    coupons = commerce_assistant.find_coupons(store_name=store_name)
    return json.dumps([c.model_dump() for c in coupons], indent=2)


# Tool definitions
search_products_tool = Tool(
    name="commerce_search_products",
    description="Search products across online marketplaces and compare prices in INR and USD.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Product search query"},
        },
        "required": ["query"],
    },
    function=tool_commerce_search_products,
)

track_price_tool = Tool(
    name="commerce_track_price_drop",
    description="Set an active price drop alert for a product.",
    parameters={
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Product title"},
            "current_price": {"type": "number", "description": "Current price in INR"},
            "target_price": {"type": "number", "description": "Alert target price in INR"},
            "url": {"type": "string", "description": "Product URL"},
        },
        "required": ["title", "current_price", "target_price", "url"],
    },
    function=tool_commerce_track_price,
)

find_coupons_tool = Tool(
    name="commerce_find_coupons",
    description="Search active promotional codes and coupons for an e-commerce platform.",
    parameters={
        "type": "object",
        "properties": {
            "store_name": {"type": "string", "description": "Store name (e.g. 'Amazon', 'Myntra')"},
        },
        "required": ["store_name"],
    },
    function=tool_commerce_find_coupons,
)

TOOLS = [
    search_products_tool,
    track_price_tool,
    find_coupons_tool,
]
