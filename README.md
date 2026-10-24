# Campus Customs Shop + Chatbot

MGT 409 (AI Foundations for Managers), Homework 4. A storefront for **Campus Customs**, the Yale gear shop on Broadway in New Haven, with **Will**, a PydanticAI chatbot that looks up real prices and stock, puts product cards on the page, remembers logged-in shoppers, and follows the safety rules in `backend/prompts/prompt.md`.

- **Front end:** Vite + React + TypeScript (`frontend/`)
- **Back end:** FastAPI + PydanticAI through Portkey (`backend/`)
- **How it all works:** `output/harness.md` (model fields, tools, safety rules, specs, audit trail)

## Layout

```
hw4/
├── AI_prompts.md            # what I asked my vibe coder, problem by problem
├── requirements.txt         # Python packages for the back end
├── .env.example             # placeholders only; copy to .env and add your key
├── .gitignore               # keeps .env, the database, product images and node_modules out of Git
├── README.md
├── run_site.command         # Mac shortcut: double-click to start back end + front end
├── frontend/                # Vite React TypeScript app
├── backend/
│   ├── main.py              # FastAPI app; run with: uvicorn main:app --reload --port 8000
│   ├── agent.py             # the agent: model, prompt, tools, structured output
│   ├── models.py            # Pydantic / PydanticAI types
│   ├── tools.py             # what the agent can look up (read-only database)
│   ├── prompts/
│   │   └── prompt.md        # Will's voice and safety rules
│   ├── auth.py              # accounts and password hashing
│   ├── memory.py            # saved chat history for logged-in shoppers
│   ├── guardrails.py        # safety checks enforced in code
│   └── audit.py             # append-only audit trail
├── scripts/                 # helper used by run_site.command
└── output/
    ├── harness.md
    ├── design.md
    ├── usability.md
    ├── app_check.html
    ├── app_check_images/     # screenshots linked from app_check.html
    ├── design_images/        # before/after screenshots for design.md
    └── audit_trail.json
```

The agent itself is four files under `backend/`: `prompts/prompt.md`, `agent.py`, `tools.py` and `models.py`. The other backend files are helpers they use.

**Local-only data pack (not in Git):**

```
data/
├── campus_customs.db        # catalogue, inventory, users, chat history
└── products/                # images referenced by the catalogue
```

## Run it

### 1. Put the data pack in place
Unzip the course data pack so you have `hw4/data/campus_customs.db` and `hw4/data/products/*.jpg`.

### 2. Add your API key
```
cp .env.example .env
```
Open `.env` and replace `your-portkey-key-here` with your Portkey key. (`.env` is ignored by Git and is never committed.)

### 3. Start the back end (terminal 1)
Needs Python 3.10+.
```
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cd backend
uvicorn main:app --reload --port 8000
```
Check it at http://localhost:8000/api/health.

### 4. Start the front end (terminal 2)
Needs Node.js 18+.
```
cd frontend
npm install
npm run dev
```
Open http://localhost:5173. The dev server passes `/api` and `/images` through to the back end on port 8000.

**On a Mac, steps 3 and 4 in one go:** double-click `run_site.command`.

### Test account
`test@campuscustoms.yale.edu` / `password` (from the course database).

## What's where for grading

| Problem | Where |
|---|---|
| 1 Vibe coder prompts | `AI_prompts.md` |
| 2 Database analysis | `output/harness.md` (Part 2, Database) |
| 3 Website | `frontend/` |
| 4 Accounts | `backend/auth.py`, `frontend/src/pages/Login.tsx`, `CreateAccount.tsx` |
| 5 Agent backend | `backend/main.py`, `agent.py`, `models.py`, `tools.py`, `prompts/prompt.md` |
| 6 Lookup tools | `backend/tools.py` (`get_product_description`, `get_price`, `check_stock`) |
| 7 Chat → product cards | `frontend/src/components/ChatResults.tsx`, `ChatWidget.tsx` |
| 8 Customer memory | `backend/memory.py`, `agent.py` (`ShopDeps`, "Right now" note) |
| 9 Usability | `output/usability.md` |
| 10 Design | `output/design.md` |
| 11 App check | `output/app_check.html` + `output/app_check_images/` |
| 12 Audit + harness | `output/audit_trail.json`, `backend/audit.py`, `backend/guardrails.py`, `output/harness.md` (Part 1) |
