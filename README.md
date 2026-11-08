# ShiftBridge API

ShiftBridge is a modern shift and project management API built with **FastAPI**, **SQLAlchemy**, and an **AI assistant powered by local LLMs via the OpenAI API** standard (such as Ollama, LM Studio, vLLM, or LocalAI).

Workers can chat with the local AI model to view coworker schedules, inspect their own shifts, and reschedule their shifts with automated conflict checking.

---

## Features

- **Authentication & Security**: Secure user signup, login, and profile access using JWT Bearer tokens and bcrypt password hashing.
- **Projects & Shifts Models**:
  - `Project`: Tracks project title, manager (`manager_id` foreign key), and assigned workers (many-to-many relationship).
  - `Shift`: Tracks project association (`project_id`), worker ownership (`owner_id`), `start_date`, and duration (`length`).
- **Local AI Agent via OpenAI API**:
  - Connects to any OpenAI-compatible local model server (e.g., Ollama at `http://localhost:11434/v1` or custom host).
  - Uses OpenAI function calling / tools to inspect coworker shifts and execute shift reschedules directly against the database.
  - Built-in resilient fallback engine to ensure offline continuity and instant test execution.
- **Data Seeding**: Instant database seeding script generating 1 manager, 15 worker accounts, 1 project, and staggered shifts.

---

## Tech Stack

- **Framework**: FastAPI
- **Database / ORM**: SQLite & SQLAlchemy 2.0
- **Validation**: Pydantic v2
- **AI / LLM Integration**: `openai` Python SDK (OpenAI-compatible local LLM endpoint with Tool Calling)
- **Testing**: Pytest & Starlette TestClient

---

## Getting Started

### 1. Prerequisites

- Python 3.10 or higher
- (Optional) Local LLM runner such as [Ollama](https://ollama.com/), [LM Studio](https://lmstudio.ai/), or vLLM.

### 2. Clone & Setup Virtual Environment

```bash
# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
# On Linux/macOS:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate
```

### 3. Install Dependencies

Install all required packages using `requirements.txt`:

```bash
pip install -r requirements.txt
```

---

## Configuration

Create or modify your `.env` file in the root directory (refer to `.env.example`):

```ini
APP_NAME="ShiftBridge API"
DEBUG_MODE=true
DATABASE_URL="sqlite:///./shiftbridge.db"
SECRET_KEY="your-secure-jwt-secret-key"

# Local LLM settings (OpenAI-compatible endpoint)
LOCAL_LLM_BASE_URL="http://localhost:11434/v1"
LOCAL_LLM_API_KEY="ollama"
LOCAL_LLM_MODEL="llama3.2"
```

> **Note on Local LLMs**:
> If you are using Ollama, ensure your model is pulled:
> ```bash
> ollama pull llama3.2
> # or
> ollama pull qwen2.5
> ```

---

## Database Seeding

To seed the database with **1 manager**, **15 workers in one project**, and **15 upcoming scheduled shifts**, run:

```bash
python seed.py
```

### Sample Seeded Credentials

| Role | Email | Password | Details |
|---|---|---|---|
| **Manager** | `manager@shiftbridge.com` | `password123` | Sarah Connor (Project Manager) |
| **Worker 1** | `worker1@shiftbridge.com` | `password123` | Alex Morgan |
| **Worker 2** | `worker2@shiftbridge.com` | `password123` | Brian Davis |
| ... | ... | ... | ... |
| **Worker 15** | `worker15@shiftbridge.com` | `password123` | Olivia Martinez |

To reset and re-seed the database:

```bash
python seed.py --reset
```

---

## Running the Application

Start the FastAPI application with Uvicorn:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Once running:
- **API Root**: [http://localhost:8000/](http://localhost:8000/)
- **Interactive Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## Running Automated Tests

Run the full test suite using `pytest`:

```bash
pytest
```

Run tests with verbose output:

```bash
pytest -v
```

The test suite covers:
- User signup, duplicate validation, login, and JWT authentication (`tests/test_auth.py`)
- Project and Shift model creation, many-to-many worker assignment, relationships, and cascading deletes (`tests/test_models.py`)
- AI Chat endpoints, OpenAI tool calling round-trip, multi-turn reschedule, and direct shift APIs (`tests/test_chat_and_tools.py`)
- Data seeding script verification and idempotency (`tests/test_seed.py`)

---

## API Endpoints Overview

### Authentication (`/auth`)
- `POST /auth/signup` - Register a new worker account
- `POST /auth/login` - Authenticate and receive a JWT Bearer access token
- `GET /auth/me` - Retrieve current authenticated user profile

### AI Chat & Tools (`/chat`)
- `POST /chat` - Natural language chat with the local LLM to reschedule shifts or inspect coworker schedules
  ```json
  {
    "message": "Can you show me other workers' shifts and reschedule my shift on project 1 to 2026-11-20 09:00?",
    "history": []
  }
  ```
- `GET /chat/tools` - Exposes OpenAI-compatible tool schemas (`get_other_workers_shifts`, `reschedule_shift`, `get_my_shifts`)
- `POST /chat/tools/execute` - Directly invoke a tool by name with arguments

### Shifts (`/shifts`)
- `GET /shifts/my-shifts` - List current user's shifts
- `GET /shifts/project/{project_id}/workers` - List other workers' shifts in a project
- `PATCH /shifts/{shift_id}/reschedule` - Directly reschedule a shift
