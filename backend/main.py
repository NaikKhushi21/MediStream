"""
MediStream Backend - FastAPI Orchestration Layer
Handles PDF uploads, PII redaction, LangGraph orchestration, and WebRTC endpoints
"""
from fastapi import FastAPI, UploadFile, File, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from contextlib import asynccontextmanager
import os
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

from services.pdf_parser import PDFParser
from services.pii_redactor import PIIRedactor
from services.fhir_client import FHIRClient
from agents.triage_agent import TriageAgent
from models.state import TriageState

load_dotenv()

app = FastAPI(
    title="MediStream API",
    description="Agentic Patient Triage & Lab Interpreter",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
pdf_parser = PDFParser()
pii_redactor = PIIRedactor()
fhir_client = FHIRClient()
triage_agent = TriageAgent()


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    await triage_agent.initialize()


@app.get("/")
async def root():
    return {"message": "MediStream API", "status": "operational"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "services": {
        "pdf_parser": "ready",
        "pii_redactor": "ready",
        "fhir_client": "ready",
        "triage_agent": "ready"
    }}


@app.post("/api/upload-lab")
async def upload_lab(file: UploadFile = File(...)):
    """
    Upload and process a lab report PDF
    Returns: Extracted text (redacted), session ID for state tracking
    """
    try:
        # Save uploaded file temporarily
        os.makedirs("uploads", exist_ok=True)
        file_path = f"uploads/{file.filename}"
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Extract text from PDF
        extracted_text = pdf_parser.extract_text(file_path)
        
        # Get PII entities before redaction
        pii_entities = pii_redactor.get_detected_entities(extracted_text)
        
        # Redact PII
        redacted_text = pii_redactor.redact(extracted_text)
        
        # Initialize LangGraph state
        session_id = f"session_{os.urandom(8).hex()}"
        
        # Save original PDF with session ID
        os.makedirs("uploads/pdfs", exist_ok=True)
        original_pdf_path = f"uploads/pdfs/{session_id}_original.pdf"
        import shutil
        shutil.copy(file_path, original_pdf_path)
        
        # Create redacted PDF
        redacted_pdf_path = f"uploads/pdfs/{session_id}_redacted.pdf"
        pdf_parser.create_redacted_pdf(file_path, extracted_text, pii_entities, redacted_pdf_path)
        
        initial_state = TriageState(
            session_id=session_id,
            raw_text=extracted_text,
            redacted_text=redacted_text,
            lab_interpreted=False,
            biomarkers={},
            specialist_needed=False,
            specialist_results=[],
            safety_approved=False,
            fhir_observation_id=None
        )
        
        # Store initial state
        await triage_agent.set_state(session_id, initial_state)
        
        # Clean up temp file
        os.remove(file_path)
        
        return {
            "session_id": session_id,
            "original_text": extracted_text,
            "redacted_text": redacted_text,
            "status": "uploaded"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing lab report: {str(e)}")


@app.post("/api/interpret/{session_id}")
async def interpret_lab(session_id: str):
    """
    Trigger the LangGraph agent to interpret the lab results
    """
    try:
        result = await triage_agent.run_interpretation(session_id)
        return result
    except Exception as e:
        import traceback
        error_detail = str(e)
        logger.error(f"Error in interpret_lab endpoint: {error_detail}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error interpreting lab: {error_detail}")


@app.get("/api/state/{session_id}")
async def get_state(session_id: str):
    """
    Get current state of the triage agent
    """
    try:
        state = await triage_agent.get_state(session_id)
        if not state:
            raise HTTPException(status_code=404, detail="Session not found")
        return state.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving state: {str(e)}")


@app.post("/api/approve-specialist-search/{session_id}")
async def approve_specialist_search(session_id: str):
    """
    Human-in-the-loop approval for specialist search
    """
    try:
        result = await triage_agent.approve_specialist_search(session_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error approving search: {str(e)}")


@app.post("/api/save-to-fhir/{session_id}")
async def save_to_fhir(session_id: str):
    """
    Save interpreted lab results to FHIR endpoint
    """
    try:
        result = await triage_agent.save_to_fhir(session_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving to FHIR: {str(e)}")


@app.get("/api/pdf/{session_id}/original")
async def get_original_pdf(session_id: str):
    """Serve the original PDF file for inline viewing only"""
    pdf_path = f"uploads/pdfs/{session_id}_original.pdf"
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF not found")
    return FileResponse(
        pdf_path, 
        media_type="application/pdf",
        headers={
            "Content-Disposition": "inline",
            "X-Content-Type-Options": "nosniff"
        }
    )


@app.get("/api/pdf/{session_id}/redacted")
async def get_redacted_pdf(session_id: str):
    """Serve the redacted PDF file for inline viewing only"""
    pdf_path = f"uploads/pdfs/{session_id}_redacted.pdf"
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="Redacted PDF not found")
    return FileResponse(
        pdf_path, 
        media_type="application/pdf",
        headers={
            "Content-Disposition": "inline",
            "X-Content-Type-Options": "nosniff"
        }
    )


@app.post("/api/chat/{session_id}")
async def chat(session_id: str, request: dict):
    """
    Chat endpoint for asking questions about lab results
    Uses the LLM with context from the lab interpretation
    """
    try:
        message = request.get("message", "")
        if not message:
            raise HTTPException(status_code=400, detail="Message is required")
        
        # Get current state
        state = await triage_agent.get_state(session_id)
        if not state:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Build context from biomarkers
        biomarkers_context = ""
        if state.biomarkers:
            biomarkers_list = []
            for name, biomarker in state.biomarkers.items():
                # Handle both Pydantic models and dictionaries
                if hasattr(biomarker, 'value'):
                    # It's a Pydantic model
                    value = biomarker.value
                    unit = biomarker.unit
                    normal_min = biomarker.normal_range_min if biomarker.normal_range_min is not None else 'N/A'
                    normal_max = biomarker.normal_range_max if biomarker.normal_range_max is not None else 'N/A'
                    status = biomarker.status
                else:
                    # It's a dictionary
                    value = biomarker.get('value', 'N/A')
                    unit = biomarker.get('unit', '')
                    normal_min = biomarker.get('normal_range_min', 'N/A')
                    normal_max = biomarker.get('normal_range_max', 'N/A')
                    status = biomarker.get('status', 'unknown')
                
                biomarkers_list.append(
                    f"- {name}: {value} {unit} "
                    f"(Normal: {normal_min}-{normal_max} {unit}, "
                    f"Status: {status})"
                )
            biomarkers_context = "\n".join(biomarkers_list)
        
        # Create prompt with context
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_openai import ChatOpenAI
        import os
        
        llm = ChatOpenAI(
            model="google/gemini-2.5-flash",
            temperature=0.7,
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url="https://openrouter.ai/api/v1",
            max_tokens=int(os.getenv("OPENROUTER_MAX_TOKENS", "5000")),
            default_headers={
                "HTTP-Referer": "https://github.com/yourusername/MediStream",
                "X-Title": "MediStream"
            }
        )
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a knowledgeable and empathetic medical assistant helping a patient understand their lab results. Your goal is to provide clear, accurate, and reassuring information.

CONTEXT - Patient's Lab Results:
{biomarkers}

RESPONSE STRUCTURE (MUST FOLLOW THIS ORDER):
1. **Direct Answer First**: Start with a clear, direct answer to their question
2. **Main Content**: Provide detailed explanation with:
   - Specific biomarker values from their results
   - What the values mean in plain language
   - Why it matters for their health
   - Any relevant context
3. **Action Items** (if applicable): Brief, actionable next steps
4. **NO DISCLAIMERS IN MIDDLE**: Do not include disclaimers, warnings, or questions in the middle of your response
5. **NO QUESTIONS IN MIDDLE**: Do not ask "Do you have any other questions?" or similar in the middle of your response

GUIDELINES:
1. **Be Clear and Simple**: Explain medical terms in plain language that anyone can understand
2. **Be Specific**: Reference the actual values from their lab results when answering
3. **Be Reassuring**: For normal values, acknowledge that's good news. For abnormal values, explain what it means without causing unnecessary alarm
4. **Be Educational**: Help them understand what each biomarker means and why it matters
5. **Be Actionable**: Suggest appropriate next steps (e.g., "discuss with your doctor", "monitor over time", "consider lifestyle changes")

TONE: Professional yet warm, empathetic, and supportive. Avoid medical jargon when possible, but explain it when necessary.

FORMAT: 
- Use clear paragraphs and bullet points
- Structure your response logically with section headers when discussing multiple biomarkers
- Format biomarker results as: "Biomarker Name (value unit): explanation"
- Use **bold** for section headers and important phrases
- Keep the response flowing without interruptions

CRITICAL: 
- Do NOT include disclaimers like "Please remember, I'm a medical assistant" or "This is for educational purposes" in the middle of your response
- Do NOT ask questions like "Do you have any other questions?" in the middle of your response
- Provide a direct, helpful answer without interruptions
- Keep the response structured and easy to read"""),
            ("user", "{question}")
        ])
        
        chain = prompt | llm
        response = await chain.ainvoke({
            "biomarkers": biomarkers_context or "No biomarkers available yet.",
            "question": message
        })
        
        return {"message": response.content}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error processing chat message: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
