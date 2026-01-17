"""
Triage Agent - LangGraph orchestration for patient triage workflow
Multi-node graph: Interpreter -> Specialist Scout -> Safety Audit
"""
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from typing import Dict, Any, Optional, TypedDict
import os
import json
import logging
from datetime import datetime

from models.state import TriageState, Biomarker, SpecialistResult
from services.fhir_client import FHIRClient
from agents.specialist_scout import SpecialistScout

logger = logging.getLogger(__name__)


# LangGraph state as TypedDict (required by LangGraph)
class GraphState(TypedDict):
    """State for LangGraph workflow"""
    session_id: str
    raw_text: str
    redacted_text: str
    lab_interpreted: bool
    biomarkers: Dict[str, Dict[str, Any]]
    interpretation_summary: Optional[str]
    specialist_needed: bool
    specialist_condition: Optional[str]
    specialist_type: Optional[str]
    patient_zip: Optional[str]
    specialist_search_approved: bool
    specialist_results: list
    safety_approved: bool
    medical_disclaimer: Optional[str]
    fhir_observation_id: Optional[str]
    fhir_patient_id: Optional[str]
    created_at: str
    updated_at: str


class TriageAgent:
    """
    Main LangGraph agent orchestrating the triage workflow
    """
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model="google/gemini-2.5-flash",
            temperature=0.1,
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url="https://openrouter.ai/api/v1",
            max_tokens=int(os.getenv("OPENROUTER_MAX_TOKENS", "3500")),  # Configurable via env var (default 3500)
            default_headers={
                "HTTP-Referer": "https://github.com/yourusername/MediStream",  # Optional: for OpenRouter analytics
                "X-Title": "MediStream"  # Optional: for OpenRouter analytics
            }
        )
        os.makedirs("checkpoints", exist_ok=True)
        # AsyncSqliteSaver.from_conn_string returns an async context manager
        self._checkpointer_cm = AsyncSqliteSaver.from_conn_string("checkpoints/triage_agent.db")
        self.checkpointer = None  # Will be initialized in initialize() method
        self.fhir_client = FHIRClient()
        self.specialist_scout = SpecialistScout()
        self.graph = None
        self._workflow = None  # Store the workflow before compilation
        self._build_graph()  # Build the workflow structure
    
    def _build_graph(self):
        """Build the LangGraph workflow"""
        workflow = StateGraph(GraphState)
        
        # Add a no-op init node for storing initial state without processing
        async def _init_node(state: GraphState) -> GraphState:
            """No-op node that just returns the state as-is"""
            return state
        
        # Add nodes
        workflow.add_node("init", _init_node)
        workflow.add_node("interpreter", self._interpret_lab_node)
        workflow.add_node("specialist_scout", self._specialist_scout_node)
        workflow.add_node("safety_audit", self._safety_audit_node)
        
        # Define edges
        workflow.set_entry_point("init")
        workflow.add_edge("init", "interpreter")
        
        # Conditional routing after interpretation
        workflow.add_conditional_edges(
            "interpreter",
            self._should_search_specialist,
            {
                "search": "specialist_scout",
                "skip": "safety_audit"
            }
        )
        
        # After specialist search, go to safety audit
        workflow.add_edge("specialist_scout", "safety_audit")
        
        # Safety audit is the final node
        workflow.add_edge("safety_audit", END)
        
        # Store workflow - will be compiled in initialize() after checkpointer is ready
        self._workflow = workflow
    
    async def initialize(self):
        """Initialize the agent and services"""
        os.makedirs("checkpoints", exist_ok=True)
        # Enter the async context manager to get the actual checkpointer
        self.checkpointer = await self._checkpointer_cm.__aenter__()
        
        # Build the workflow if not already built
        if self._workflow is None:
            self._build_graph()
        
        # Compile graph with checkpointer for state persistence
        self.graph = self._workflow.compile(checkpointer=self.checkpointer)
        
        await self.specialist_scout.initialize()
        logger.info("Triage Agent initialized")
    
    async def run_interpretation(self, session_id: str) -> Dict[str, Any]:
        """
        Run the full triage workflow for a session
        
        Args:
            session_id: Session identifier
            
        Returns:
            Final state after workflow completion
        """
        try:
            config = {"configurable": {"thread_id": session_id, "checkpoint_ns": ""}}
            
            # Get current state first
            current_state = await self.get_state(session_id)
            if not current_state:
                raise ValueError(f"Session {session_id} not found")
            
            # Convert TriageState to GraphState
            graph_state = self._triage_state_to_graph_state(current_state)
            
            # If already interpreted, don't run again
            if current_state.lab_interpreted:
                logger.info("Lab already interpreted, skipping workflow")
                return {
                    "session_id": session_id,
                    "status": "already_completed",
                    "message": "Lab results already interpreted"
                }
            
            # Run the graph - it will start from init node and continue through interpreter
            final_state = None
            async for state in self.graph.astream(
                graph_state,
                config=config
            ):
                final_state = state
                logger.info(f"Graph state update: {list(state.keys())}")
            
            # Get the final state
            if final_state:
                state_dict = list(final_state.values())[0] if final_state else {}
                return {
                    "session_id": session_id,
                    "status": "completed",
                    "state": state_dict
                }
            
            return {"session_id": session_id, "status": "running"}
        
        except Exception as e:
            logger.error(f"Error running interpretation: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    async def get_state(self, session_id: str) -> Optional[TriageState]:
        """Get current state for a session"""
        try:
            config = {"configurable": {"thread_id": session_id, "checkpoint_ns": ""}}
            state = await self.graph.aget_state(config)
            
            if state and hasattr(state, 'values') and state.values:
                # state.values is a dict containing the actual state
                graph_state = state.values
                if graph_state:
                    return self._graph_state_to_triage_state(graph_state)
            return None
        
        except Exception as e:
            logger.error(f"Error getting state: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    async def set_state(self, session_id: str, state: TriageState):
        """Set initial state for a session"""
        try:
            config = {"configurable": {"thread_id": session_id, "checkpoint_ns": ""}}
            graph_state = self._triage_state_to_graph_state(state)
            
            # Use astream to run just the init node, which stores the state
            # Then break to stop before running the interpreter
            async for step in self.graph.astream(graph_state, config=config):
                # Stop after the init node stores the state
                if "init" in step:
                    break
        
        except Exception as e:
            logger.error(f"Error setting state: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    def _triage_state_to_graph_state(self, triage_state: TriageState) -> GraphState:
        """Convert TriageState (Pydantic) to GraphState (TypedDict)"""
        return {
            "session_id": triage_state.session_id,
            "raw_text": triage_state.raw_text,
            "redacted_text": triage_state.redacted_text,
            "lab_interpreted": triage_state.lab_interpreted,
            "biomarkers": {
                k: v.model_dump() if hasattr(v, 'model_dump') else v
                for k, v in triage_state.biomarkers.items()
            },
            "interpretation_summary": triage_state.interpretation_summary,
            "specialist_needed": triage_state.specialist_needed,
            "specialist_condition": triage_state.specialist_condition,
            "specialist_type": triage_state.specialist_type,
            "patient_zip": triage_state.patient_zip,
            "specialist_search_approved": triage_state.specialist_search_approved,
            "specialist_results": [
                r.model_dump() if hasattr(r, 'model_dump') else r
                for r in triage_state.specialist_results
            ],
            "safety_approved": triage_state.safety_approved,
            "medical_disclaimer": triage_state.medical_disclaimer,
            "fhir_observation_id": triage_state.fhir_observation_id,
            "fhir_patient_id": triage_state.fhir_patient_id,
            "created_at": triage_state.created_at.isoformat() if isinstance(triage_state.created_at, datetime) else triage_state.created_at,
            "updated_at": triage_state.updated_at.isoformat() if isinstance(triage_state.updated_at, datetime) else triage_state.updated_at,
        }
    
    def _graph_state_to_triage_state(self, graph_state: GraphState) -> TriageState:
        """Convert GraphState (TypedDict) to TriageState (Pydantic)"""
        # Convert biomarkers
        biomarkers = {}
        for k, v in graph_state.get("biomarkers", {}).items():
            if isinstance(v, dict):
                biomarkers[k] = Biomarker(**v)
            else:
                biomarkers[k] = v
        
        # Convert specialist results
        specialist_results = []
        for r in graph_state.get("specialist_results", []):
            if isinstance(r, dict):
                specialist_results.append(SpecialistResult(**r))
            else:
                specialist_results.append(r)
        
        return TriageState(
            session_id=graph_state["session_id"],
            raw_text=graph_state.get("raw_text", ""),
            redacted_text=graph_state.get("redacted_text", ""),
            lab_interpreted=graph_state.get("lab_interpreted", False),
            biomarkers=biomarkers,
            interpretation_summary=graph_state.get("interpretation_summary"),
            specialist_needed=graph_state.get("specialist_needed", False),
            specialist_condition=graph_state.get("specialist_condition"),
            specialist_type=graph_state.get("specialist_type"),
            patient_zip=graph_state.get("patient_zip"),
            specialist_search_approved=graph_state.get("specialist_search_approved", False),
            specialist_results=specialist_results,
            safety_approved=graph_state.get("safety_approved", False),
            medical_disclaimer=graph_state.get("medical_disclaimer"),
            fhir_observation_id=graph_state.get("fhir_observation_id"),
            fhir_patient_id=graph_state.get("fhir_patient_id"),
            created_at=datetime.fromisoformat(graph_state.get("created_at", datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(graph_state.get("updated_at", datetime.now().isoformat())),
        )
    
    async def approve_specialist_search(self, session_id: str) -> Dict[str, Any]:
        """Approve specialist search (Human-in-the-loop)"""
        try:
            state = await self.get_state(session_id)
            if not state:
                raise ValueError("Session not found")
            
            state.specialist_search_approved = True
            state.updated_at = datetime.now()
            
            # Continue workflow from specialist scout
            config = {"configurable": {"thread_id": session_id, "checkpoint_ns": ""}}
            graph_state = self._triage_state_to_graph_state(state)
            await self.graph.ainvoke(
                graph_state,
                config=config
            )
            
            return {
                "session_id": session_id,
                "status": "approved",
                "message": "Specialist search approved"
            }
        
        except Exception as e:
            logger.error(f"Error approving search: {e}")
            raise
    
    async def save_to_fhir(self, session_id: str) -> Dict[str, Any]:
        """Save interpreted results to FHIR"""
        try:
            state = await self.get_state(session_id)
            if not state:
                raise ValueError("Session not found")
            
            observation_ids = []
            for biomarker_name, biomarker in state.biomarkers.items():
                if isinstance(biomarker, dict):
                    observation = await self.fhir_client.create_observation({
                        "name": biomarker.get("name", biomarker_name),
                        "value": biomarker.get("value", 0),
                        "unit": biomarker.get("unit", ""),
                        "status": biomarker.get("status", "normal"),
                        "loinc_code": self._get_loinc_code(biomarker_name)
                    })
                else:
                    observation = await self.fhir_client.create_observation({
                        "name": biomarker.name,
                        "value": biomarker.value,
                        "unit": biomarker.unit,
                        "status": biomarker.status,
                        "loinc_code": self._get_loinc_code(biomarker_name)
                    })
                observation_ids.append(observation.get("id"))
            
            state.fhir_observation_id = ",".join(observation_ids)
            state.updated_at = datetime.now()
            
            return {
                "session_id": session_id,
                "status": "saved",
                "observation_ids": observation_ids
            }
        
        except Exception as e:
            logger.error(f"Error saving to FHIR: {e}")
            raise
    
    # Node implementations
    async def _interpret_lab_node(self, state: GraphState) -> GraphState:
        """Node 1: Interpret lab results and extract biomarkers"""
        logger.info("Running interpreter node")
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a medical lab interpreter. Extract biomarkers from lab reports.
            
            Lab reports may be in various formats:
            - Tables with columns: Test Name, Result, Unit, Reference Range
            - Lists with biomarker names and values
            - Mixed formats with headers and data
            
            For each biomarker found, extract:
            1. Name (e.g., "Glucose", "Cholesterol", "Hemoglobin", "RBC Count")
            2. Value and unit (e.g., "141 mmol/L", "14.5 g/dL", "4.79 million/cmm")
            3. Normal range (e.g., "135-145 mmol/L", "< 41 U/L", "13.0 - 16.5")
            4. Status: Compare value to normal range and set to "normal", "high", "low", or "critical"
            5. Brief interpretation
            
            Important:
            - Extract ALL biomarkers you find in the report
            - Handle different units (mmol/L, g/dL, %, U/L, etc.)
            - Handle different range formats (135-145, < 41, >= 7.0, etc.)
            - If a value is within range, status is "normal"
            - If value is above range, status is "high"
            - If value is below range, status is "low"
            - If value is critically outside range, status is "critical"
            
            Return ONLY a valid JSON object with biomarkers as keys. Each biomarker should have:
            - "Name": string
            - "Value": string with number and unit (e.g., "141 mmol/L")
            - "Normal_range": string (e.g., "135-145 mmol/L")
            - "Status": "normal", "high", "low", or "critical"
            - "Interpretation": string
            
            Example format:
            {{
              "Sodium": {{
                "Name": "Sodium",
                "Value": "141 mmol/L",
                "Normal_range": "135-145 mmol/L",
                "Status": "normal",
                "Interpretation": "Sodium level is within the normal range."
              }},
              "Hemoglobin": {{
                "Name": "Hemoglobin",
                "Value": "14.5 g/dL",
                "Normal_range": "13.0 - 16.5",
                "Status": "normal",
                "Interpretation": "Hemoglobin level is within the normal range."
              }}
            }}
            
            Return ONLY the JSON, no additional text, no markdown code blocks, no explanations."""),
            ("user", "Interpret this lab report and extract all biomarkers:\n\n{lab_text}")
        ])
        
        chain = prompt | self.llm
        
        try:
            # Preprocess the lab text to help with extraction
            lab_text = state.get("redacted_text", "")
            processed_text = lab_text
            
            # If text is very long, try to focus on the biomarker sections
            # Look for common section headers and table structures
            # Lower threshold to be more aggressive with preprocessing
            if len(lab_text) > 2000:
                # Try to extract just the relevant biomarker sections
                lines = lab_text.split('\n')
                relevant_lines = []
                in_biomarker_section = False
                
                # Keywords that indicate biomarker sections
                biomarker_keywords = ['ANALYTES', 'RESULTS', 'Test', 'Biomarker', 'Lab', 
                                     'Sodium', 'Potassium', 'Glucose', 'Hemoglobin', 'RBC',
                                     'Creatinine', 'Cholesterol', 'ALT', 'AST', 'HbA1c',
                                     'Complete Blood Count', 'Biochemistry', 'Chemistry',
                                     'HEMATOLOGY', 'CBC', 'LIPID', 'LIVER', 'KIDNEY', 'THYROID']
                
                for line in lines:
                    line_upper = line.upper()
                    # Check if this line contains biomarker keywords
                    if any(keyword.upper() in line_upper for keyword in biomarker_keywords):
                        in_biomarker_section = True
                    
                    # Keep lines that look like biomarker data (contain numbers and units)
                    if in_biomarker_section or any(char.isdigit() for char in line):
                        if any(unit in line for unit in ['mmol/L', 'g/dL', 'U/L', '%', 'mg/L', '/cmm', '/hpf', 'fL', 'pg', 'ng/mL', 'mIU/L']):
                            relevant_lines.append(line)
                        elif len(line.strip()) > 0 and not line.strip().startswith('#'):
                            # Keep lines that might be part of a table
                            if '|' in line or '\t' in line or any(char.isdigit() for char in line):
                                relevant_lines.append(line)
                
                # Use processed text if we found relevant lines
                if relevant_lines:
                    processed_text = "\n".join(relevant_lines)
                    # Limit the processed text to avoid exceeding token limits
                    # Rough estimate: 1 token ≈ 4 characters, so 3500 tokens ≈ 14000 characters
                    # Reserve some for the response, so limit input to ~7000 characters
                    max_input_chars = 7000
                    if len(processed_text) > max_input_chars:
                        processed_text = processed_text[:max_input_chars]
                        logger.info(f"Preprocessed text: reduced from {len(lab_text)} to {len(processed_text)} characters (truncated to fit token limit)")
                    else:
                        logger.info(f"Preprocessed text: reduced from {len(lab_text)} to {len(processed_text)} characters")
            
            logger.info(f"Sending {len(processed_text)} characters to LLM (original: {len(lab_text)})")
            
            response = await chain.ainvoke({"lab_text": processed_text})
            logger.info(f"LLM response received, length: {len(response.content) if hasattr(response, 'content') else 'N/A'}")
        except Exception as e:
            logger.error(f"Error calling LLM: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
        
        # Parse LLM response to extract biomarkers
        biomarkers = self._parse_biomarkers(response.content)
        logger.info(f"Parsed {len(biomarkers)} biomarkers from LLM response")
        
        # Determine if specialist is needed
        specialist_needed = any(
            b.status in ["high", "low", "critical"] 
            for b in biomarkers.values()
        )
        
        # Determine specialist type based on abnormal values
        specialist_type = None
        specialist_condition = None
        if specialist_needed:
            specialist_type, specialist_condition = self._determine_specialist_type(biomarkers)
        
        # Update state
        biomarkers_dict = {
            k: v.model_dump() if hasattr(v, 'model_dump') else v
            for k, v in biomarkers.items()
        }
        
        state["biomarkers"] = biomarkers_dict
        state["lab_interpreted"] = True
        state["specialist_needed"] = specialist_needed
        state["specialist_type"] = specialist_type
        state["specialist_condition"] = specialist_condition
        
        # Create a clean summary instead of raw LLM response
        if biomarkers:
            summary = f"Successfully analyzed {len(biomarkers)} biomarker(s). "
            abnormal_count = sum(1 for b in biomarkers.values() if b.status != "normal")
            if abnormal_count == 0:
                summary += "All values are within normal ranges."
            else:
                summary += f"{abnormal_count} value(s) require attention."
            state["interpretation_summary"] = summary
        else:
            # If parsing failed, store a shorter version of the response
            state["interpretation_summary"] = response.content[:200] + "..." if len(response.content) > 200 else response.content
        
        state["updated_at"] = datetime.now().isoformat()
        
        return state
    
    async def _specialist_scout_node(self, state: GraphState) -> GraphState:
        """Node 2: Search for specialists using browser-use agent"""
        logger.info("Running specialist scout node")
        
        # Check if search is approved (HITL)
        if not state.get("specialist_search_approved", False):
            logger.info("Specialist search pending approval")
            return state
        
        if not state.get("specialist_type") or not state.get("patient_zip"):
            logger.warning("Missing specialist type or zip code")
            return state
        
        # Use browser-use agent to search for specialists
        try:
            results = await self.specialist_scout.search_specialists(
                specialty=state["specialist_type"],
                zip_code=state.get("patient_zip", "00000"),
                condition=state.get("specialist_condition")
            )
            
            state["specialist_results"] = [
                r.model_dump() if hasattr(r, 'model_dump') else r
                for r in results
            ]
            state["updated_at"] = datetime.now().isoformat()
        
        except Exception as e:
            logger.error(f"Error in specialist search: {e}")
        
        return state
    
    async def _safety_audit_node(self, state: GraphState) -> GraphState:
        """Node 3: Safety audit and medical disclaimer"""
        logger.info("Running safety audit node")
        
        disclaimer = """⚠️ MEDICAL DISCLAIMER ⚠️

This interpretation is for informational purposes only and does not constitute medical advice.
The results provided are based on automated analysis and should be reviewed by a licensed healthcare provider.

1. This tool is not a substitute for professional medical diagnosis or treatment.
2. Always consult with a qualified healthcare provider for medical decisions.
3. In case of emergency, contact emergency services immediately.
4. Lab values may vary based on individual circumstances and testing methods.

Generated by MediStream Agentic Triage System - For Educational/Portfolio Purposes Only."""
        
        state["medical_disclaimer"] = disclaimer
        state["safety_approved"] = True
        state["updated_at"] = datetime.now().isoformat()
        
        return state
    
    def _should_search_specialist(self, state: GraphState) -> str:
        """Conditional routing: should we search for specialists?"""
        if state.get("specialist_needed", False):
            return "search"
        return "skip"
    
    def _parse_biomarkers(self, llm_response: str) -> Dict[str, Biomarker]:
        """Parse LLM response to extract biomarker data"""
        biomarkers = {}
        
        def extract_value_and_unit(value_str: str) -> tuple:
            """Extract numeric value and unit from strings like '141 mmol/L' or '< 41 U/L'"""
            import re
            if not value_str or not isinstance(value_str, str):
                return (0.0, "")
            
            # Remove comparison operators like "<", ">", "<=", ">="
            value_str = re.sub(r'^[<>=]+', '', value_str.strip())
            
            # Extract number (supports decimals and scientific notation)
            match = re.search(r'([\d.]+(?:[eE][+-]?\d+)?)', value_str)
            if match:
                try:
                    numeric_value = float(match.group(1))
                    # Extract unit (everything after the number)
                    unit = value_str[match.end():].strip()
                    return (numeric_value, unit)
                except ValueError:
                    pass
            return (0.0, value_str)
        
        def parse_normal_range(normal_range_str: str) -> tuple:
            """Parse normal range from strings like '135-145 mmol/L' or '< 41 U/L'"""
            import re
            if not normal_range_str or not isinstance(normal_range_str, str):
                return (None, None)
            
            # Handle range format: "135-145 mmol/L"
            range_match = re.search(r'([\d.]+)\s*-\s*([\d.]+)', normal_range_str)
            if range_match:
                try:
                    min_val = float(range_match.group(1))
                    max_val = float(range_match.group(2))
                    return (min_val, max_val)
                except ValueError:
                    pass
            
            # Handle single value with comparison: "< 41 U/L"
            single_match = re.search(r'([<>=]+)?\s*([\d.]+)', normal_range_str)
            if single_match:
                try:
                    val = float(single_match.group(2))
                    operator = single_match.group(1) if single_match.group(1) else ""
                    if operator == "<":
                        return (None, val)  # Only max value
                    elif operator == ">":
                        return (val, None)  # Only min value
                    else:
                        return (val, val)  # Exact value
                except ValueError:
                    pass
            
            return (None, None)
        
        try:
            # Try to extract JSON from response
            # Handle markdown code blocks (```json ... ```)
            import re
            
            json_str = None
            
            # Step 1: Find where JSON starts (after ```json or ``` or just {)
            json_start = -1
            
            # Check for markdown code block
            code_block_match = re.search(r'```(?:json)?\s*', llm_response, re.IGNORECASE)
            if code_block_match:
                # Find the first { after the code block marker
                search_start = code_block_match.end()
                json_start = llm_response.find("{", search_start)
            else:
                # No code block, just find the first {
                json_start = llm_response.find("{")
            
            if json_start != -1:
                # Extract JSON by counting braces
                brace_count = 0
                json_end = -1
                in_string = False
                escape_next = False
                
                for i in range(json_start, len(llm_response)):
                    char = llm_response[i]
                    
                    if escape_next:
                        escape_next = False
                        continue
                    
                    if char == '\\':
                        escape_next = True
                        continue
                    
                    if char == '"' and not escape_next:
                        in_string = not in_string
                        continue
                    
                    if not in_string:
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                json_end = i + 1
                                break
                
                if json_end > json_start:
                    json_str = llm_response[json_start:json_end]
                elif brace_count > 0:
                    # JSON might be incomplete, try to use what we have and fix it
                    json_str = llm_response[json_start:]
                    logger.warning(f"Incomplete JSON detected, will attempt to fix (missing {brace_count} closing braces)")
            
            if json_str:
                # Clean up the JSON string
                json_str = json_str.strip()
                
                # Try to fix common JSON issues
                # Remove trailing commas before closing braces/brackets
                # This is safe because trailing commas are invalid in JSON
                # Handle various patterns: ", }", ",}", ",  }}", etc.
                # Use multiple passes to catch all cases
                json_str = re.sub(r',\s*([}\]])', r'\1', json_str)  # ", }" or ",]"
                json_str = re.sub(r',+([}\]])', r'\1', json_str)  # ",}" or ",}}" (multiple commas/braces)
                json_str = re.sub(r',\s*([}\]])+', r'\1', json_str)  # ", }}" (comma before multiple braces)
                
                # Try to complete incomplete JSON if it's cut off
                # Count opening vs closing braces
                open_braces = json_str.count('{')
                close_braces = json_str.count('}')
                if open_braces > close_braces:
                    # Add missing closing braces
                    json_str += '}' * (open_braces - close_braces)
                
                # Try parsing - if it fails, try more aggressive cleanup
                try:
                    data = json.loads(json_str)
                except json.JSONDecodeError as parse_error:
                    logger.warning(f"Initial JSON parse failed: {parse_error}, attempting more aggressive cleanup")
                    # More aggressive: remove all trailing commas before } or ]
                    # This is safe because trailing commas are always invalid in JSON
                    # Try multiple cleanup strategies
                    original_json = json_str
                    
                    # Strategy 1: Remove all commas before closing braces/brackets
                    json_str = re.sub(r',+(\s*[}\]])', r'\1', json_str)
                    
                    # Strategy 2: If still failing, try removing commas before any sequence of closing braces
                    try:
                        data = json.loads(json_str)
                    except json.JSONDecodeError:
                        json_str = re.sub(r',(\s*[}\]])+', lambda m: m.group(1), json_str)
                        try:
                            data = json.loads(json_str)
                        except json.JSONDecodeError as final_error:
                            # Strategy 3: Try to fix unterminated strings
                            error_msg = str(final_error)
                            parsed_data = None
                            
                            if "Unterminated string" in error_msg:
                                logger.warning("Attempting to fix unterminated string in JSON")
                                # Find the position of the error
                                error_pos = final_error.pos if hasattr(final_error, 'pos') else len(json_str) - 100
                                # Look backwards from error position to find the start of the unterminated string
                                # Find the last unclosed quote before the error
                                last_quote_pos = json_str.rfind('"', 0, error_pos)
                                if last_quote_pos != -1:
                                    # Check if this quote is escaped
                                    if last_quote_pos > 0 and json_str[last_quote_pos - 1] != '\\':
                                        # Try to close the string and add closing braces
                                        # Find where the string should end (before the next } or ,)
                                        next_brace = json_str.find('}', error_pos)
                                        if next_brace != -1:
                                            # Insert closing quote before the brace
                                            fixed_json = json_str[:next_brace] + '"' + json_str[next_brace:]
                                            try:
                                                parsed_data = json.loads(fixed_json)
                                            except json.JSONDecodeError:
                                                # If still failing, try removing the incomplete entry
                                                # Find the start of the last incomplete entry
                                                last_comma = json_str.rfind(',', 0, last_quote_pos)
                                                if last_comma != -1:
                                                    # Remove everything from the last comma to the end, then close properly
                                                    fixed_json = json_str[:last_comma] + '}'
                                                    # Add missing closing braces
                                                    open_braces = fixed_json.count('{')
                                                    close_braces = fixed_json.count('}')
                                                    if open_braces > close_braces:
                                                        fixed_json += '}' * (open_braces - close_braces)
                                                    try:
                                                        parsed_data = json.loads(fixed_json)
                                                    except json.JSONDecodeError as e:
                                                        logger.error(f"Failed to parse JSON after all cleanup attempts. Error: {e}")
                                                        logger.error(f"JSON around error position: {fixed_json[max(0, error_pos-100):error_pos+100]}")
                                                        raise
                                                else:
                                                    raise
                            
                            if parsed_data is None:
                                logger.error(f"Failed to parse JSON after cleanup. Error: {final_error}")
                                logger.error(f"JSON around error position: {json_str[max(0, final_error.pos-100):final_error.pos+100]}")
                                raise final_error
                            
                            data = parsed_data
                
                for key, value in data.items():
                    if isinstance(value, dict):
                        # Extract value and unit from the "Value" field
                        value_str = value.get("Value", value.get("value", ""))
                        numeric_value, unit = extract_value_and_unit(value_str)
                        
                        # If unit is empty, try to get it from a separate "unit" field
                        if not unit:
                            unit = value.get("unit", "")
                        
                        # Parse normal range
                        normal_range_str = value.get("Normal_range", value.get("normal_range", ""))
                        normal_range_min, normal_range_max = parse_normal_range(normal_range_str)
                        
                        biomarkers[key] = Biomarker(
                            name=value.get("Name", value.get("name", key)),
                            value=numeric_value,
                            unit=unit,
                            normal_range_min=normal_range_min,
                            normal_range_max=normal_range_max,
                            status=value.get("Status", value.get("status", "normal")).lower(),
                            interpretation=value.get("Interpretation", value.get("interpretation"))
                        )
                
                logger.info(f"Successfully parsed {len(biomarkers)} biomarkers")
            else:
                logger.warning("No JSON found in LLM response")
                logger.warning(f"Response preview: {llm_response[:200]}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            if 'json_str' in locals() and json_str:
                logger.error(f"Attempted to parse (first 500 chars): {json_str[:500]}")
                logger.error(f"Attempted to parse (last 500 chars): {json_str[-500:]}")
                logger.error(f"JSON string length: {len(json_str)}")
                logger.error(f"Open braces: {json_str.count('{')}, Close braces: {json_str.count('}')}")
            else:
                logger.error("No JSON string extracted")
            logger.error(f"Full LLM response preview (first 1000 chars): {llm_response[:1000]}")
            # Try to parse as plain text and extract what we can
            # Don't create fallback - let it return empty dict
        except Exception as e:
            logger.error(f"Error parsing biomarkers: {e}")
            import traceback
            logger.error(traceback.format_exc())
            logger.error(f"Response preview: {llm_response[:500]}")
            # Don't create fallback - return empty dict so UI shows proper error
        
        return biomarkers
    
    def _determine_specialist_type(self, biomarkers: Dict[str, Biomarker]) -> tuple:
        """Determine which specialist type is needed based on abnormal biomarkers"""
        # Simple mapping logic
        specialist_map = {
            "glucose": ("Endocrinologist", "Diabetes/Glucose Management"),
            "cholesterol": ("Cardiologist", "High Cholesterol"),
            "creatinine": ("Nephrologist", "Kidney Function"),
            "hemoglobin": ("Hematologist", "Blood Disorders"),
            "tsh": ("Endocrinologist", "Thyroid Function"),
            "alt": ("Hepatologist", "Liver Function"),
            "ast": ("Hepatologist", "Liver Function")
        }
        
        for biomarker_name, biomarker in biomarkers.items():
            if biomarker.status in ["high", "low", "critical"]:
                biomarker_lower = biomarker_name.lower()
                for key, (specialist, condition) in specialist_map.items():
                    if key in biomarker_lower:
                        return (specialist, condition)
        
        # Default
        return ("Primary Care Physician", "Abnormal Lab Values")
    
    def _get_loinc_code(self, biomarker_name: str) -> str:
        """Map biomarker name to LOINC code"""
        loinc_map = {
            "glucose": "2339-0",
            "cholesterol": "2093-3",
            "hdl": "2085-9",
            "ldl": "2089-1",
            "triglycerides": "2571-8",
            "creatinine": "2160-0",
            "hemoglobin": "718-7",
            "tsh": "3016-3"
        }
        
        biomarker_lower = biomarker_name.lower()
        for key, code in loinc_map.items():
            if key in biomarker_lower:
                return code
        
        return "33747-0"  # Default LOINC code
