# Production Deployment Instructions

This document details the step-by-step instructions to deploy FundForge AI to production environments using Docker Compose, Nginx, and GitHub Actions.

---

## 🐳 Dockerized Multi-Container Architecture

Production deployment orchestrates four distinct container services defined in `docker-compose.yml`:
1. **`fundforge_nginx`**: Reverse proxy mapping public port `80`/`443` to frontend files and routing `/api/v1` to the backend.
2. **`fundforge_backend`**: WSGI Flask server executed via Gunicorn using gevent asynchronous workers.
3. **`fundforge_db`**: Persistent PostgreSQL database storage.
4. **`fundforge_redis`**: Celery broker, caching database, and API rate limiter.

---

## 🚀 Step-by-Step Deployment Guide

### Step 1: Clone and Environment Config

1. Clone the repository to the production server:
   ```bash
   git clone https://github.com/your-org/FundForge-AI.git /opt/fundforge
   cd /opt/fundforge
   ```
2. Create your production environment settings file:
   ```bash
   cp .env.example .env
   ```
3. Update settings in `.env`:
   - Set `FLASK_ENV=production`
   - Set unique, cryptographically strong random secrets for `FLASK_SECRET_KEY` and `JWT_SECRET`:
     ```bash
     python -c "import secrets; print(secrets.token_hex(32))"
     ```
   - Provide credentials for IBM watsonx, Google Gemini, and Groq.

### Step 2: Build and Launch Containers

1. Run the build command to bundle the Vite production frontend and package the Flask application container:
   ```bash
   docker compose build
   ```
2. Start the service stack in detached background mode:
   ```bash
   docker compose up -d
   ```
3. Verify all services are online and healthy:
   ```bash
   docker compose ps
   ```

### Step 3: Run Database Migrations

Apply database DDL updates inside the backend container context:
```bash
docker compose exec backend flask db upgrade
```

---

## 🔒 Production Security Checklist

* [ ] **SSL/TLS Encryption**: Modify `nginx/nginx.conf` to enable SSL termination on port `443` using Let's Encrypt certificates.
* [ ] **Database Backups**: Schedule recurring cron jobs to back up the PostgreSQL volume:
  ```bash
  pg_dump -U fundforge_user fundforge_db > backup.sql
  ```
* [ ] **Gunicorn Workers**: The backend `Dockerfile` launches with 4 asynchronous workers (`--workers 4 --worker-class gevent`). For heavy production loads, scale this to `(2 * CPU_CORES) + 1`.
* [ ] **Credentials Management**: Do not commit the `.env` file to source control. In cloud providers (AWS ECS, GCP Cloud Run), inject credentials using Secret Manager parameters.

---

## 🔄 CI/CD Pipeline (GitHub Actions)

The repository configures a complete automated CI/CD pipeline in `.github/workflows/ci.yml`:
1. **Lint & Test**: Runs automated unit tests and code checks.
2. **Vite Build Verification**: Runs the frontend compiler to verify bundling passes without typescript or syntax errors.
3. **Docker Build Check**: Initiates a dry-run image generation sequence for the backend app.
