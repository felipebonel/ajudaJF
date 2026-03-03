# AjudaJF - WhatsApp Crisis Intelligence Assistant

AjudaJF is a local-first automation designed for emergency volunteer coordination. It connects to WhatsApp Web, captures incoming group messages, structures operational data with an LLM, and exposes a contextual Q&A API.

## Why this exists
During communication crises (like floods), volunteers share critical information in high-volume WhatsApp groups. This project transforms unstructured chats into searchable, actionable knowledge.

## Key capabilities
- **Scrape multiple WhatsApp groups** from a local browser session.
- **Process messages asynchronously** through an in-memory queue.
- **Extract structured volunteer actions** (transport, supplies, rescue, shelter, etc.).
- **Store and query contextual knowledge** with lightweight SQLite.
- **Ask natural-language questions** through a local FastAPI endpoint.

## Architecture

```text
WhatsApp Web (Playwright)
        |
        v
MessageScraper -> asyncio.Queue -> MessageProcessor
                                    |
                                    v
                        LLM extraction adapter
                                    |
                                    v
                              SQLite store
                                    |
                                    v
                           FastAPI /ask endpoint
```

## Run locally

### 1) Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

### 2) Configure environment

```bash
cp .env.example .env
```

Optional values:
- `OPENAI_API_KEY`: if omitted, the app falls back to heuristic extraction.
- `WHATSAPP_GROUPS`: comma-separated group names to monitor.
- `DATABASE_PATH`: SQLite path (default `./ajuda.db`).

### 3) Start API + background workers

```bash
uvicorn app.main:app --reload
```

### 4) Connect WhatsApp Web session

Open endpoint docs at `http://127.0.0.1:8000/docs` and call:
- `POST /scraper/start` to launch browser automation.
- Scan QR code once in Chromium.

## API

- `POST /scraper/start` – start scraping loop.
- `POST /scraper/stop` – stop scraping loop.
- `GET /events` – list extracted events.
- `POST /ask` – ask context questions from stored data.

Example:

```json
{
  "question": "Quem consegue transportar comida para o bairro Dom Bosco hoje?"
}
```

## Notes
- This project is a starter implementation with clear interfaces for plugging in robust LLM/RAG layers.
- Keep usage aligned with privacy regulations and WhatsApp terms.
- For production, move from SQLite to Postgres + vector index and add authentication.
