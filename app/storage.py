import sqlite3
from pathlib import Path

from app.models import StructuredEvent


class EventStore:
    def __init__(self, db_path: str) -> None:
        self.db_path = Path(db_path)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_name TEXT NOT NULL,
                    sender TEXT NOT NULL,
                    message_text TEXT NOT NULL,
                    category TEXT NOT NULL,
                    location_from TEXT,
                    location_to TEXT,
                    capability TEXT NOT NULL,
                    urgency INTEGER NOT NULL,
                    timestamp TEXT NOT NULL
                )
                """
            )

    def add_event(self, event: StructuredEvent) -> StructuredEvent:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO events
                (group_name, sender, message_text, category, location_from, location_to, capability, urgency, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.group_name,
                    event.sender,
                    event.message_text,
                    event.category,
                    event.location_from,
                    event.location_to,
                    event.capability,
                    event.urgency,
                    event.timestamp.isoformat(),
                ),
            )
            event.id = cursor.lastrowid
        return event

    def list_events(self, limit: int = 100) -> list[StructuredEvent]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM events
                ORDER BY datetime(timestamp) DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [StructuredEvent(**dict(row)) for row in rows]

    def search_events(self, query: str, limit: int = 5) -> list[StructuredEvent]:
        pattern = f"%{query}%"
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM events
                WHERE message_text LIKE ?
                OR capability LIKE ?
                OR category LIKE ?
                OR ifnull(location_from, '') LIKE ?
                OR ifnull(location_to, '') LIKE ?
                ORDER BY urgency DESC, datetime(timestamp) DESC
                LIMIT ?
                """,
                (pattern, pattern, pattern, pattern, pattern, limit),
            ).fetchall()

        return [StructuredEvent(**dict(row)) for row in rows]
