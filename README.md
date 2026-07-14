# FundForge AI 🚀

### AI-Powered Grant & Funding Discovery Platform for Indian Startups

> Discover government grants, evaluate startup eligibility with precision scoring, and generate tailored funding proposals — powered by IBM Granite AI with a 3-provider automatic fallback chain.

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.x-000000?style=flat-square&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-5-646CFF?style=flat-square&logo=vite&logoColor=white)](https://vitejs.dev/)
[![IBM watsonx](https://img.shields.io/badge/IBM-Granite_AI-BE95FF?style=flat-square&logo=ibm&logoColor=white)](https://www.ibm.com/watsonx)
[![RAG](https://img.shields.io/badge/RAG-watsonx_Index-FF6F00?style=flat-square)](https://www.ibm.com/watsonx)
[![JWT](https://img.shields.io/badge/Auth-JWT-000000?style=flat-square&logo=jsonwebtokens&logoColor=white)](https://jwt.io/)
[![SQLite](https://img.shields.io/badge/SQLite-Local_Dev-003B57?style=flat-square&logo=sqlite&logoColor=white)](https://sqlite.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat-square&logo=docker&logoColor=white)](https://docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Active-brightgreen?style=flat-square)]()
[![Version](https://img.shields.io/badge/Version-1.0.0-blue?style=flat-square)]()

FundForge AI is a production-grade fullstack platform that solves a critical challenge for Indian startups: **finding and winning the right government grants**. It combines a curated grant registry, a rules-based eligibility scoring engine, and IBM Granite AI-powered proposal generation with RAG to produce structured, context-aware funding proposals. The AI layer is resilient by design — automatic failover across IBM watsonx, Google Gemini, and Grok ensures zero downtime on proposal generation.

<br>

## Table of Contents

- [Highlights](#highlights)
- [Screenshots](#screenshots)
- [Architecture](#architecture)
- [AI Architecture](#ai-architecture)
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
- [Repository Overview](#repository-overview)
- [Future Roadmap](#future-roadmap)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)

<br>

## Highlights

✔ AI-powered Grant Discovery with curated Indian government grant registry  
✔ Rules-based Eligibility Scoring Engine with readiness percentage  
✔ Proposal Generation using IBM Granite AI  
✔ Retrieval-Augmented Generation (RAG) via watsonx Vector Index  
✔ 3-Provider AI Fallback Chain — IBM → Gemini → Grok  
✔ FSM-based Application Tracker with state transitions  
✔ PDF Proposal Export  
✔ Real-time AI Telemetry and provider health monitoring  
✔ Stateless JWT Authentication with access and refresh tokens  
✔ Responsive React SPA with Vite  

<br>

## Screenshots

### Landing Page
<img width="1917" height="1093" alt="image" src="https://github.com/user-attachments/assets/7e903a39-0d92-4007-ae9a-0eb5ac02424e" />


### Dashboard
<img width="1917" height="1091" alt="image" src="https://github.com/user-attachments/assets/0e9504df-9028-45f0-ad0b-414a4c994f2e" />


### Grant Explorer
<img width="1917" height="1087" alt="image" src="https://github.com/user-attachments/assets/07386d9a-2842-451f-856f-f0a4c35cc011" />


### Eligibility Checker
<img width="1917" height="1095" alt="image" src="https://github.com/user-attachments/assets/4fb6b62f-7ce3-4b4b-b3b7-bf13b142272b" />


### Proposal Generator
<img width="1917" height="1086" alt="image" src="https://github.com/user-attachments/assets/d2ab1335-73cb-436f-9a72-3af5a2b257e2" />


### Application Tracker
<img width="1917" height="1088" alt="image" src="https://github.com/user-attachments/assets/c458edee-7144-4b4e-8186-6a7b0e0c6d84" />


### AI Telemetry
<img width="1917" height="1086" alt="image" src="https://github.com/user-attachments/assets/30ed95b3-cbb8-4df4-92f9-624fcd793734" />


<br>

## Architecture

```
                 React (Vite) Frontend [SPA]
                              │
                              ▼  HTTP / Nginx Reverse Proxy
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

### Request Flow

```
User Request
     │
     ▼
React SPA (Vite)
     │  /api/v1  (proxied in dev / Nginx in prod)
     ▼
Flask API Layer
     │
     ├── JWT Middleware (auth check)
     │
     ├── Route Controller
     │        │
     │        ├── Eligibility Engine  (rules evaluation + score)
     │        │
     │        ├── RAG Engine          (watsonx vector retrieval)
     │        │
     │        └── Proposal Generator  (AI draft assembly)
     │
     └── SQLAlchemy ORM
              │
              ▼
        PostgreSQL / SQLite
```

<br>

## AI Architecture

FundForge AI uses a **3-tier AI provider chain** with automatic failover, instant recovery, and real-time telemetry.

```
┌─────────────────────────────────────────────┐
│             Proposal Generation Request     │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
          ┌────────────────────────┐
          │   IBM watsonx.ai       │  ◄── Primary Provider
          │   Granite Model        │      (RAG-enhanced)
          └────────────┬───────────┘
                       │ Failure / Quota Exhausted
                       ▼
          ┌────────────────────────┐
          │   Google Gemini        │  ◄── Secondary Fallback
          └────────────┬───────────┘
                       │ Failure
                       ▼
          ┌────────────────────────┐
          │   Grok / Llama         │  ◄── Tertiary Fallback
          │   (via Groq Cloud)     │
          └────────────┬───────────┘
                       │
                       ▼
          ┌────────────────────────┐
          │   AI Telemetry Layer   │
          │   /api/v1/system/      │
          │   ai-status            │
          └────────────────────────┘
```

**Telemetry tracks:**
- Active provider at any given moment
- Failover events and reason
- Response time in milliseconds
- Automatic recovery when primary provider comes back online

<br>

## Features

| Feature | Description |
|---------|-------------|
| **Grant Discovery** | Paginated, searchable catalog of government grants curated for Indian startups |
| **Eligibility Scoring** | Rules-based engine that scores a startup profile against grant criteria and returns a readiness percentage |
| **AI Proposal Generation** | IBM Granite AI with RAG retrieves semantic startup context and drafts a structured markdown proposal |
| **PDF Export** | Compiles generated proposals into a formatted, downloadable PDF report |
| **Application Tracker** | FSM-based tracker with state transitions: `SAVED` → `RESEARCHING` → `IN_PROGRESS` |
| **AI Telemetry** | Real-time visibility into active AI provider, fallback events, and response latency |
| **Grant Recommendations** | Matches startup profile to the most relevant grants in the catalog |
| **JWT Authentication** | Stateless auth with access and refresh token support via bcrypt password hashing |
| **3-Provider Fallback** | Automatic failover across IBM → Gemini → Grok with zero manual intervention |

<br>

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React 18, Vite 5, React Router |
| **Backend** | Python 3.11+, Flask 3.x, SQLAlchemy ORM |
| **Database** | PostgreSQL 16 (production), SQLite (local dev) |
| **Authentication** | JWT (access + refresh tokens), bcryptjs |
| **AI — Primary** | IBM watsonx.ai, Granite Model |
| **AI — Fallback** | Google Gemini, Grok via Groq Cloud |
| **RAG** | IBM watsonx Vector Index |
| **Caching / Queue** | Redis, Celery |
| **Proxy / Static** | Nginx (production), Vite Proxy (development) |
| **Testing** | pytest (13 tests across 4 modules) |
| **Deployment** | Docker-ready |

<br>

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Git | Any | For cloning the repository |
| Python | 3.11+ | Backend runtime |
| Node.js | 18.0.0+ | Frontend runtime |
| npm | 9.0.0+ | Bundled with Node.js |
| Redis | Any | Caching and Celery task broker |
| PostgreSQL | 14+ | Production database (SQLite used locally) |

**API keys required:**

| Provider | Required | Purpose | Where to Get |
|----------|----------|---------|--------------|
| IBM Cloud | Optional | Primary AI provider (Granite) | [IBM Cloud Console](https://cloud.ibm.com/) |
| Google Gemini | Yes | Secondary AI fallback | [Google AI Studio](https://aistudio.google.com/) |
| Groq Cloud | Yes | Tertiary AI fallback | [Groq Console](https://console.groq.com/) |

<br>

## Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/Rohit122622/FundForge-AI.git
cd FundForge-AI
```

### 2. Create and Activate a Python Virtual Environment

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

> **Windows tip:** If you encounter an execution policy error, run PowerShell as Administrator and execute:
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

Open `.env` and populate all required fields. See [Environment Variables](#environment-variables) below.

<br>

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `FLASK_ENV` | Runtime mode: `development`, `production`, or `testing` | `development` |
| `FLASK_SECRET_KEY` | Flask session cookie signing secret | Secure random string |
| `JWT_SECRET` | Signing key for JWT access and refresh tokens | Secure random string |
| `DATABASE_URL` | SQLAlchemy database connection string | `sqlite:///instance/fundforge.db` |
| `REDIS_URL` | Redis server connection string | `redis://localhost:6379/0` |
| `IBM_API_KEY` | IBM watsonx.ai API key | `your-ibm-api-key` |
| `IBM_PROJECT_ID` | IBM watsonx workspace project GUID | `your-project-guid` |
| `IBM_URL` | IBM Cloud inference endpoint | `https://us-south.ml.cloud.ibm.com` |
| `GEMINI_API_KEY` | Google Gemini API key (secondary fallback) | `your-gemini-api-key` |
| `GROQ_API_KEY` | Groq Cloud API key (tertiary fallback) | `your-groq-api-key` |

> Never commit your `.env` file. It is excluded from version control via `.gitignore`.

<br>

## Database Setup

### Local Development — SQLite (Default)

The database file is created automatically inside `instance/` on first run. Just apply migrations:

```bash
flask --app backend.wsgi db upgrade
```

### Production — PostgreSQL

**1. Create the database:**

```sql
CREATE DATABASE fundforge_db;
```

**2. Set `DATABASE_URL` in `.env`:**

```env
DATABASE_URL=postgresql://<user>:<password>@localhost:5432/fundforge_db
```

**3. Apply migrations:**

```bash
flask --app backend.wsgi db upgrade
```

<br>

## Running the Application

### Backend

Run from the **project root directory** — not from inside `/backend`:

```bash
python -m backend.wsgi
```

> **Why `-m backend.wsgi` and not `python wsgi.py`?**  
> The backend uses package-absolute imports (e.g. `from backend.app import ...`). Running from inside `backend/` causes a `ModuleNotFoundError` because Python cannot locate the parent package. The `-m` flag injects the workspace root into `sys.path` correctly.

Backend available at: `http://localhost:5000`  
Health check: `http://localhost:5000/api/v1/system/ai-status`

### Frontend

Open a **new terminal**, then:

```bash
cd frontend
npm install
npm run dev
```

Frontend available at: `http://localhost:5173`

> API calls to `/api/v1` are automatically proxied to `http://localhost:5000` via `vite.config.js`. No manual CORS configuration is needed in development.

<br>

## Production Build

```bash
cd frontend
npm run build
```

Minified static assets are output to `frontend/dist/`. In production, Nginx serves these assets directly and reverse-proxies `/api/v1` traffic to the Gunicorn application server.

<br>

## Running Tests

Ensure your virtual environment is active, then from the project root:

```bash
python -m pytest
```

The test suite covers **13 tests across 4 modules:**

| Test File | Coverage |
|-----------|----------|
| `tests/test_auth.py` | User registration, login, and permission validation |
| `tests/test_grants.py` | Grant catalog retrieval and query filtering |
| `tests/test_tracker.py` | Application tracker FSM state transition validation |
| `tests/test_ai_fallback.py` | AI provider failover chain and recovery |

<br>

## API Reference

All JWT-protected endpoints require: `Authorization: Bearer <token>`

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
| `POST` | `/api/v1/proposals/generate` | JWT | Generate an AI proposal draft with RAG |
| `POST` | `/api/v1/documents/generate-pdf` | JWT | Compile proposal into a downloadable PDF |

### Application Tracker

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/api/v1/tracker/` | JWT | List all tracked grant applications |
| `POST` | `/api/v1/tracker/<id>/transition` | JWT | Execute FSM state transition |

### System

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/api/v1/system/ai-status` | Public | Live AI provider telemetry and fallback metrics |

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

Follow this sequence to verify all platform capabilities end-to-end.

**1. Register an account**  
Navigate to `http://localhost:5173/register` and create a new user account.

**2. Log in**  
Authenticate at `http://localhost:5173/login`. You will receive a JWT access token stored in the client.

**3. Build your startup profile**  
Complete the onboarding form with your startup's founding year, sector, stage, and description. This profile powers eligibility scoring and RAG context retrieval.

**4. Explore the grant catalog**  
Browse and filter grants on the Grant Explorer page.

**5. Check eligibility**  
Select a grant (e.g. Startup India Seed Fund Scheme) and trigger the Eligibility Checker. You will receive a scorecard showing matched criteria and a final readiness percentage.

**6. Generate a proposal**  
Click Generate Proposal. The RAG engine retrieves semantic context from your startup profile, and IBM Granite drafts a structured markdown funding proposal.

**7. Download the PDF**  
Click Download PDF to package the proposal into a formatted PDF report.

**8. Track your application**  
Click Track Application. The tracker initialises at `SAVED`. Transition it through `RESEARCHING` → `IN_PROGRESS`.

**9. Test AI failover**  
Set an invalid `IBM_API_KEY` in `.env` to simulate a quota failure. Regenerate a proposal and observe the backend terminal:
```
[WARNING] IBM watsonx failed, trying Gemini fallback.
```
The proposal generates successfully via Gemini.

**10. Verify telemetry**  
Hit `GET /api/v1/system/ai-status`. Confirm `"current_primary_provider": "Gemini"` and `"fallback_used": true`.

**11. Confirm recovery**  
Restore your valid `IBM_API_KEY` in `.env`. Regenerate a proposal. Telemetry automatically reverts to IBM as primary — no restart required.

<br>

## Project Structure

```
FundForge-AI/
├── backend/
│   ├── config/               # Environment configuration and settings
│   ├── controllers/          # API controllers (Auth, Grants, Proposals, System)
│   ├── database/             # DB setup, session manager, and schema
│   ├── eligibility/          # Rules evaluation and scoring engine
│   ├── grant_engine/         # Curated government grant registry
│   ├── ibm/                  # IBM Granite interface and AI fallback manager
│   ├── models/               # SQLAlchemy ORM models
│   ├── proposal_generator/   # Proposal document templating engine
│   ├── rag/                  # watsonx vector store integration
│   ├── routes/               # Flask Blueprint URL routers
│   ├── utils/                # PDF compiler, JWT helpers, response envelopes
│   ├── requirements.txt      # Python backend dependencies
│   └── wsgi.py               # Application entrypoint
│
├── frontend/
│   ├── src/
│   │   ├── components/       # Reusable UI component blocks
│   │   ├── contexts/         # Auth, Theme, and Toast context stores
│   │   ├── services/         # HTTP API client services
│   │   ├── pages/            # Route page views (Landing, Proposal Builder)
│   │   └── App.jsx           # React route configuration
│   └── vite.config.js        # Vite dev config and API proxy rule
│
├── docs/                     # Technical references and architecture guides
├── tests/
│   ├── test_auth.py          # Authentication and permission tests
│   ├── test_grants.py        # Grant catalog retrieval tests
│   ├── test_tracker.py       # FSM state transition tests
│   └── test_ai_fallback.py   # AI fallback chain tests
├── .env.example              # Environment variable template
└── README.md
```

<br>

## Troubleshooting

**`ModuleNotFoundError: No module named 'backend'`**  
You are running the command from inside the `backend/` subdirectory. Navigate to the project root (`cd ..`) and use `python -m backend.wsgi` instead of `python wsgi.py`.

**PowerShell execution policy error on Windows**  
Run PowerShell as Administrator and execute:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope LocalMachine
```

**`.env` variables not loading / config crashes**  
Ensure you ran `cp .env.example .env` from the project root and that all mandatory fields are populated with valid values.

**Port 5000 or 5173 already in use**

Linux / macOS:
```bash
kill -9 $(lsof -t -i:5000)
```
Windows:
```powershell
Stop-Process -Id (Get-NetTCPConnection -LocalPort 5000).OwningProcess
```

**CORS errors in the browser**  
Verify that `CORS(app)` is correctly configured in `backend/app.py` and that `vite.config.js` is proxying `/api/v1` requests to `http://localhost:5000`.

**AI proposal generation failing across all providers**  
Check that `GEMINI_API_KEY` and `GROQ_API_KEY` are valid in `.env`. At least one fallback provider must be operational for proposal generation to succeed.

<br>

## Repository Overview

| Property | Detail |
|----------|--------|
| **Project Type** | Fullstack Web Application |
| **Primary Language** | Python (Backend), JavaScript (Frontend) |
| **Architecture** | Decoupled REST API + React SPA |
| **Frontend** | React 18, Vite 5 |
| **Backend** | Flask 3.x, SQLAlchemy ORM |
| **Database** | PostgreSQL (prod), SQLite (dev) |
| **AI Models** | IBM Granite, Google Gemini, Grok/Llama |
| **Authentication** | Stateless JWT with bcrypt |
| **Deployment** | Nginx + Gunicorn, Docker-ready |
| **Test Coverage** | 13 tests across 4 modules |
| **License** | MIT |
| **Status** | Active |

<br>

## Future Roadmap

- [ ] **Docker Compose Setup** — One-command local deployment for backend, frontend, Redis, and PostgreSQL
- [ ] **Email Notifications** — Automated alerts for grant deadlines, application status changes, and proposal readiness
- [ ] **Additional Grant Sources** — Expand the grant registry to include state-level schemes, SIDBI programs, and DPIIT initiatives
- [ ] **Admin Dashboard** — Internal panel for managing the grant catalog, user accounts, and MRV data
- [ ] **Advanced Analytics** — Sector-wise grant success rates, eligibility trend analysis, and proposal performance metrics
- [ ] **Mobile Application** — React Native iOS and Android client
- [ ] **Multi-language Support** — Hindi and regional language UI for broader accessibility
- [ ] **Vector Search Improvements** — Hybrid dense-sparse retrieval for more accurate RAG context
- [ ] **Real-time Collaboration** — Multi-user proposal editing with shared workspaces

<br>

## Contributing

Contributions are welcome. Please follow this workflow:

**1. Fork the repository**
```bash
# Click "Fork" on https://github.com/Rohit122622/FundForge-AI
```

**2. Clone your fork**
```bash
git clone https://github.com/<your-username>/FundForge-AI.git
cd FundForge-AI
```

**3. Create a feature branch**
```bash
git checkout -b feature/your-feature-name
```

**4. Make your changes and commit**
```bash
git add .
git commit -m "feat: add your feature description"
```

**5. Push to your fork**
```bash
git push origin feature/your-feature-name
```

**6. Open a Pull Request**  
Go to `https://github.com/Rohit122622/FundForge-AI` and click **New Pull Request**. Describe your changes clearly and link any relevant issues.

<br>

## License

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for full details.

<br>

## Contact

**Developer:** Rohit Posimsetti  
**Email:** rohit122622@gmail.com  
**GitHub:** [@Rohit122622](https://github.com/Rohit122622)  
**LinkedIn:** [Add your LinkedIn URL here]

<br>

<p align="center">
  Built with care for the Indian startup ecosystem.
  <br>
  If this project helped you, consider giving it a ⭐ on <a href="https://github.com/Rohit122622/FundForge-AI">GitHub</a>.
</p>
