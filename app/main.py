import asyncio
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

from app.llm import LLMExtractor
from app.models import AskRequest, AskResponse, RawMessage, StructuredEvent
from app.scraper import WhatsAppScraper
from app.storage import EventStore

load_dotenv()

DATABASE_PATH = os.getenv("DATABASE_PATH", "./ajuda.db")
GROUPS = os.getenv("WHATSAPP_GROUPS", "").split(",")

queue: asyncio.Queue[RawMessage] = asyncio.Queue(maxsize=1000)
extractor = LLMExtractor()
store = EventStore(DATABASE_PATH)
scraper = WhatsAppScraper(queue=queue, groups=GROUPS)


async def message_processor() -> None:
    while True:
        message = await queue.get()
        try:
            event = await extractor.extract(message)
            store.add_event(event)
        finally:
            queue.task_done()


@asynccontextmanager
async def lifespan(_: FastAPI):
    processor_task = asyncio.create_task(message_processor(), name="message-processor")
    try:
        yield
    finally:
        processor_task.cancel()


app = FastAPI(title="AjudaJF Crisis Assistant", lifespan=lifespan)


@app.post("/scraper/start")
async def start_scraper() -> dict[str, str]:
    await scraper.start()
    return {"status": "running"}


@app.post("/scraper/stop")
async def stop_scraper() -> dict[str, str]:
    await scraper.stop()
    return {"status": "stopped"}


@app.get("/events", response_model=list[StructuredEvent])
async def list_events(limit: int = 100) -> list[StructuredEvent]:
    return store.list_events(limit=limit)


@app.post("/ask", response_model=AskResponse)
async def ask_question(payload: AskRequest) -> AskResponse:
    events = store.search_events(payload.question, limit=5)
    if not events:
        return AskResponse(
            answer=(
                "Não encontrei dados suficientes nas mensagens coletadas. "
                "Continue o scraping dos grupos e tente novamente."
            ),
            supporting_events=[],
        )

    answer_lines = [
        "Com base nas mensagens recentes, estes são os sinais mais relevantes:",
    ]
    for event in events:
        answer_lines.append(
            f"- {event.sender} ({event.group_name}) oferece {event.capability} "
            f"[{event.category}] de {event.location_from or 'origem não informada'} "
            f"para {event.location_to or 'destino não informado'}"
        )

    return AskResponse(answer="\n".join(answer_lines), supporting_events=events)
