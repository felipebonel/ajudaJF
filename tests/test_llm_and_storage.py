from app.llm import LLMExtractor
from app.models import RawMessage
from app.storage import EventStore


def test_heuristic_extraction_and_storage(tmp_path):
    extractor = LLMExtractor()
    message = RawMessage(
        group_name="Voluntarios Centro",
        sender="Ana",
        text="Tenho carro e posso levar comida do Centro para Dom Bosco agora",
    )

    event = extractor._heuristic_extract(message)

    assert event.category in {"supplies", "mobility"}
    assert event.capability in {"food_transport", "people_or_goods_transport"}

    store = EventStore(str(tmp_path / "test.db"))
    persisted = store.add_event(event)
    assert persisted.id is not None

    fetched = store.search_events("comida", limit=3)
    assert fetched
    assert fetched[0].sender == "Ana"
