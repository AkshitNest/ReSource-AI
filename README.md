# ReSource AI

ReSource AI is an agentic B2B marketplace for social good. Organizations can describe real-world needs, discover verified supply, route surplus to purpose, and approve complete procurement packets before payment.

## Structure

```text
ReSource AI/
├── frontend/        # React + Vite marketplace and buyer/seller workspaces
├── backend/         # Flask API, SQLAlchemy models, agent contracts and workflows
├── README.md
└── .gitignore
```

Frontend and backend remain completely separate. The frontend uses Axios and an authenticated JWT to call the Flask API; marketplace, requirements, inventory, packets and workspace metrics are rendered from the database.

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The public site includes the mission landing page, marketplace, authentication entry point, buyer workspace, seller workspace, AI workspaces, requirements, packets, inventory, fulfillment and impact reporting.

## Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python run.py
```

The backend uses PostgreSQL when `DATABASE_URL` is configured and SQLite for a lightweight local run. A new local database starts empty. It exposes health, authentication, marketplace, requirements, inventory, demand, packet approval, Proof-of-Intent and liquidity-router endpoints, validates requirements with Pydantic agent outputs, and revalidates packet stock before approval.

## Product architecture

- **Demand Agent**: converts natural-language context into mandatory and optional requirement items, assumptions and clarification questions.
- **Supply Agent**: surfaces eligible inventory, surplus, demand matches and stock/expiry signals without publishing seller changes automatically.
- **Shopping Agent**: deterministically selects compatible current listings, checks quantities and budget, and produces an explainable packet.
- **Human approval boundary**: packet approval is separate from checkout. Price or stock drift requires renewed approval.
- **PayPal boundary**: credentials belong in backend environment variables; server-side order creation and capture verification are isolated in the payment adapter. Webhook reconciliation and approved marketplace disbursement configuration remain deployment-specific.

## Agent payment safety demos

- **Proof-of-Intent escrow** (`/app/guardrail`): creates SHA-256 hashes and an HMAC signature for the buyer's original prompt and parsed constraints. Checkout payloads, merchant DOM snapshots, and agent logs are hashed and compared against that proof. Budget, merchant, quantity, product, DOM drift, and prompt-injection signals block authorization deterministically.
- **MCP surface**: `/api/guardrail/mcp/tools` and `/api/guardrail/mcp/call` expose intent creation, checkout verification, authorization, and agent-log digest tools for an agent runtime.
- **Cross-platform liquidity router** (`/app/router`): accepts seller-specific payment legs with dependencies, FX rates, and partner fee basis points. It calculates totals deterministically, executes legs in dependency order, and compensates completed legs when a later leg fails. With PayPal credentials it uses server-created Sandbox orders; without credentials the explicit local Sandbox adapter exercises the same state machine.

## Status

This is a production-oriented hackathon foundation: the major user journeys and API data contracts are functional, while PayPal Sandbox capture/disbursement, email verification delivery, object storage, and production LLM provider credentials are intentionally configuration-dependent integration steps.
