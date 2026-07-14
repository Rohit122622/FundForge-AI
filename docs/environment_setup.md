# Environment Setup Guide

This guide describes how to configure the environment variables required by FundForge AI for development, testing, and production environments.

---

## 📋 Environment Configuration Checklists

All configurations are read from the `.env` file located in the project root directory.

### 1. General & Security Settings

| Variable | Description | Default / Example | Required In |
|---|---|---|---|
| `FLASK_ENV` | Mode to run Flask (`development`, `production`, `testing`) | `development` | All |
| `FLASK_SECRET_KEY` | Key for session signing & cookie serialization | *Generate a secure random string* | Production |
| `JWT_SECRET` | Secret key used to sign JWT Access/Refresh tokens | *Generate a secure random string* | Production |

### 2. Databases & Cache Services

| Variable | Description | Default / Example | Required In |
|---|---|---|---|
| `DATABASE_URL` | SQLAlchemy Connection URI for PostgreSQL DB | `postgresql://user:pass@localhost:5432/db` | Production / Dev |
| `REDIS_URL` | Redis URL for Celery background tasks & rate limiter caching | `redis://localhost:6379/0` | Production |

### 3. AI Providers Configuration

FundForge AI implements a resilient, tiered fallback chain. Keys for all three layers must be set to ensure transparent failovers.

#### IBM watsonx.ai (Primary Provider)
* **`IBM_API_KEY`**: IBM Cloud API key generated from the IAM dashboard.
* **`IBM_PROJECT_ID`**: Project GUID linked to your watsonx.ai instance.
* **`IBM_URL`**: Region URL for IBM Cloud watsonx inference service (e.g. `https://us-south.ml.cloud.ibm.com`).
* **`IBM_GRANITE_MODEL_ID`**: Primary inference model. Default: `ibm/granite-13b-instruct-v2`.

#### Google Gemini API (Secondary Fallback)
* **`GEMINI_API_KEY`**: API Key obtained from Google AI Studio. Used by `GeminiProvider` when IBM exhausts its quota, times out, or fails.

#### Grok/Groq Cloud API (Tertiary Fallback)
* **`GROQ_API_KEY`**: API Key obtained from Groq Console. Used to query the `llama3-8b-8192` model as the final failover layer.

---

## 🛠️ Local Development Installation

### Backend Setup (Flask)

1. Navigate to the backend directory and install Python dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```
2. Run database migrations:
   ```bash
   flask db upgrade
   ```
3. Run the development server:
   ```bash
   flask run --port=5000
   ```

### Frontend Setup (Vite + React)

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Run the hot-reloading development server:
   ```bash
   npm run dev
   ```

---

## 🛡️ Env Validation Checks

During application startup (via the Flask Application Factory in `app.py`), the settings validation engine runs:
- If a critical environment variable is missing (e.g. `FLASK_SECRET_KEY` in production mode), the server will log an error and refuse to start.
- If fallback provider keys are missing, the server will emit warning logs advising that failover layers are inactive.
