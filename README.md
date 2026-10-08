# Riftlike backend

FastAPI backend for Riftlike, the 2026 League of Legends World Championship played as a roguelike.

This repo holds the API and the game engine. The browser client lives in its own repo.

Work in progress. Setup and usage docs will grow as the code does.

## Running locally

Requires Python 3.11 or newer.

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8010
```

The API starts on http://127.0.0.1:8010. Check it is alive at http://127.0.0.1:8010/api/health.
