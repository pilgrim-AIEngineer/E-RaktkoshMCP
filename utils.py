import json
import os
from typing import Dict, List, Tuple
from thefuzz import process, fuzz

CACHE_FILE = "hierarchy.json"

def save_hierarchy(data: Dict):
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f, indent=2)

def load_hierarchy() -> Dict:
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return {}

def fuzzy_match_state(query: str, states: Dict[str, str]) -> Tuple[str, str, int]:
    """
    Returns (state_id, state_name, score)
    """
    # Create a map of name -> id for reverse lookup
    name_to_id = {v: k for k, v in states.items()}
    
    # Extract just the names for matching
    choices = list(states.values())
    
    # Use extractOne to find best match
    best_match = process.extractOne(query, choices, scorer=fuzz.token_sort_ratio)
    
    if best_match:
        name, score = best_match
        return name_to_id[name], name, score
    return None, None, 0

def fuzzy_match_district(query: str, districts: Dict[str, str]) -> Tuple[str, str, int]:
    """
    Returns (district_id, district_name, score)
    """
    name_to_id = {v: k for k, v in districts.items()}
    choices = list(districts.values())
    
    best_match = process.extractOne(query, choices, scorer=fuzz.token_sort_ratio)
    
    if best_match:
        name, score = best_match
        return name_to_id[name], name, score
    return None, None, 0
