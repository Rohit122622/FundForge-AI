# API Documentation

FundForge AI exposes a versioned REST API under the `/api/v1` URL prefix. All successful requests return standard JSON envelopes.

---

## 🔒 Security & Authentication

All protected endpoints require an authorization header carrying a valid JWT Bearer access token:
```http
Authorization: Bearer <your-access-token>
```

---

## 📂 Endpoints Reference

### 1. Authentication

#### Register User
* **Endpoint**: `POST /api/v1/auth/register`
* **Content-Type**: `application/json`
* **Request Body**:
  ```json
  {
    "email": "founder@startup.in",
    "password": "SecurePassword123!",
    "first_name": "Raj",
    "last_name": "Kumar"
  }
  | Field | Type | Description |
  |---|---|---|
  | `email` | string | Valid unique email address |
  | `password` | string | String satisfying complexity constraints |
  | `first_name` | string | First name |
  | `last_name` | string | Last name |
  ```
* **Success Response (201 Created)**:
  ```json
  {
    "success": true,
    "data": {
      "user": {
        "id": "user-uuid",
        "email": "founder@startup.in",
        "first_name": "Raj",
        "last_name": "Kumar"
      }
    },
    "message": "User registered successfully."
  }
  ```

#### Login / Authenticate
* **Endpoint**: `POST /api/v1/auth/login`
* **Request Body**:
  ```json
  {
    "email": "founder@startup.in",
    "password": "SecurePassword123!"
  }
  ```
* **Success Response (200 OK)**:
  ```json
  {
    "success": true,
    "data": {
      "access_token": "eyJhbGciOi...",
      "refresh_token": "eyJhbGciOi...",
      "user": {
        "id": "user-uuid",
        "email": "founder@startup.in",
        "role": "founder"
      }
    },
    "message": "Login successful."
  }
  ```

---

### 2. Grants Catalog

#### List & Search Grants
* **Endpoint**: `GET /api/v1/grants`
* **Parameters**:
  - `page` (int, default `1`)
  - `per_page` (int, default `20`)
  - `q` (string search term)
  - `sector` (string sector filter)
  - `stage` (string stage filter)
* **Success Response (200 OK)**:
  ```json
  {
    "success": true,
    "data": [
      {
        "id": "sisfs",
        "title": "Startup India Seed Fund Scheme",
        "max_funding_amount": 2000000,
        "description": "Financial assistance to startups for proof of concept..."
      }
    ],
    "message": "Grants retrieved successfully."
  }
  ```

---

### 3. AI Proposal Generator

#### Generate Full Proposal Draft
* **Endpoint**: `POST /api/v1/proposals/generate`
* **Headers**: Requires Bearer JWT
* **Request Body**:
  ```json
  {
    "grant_id": "sisfs",
    "startup_profile": {
      "company_name": "NeoTech Solutions",
      "stage": "seed",
      "industry": "healthcare",
      "description": "We are building an AI-powered ECG diagnostic monitor...",
      "problem_statement": "Cardiac diagnostics are inaccessible in rural areas...",
      "solution_statement": "A low-cost IoT ECG device linking patients to clinicians..."
    },
    "sections": ["executive_summary", "problem_analysis"],
    "tone": "professional",
    "use_rag": true
  }
  ```
* **Success Response (201 Created)**:
  ```json
  {
    "success": true,
    "data": {
      "proposal_id": "proposal-uuid",
      "version": 1,
      "status": "complete",
      "quality_score": 85,
      "readiness_band": "Ready to Submit",
      "draft": {
        "sections": {
          "executive_summary": "## Executive Summary\nNeoTech Solutions is developing a revolutionary cardiac...",
          "problem_analysis": "## Problem Analysis\nIn rural India, cardiac patients face severe delays..."
        }
      },
      "ai_metadata": {
        "provider": "IBM",
        "fallback_used": false,
        "response_time_ms": 1250.4
      }
    },
    "message": "Proposal generated successfully. Quality: 85/100."
  }
  ```

---

### 4. Telemetry & Observability

#### Get AI Fallback Engine Status
* **Endpoint**: `GET /api/v1/system/ai-status`
* **Success Response (200 OK)**:
  ```json
  {
    "success": true,
    "data": {
      "current_primary_provider": "IBM",
      "fallback_chain": ["IBM", "Gemini", "Grok"],
      "provider_health": {
        "IBM": true,
        "Gemini": true,
        "Grok": true
      },
      "last_active_provider": "IBM",
      "fallback_used": false,
      "response_time_ms": 1250.4
    },
    "message": "AI status retrieved successfully."
  }
  ```
