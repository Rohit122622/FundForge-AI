# FundForge AI — AI-Powered Grant & Funding Finder

FundForge AI is a production-grade, AI-powered platform for discovering government grants, evaluating eligibility, and generating tailored funding proposals for Indian startups.

This guide provides absolute step-by-step instructions to get the platform up and running locally or in production.

---

## 🏗️ Project Architecture

```
                 React (Vite) Frontend [SPA]
                              │
                              ▼ (HTTP Nginx Proxy)
                     Flask Backend API
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
  Authentication     Eligibility Engine     Proposal Generator
  (JWT, bcrypt)        (Rules-based)         (IBM Granite AI)
        │                     │                     │
        ▼                     ▼                     ▼
  PostgreSQL DB          RAG Engine        AI Fallback Chain
 (SQLAlchemy ORM)     (watsonx Index)     (IBM ➔ Gemini ➔ Grok)
```

---

## 📋 1. Prerequisites

Before starting, ensure you have the following software installed:

* **Git**: To clone and manage code.
* **Python**: Version `3.11` or higher.
* **Node.js**: Version `18.0.0` or higher.
* **npm**: Version `9.0.0` or higher (installed automatically with Node.js).
* **IBM Cloud Account** (Optional): Required if utilizing Granite as primary inference.
* **Gemini API Key**: Required for fallback generation (obtainable from Google AI Studio).
* **Grok API Key**: Required for tertiary fallback generation (obtainable from Groq Console).

---

## 📥 2. Cloning the Project

Open your terminal or command prompt and execute:

```bash
git clone https://github.com/your-org/FundForge-AI.git
cd FundForge-AI
```

---

## 🐍 3. Backend Setup

### Step A: Create and Activate Virtual Environment
Run the commands from the **project root directory**:

**On Windows (PowerShell):**
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

**On Linux / macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step B: Install Python dependencies
Install all package requirements inside the activated virtual environment:
```bash
pip install -r backend/requirements.txt
```

### Step C: Environment Configuration
Copy the sample environment file to `.env` in the **project root folder**:
```bash
cp .env.example .env
```

Open `.env` and fill in the configuration variables.

#### Environment Variables Reference

| Variable | Description | Example / Recommended Value |
|---|---|---|
| `FLASK_ENV` | Running environment mode (`development`, `production`, `testing`) | `development` |
| `FLASK_SECRET_KEY` | Flask session cookie signing secret | *Create a secure random string* |
| `JWT_SECRET` | Secret key used to sign JWT Access/Refresh tokens | *Create a secure random string* |
| `DATABASE_URL` | SQLAlchemy Database connection string | `sqlite:///instance/fundforge.db` (for local dev) |
| `REDIS_URL` | Redis server connection string (caching & celery task broker) | `redis://localhost:6379/0` |
| `IBM_API_KEY` | IBM watsonx.ai Cloud API key | `OdvxVIMDwheMwyVeN...` |
| `IBM_PROJECT_ID` | Project GUID linked to watsonx workspace | `8a219719-a8b5-4c0e-...` |
| `IBM_URL` | IBM Cloud Watson inference URL | `https://us-south.ml.cloud.ibm.com` |
| `GEMINI_API_KEY` | Google Gemini API key (secondary fallback) | `AIzaSyDG-_voPS0xD...` |
| `GROQ_API_KEY` | Groq Cloud API Key (tertiary Grok/Llama fallback) | `gsk_CJyWdxjHjR8vl...` |

---

## 🗄️ 4. Database Setup & Migrations

FundForge AI uses SQLAlchemy ORM to manage database structures and support both local **SQLite** and production-grade **PostgreSQL**.

### Option A: Local SQLite (Default)
When using the SQLite database (`sqlite:///instance/fundforge.db`):
- The database file is created automatically inside the `instance/` folder on first start.
- Run database migrations to construct the tables:
  ```bash
  flask --app backend.wsgi db upgrade
  ```

### Option B: Production PostgreSQL
When deploying with PostgreSQL:
1. Initialize the PostgreSQL server and create a database named `fundforge_db`:
   ```sql
   CREATE DATABASE fundforge_db;
   ```
2. Set the `DATABASE_URL` in `.env`:
   ```env
   DATABASE_URL=postgresql://<user>:<password>@localhost:5432/fundforge_db
   ```
3. Run the migrations to synchronize schemas:
   ```bash
   flask --app backend.wsgi db upgrade
   ```

---

## 🚀 5. Running the Backend Server

To start the backend, execute the following command from the **project root dir
```

### Why is this the correct command?
1. **Absolute Packages**: The backend python code uses package-absolute imports (e.g. `from backend.app import ...`). Running `python wsgi.py` from inside the `backend` folder will crash with a `ModuleNotFoundError` because Python is unaware of the parent path. Executing `python -m backend.wsgi` from the root injects the workspace root folder into `sys.path`.
2. **WSGI Entry Point**: `backend/app.py` implements the Flask Application Factory pattern, exposing `create_app()`. It does not execute a server when run directly. `backend/wsgi.py` initializes the app and executes the development server on `http://localhost:5000`.

---

## 💻 6. Frontend Setup

Open a new terminal window, navigate to the frontend folder, and launch the Vite development server:

```bash
cd frontend
npm install
npm run dev
```

* The dev server will spin up on default Vite port: **`http://localhost:5173`**
* Requests targeting `/api/v1` are automatically proxied to the Flask server at `http://localhost:5000` via configuration in `vite.config.js`.

---

## 📦 7. Production Build

To compile and bundle frontend assets for production:

```bash
cd frontend
npm run build
```

* **Output Folder**: High-performance, minified static files are generated in `frontend/dist/`.
* In production, the Nginx web server serves these static assets directly and reverse-proxies `/api/v1` traffic to the backend Gunicorn sockets.

---

## 🧪 8. Running Tests

### Backend Unit & Integration Tests
Ensure your virtual environment is active and run:
```bash
python -m pytest
```

This runs the complete suite of **13 tests** covering:
- User authentication and permissions validation (`tests/test_auth.py`)
- Curated grants catalog retrieval and queries (`tests/test_grants.py`)
- Application Tracker FSM state transition validation (`tests/test_tracker.py`)
- AI provider fallback manager failovers (`tests/test_ai_fallback.py`)

### Frontend Tests
Currently, no frontend component tests are configured. Build checks are validated via `npm run build` during CI runs.

---

## 🚶‍♂️ 9. End-to-End Demo Walkthrough

Follow this sequence to test and verify all platform capabilities:

1. **Register an Account**: Go to `http://localhost:5173/register` and create an account.
2. **Login**: Authenticate at `http://localhost:5173/login` to obtain your JWT token.
3. **Build Startup Profile**: Complete the onboarding form, entering details such as founding year, sector, stage, and descriptions.
4. **Discover curations**: Search/filter the catalog on the Grant Explorer page.
5. **Evaluate Eligibility**: Choose a grant (e.g. `Startup India Seed Fund Scheme`) and trigger the Eligibility Checker. You will receive a score card showing matching criteria and a final readiness percentage.
6. **Generate Proposal**: Click "Generate Proposal". The system uses RAG to retrieve semantic startup context and drafts a structured markdown grant proposal.
7. **Download PDF Report**: Click "Download PDF" to request the PDF compiler, which packages the proposal details into a structured document.
8. **Track Application State**: Click "Track Application". Enters the application tracking system at the `SAVED` state. Transition it to `RESEARCHING`, then `IN_PROGRESS`.
9. **Test AI Failover Chain**:
   - Temporarily modify your `.env` or configuration to supply an invalid `IBM_API_KEY` (simulating quota limit/quota exhausted).
   - Generate a proposal again.
   - Look at the terminal backend log; it shows the transition block:
     `[WARNING] IBM watsonx failed, trying Gemini fallback.`
     It then queries Gemini and finishes successfully.
10. **Query AI Telemetry**:
    - Hit `GET /api/v1/system/ai-status` in your browser or Postman.
    - Expected output:
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
    - Restore your correct `IBM_API_KEY` in `.env`.
    - Trigger another proposal. The telemetry status reverts to `"IBM"` as primary automatically, proving instant recovery.

---

## 🗺️ 10. API Endpoints Reference

| Verb | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/v1/auth/register` | Public | Register a new user |
| `POST` | `/api/v1/auth/login` | Public | Authenticate user & retrieve JWTs |
| `GET` | `/api/v1/grants/` | Public | Paginated list of grants with search |
| `GET` | `/api/v1/grants/<id>` | Public | Retrieve single grant catalog details |
| `POST` | `/api/v1/grants/recommend` | JWT | Get matched list |
| `POST` | `/api/v1/eligibility/check` | JWT | Check startup match criteria |
| `POST` | `/api/v1/proposals/generate` | JWT | Generate AI draft with RAG |
| `GET` | `/api/v1/tracker/` | JWT | List active tracked applications |
| `POST` | `/api/v1/tracker/<id>/transition` | JWT | Execute FSM status transition |
| `POST` | `/api/v1/documents/generate-pdf` | JWT | Package a proposal as a PDF |
| `GET` | `/api/v1/system/ai-status` | Public | Expose fallback metrics and health |

---

## 🔧 11. Troubleshooting

### 1. `ModuleNotFoundError: No module named 'backend'`
* **Cause**: Running commands from inside the `backend` subdirectory.
* **Fix**: Navigate back to the parent directory (`cd ..`) and execute python commands using the `-m` module flag, e.g., `python -m backend.wsgi`.

### 2. PowerShell script execution disabled
* **Cause**: Windows Execution Policy prevents loading PS scripts.
* **Fix**: Run PowerShell as Administrator and execute:
  ```powershell
  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope LocalMachine
  ```

### 3. Missing env variables / Config crashes
* **Cause**: `.env` file not created or not populated with mandatory fields.
* **Fix**: Ensure `cp .env.example .env` was run in the root directory, and verify keys are correctly filled.

### 4. Gunicorn or Python port 5000/5173 already in use
* **Cause**: Another service is occupying the port.
* **Fix**: Find and kill the process:
  - **Windows**: `Stop-Process -Id (Get-NetTCPConnection -LocalPort 5000).OwningProcess`
  - **Linux/macOS**: `kill -9 $(lsof -t -i:5000)`

### 5. CORS Errors
* **Cause**: Frontend tries to communicate with Backend at a host/port mismatch without options header allowances.
* **Fix**: Ensure the `CORS(app)` configurations are intact in `backend/app.py` and that the Vite configuration proxies calls to the correct port.

---

## 📂 12. Project Directory Structure

```
FundForge-AI/
├── backend/                   # Flask Server Application Code
│   ├── config/                # Environment configuration & settings
│   ├── controllers/           # API controllers (Auth, Grants, Proposals, System)
│   ├── database/              # DB setup, session manager, schema
│   ├── eligibility/           # Rules evaluation & scoring algorithm
│   ├── grant_engine/          # Curated grant registry database
│   ├── ibm/                   # AI Provider interface (Granite, Fallback manager)
│   ├── models/                # SQLAlchemy database models
│   ├── proposal_generator/    # Proposal document templating engine
│   ├── rag/                   # watsonx vector store integration
│   ├── routes/                # Blueprint URL router setup
│   ├── utils/                 # PDF compilers, JWT, response envelope helpers
│   ├── requirements.txt       # Python backend dependencies list
│   └── wsgi.py                # Core entry point python file
├── frontend/                  # React SPA Client Code (Vite)
│   ├── src/
│   │   ├── components/        # Reusable UI component blocks
│   │   ├── contexts/          # Context stores (Auth, Theme, Toasts)
│   │   ├── services/          # HTTP API client services
│   │   ├── pages/             # Route page views (Landing, Proposal builder)
│   │   └── App.jsx            # React route configurations
│   └── vite.config.js         # Vite dev configuration & API Proxy rule
└── docs/                      # Technical references & architecture guides
```
