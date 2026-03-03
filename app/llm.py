import json
import os
import re
from typing import Any
from urllib import request

from app.models import RawMessage, StructuredEvent


class LLMExtractor:
    """Extraction adapter with optional OpenAI call and a local heuristic fallback."""

    def __init__(self) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY", "").strip()

    async def extract(self, message: RawMessage) -> StructuredEvent:
        if self.api_key:
            try:
                return await self._extract_with_openai(message)
            except Exception:
                pass
        return self._heuristic_extract(message)

    async def _extract_with_openai(self, message: RawMessage) -> StructuredEvent:
        prompt = (
            "Extract structured emergency volunteering intent from this WhatsApp message. "
            "Return JSON with keys: category, location_from, location_to, capability, urgency (1-5).\n"
            f"Group: {message.group_name}\n"
            f"Sender: {message.sender}\n"
            f"Text: {message.text}"
        )
        payload: dict[str, Any] = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "You extract operational crisis events as JSON only."},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
        }

        req = request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))

        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)

        return StructuredEvent(
            group_name=message.group_name,
            sender=message.sender,
            message_text=message.text,
            category=parsed.get("category", "unknown"),
            location_from=parsed.get("location_from"),
            location_to=parsed.get("location_to"),
            capability=parsed.get("capability", "unclassified"),
            urgency=int(parsed.get("urgency", 1)),
            timestamp=message.timestamp,
        )

    def _heuristic_extract(self, message: RawMessage) -> StructuredEvent:
        text = message.text.lower()
        category = "coordination"
        capability = "general_help"
        urgency = 1

        if any(word in text for word in ["resgate", "salvar", "ilhado", "socorro"]):
            category = "rescue"
            capability = "rescue_support"
            urgency = 5
        elif any(word in text for word in ["comida", "marmita", "cesta", "alimento"]):
            category = "supplies"
            capability = "food_transport"
            urgency = 3
        elif any(word in text for word in ["abrigo", "acolhimento", "hospedar"]):
            category = "shelter"
            capability = "housing_support"
            urgency = 4
        elif any(word in text for word in ["carro", "caminhonete", "transporte", "levo"]):
            category = "mobility"
            capability = "people_or_goods_transport"
            urgency = 2

        location_from = _extract_neighborhood(text, "de")
        location_to = _extract_neighborhood(text, "para")

        return StructuredEvent(
            group_name=message.group_name,
            sender=message.sender,
            message_text=message.text,
            category=category,
            location_from=location_from,
            location_to=location_to,
            capability=capability,
            urgency=urgency,
            timestamp=message.timestamp,
        )


def _extract_neighborhood(text: str, token: str) -> str | None:
    match = re.search(rf"\b{token}\s+([a-zà-ú\s]+?)(?:\s+(?:para|com|hoje|agora|$))", text)
    if not match:
        return None
    return match.group(1).strip().title()
