from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Literal

from .db import Database
from .models import Opportunity, SimulatedTrade

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class PersistEvent:
    kind: Literal["opportunity", "trade"]
    payload: Opportunity | SimulatedTrade


class PersistenceManager:
    def __init__(self, db: Database, *, queue_size: int = 5000) -> None:
        self._db = db
        self._queue: asyncio.Queue[PersistEvent | None] = asyncio.Queue(maxsize=queue_size)
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        if self._task is not None:
            return
        self._task = asyncio.create_task(self._run(), name="persistence-worker")

    async def stop(self) -> None:
        if self._task is None:
            return
        await self._queue.put(None)
        await self._task
        self._task = None

    def submit_opportunity(self, item: Opportunity) -> None:
        try:
            self._queue.put_nowait(PersistEvent(kind="opportunity", payload=item))
        except asyncio.QueueFull:
            logger.warning("Persistence queue full; dropping opportunity")

    def submit_trade(self, item: SimulatedTrade) -> None:
        try:
            self._queue.put_nowait(PersistEvent(kind="trade", payload=item))
        except asyncio.QueueFull:
            logger.warning("Persistence queue full; dropping trade")

    async def list_opportunities(self, limit: int = 100) -> list[Opportunity]:
        return await self._db.list_opportunities(limit=limit)

    async def list_trades(self, limit: int = 100) -> list[SimulatedTrade]:
        return await self._db.list_trades(limit=limit)

    async def _run(self) -> None:
        while True:
            event = await self._queue.get()
            try:
                if event is None:
                    return
                if event.kind == "opportunity":
                    await self._db.insert_opportunity(event.payload)  # type: ignore[arg-type]
                elif event.kind == "trade":
                    await self._db.insert_trade(event.payload)  # type: ignore[arg-type]
            except Exception:
                logger.exception("Failed to persist %s", getattr(event, "kind", "unknown"))
            finally:
                self._queue.task_done()
