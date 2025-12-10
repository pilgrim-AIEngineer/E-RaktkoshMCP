from fastmcp import FastMCP, Context
from dotenv import load_dotenv
import os
import json
from contextlib import asynccontextmanager
from typing import Dict, List

from models import BloodGroup, StockResult
from scraper import ERaktKoshScraper
from utils import save_hierarchy, load_hierarchy, fuzzy_match_state, fuzzy_match_district
from graph import app as agent_graph
import sys
import subprocess
from fastmcp import FastMCP

# --- ADD THIS BLOCK START ---
try:
    from playwright.sync_api import sync_playwright
    # Dry run to check if browsers are installed
    with sync_playwright() as p:
        p.chromium.launch()
except Exception:
    print("⚠️ Playwright browsers not found. Installing chromium...")
    # Force install Chromium inside the cloud environment
    subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])

# Load environment variables
load_dotenv()

# Global state
scraper = ERaktKoshScraper()
hierarchy_cache = {}

@asynccontextmanager
async def lifespan(server: FastMCP):
    """
    Lifespan manager for the FastMCP server.
    Handles cache warming and browser initialization.
    """
    global hierarchy_cache
    
    # 1. Initialize Scraper
    await scraper.start()
    
    # 2. Check Cache
    hierarchy_cache = load_hierarchy()
    
    if not hierarchy_cache or not hierarchy_cache.get("states"):
        print("Cache miss or empty. Warming up hierarchy cache (Cold Path)...")
        try:
            hierarchy_cache = await scraper.get_hierarchy()
            save_hierarchy(hierarchy_cache)
            print("Cache warming complete.")
        except Exception as e:
            print(f"Failed to warm cache: {e}")
    else:
        print("Cache hit. Loaded hierarchy from disk.")
        
    yield
    
    # Cleanup
    await scraper.stop()

# Initialize FastMCP server
mcp = FastMCP("eRaktKosh Agent", lifespan=lifespan)

@mcp.resource("eraktkosh://locations")
def get_locations() -> str:
    """Returns the cached State-District hierarchy."""
    return json.dumps(hierarchy_cache, indent=2)

# Logic functions (exposed for testing)
async def _normalize_location(location_query: str) -> Dict[str, str]:
    states = hierarchy_cache.get("states", {})
    districts_map = hierarchy_cache.get("districts", {})
    
    # Try State
    s_id, s_name, s_score = fuzzy_match_state(location_query, states)
    if s_score > 80:
        return {
            "type": "State",
            "name": s_name,
            "code": s_id,
            "confidence": str(s_score)
        }
        
    # Try District
    best_d_score = 0
    best_result = None
    
    for s_id, d_map in districts_map.items():
        d_id, d_name, d_score = fuzzy_match_district(location_query, d_map)
        if d_score > best_d_score:
            best_d_score = d_score
            best_result = {
                "type": "District",
                "name": d_name,
                "code": d_id,
                "state_code": s_id,
                "state_name": states.get(s_id),
                "confidence": str(d_score)
            }
            
    if best_d_score > 80:
        return best_result
        
    return {"error": "Location not found", "confidence": str(max(s_score, best_d_score))}

async def _fetch_stock(location_query: str, blood_group: str, blood_component: str = "Packed Red Blood Cells") -> str:
    # 1. Normalize Blood Group and Component
    # Handle explicit None passed from tool wrapper
    if blood_component is None:
        blood_component = "Packed Red Blood Cells"

    bg_code = blood_group
    bc_code = blood_component
    
    cached_bgs = hierarchy_cache.get("blood_groups", {})
    cached_bcs = hierarchy_cache.get("blood_components", {})

    # Simple fuzzy match for BG if available
    if cached_bgs:
        for bid, bname in cached_bgs.items():
            if blood_group.lower() in bname.lower() or bname.lower() in blood_group.lower():
                bg_code = bid
                break
    
    # Simple fuzzy match for BC if available
    if blood_component and cached_bcs:
        for cid, cname in cached_bcs.items():
            if blood_component.lower() in cname.lower() or cname.lower() in blood_component.lower():
                bc_code = cid
                break

    initial_state = {
        "messages": [],
        "location_query": location_query,
        "blood_group_query": blood_group,
        "blood_component_query": blood_component,
        "normalized_bg_code": bg_code,
        "normalized_bc_code": bc_code,
        "hierarchy": hierarchy_cache
    }
    
    result = await agent_graph.ainvoke(initial_state)
    
    if result.get("error"):
        return f"Error: {result['error']}"
        
    stock = result.get("stock_results")
    if stock:
        return json.dumps([s.model_dump() for s in stock], indent=2)
        
    return "No stock found."

@mcp.tool()
async def normalize_location(location_query: str) -> Dict[str, str]:
    """
    Normalizes a location string (State or District) to internal codes.
    Uses fuzzy matching against the cached hierarchy.
    """
    return await _normalize_location(location_query)

@mcp.tool()
async def fetch_stock(location_query: str, blood_group: str, blood_component: str = None) -> str:
    """
    Fetches real-time blood stock availability.
    
    Args:
        location_query: City, District, or State name (e.g., "Pune", "Delhi")
        blood_group: Blood group name (e.g., "O+", "A Positive")
        blood_component: Optional blood component (e.g., "Whole Blood", "Plasma", "Platelets")
    """
    return await _fetch_stock(location_query, blood_group, blood_component)

if __name__ == "__main__":
    mcp.run(transport='stdio')
