"""
LangGraph State Model - Strictly typed state for the triage agent
"""
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


class Biomarker(BaseModel):
    """Represents a single lab biomarker"""
    name: str
    value: float
    unit: str
    normal_range_min: Optional[float] = None
    normal_range_max: Optional[float] = None
    status: str = Field(default="normal", description="normal, high, low, critical")
    interpretation: Optional[str] = None


class SpecialistResult(BaseModel):
    """Result from specialist search"""
    name: str
    specialty: str
    location: str
    distance: Optional[str] = None
    rating: Optional[float] = None
    url: Optional[str] = None


class TriageState(BaseModel):
    """
    Main state object for LangGraph agent
    Tracks the entire triage workflow
    """
    session_id: str
    raw_text: str = Field(default="", description="Original extracted text from PDF")
    redacted_text: str = Field(default="", description="PII-redacted text for LLM processing")
    
    # Interpretation phase
    lab_interpreted: bool = Field(default=False, description="Whether lab has been interpreted")
    biomarkers: Dict[str, Biomarker] = Field(default_factory=dict, description="Extracted biomarkers")
    interpretation_summary: Optional[str] = None
    
    # Specialist search phase
    specialist_needed: bool = Field(default=False, description="Whether specialist search is needed")
    specialist_condition: Optional[str] = None  # e.g., "High Cholesterol"
    specialist_type: Optional[str] = None  # e.g., "Cardiologist"
    patient_zip: Optional[str] = None
    specialist_search_approved: bool = Field(default=False, description="HITL approval for search")
    specialist_results: List[SpecialistResult] = Field(default_factory=list)
    
    # Safety and compliance
    safety_approved: bool = Field(default=False, description="Safety audit passed")
    medical_disclaimer: Optional[str] = None
    
    # FHIR integration
    fhir_observation_id: Optional[str] = None
    fhir_patient_id: Optional[str] = None
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "session_abc123",
                "redacted_text": "Lab results show...",
                "lab_interpreted": True,
                "biomarkers": {
                    "glucose": {
                        "name": "Glucose",
                        "value": 110.0,
                        "unit": "mg/dL",
                        "status": "high"
                    }
                },
                "specialist_needed": True,
                "specialist_type": "Endocrinologist"
            }
        }
