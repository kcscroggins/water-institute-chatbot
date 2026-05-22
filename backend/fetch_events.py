"""
Fetch events from the Water Institute WordPress site using The Events Calendar REST API.
Outputs a structured text file for ingestion into the chatbot's ChromaDB.

Usage:
    python fetch_events.py                  # Fetch and save events
    python fetch_events.py --dry-run        # Preview without saving
    python fetch_events.py --url URL        # Use a custom WordPress site URL

After running this script, re-run ingest_faculty.py to update ChromaDB:
    python ingest_faculty.py
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from html import unescape
import re

try:
    import requests
except ImportError:
    print("Error: 'requests' package is required. Install with: pip install requests")
    sys.exit(1)


DEFAULT_WP_URL = "https://waterinstitute.ufl.edu"
OUTPUT_PATH = Path(__file__).parent / ".." / "data" / "general_info" / "events.txt"


def strip_html(html_text: str) -> str:
    """Remove HTML tags and decode entities."""
    if not html_text:
        return ""
    text = re.sub(r'<[^>]+>', '', html_text)
    text = unescape(text)
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def format_datetime(start_str: str, end_str: str = None) -> str:
    """Format event date/time strings into a readable format.

    The Events Calendar API returns dates like '2026-06-15 09:00:00'.
    """
    try:
        start = datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return start_str or "TBD"

    date_part = start.strftime("%B %d, %Y")
    time_part = start.strftime("%-I:%M %p")

    if end_str:
        try:
            end = datetime.strptime(end_str, "%Y-%m-%d %H:%M:%S")
            # Same day
            if start.date() == end.date():
                return f"{date_part}, {time_part} - {end.strftime('%-I:%M %p')}"
            else:
                return f"{date_part}, {time_part} - {end.strftime('%B %d, %Y, %-I:%M %p')}"
        except (ValueError, TypeError):
            pass

    return f"{date_part}, {time_part}"


def fetch_events(base_url: str) -> list[dict]:
    """Fetch upcoming events from The Events Calendar REST API."""
    api_url = f"{base_url.rstrip('/')}/wp-json/tribe/events/v1/events"

    params = {
        "start_date": "now",
        "per_page": 50,
        "status": "publish",
    }

    print(f"Fetching events from: {api_url}")

    try:
        response = requests.get(api_url, params=params, timeout=30)
        response.raise_for_status()
    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to {api_url}")
        print("Make sure The Events Calendar plugin is installed and the REST API is enabled.")
        return []
    except requests.exceptions.HTTPError as e:
        print(f"Error: HTTP {e.response.status_code} from {api_url}")
        if e.response.status_code == 404:
            print("The Events Calendar REST API endpoint not found.")
            print("Make sure The Events Calendar plugin is installed and activated.")
        return []
    except requests.exceptions.RequestException as e:
        print(f"Error fetching events: {e}")
        return []

    data = response.json()
    raw_events = data.get("events", [])
    print(f"Found {len(raw_events)} upcoming events")

    events = []
    for ev in raw_events:
        # Extract venue/location
        venue = ev.get("venue", {}) or {}
        location_parts = []
        if venue.get("venue"):
            location_parts.append(venue["venue"])
        if venue.get("address"):
            addr = venue["address"]
            if addr.get("address"):
                location_parts.append(addr["address"])
            if addr.get("city"):
                location_parts.append(addr["city"])
        location = ", ".join(location_parts) if location_parts else "TBD"

        # Extract categories
        categories = []
        for cat in ev.get("categories", []):
            if isinstance(cat, dict):
                categories.append(cat.get("name", ""))
            elif isinstance(cat, str):
                categories.append(cat)

        # Extract organizer
        organizer_list = ev.get("organizer", []) or []
        organizers = []
        for org in organizer_list if isinstance(organizer_list, list) else [organizer_list]:
            if isinstance(org, dict):
                organizers.append(org.get("organizer", ""))
            elif isinstance(org, str):
                organizers.append(org)

        event = {
            "title": strip_html(ev.get("title", "Untitled Event")),
            "date": format_datetime(
                ev.get("start_date", ""),
                ev.get("end_date", "")
            ),
            "location": location,
            "description": strip_html(ev.get("description", "")),
            "url": ev.get("url", ""),
            "categories": ", ".join(c for c in categories if c),
            "cost": ev.get("cost", ""),
            "organizer": ", ".join(o for o in organizers if o),
        }
        events.append(event)

    return events


def format_events_text(events: list[dict]) -> str:
    """Format events into the structured text format for chatbot ingestion."""
    lines = [
        "Water Institute Events",
        f"Last Updated: {datetime.now().strftime('%Y-%m-%d')}",
        "",
        "Upcoming Events:",
        "",
    ]

    if not events:
        lines.append("No upcoming events at this time. Check the Water Institute website for the latest schedule.")
        lines.append("Website: https://waterinstitute.ufl.edu/")
        return "\n".join(lines)

    for ev in events:
        lines.append(f"Event: {ev['title']}")
        lines.append(f"Date: {ev['date']}")
        lines.append(f"Location: {ev['location']}")

        if ev.get("description"):
            # Truncate long descriptions
            desc = ev["description"]
            if len(desc) > 300:
                desc = desc[:297] + "..."
            lines.append(f"Description: {desc}")

        if ev.get("url"):
            lines.append(f"URL: {ev['url']}")

        if ev.get("categories"):
            lines.append(f"Categories: {ev['categories']}")

        if ev.get("cost"):
            lines.append(f"Cost: {ev['cost']}")

        if ev.get("organizer"):
            lines.append(f"Organizer: {ev['organizer']}")

        lines.append("")  # blank line between events

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Fetch events from the Water Institute WordPress site"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview output without saving to file"
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_WP_URL,
        help=f"WordPress site URL (default: {DEFAULT_WP_URL})"
    )
    parser.add_argument(
        "--output",
        default=str(OUTPUT_PATH),
        help=f"Output file path (default: {OUTPUT_PATH})"
    )
    args = parser.parse_args()

    events = fetch_events(args.url)
    output_text = format_events_text(events)

    if args.dry_run:
        print("\n--- DRY RUN (not saving) ---\n")
        print(output_text)
        print(f"\n--- Would save to: {args.output} ---")
    else:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output_text, encoding="utf-8")
        print(f"\nSaved {len(events)} events to: {output_path}")
        print("\nNext step: Run 'python ingest_faculty.py' to update ChromaDB with event data.")


if __name__ == "__main__":
    main()
