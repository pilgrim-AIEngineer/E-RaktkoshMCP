from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from models import BloodGroup, StockResult
from utils import fuzzy_match_state, fuzzy_match_district
from scraper import ERaktKoshScraper

class AgentState(TypedDict):
    messages: List[BaseMessage]
    location_query: Optional[str]
    blood_group_query: Optional[str]
    blood_component_query: Optional[str]
    normalized_state_code: Optional[str]
    normalized_state_name: Optional[str]
    normalized_district_code: Optional[str]
    normalized_district_name: Optional[str]
    normalized_bg_code: Optional[str]
    normalized_bc_code: Optional[str]
    ambiguity_candidates: Optional[List[Dict]]
    stock_results: Optional[List[StockResult]]
    error: Optional[str]
    hierarchy: Dict # Injected from context

def normalize_input(state: AgentState):
    """
    Extracts entities and performs fuzzy matching.
    """
    messages = state.get("messages", [])
    loc_query = state.get("location_query", "")
    
    if not messages and not loc_query:
        return {"error": "No input provided"}
    
    if messages and not loc_query:
        loc_query = messages[-1].content
    
    hierarchy = state.get("hierarchy", {})
    states_map = hierarchy.get("states", {})
    
    # Try to match state first
    s_id, s_name, s_score = fuzzy_match_state(loc_query, states_map)
    
    if s_score > 80:
        return {
            "normalized_state_code": s_id,
            "normalized_state_name": s_name,
            "normalized_district_code": "-1",
            "normalized_district_name": "All Districts"
        }
        
    # If not state, try district
    best_d_score = 0
    best_d_id = None
    best_d_name = None
    best_s_id_for_d = None
    
    candidates = []
    
    districts_map = hierarchy.get("districts", {})
    
    for s_id, d_map in districts_map.items():
        d_id, d_name, d_score = fuzzy_match_district(loc_query, d_map)
        if d_score > 60:
            candidates.append({
                "type": "District",
                "name": d_name,
                "code": d_id,
                "state_code": s_id,
                "state_name": states_map.get(s_id),
                "score": d_score
            })
            if d_score > best_d_score:
                best_d_score = d_score
                best_d_id = d_id
                best_d_name = d_name
                best_s_id_for_d = s_id
            
    if best_d_score > 90:
         return {
            "normalized_state_code": best_s_id_for_d,
            "normalized_state_name": states_map.get(best_s_id_for_d),
            "normalized_district_code": best_d_id,
            "normalized_district_name": best_d_name
        }
    
    if candidates:
        # Sort by score
        candidates.sort(key=lambda x: x["score"], reverse=True)
        # If top score is low or multiple high scores, return ambiguity
        return {"ambiguity_candidates": candidates[:3]}
        
    return {"error": f"Could not find location '{loc_query}'. Please be more specific."}

def ask_clarification(state: AgentState):
    candidates = state.get("ambiguity_candidates", [])
    msg = "Location is ambiguous. Did you mean:\n"
    for c in candidates:
        msg += f"- {c['name']} in {c['state_name']}?\n"
    return {"error": msg}

async def scrape_stock(state: AgentState):
    s_code = state.get("normalized_state_code")
    d_code = state.get("normalized_district_code")
    bg_code = state.get("normalized_bg_code")
    bc_code = state.get("normalized_bc_code")
    
    if not (s_code and d_code and bg_code):
        return {"error": "Missing location or blood group details."}
        
    scraper = ERaktKoshScraper()
    await scraper.start()
    try:
        results = await scraper.fetch_stock(s_code, d_code, bg_code, bc_code)
        return {"stock_results": results}
    except Exception as e:
        return {"error": str(e)}
    finally:
        await scraper.stop()

# Define Graph
workflow = StateGraph(AgentState)

workflow.add_node("normalize", normalize_input)
workflow.add_node("scrape", scrape_stock)
workflow.add_node("clarify", ask_clarification)

workflow.set_entry_point("normalize")

def should_scrape(state: AgentState):
    if state.get("error"):
        return END
    if state.get("ambiguity_candidates"):
        return "clarify"
    if state.get("normalized_state_code") and state.get("normalized_district_code"):
        return "scrape"
    return END

workflow.add_conditional_edges(
    "normalize",
    should_scrape
)

workflow.add_edge("scrape", END)
workflow.add_edge("clarify", END)

app = workflow.compile()
