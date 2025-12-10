from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Optional

class BloodGroup(str, Enum):
    A_POS = "11"
    B_POS = "13"
    O_POS = "15"
    AB_POS = "17"
    A_NEG = "12"
    B_NEG = "14"
    O_NEG = "16"
    AB_NEG = "18"
    BOMBAY_POS = "22"
    BOMBAY_NEG = "23"
    ALL = "all"

class StockResult(BaseModel):
    blood_bank_name: str
    category: str
    availability: str
    last_updated: str
    
class ScrapedHierarchy(BaseModel):
    states: dict[str, str] # id -> name
    districts: dict[str, dict[str, str]] # state_id -> {district_id -> district_name}
    blood_groups: dict[str, str] # id -> name
    blood_components: dict[str, str] # id -> name
