# MediStream Setup Guide

## Prerequisites

- Python 3.11+
- Node.js 18+
- npm or yarn

## Backend Setup

1. **Create virtual environment:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Install Playwright (for browser-use):**
```bash
playwright install
```

4. **Set up environment variables:**
```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

5. **Create necessary directories:**
```bash
mkdir -p uploads checkpoints
```

6. **Run the backend:**
```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`

## Frontend Setup

1. **Install dependencies:**
```bash
cd frontend
npm install
```

2. **Set up environment variables (optional):**
```bash
# Create .env file if you want to change API URL
echo "VITE_API_URL=http://localhost:8000" > .env
```

3. **Run the frontend:**
```bash
npm run dev
```

The frontend will be available at `http://localhost:3000`

## Testing the Application

1. Start both backend and frontend servers
2. Open `http://localhost:3000` in your browser
3. Upload a lab report PDF
4. Click "Start Interpretation" to trigger the LangGraph workflow
5. If specialist search is needed, approve it when prompted
6. View results and use the voice interface

## Key Features

- **PII Redaction**: All uploaded documents are automatically redacted using Microsoft Presidio
- **State Persistence**: LangGraph uses SQLite checkpointer to persist state across sessions
- **FHIR Integration**: Lab results can be saved to HAPI FHIR public endpoint
- **Human-in-the-Loop**: Specialist search requires explicit approval
- **Voice Interface**: WebRTC-ready interface for real-time voice interaction

## Troubleshooting

### Presidio Installation Issues
If Presidio fails to install, you may need:
```bash
pip install spacy
python -m spacy download en_core_web_sm
```

### Playwright Issues
If browser-use doesn't work:
```bash
playwright install chromium
```

### LangGraph State Issues
If you see state-related errors, ensure the `checkpoints/` directory exists and is writable.

## Architecture Notes

- **Backend**: FastAPI with async/await throughout
- **State Management**: LangGraph with SQLite checkpointer
- **PII Handling**: Microsoft Presidio runs locally (no external API calls)
- **LLM**: Gemini 2.5 Flash (via OpenRouter) for cost-effective processing
- **Frontend**: React 19 with TypeScript and Tailwind CSS
