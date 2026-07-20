"""
In-memory cache of upcoming UF Water Institute events from the LiveWhale
calendar (calendar.ufl.edu). The cached events are injected directly into the
chatbot's system prompt so the LLM always sees the full, current list without
depending on RAG retrieval.

Run this file directly to preview what would be injected:
    python events_cache.py
"""

import logging
import re
import threading
import time
from datetime import datetime
from html import unescape
from typing import Optional

import requests


logger = logging.getLogger(__name__)


LIVEWHALE_BASE = "https://calendar.ufl.edu"
GROUP_TITLE = "UF Water Institute"
# CloudFront in front of calendar.ufl.edu rejects the default requests/curl UA with a 403.
BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
CACHE_TTL_SECONDS = 3600
FETCH_TIMEOUT_SECONDS = 60
DESCRIPTION_MAX_CHARS = 400


def _strip_html(text: Optional[str]) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    text = unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _format_datetime(start_iso: Optional[str], end_iso: Optional[str], is_all_day: bool) -> str:
    if not start_iso:
        return "TBD"
    try:
        start = datetime.fromisoformat(start_iso)
    except (ValueError, TypeError):
        return start_iso

    date_part = start.strftime("%B %-d, %Y")
    if is_all_day:
        return f"{date_part} (All Day)"

    time_part = start.strftime("%-I:%M %p")
    if end_iso:
        try:
            end = datetime.fromisoformat(end_iso)
            if start.date() == end.date():
                return f"{date_part}, {time_part} - {end.strftime('%-I:%M %p')}"
            return f"{date_part}, {time_part} - {end.strftime('%B %-d, %Y, %-I:%M %p')}"
        except (ValueError, TypeError):
            pass
    return f"{date_part}, {time_part}"


def fetch_upcoming_events() -> list[dict]:
    """Fetch upcoming Water Institute events from LiveWhale. Raises on failure."""
    api_url = f"{LIVEWHALE_BASE}/live/json/events"
    headers = {"User-Agent": BROWSER_UA, "Accept": "application/json"}

    response = requests.get(api_url, headers=headers, timeout=FETCH_TIMEOUT_SECONDS)
    response.raise_for_status()

    all_events = response.json()
    if not isinstance(all_events, list):
        raise ValueError(f"Expected JSON list, got {type(all_events).__name__}")

    wi_events = [e for e in all_events if e.get("group_title") == GROUP_TITLE]

    events = []
    for ev in wi_events:
        location = ev.get("location") or ev.get("location_title") or ""
        if not location:
            location = "Online" if ev.get("is_online") else "TBD"

        online_url = ev.get("online_url") if ev.get("is_online") else None
        categories = [unescape(c).strip() for c in (ev.get("event_types") or []) if c]

        events.append({
            "title": _strip_html(ev.get("title", "Untitled Event")),
            "date": _format_datetime(
                ev.get("date_iso"),
                ev.get("date2_iso"),
                bool(ev.get("is_all_day")),
            ),
            "location": location,
            "description": _strip_html(ev.get("description", "")),
            "url": ev.get("url", ""),
            "online_url": online_url,
            "categories": categories,
            "cost": ev.get("cost") or "",
            "organizer": _strip_html(ev.get("contact_info", "")),
        })
    return events


class EventsCache:
    """Thread-safe cache with TTL and last-known-good fallback on fetch failure."""

    def __init__(self, ttl_seconds: int = CACHE_TTL_SECONDS):
        self._ttl = ttl_seconds
        self._lock = threading.Lock()
        self._events: list[dict] = []
        self._fetched_at: Optional[float] = None
        self._last_error: Optional[str] = None

    def is_stale(self) -> bool:
        if self._fetched_at is None:
            return True
        return (time.time() - self._fetched_at) > self._ttl

    def refresh(self) -> bool:
        """Fetch and update cache. Returns True on success; keeps old data on failure."""
        try:
            events = fetch_upcoming_events()
        except Exception as e:
            with self._lock:
                self._last_error = f"{type(e).__name__}: {e}"
            logger.warning(f"Events fetch failed, keeping last-known-good cache: {e}")
            return False

        with self._lock:
            self._events = events
            self._fetched_at = time.time()
            self._last_error = None
        logger.info(f"Refreshed events cache: {len(events)} upcoming {GROUP_TITLE} events")
        return True

    def format_for_prompt(self) -> str:
        """Render the events block for injection into the system prompt."""
        with self._lock:
            events = list(self._events)
            fetched_at = self._fetched_at

        if not events:
            body = (
                "No upcoming UF Water Institute events are currently scheduled "
                "on the official calendar."
            )
        else:
            entries = []
            for i, ev in enumerate(events, 1):
                lines = [
                    f"{i}. {ev['title']}",
                    f"   Date: {ev['date']}",
                    f"   Location: {ev['location']}",
                ]
                if ev.get("categories"):
                    lines.append(f"   Categories: {', '.join(ev['categories'])}")
                if ev.get("description"):
                    desc = ev["description"]
                    if len(desc) > DESCRIPTION_MAX_CHARS:
                        desc = desc[: DESCRIPTION_MAX_CHARS - 3] + "..."
                    lines.append(f"   Description: {desc}")
                if ev.get("url"):
                    lines.append(f"   Event page: {ev['url']}")
                if ev.get("online_url"):
                    lines.append(f"   Registration: {ev['online_url']}")
                if ev.get("organizer"):
                    lines.append(f"   Contact: {ev['organizer']}")
                entries.append("\n".join(lines))
            body = "\n\n".join(entries)

        refreshed = (
            datetime.fromtimestamp(fetched_at).strftime("%Y-%m-%d %H:%M")
            if fetched_at
            else "unknown"
        )
        return (
            "UPCOMING EVENTS (authoritative — this is the COMPLETE list of upcoming "
            "UF Water Institute events, sourced from calendar.ufl.edu. Never invent "
            "events. If a user asks about an event not listed here, tell them no "
            "other events are currently scheduled on the official calendar. "
            f"Last refreshed: {refreshed}):\n\n{body}"
        )

    def status(self) -> dict:
        with self._lock:
            age = (time.time() - self._fetched_at) if self._fetched_at else None
            return {
                "event_count": len(self._events),
                "fetched_at": self._fetched_at,
                "age_seconds": age,
                "stale": self.is_stale(),
                "last_error": self._last_error,
            }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    cache = EventsCache()
    cache.refresh()
    print("--- format_for_prompt() output ---\n")
    print(cache.format_for_prompt())
    print("\n--- status() ---")
    print(cache.status())
