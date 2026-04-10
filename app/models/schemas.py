from pydantic import BaseModel
from typing import List, Dict

class PredictionResult(BaseModel):
    fault_type: str
    fault_label: int
    severity: str
    confidence: float
    shap_reasons: List[Dict]
    suggestions: List[Dict]