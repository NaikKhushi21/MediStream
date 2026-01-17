# MediStream: Agentic Patient Triage & Lab Interpreter

A high-caliber 2026 portfolio piece demonstrating complex state management (LangGraph), real-time communication (WebRTC), and strict data governance (PII/HIPAA concepts).

## Architecture

### Frontend (React/TypeScript)
- Dashboard for uploading lab PDFs
- WebRTC voice interface for real-time AI conversation
- Human-in-the-loop approval mechanisms

### Backend (FastAPI/Python)
- Orchestration layer managing LangGraph states
- PDF parsing with PyMuPDF
- PII redaction with Microsoft Presidio
- FHIR integration for patient records

### The Agent (LangGraph)
- **Node 1 (Interpreter)**: Extracts biomarkers and cross-references with NIH Clinical Tables
- **Node 2 (Specialist Scout)**: Browser-use agent searches for specialists when needed
- **Node 3 (Safety Audit)**: Ensures medical disclaimers and safety compliance

## Tech Stack

- **Frontend**: React 19, TypeScript, Tailwind CSS
- **Backend**: FastAPI, Pydantic v2
- **Orchestration**: LangGraph
- **Browser Agent**: browser-use (Playwright)
- **Voice/WebRTC**: OpenAI Realtime API
- **Compliance**: Microsoft Presidio
- **Data Standard**: HAPI FHIR Public API
- **LLM**: Gemini 2.5 Flash (via OpenRouter)

## Setup

### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

## Environment Variables

Create a `.env` file in the backend directory:
```
OPENROUTER_API_KEY=your_openrouter_api_key
HAPI_FHIR_BASE_URL=https://hapi.fhir.org/baseR4
```

## Features

- ✅ HIPAA-conscious PII redaction before LLM processing
- ✅ Automated lab interpretation with biomarker extraction
- ✅ Autonomous specialist matching via browser automation
- ✅ Real-time voice interaction via WebRTC
- ✅ State persistence with SQLite checkpointer
- ✅ FHIR-compliant data storage
- ✅ Human-in-the-loop approval workflows
