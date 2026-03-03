import asyncio
import contextlib
from dataclasses import dataclass, field

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from app.models import RawMessage


@dataclass
class ScraperState:
    running: bool = False
    task: asyncio.Task | None = None
    seen_message_signatures: set[str] = field(default_factory=set)


class WhatsAppScraper:
    def __init__(self, queue: asyncio.Queue[RawMessage], groups: list[str]) -> None:
        self.queue = queue
        self.groups = [g.strip() for g in groups if g.strip()]
        self.state = ScraperState()

    async def start(self) -> None:
        if self.state.running:
            return
        self.state.running = True
        self.state.task = asyncio.create_task(self._run(), name="whatsapp-scraper")

    async def stop(self) -> None:
        self.state.running = False
        if self.state.task:
            self.state.task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.state.task

    async def _run(self) -> None:
        async with async_playwright() as p:
            browser: Browser = await p.chromium.launch(headless=False)
            context: BrowserContext = await browser.new_context()
            page: Page = await context.new_page()

            await page.goto("https://web.whatsapp.com/")
            await page.wait_for_timeout(15000)

            while self.state.running:
                for group in self.groups:
                    await self._scan_group(page, group)
                await asyncio.sleep(2)

            await context.close()
            await browser.close()

    async def _scan_group(self, page: Page, group_name: str) -> None:
        search = page.locator("div[contenteditable='true'][data-tab='3']")
        if await search.count() == 0:
            return

        await search.first.click()
        await search.first.fill(group_name)
        await page.wait_for_timeout(1000)

        title_locator = page.locator(f"span[title='{group_name}']")
        if await title_locator.count() == 0:
            return

        await title_locator.first.click()
        await page.wait_for_timeout(500)

        messages = page.locator("div.message-in, div.message-out")
        count = await messages.count()
        start = max(0, count - 8)

        for idx in range(start, count):
            message = messages.nth(idx)
            text_locator = message.locator("span.selectable-text")
            sender_locator = message.locator("span[dir='auto']")

            if await text_locator.count() == 0:
                continue

            text = (await text_locator.first.inner_text()).strip()
            sender = (
                (await sender_locator.first.inner_text()).strip()
                if await sender_locator.count() > 0
                else "unknown"
            )

            signature = f"{group_name}|{sender}|{text}"
            if signature in self.state.seen_message_signatures:
                continue

            self.state.seen_message_signatures.add(signature)
            await self.queue.put(RawMessage(group_name=group_name, sender=sender, text=text))
