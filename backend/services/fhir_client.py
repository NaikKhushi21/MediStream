"""
FHIR Client Service - Interfaces with HAPI FHIR public API
Converts lab data to FHIR Observation resources
"""
import httpx
import os
from typing import Optional, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class FHIRClient:
    """
    Client for interacting with HAPI FHIR public API
    Handles conversion of lab results to FHIR Observation resources
    """
    
    def __init__(self):
        self.base_url = os.getenv("HAPI_FHIR_BASE_URL", "https://hapi.fhir.org/baseR4")
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def create_observation(self, biomarker_data: Dict[str, Any], patient_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a FHIR Observation resource from biomarker data
        
        Args:
            biomarker_data: Dictionary containing biomarker information
            patient_id: Optional FHIR patient ID
            
        Returns:
            Created Observation resource
        """
        try:
            # Build FHIR Observation resource
            observation = {
                "resourceType": "Observation",
                "status": "final",
                "category": [
                    {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                                "code": "laboratory",
                                "display": "Laboratory"
                            }
                        ]
                    }
                ],
                "code": {
                    "coding": [
                        {
                            "system": "http://loinc.org",
                            "code": biomarker_data.get("loinc_code", "33747-0"),
                            "display": biomarker_data.get("name", "Lab Test")
                        }
                    ],
                    "text": biomarker_data.get("name", "Lab Test")
                },
                "valueQuantity": {
                    "value": biomarker_data.get("value"),
                    "unit": biomarker_data.get("unit", ""),
                    "system": "http://unitsofmeasure.org",
                    "code": biomarker_data.get("unit", "")
                },
                "effectiveDateTime": datetime.now().isoformat(),
                "interpretation": [
                    {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                                "code": self._map_status_to_fhir(biomarker_data.get("status", "normal")),
                                "display": biomarker_data.get("status", "normal").upper()
                            }
                        ]
                    }
                ]
            }
            
            # Add reference to patient if provided
            if patient_id:
                observation["subject"] = {
                    "reference": f"Patient/{patient_id}"
                }
            
            # POST to HAPI FHIR
            response = await self.client.post(
                f"{self.base_url}/Observation",
                json=observation,
                headers={"Content-Type": "application/fhir+json"}
            )
            
            if response.status_code in [200, 201]:
                result = response.json()
                logger.info(f"Created FHIR Observation: {result.get('id')}")
                return result
            else:
                logger.error(f"Failed to create FHIR Observation: {response.status_code} - {response.text}")
                raise Exception(f"FHIR API error: {response.status_code}")
        
        except Exception as e:
            logger.error(f"Error creating FHIR Observation: {e}")
            raise
    
    async def get_observation(self, observation_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a FHIR Observation by ID
        
        Args:
            observation_id: FHIR Observation ID
            
        Returns:
            Observation resource or None
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/Observation/{observation_id}",
                headers={"Accept": "application/fhir+json"}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Observation not found: {observation_id}")
                return None
        
        except Exception as e:
            logger.error(f"Error retrieving FHIR Observation: {e}")
            return None
    
    async def search_observations(self, patient_id: Optional[str] = None, 
                                  code: Optional[str] = None) -> list:
        """
        Search for FHIR Observations
        
        Args:
            patient_id: Optional patient ID to filter by
            code: Optional LOINC code to filter by
            
        Returns:
            List of Observation resources
        """
        try:
            params = {}
            if patient_id:
                params["subject"] = f"Patient/{patient_id}"
            if code:
                params["code"] = code
            
            response = await self.client.get(
                f"{self.base_url}/Observation",
                params=params,
                headers={"Accept": "application/fhir+json"}
            )
            
            if response.status_code == 200:
                bundle = response.json()
                if bundle.get("resourceType") == "Bundle":
                    return bundle.get("entry", [])
                return []
            else:
                logger.warning(f"Search failed: {response.status_code}")
                return []
        
        except Exception as e:
            logger.error(f"Error searching FHIR Observations: {e}")
            return []
    
    def _map_status_to_fhir(self, status: str) -> str:
        """Map internal status to FHIR interpretation code"""
        mapping = {
            "normal": "N",
            "high": "H",
            "low": "L",
            "critical": "HH"
        }
        return mapping.get(status.lower(), "N")
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
