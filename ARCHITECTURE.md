# MediStream Architecture Documentation

## System Overview

MediStream is built as a modern, agentic healthcare application with a clear separation between frontend and backend, leveraging LangGraph for complex workflow orchestration.

## Component Architecture

### Backend Layer (FastAPI)

```
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Application                  │
│                      (main.py)                          │
└─────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
┌───────▼────────┐  ┌──────▼──────┐  ┌────────▼────────┐
│  PDF Parser    │  │ PII Redactor│  │  FHIR Client    │
│  (PyMuPDF)     │  │ (Presidio)  │  │  (HAPI FHIR)    │
└────────────────┘  └─────────────┘  └─────────────────┘
                            │
                    ┌───────▼────────┐
                    │  Triage Agent  │
                    │  (LangGraph)   │
                    └───────┬────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
┌───────▼────────┐  ┌──────▼──────┐  ┌────────▼────────┐
│  Interpreter   │  │  Specialist │  │  Safety Audit  │
│     Node       │  │ Scout Node  │  │     Node       │
└────────────────┘  └─────────────┘  └─────────────────┘
                            │
                    ┌───────▼────────┐
                    │ Browser Agent  │
                    │  (browser-use) │
                    └────────────────┘
```

### Frontend Layer (React)

```
┌─────────────────────────────────────────────────────────┐
│                    React Application                    │
│                      (App.tsx)                         │
└─────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
┌───────▼────────┐  ┌──────▼──────┐  ┌────────▼────────┐
│  Lab Upload    │  │ Interpretation│  │ Voice Interface │
│   Component    │  │   Results     │  │   (WebRTC)     │
└────────────────┘  └───────────────┘  └─────────────────┘
                            │
                    ┌───────▼────────┐
                    │  API Service   │
                    │   (axios)      │
                    └────────────────┘
```

## Data Flow

### 1. Lab Upload Flow

```
User Uploads PDF
    │
    ▼
PDF Parser (PyMuPDF)
    │
    ▼
Extract Text
    │
    ▼
PII Redactor (Presidio)
    │
    ▼
Redacted Text
    │
    ▼
Initialize LangGraph State
    │
    ▼
Store in SQLite Checkpointer
```

### 2. Interpretation Flow

```
Trigger Interpretation
    │
    ▼
LangGraph: Interpreter Node
    │
    ├─► LLM (GPT-4o-mini)
    │   └─► Extract Biomarkers
    │
    ├─► Determine Normal Ranges
    │
    └─► Identify Abnormalities
        │
        ▼
    Specialist Needed?
        │
        ├─► Yes → HITL Approval
        │       │
        │       ▼
        │   Specialist Scout Node
        │       │
        │       ▼
        │   Browser Agent Search
        │
        └─► No → Safety Audit Node
                │
                ▼
            Medical Disclaimer
                │
                ▼
            Complete
```

### 3. State Management

```
TriageState (Pydantic)
    │
    ├─► API Layer (FastAPI)
    │   └─► JSON Serialization
    │
    └─► GraphState (TypedDict)
        │
        └─► LangGraph Workflow
            │
            └─► SQLite Checkpointer
                └─► State Persistence
```

## Key Design Decisions

### 1. State Conversion Layer

**Why:** LangGraph requires TypedDict for state, but Pydantic provides better validation for API layer.

**Solution:** Conversion functions between `TriageState` (Pydantic) and `GraphState` (TypedDict).

### 2. Local PII Redaction

**Why:** HIPAA compliance requires no PHI to be sent to third-party LLMs.

**Solution:** Microsoft Presidio runs locally, redacting PII before any LLM calls.

### 3. Human-in-the-Loop

**Why:** Medical decisions require human oversight, especially for specialist referrals.

**Solution:** LangGraph's interrupt capability allows workflow to pause for approval.

### 4. SQLite Checkpointer

**Why:** Need state persistence across sessions without complex database setup.

**Solution:** LangGraph's built-in SQLite checkpointer provides simple, reliable persistence.

### 5. Browser Automation

**Why:** Real-world specialist search requires navigating complex web interfaces.

**Solution:** browser-use (Playwright) provides autonomous navigation capabilities.

## Security Considerations

1. **PII Redaction**: All sensitive data redacted before LLM processing
2. **Local Processing**: Presidio runs on-premise, no external API calls
3. **State Encryption**: SQLite checkpointer can be encrypted (future enhancement)
4. **API Authentication**: Add JWT/auth tokens for production
5. **Input Validation**: Pydantic models ensure type safety

## Scalability Considerations

1. **State Storage**: SQLite works for single-instance; migrate to PostgreSQL for multi-instance
2. **LLM Caching**: Add caching layer for repeated interpretations
3. **Browser Pool**: Pool browser instances for specialist search
4. **Async Processing**: All I/O operations are async
5. **Rate Limiting**: Add rate limiting for API endpoints

## Monitoring & Observability

**Recommended Additions:**
- Structured logging (JSON logs)
- Prometheus metrics
- Distributed tracing (OpenTelemetry)
- Error tracking (Sentry)
- Health check endpoints

## Future Enhancements

1. **NIH Clinical Tables Integration**: Real-time normal range lookups
2. **Multi-language Support**: Internationalize PII redaction
3. **Advanced Browser Automation**: Multi-site specialist search
4. **Voice AI Integration**: Complete OpenAI Realtime API integration
5. **Mobile App**: React Native version
6. **Analytics Dashboard**: Track interpretation accuracy
7. **ML Model Fine-tuning**: Custom model for biomarker extraction
