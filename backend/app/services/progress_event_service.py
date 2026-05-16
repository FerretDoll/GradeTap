from __future__ import annotations

import json
import threading
import time
from collections import defaultdict, deque
from collections.abc import Generator
from dataclasses import dataclass
from typing import Any


@dataclass
class ProgressEvent:
    event: str
    data: dict[str, Any]
    event_id: int


class ProgressEventService:
    def __init__(self, max_events_per_channel: int = 300) -> None:
        self._max_events_per_channel = max_events_per_channel
        self._events: dict[str, deque[ProgressEvent]] = defaultdict(
            lambda: deque(maxlen=self._max_events_per_channel),
        )
        self._conditions: dict[str, threading.Condition] = defaultdict(threading.Condition)
        self._next_event_id = 1
        self._lock = threading.Lock()

    def publish(self, channel: str, event: str, data: dict[str, Any]) -> None:
        with self._lock:
            event_id = self._next_event_id
            self._next_event_id += 1
        progress_event = ProgressEvent(event=event, data=data, event_id=event_id)
        condition = self._conditions[channel]
        with condition:
            self._events[channel].append(progress_event)
            condition.notify_all()

    def stream(self, channel: str, heartbeat_seconds: float = 15.0) -> Generator[str, None, None]:
        last_event_id = self._events[channel][-1].event_id if self._events[channel] else 0
        while True:
            condition = self._conditions[channel]
            with condition:
                pending = [event for event in self._events[channel] if event.event_id > last_event_id]
                if not pending:
                    condition.wait(timeout=heartbeat_seconds)
                    pending = [event for event in self._events[channel] if event.event_id > last_event_id]

            if pending:
                for event in pending:
                    last_event_id = event.event_id
                    yield self._format_sse(event)
            else:
                yield f": heartbeat {int(time.time())}\n\n"

    def _format_sse(self, event: ProgressEvent) -> str:
        data = json.dumps(event.data, ensure_ascii=False)
        return f"id: {event.event_id}\nevent: {event.event}\ndata: {data}\n\n"


progress_event_service = ProgressEventService()
