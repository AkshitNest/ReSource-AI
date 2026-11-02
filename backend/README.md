# ReSource AI API

The backend is a modular Flask API for the ReSource AI marketplace. It uses PostgreSQL in deployed environments and can use SQLite locally when `DATABASE_URL` is not set.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python run.py
```

The first run creates an empty schema. Organizations, products, listings, requirements and packets are created through authenticated application workflows.

## Modules

- `auth`: registration, login, JWT-protected identity and role switching
- `marketplace`: products, sellers, inventory-safe listing reads
- `requirements`: buyer requirement creation and Demand Agent jobs
- `packets`: Shopping Agent packet reads, approval revalidation, state changes
- `dashboard`: role-specific dashboard summaries and impact metrics
- `agents`: provider-agnostic structured agent contracts and deterministic matching rules
- `agent_security`: signed Proof-of-Intent records, deterministic checkout verification, and MCP-style tool endpoints
- `liquidity`: dependency-aware multi-party route planning, PayPal leg execution, and compensation state transitions

The PayPal adapter is intentionally isolated for sandbox credentials and marketplace approval configuration. No payment is reported as complete unless a verified provider response is recorded by the backend.
