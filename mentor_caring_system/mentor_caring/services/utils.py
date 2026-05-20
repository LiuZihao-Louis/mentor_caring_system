from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable, Optional


def is_blank(value: object) -> bool:
    return value is None or (isinstance(value, str) and value.strip() == "")


def require_non_blank(value: object, label: str) -> str:
    if is_blank(value):
        raise ValueError(f"{label} is required")
    return str(value).strip()


def parse_time(value: str) -> datetime:
    return datetime.strptime(value, "%H:%M")


def iter_30_minute_slots(start_time: str, end_time: str):
    start = parse_time(start_time)
    end = parse_time(end_time)
    if start >= end:
        raise ValueError("start_time must be before end_time")
    current = start
    while current + timedelta(minutes=30) <= end:
        slot_end = current + timedelta(minutes=30)
        yield current.strftime("%H:%M"), slot_end.strftime("%H:%M")
        current = slot_end
