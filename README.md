# NestMatch AI

AI-powered apartment hunting for college students. Paste listings, get compatibility scores, and track your hunt on a Kanban board.

## Tech Stack

- **Frontend:** React (Vite), TypeScript, Tailwind CSS, Lucide React
- **Backend:** FastAPI, SQLAlchemy, PostgreSQL

## Project Structure

```
nestmatch-ai/
├── frontend/          # React + Vite app
│   └── src/
│       ├── components/layout/   # Sidebar, TopNavbar, DashboardLayout
│       ├── context/             # StudentProfile global state
│       ├── pages/               # Route pages
│       └── types/               # TypeScript interfaces
└── backend/           # FastAPI API server
    └── app/
        ├── main.py              # App entry + health check
        ├── config.py            # Settings from env
        └── database.py          # SQLAlchemy connection
```

## Getting Started

### Prerequisites

- Node.js 20+
- Python 3.11+
- PostgreSQL optional (SQLite is used by default — no install needed)

### Database

SQLite is configured by default (`backend/nestmatch.db`). No setup required.

For PostgreSQL instead, set `DATABASE_URL` in `backend/.env` and create the database:

```bash
createdb nestmatch
```

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

Health check: http://localhost:8000/api/health

### Frontend

```bash
cd frontend
npm install
npm run dev
```

App: http://localhost:5173

## Phase 1 (Complete)

- [x] Vite + React + TypeScript + Tailwind CSS
- [x] FastAPI backend with PostgreSQL connection
- [x] Dashboard layout (sidebar, navbar, main viewport)
- [x] StudentProfile context with localStorage persistence

## Phase 2 (Complete)

- [x] Multi-step Student Profile form (campus, budget, commute, tags)
- [x] Profile persistence to PostgreSQL via `PUT /api/profile`
- [x] Add New Apartment modal with listing text/URL input
- [x] Apartment drafts via `POST /api/apartments` (status: pending)

## Phase 3 (Complete)

- [x] `POST /api/parse-listing` with structured JSON output
- [x] OpenAI gpt-4o-mini integration (falls back to smart mock parser)
- [x] Compatibility score + category breakdowns
- [x] Red flags, pros/cons, and 3 landlord follow-up questions
- [x] Auto-parse on add, skeleton loaders, toast notifications
- [x] Listing detail page with full analysis dashboard

## Phase 4 (Complete)

- [x] Kanban shortlist board with drag-and-drop and arrow controls
- [x] `PUT /api/apartments/{id}/status` endpoint
- [x] Listing detail view with map placeholder
- [x] "Ask the Landlord" copyable message generator
- [x] Clear labeling of sample vs. real listings
