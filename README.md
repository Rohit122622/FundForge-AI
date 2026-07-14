# FundForge AI 🚀
### AI-Powered Grant & Funding Discovery Platform for Indian Startups

> Discover government grants, evaluate eligibility with precision scoring, and generate tailored funding proposals — powered by IBM Granite AI with a 3-provider fallback chain.

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.x-000000?style=flat-square&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-5-646CFF?style=flat-square&logo=vite&logoColor=white)](https://vitejs.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://postgresql.org/)
[![IBM watsonx](https://img.shields.io/badge/IBM-watsonx.ai-BE95FF?style=flat-square&logo=ibm&logoColor=white)](https://www.ibm.com/watsonx)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)

<br>

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [Database Setup](#database-setup)
- [Running the Application](#running-the-application)
- [Production Build](#production-build)
- [Running Tests](#running-tests)
- [API Reference](#api-reference)
- [Demo Walkthrough](#demo-walkthrough)
- [Project Structure](#project-structure)
- [Troubleshooting](#troubleshooting)
- [Contact](#contact)

<br>

## Overview

FundForge AI is a production-grade fullstack platform that solves a critical problem for Indian startups: **finding and winning the right government grants**. The platform combines a curated grant registry, a rules-based eligibility scoring engine, and IBM Granite AI-powered proposal generation with RAG (Retrieval-Augmented Generation) to produce structured, tailored funding proposals.

The AI layer is resilient by design — if IBM watsonx is unavailable, the system automatically falls over to Google Gemini, then Grok/Llama, with real-time telemetry tracking which provider is active.

<br>

## Architecture

```
                 React (Vite) Frontend [SPA]
                              │
                              ▼ (HTTP / Nginx Reverse Proxy)
                     Flask Backend API
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
  Authentication     Eligibility Engine     Proposal Generator
  (JWT + bcrypt)      (Rules-based)         (IBM Granite AI)
        │                     │                     │
        ▼                     ▼                     ▼
  PostgreSQL DB          RAG Engine        AI Fallback Chain
 (SQLAlchemy ORM)    (watsonx Index)    IBM → Gemini → Grok
```

### AI Fallback Chain

The platform uses a 3-tier AI provider chain with automatic failover and instant recovery:

```
Request → IBM watsonx (Primary)
               │ Failure
               ▼
          Google Gemini (Secondary)
               │ Failure
               ▼
          Grok / Llama via Groq (Tertiary)
```

Provider status, failover events, and response times are tracked live via `GET /api/v1/system/ai-status`.

<br>

## Features

| Feature | Description |
|---------|-------------|
| **Grant Discovery** | Paginated, searchable catalog of government grants curated for Indian startups |
| **Eligibility Scoring** | Rules-based engine that scores startup profile against grant criteria with a readiness percentage |
| **AI Proposal Generation** | IBM Granite AI + RAG retrieves semantic startup context and drafts a structured markdown proposal |
| **PDF Export** | Compiles generated proposals into a formatted downloadable PDF |
| **Application Tracker** | FSM-based tracker with state transitions: SAVED → RESEARCHING → IN_PROGRESS |
| **AI Telemetry** | Real-time visibility into active AI provider, failover events, and response times |
| **JWT Auth** | Stateless authentication with access and refresh token support |
| **3-Provider Fallback** | Automatic failover across IBM → Gemini → Grok with zero manual intervention |

<br>

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React 18, Vite, React Router |
| **Backend** | Python 3.11+, Flask, SQLAlchemy ORM |
| **Database** | PostgreSQL (production), SQLite (local dev) |
| **Auth** | JWT (access + refresh tokens), bcrypt |
| **AI Primary** | IBM watsonx.ai — Granite model |
| **AI Fallback** | Google Gemini, Grok via Groq Cloud |
| **RAG** | watsonx Vector Index |
| **Caching / Queue** | Redis, Celery |
| **Proxy / Static** | Nginx (production) |
| **Testing** | pytest (13 tests across 4 modules) |

<br>

## Prerequisites

Before starting, ensure you have the following installed:

| Tool | Version | Notes |
|------|---------|-------|
| Git | Any | For cloning the repository |
| Python | 3.11+ | Required for backend |
| Node.js | 18.0.0+ | Required for frontend |
| npm | 9.0.0+ | Bundled with Node.js |
| Redis | Any | Required for caching and Celery |
| PostgreSQL | 14+ | Required for production; SQLite used locally |

**API Keys required:**

- **IBM Cloud** *(optional)* — for IBM Granite as primary AI provider
- **Google Gemini** — secondary AI fallback ([Google AI Studio](https://aistudio.google.com/))
- **Groq Cloud** — tertiary AI fallback ([Groq Console](https://console.groq.com/))

<br>

## Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/FundForge-AI.git
cd FundForge-AI
```

### 2. Create and Activate Python Virtual Environment

**Linux / macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows (PowerShell):**
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

> **Windows tip:** If you hit an execution policy error, run PowerShell as Administrator and execute:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope LocalMachine
> ```

### 3. Install Backend Dependencies

```bash
pip install -r backend/requirements.txt
```

### 4. Configure Environment Variables

```bash
cp .env.example .env
```

Open `.env` and populate all required fields. See the [Environment Variables](#environment-variables) section below.

<br>

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `FLASK_ENV` | Runtime mode (`development`, `production`, `testing`) | `development` |
| `FLASK_SECRET_KEY` | Flask session signing secret | Secure random string |
| `JWT_SECRET` | JWT access/refresh token signing key | Secure random string |
| `DATABASE_URL` | SQLAlchemy connection string | `sqlite:///instance/fundforge.db` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `IBM_API_KEY` | IBM watsonx.ai API key | `OdvxVIMDwheMwyVeN...` |
| `IBM_PROJECT_ID` | IBM watsonx workspace project GUID | `8a219719-a8b5-4c0e-...` |
| `IBM_URL` | IBM Cloud inference endpoint | `https://us-south.ml.cloud.ibm.com` |
| `GEMINI_API_KEY` | Google Gemini API key (secondary fallback) | `AIzaSyDG-_voPS0xD...` |
| `GROQ_API_KEY` | Groq Cloud API key (tertiary fallback) | `gsk_CJyWdxjHjR8vl...` |

<br>

## Database Setup

### Local Development (SQLite — Default)

The database file is created automatically inside `instance/` on first run. Just run migrations:

```bash
flask --app backend.wsgi db upgrade
```

### Production (PostgreSQL)

1. Create the database:

```sql
CREATE DATABASE fundforge_db;
```

2. Set `DATABASE_URL` in `.env`:

```env
DATABASE_URL=postgresql://<user>:<password>@localhost:5432/fundforge_db
```

3. Run migrations:

```bash
flask --app backend.wsgi db upgrade
```

<br>

## Running the Application

### Backend

Run from the **project root directory** (not inside `/backend`):

```bash
python -m backend.wsgi
```

> **Why `-m backend.wsgi`?** The backend uses package-absolute imports (e.g. `from backend.app import ...`). Running from inside the `backend/` folder causes `ModuleNotFoundError` because Python won't find the parent package. The `-m` flag injects the workspace root into `sys.path` correctly.

Backend runs at: `http://localhost:5000`

### Frontend

Open a **new terminal**, then:

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at: `http://localhost:5173`

> API calls to `/api/v1` are automatically proxied to `http://localhost:5000` via `vite.config.js` — no manual CORS setup needed in development.

<br>

## Production Build

```bash
cd frontend
npm run build
```

Minified static assets are output to `frontend/dist/`. In production, Nginx serves these directly and reverse-proxies `/api/v1` traffic to Gunicorn.

<br>

## Running Tests

Ensure your virtual environment is active, then from the project root:

```bash
python -m pytest
```

The test suite covers 13 tests across 4 modules:

| Test File | Coverage |
|-----------|----------|
| `tests/test_auth.py` | User authentication and permission validation |
| `tests/test_grants.py` | Grant catalog retrieval and query filtering |
| `tests/test_tracker.py` | Application tracker FSM state transitions |
| `tests/test_ai_fallback.py` | AI provider failover chain validation |

<br>

## API Reference

All JWT-protected endpoints require an `Authorization: Bearer <token>` header.

### Auth

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/api/v1/auth/register` | Public | Register a new user account |
| `POST` | `/api/v1/auth/login` | Public | Authenticate and receive JWT tokens |

### Grants

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/api/v1/grants/` | Public | Paginated grant list with search and filters |
| `GET` | `/api/v1/grants/<id>` | Public | Single grant details |
| `POST` | `/api/v1/grants/recommend` | JWT | Get grants matched to startup profile |

### Eligibility & Proposals

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/api/v1/eligibility/check` | JWT | Score startup eligibility against a grant |
| `POST` | `/api/v1/proposals/generate` | JWT | Generate AI proposal draft with RAG |
| `POST` | `/api/v1/documents/generate-pdf` | JWT | Compile proposal into a downloadable PDF |

### Tracker

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/api/v1/tracker/` | JWT | List all tracked applications |
| `POST` | `/api/v1/tracker/<id>/transition` | JWT | Execute FSM state transition |

### System

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/api/v1/system/ai-status` | Public | AI provider telemetry and fallback metrics |

**Sample AI status response:**

```json
{
  "success": true,
  "data": {
    "current_primary_provider": "Gemini",
    "last_active_provider": "Gemini",
    "fallback_used": true,
    "response_time_ms": 1420.5
  }
}
```

<br>

## Demo Walkthrough

Follow this sequence to verify all platform capabilities end-to-end:

1. **Register** at `http://localhost:5173/register`
2. **Login** at `http://localhost:5173/login` to receive your JWT
3. **Build Startup Profile** — complete onboarding with sector, stage, founding year, and description
4. **Explore Grants** — browse and filter the Grant Explorer catalog
5. **Check Eligibility** — select a grant (e.g. Startup India Seed Fund Scheme) and run the eligibility checker to see your score and readiness percentage
6. **Generate Proposal** — click Generate Proposal; RAG retrieves startup context and drafts a structured markdown proposal
7. **Download PDF** — package the proposal into a formatted PDF report
8. **Track Application** — enter the tracker at `SAVED`, then transition to `RESEARCHING` → `IN_PROGRESS`
9. **Test AI Failover** — set an invalid `IBM_API_KEY` in `.env`, regenerate a proposal, and observe the terminal log:
```
   [WARNING] IBM watsonx failed, trying Gemini fallback.
```
10. **Check Telemetry** — hit `GET /api/v1/system/ai-status` to confirm `"current_primary_provider": "Gemini"`
11. **Restore IBM Key** — restore your valid key, regenerate, and confirm telemetry reverts to IBM automatically

<br>

## Project Structure

```
FundForge-AI/
├── backend/
│   ├── config/               # Environment config and settings
│   ├── controllers/          # API controllers (Auth, Grants, Proposals, System)
│   ├── database/             # DB setup, session manager, schema
│   ├── eligibility/          # Rules evaluation and scoring engine
│   ├── grant_engine/         # Curated grant registry
│   ├── ibm/                  # IBM Granite interface and fallback manager
│   ├── models/               # SQLAlchemy ORM models
│   ├── proposal_generator/   # Proposal document templating engine
│   ├── rag/                  # watsonx vector store integration
│   ├── routes/               # Flask Blueprint URL routers
│   ├── utils/                # PDF compiler, JWT helpers, response envelopes
│   ├── requirements.txt      # Python dependencies
│   └── wsgi.py               # Application entrypoint
│
├── frontend/
│   ├── src/
│   │   ├── components/       # Reusable UI component blocks
│   │   ├── contexts/         # Auth, Theme, Toast context stores
│   │   ├── services/         # HTTP API client services
│   │   ├── pages/            # Route page views (Landing, Proposal Builder)
│   │   └── App.jsx           # React route configuration
│   └── vite.config.js        # Vite dev config and API proxy rule
│
├── docs/                     # Technical references and architecture guides
├── tests/                    # pytest test suite
├── .env.example              # Environment variable template
└── README.md
```

<br>

## Troubleshooting

**`ModuleNotFoundError: No module named 'backend'`**
Run from the project root, not inside `/backend`. Use `python -m backend.wsgi`, not `python wsgi.py`.

**PowerShell execution policy error on Windows**
Run PowerShell as Administrator and execute:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope LocalMachine
```

**`.env` variables not loading / config crashes**
Ensure you ran `cp .env.example .env` from the project root and all mandatory fields are populated.

**Port 5000 or 5173 already in use**

Linux/macOS:
```bash
kill -9 $(lsof -t -i:5000)
```
Windows:
```powershell
Stop-Process -Id (Get-NetTCPConnection -LocalPort 5000).OwningProcess
```

**CORS errors in browser**
Ensure `CORS(app)` is configured in `backend/app.py` and Vite is proxying `/api/v1` to `http://localhost:5000` in `vite.config.js`.

<br>

## Contact

**Developer:** Rohit Posimsetti
**Email:** rohit122622@gmail.com
**GitHub:** [@Rohit122622](https://github.com/Rohit122622)

<br>

<p align="center">Distributed under the <strong>MIT License</strong>. See <a href="LICENSE">LICENSE</a> for details.</p>
