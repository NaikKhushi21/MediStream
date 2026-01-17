# MediStream: Agentic Patient Triage & Lab Interpreter

An AI-powered medical lab report interpreter that analyzes patient lab results, extracts biomarkers, and provides personalized health insights. The system uses LangGraph for multi-agent orchestration, automatically redacts PII before processing, and offers an interactive chatbot interface for patient questions. Built with React/TypeScript frontend, FastAPI backend, and integrates with FHIR-compliant healthcare systems.

## Demo

📹 **[Watch Demo Video](https://drive.google.com/file/d/1295Gwdb3jK1F6QVSQeGt0wH9FAV3QvqM/view?usp=sharing)**

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
OPENAI_API_KEY=your_api_key
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
