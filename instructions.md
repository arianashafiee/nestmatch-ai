# Project Specification: NestMatch AI (AI Apartment Hunter for College Students)

You are an expert full-stack developer and software architect. Your task is to build "NestMatch AI", a web application that helps college students find, compare, and organize apartments near campus using AI-driven extraction, scoring, and workflow automation.

## 1. Tech Stack & Architecture
- **Frontend:** React (Vite), TypeScript, Tailwind CSS, Lucide React (icons), shadcn/ui (UI components).
- **Backend:** FastAPI (Python) OR Node.js/Express (TypeScript) — [Choose the one you are most comfortable debugging, e.g., FastAPI].
- **Database:** PostgreSQL (with Prisma or SQLAlchemy) or MongoDB.
- **AI Integration:** OpenAI API (gpt-4o-mini for extraction/ranking) or Anthropic Claude API.
- **Maps:** Mapbox API or Google Maps API (or a mocked location service for local development).

---

## 2. Core Features & User Flow

### Feature 1: Student Apartment Profile
- Form to capture user preferences:
  - University/Campus location.
  - Budget (Max monthly rent).
  - Max commute time & preferred mode (Walking, Transit, Biking).
  - Living situation: Solo vs. Number of roommates.
  - Must-haves & Dealbreakers (Toggle tags: Laundry, Parking, AC, Furnished, No Basements).

### Feature 2: Listing Link/Text Ingestion & AI Extraction
- An input field where users paste an apartment listing URL or raw text description.
- **AI Workflow:** Send this text + the Student Profile to the LLM. 
- **LLM Output (JSON Schema):** Extract rent, exact location, bed/bath count, amenities, hidden fees, lease length, identified red flags, missing info, and estimated commute.

### Feature 3: AI Ranking & Comparison Dashboard
- Calculate a dynamic compatibility score (e.g., 87/100) based on how well the listing matches the Profile.
- Break down the score into categories: Affordability, Commute, Amenities, Safety/Comfort, Student Fit.
- Display a clean UI card with:
  - Pros vs. Cons / Red Flags.
  - AI-generated "Questions to ask the landlord" (e.g., "Is laundry in-unit or coins?").

### Feature 4: "Ask the Landlord" Message Generator
- A one-click button that generates a highly contextual, polite outreach email/text template based on the missing info and questions identified by the AI.
- Include a "Copy to Clipboard" functionality.

### Feature 5: Kanban Shortlist Board
- A visual board to track apartment applications with columns:
  - `Interested` (Where newly parsed apartments land)
  - `Contacted`
  - `Tour Scheduled`
  - `Applied`
  - `Archived/Rejected`
- Allow drag-and-drop or simple button clicks to move apartments between stages.

---

## 3. UI/UX Style Guide
- **Vibe:** Clean, modern, trustworthy, and student-friendly (similar to Notion or Airbnb).
- **Color Palette:** Slate/Zinc neutrals with a vibrant Indigo or Emerald accent color.
- **Layout:** Dashboard layout with a sidebar for navigation (Profile, Hunting Board, Analytics). Fully responsive for mobile use.

---

## 4. Implementation Phasing (Step-by-Step Instructions)

### Phase 1: Project Setup & Layout
1. Initialize the frontend with Vite + React + TypeScript + Tailwind CSS.
2. Initialize the backend server (FastAPI/Node) and establish a basic database connection.
3. Build the core layout: Sidebar navigation, a Top Navbar, and a main content viewport.
4. Set up global state management (or Context) to hold the `StudentProfile`.

### Phase 2: Profile & Ingestion UI
1. Create the `StudentProfile` multi-step form or settings page. Save this to the database/local state.
2. Build the "Add New Apartment" modal/page featuring a large text area for pasting listing text or URLs.

### Phase 3: AI Integration & Backend API
1. Create a POST endpoint `/api/parse-listing` that accepts the listing text and the student's profile ID.
2. Write the LLM prompt inside the backend. It must use Structured Outputs (JSON mode) to guarantee a specific schema.
3. **Prompt requirements:**
   - Compare listing details against student budget and dealbreakers.
   - Calculate a score out of 100 with categorical breakdowns.
   - Flag standard rental scams or red flags (e.g., "price too low for area", "no photos of bathroom").
   - Generate 3 specific follow-up questions.

### Phase 4: Kanban Board & Workflow
1. Build the Shortlist Board view. Render the AI-parsed apartments as cards within their respective pipeline columns.
2. Implement backend endpoints to update the `status` of an apartment listing (`PUT /api/apartments/{id}/status`).
3. Add the "View Details" view which shows the full AI analysis, map placeholder, and the "Ask the Landlord" copyable template.

---

## 5. Coding Principles & Guidelines
- **Component Design:** Keep components modular, reusable, and strictly typed in TypeScript.
- **Error Handling:** Gracefully handle API failures (especially LLM timeouts or bad URLs) with clear UI toast notifications.
- **Loading States:** Provide beautiful skeleton loaders while the AI is parsing a listing.
- **Mock Data First:** If external APIs (like Maps or OpenAI) aren't configured yet, provide robust fallback mock data so the application is instantly interactive.

Let's begin with **Phase 1**. Generate the project structure and the initial configuration files.