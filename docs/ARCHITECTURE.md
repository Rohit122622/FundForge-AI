# FundForge AI — Architecture Reference

## System Overview

FundForge AI is a three-tier SaaS application:

```
Browser (React 18 + Vite)
      │
      ▼
REST API (Python Flask)
      │
      ├── IBM watsonx.ai  (Granite LLM)
      ├── IBM Vector Index (RAG pipeline)
      └── Google Custom Search API
```

## Layer Responsibilities

| Layer | Technology | Responsibility |
|---|---|---|
| Frontend | React + Vite | SPA rendering, routing, state management |
| Backend | Flask | REST API, business logic, AI orchestration |
| AI Engine | IBM Granite | Grant matching, proposal generation |
| Vector Store | IBM Vector Index | Semantic search over grant knowledge base |
| Search | Google CSE | Live grant discovery from the web |
| Database | PostgreSQL / SQLite | User data, saved grants, proposals, tracker |
