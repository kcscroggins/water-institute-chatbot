"""
Log every chat Q&A pair to a Google Sheet for review.

Configured via three environment variables (all required to enable logging):
  GOOGLE_SHEETS_CREDENTIALS_JSON  Full service-account JSON as a string
  GOOGLE_SHEETS_ID                The spreadsheet ID (from the URL)
  GOOGLE_SHEETS_TAB               Worksheet/tab name (default: "Chat Logs")

If any are missing, logging is silently disabled and /chat continues normally.
Writes happen via FastAPI BackgroundTasks so they never block a response.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import List, Optional

logger = logging.getLogger(__name__)

# Google Sheets cell hard limit
MAX_CELL_CHARS = 50000

HEADER_ROW = [
    "timestamp_utc",
    "question",
    "response",
    "sources",
    "response_time_ms",
    "model",
    "error",
]


class ChatLogger:
    def __init__(self):
        self._worksheet = None
        self._enabled = False
        self._init_from_env()

    def _init_from_env(self):
        creds_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS_JSON")
        sheet_id = os.getenv("GOOGLE_SHEETS_ID")
        tab_name = os.getenv("GOOGLE_SHEETS_TAB", "Chat Logs")

        if not creds_json or not sheet_id:
            logger.info(
                "Chat logging disabled: set GOOGLE_SHEETS_CREDENTIALS_JSON and "
                "GOOGLE_SHEETS_ID to enable."
            )
            return

        try:
            import gspread
            from google.oauth2.service_account import Credentials
        except ImportError:
            logger.warning(
                "Chat logging disabled: gspread / google-auth not installed."
            )
            return

        try:
            creds_dict = json.loads(creds_json)
        except json.JSONDecodeError as e:
            logger.error(f"Chat logging disabled: invalid credentials JSON ({e}).")
            return

        try:
            scopes = ["https://www.googleapis.com/auth/spreadsheets"]
            creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
            client = gspread.authorize(creds)
            spreadsheet = client.open_by_key(sheet_id)

            try:
                self._worksheet = spreadsheet.worksheet(tab_name)
            except gspread.WorksheetNotFound:
                self._worksheet = spreadsheet.add_worksheet(
                    title=tab_name, rows=1000, cols=len(HEADER_ROW)
                )
                self._worksheet.append_row(HEADER_ROW)

            # Make sure header exists on a pre-existing empty tab.
            if not self._worksheet.row_values(1):
                self._worksheet.append_row(HEADER_ROW)

            self._enabled = True
            logger.info(f"Chat logging enabled → sheet '{sheet_id}' tab '{tab_name}'.")
        except Exception as e:
            logger.error(f"Chat logging disabled: failed to connect to Sheet ({e}).")

    @property
    def enabled(self) -> bool:
        return self._enabled

    def log(
        self,
        question: str,
        response: str,
        sources: List[str],
        response_time_ms: int,
        model: str,
        error: Optional[str] = None,
    ) -> None:
        """Append one row. Safe to call even if logging is disabled."""
        if not self._enabled or self._worksheet is None:
            return

        try:
            row = [
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
                _truncate(question),
                _truncate(response),
                _truncate(", ".join(sources)),
                response_time_ms,
                model,
                _truncate(error or ""),
            ]
            self._worksheet.append_row(row, value_input_option="RAW")
        except Exception as e:
            # Never let logging failures surface — just record server-side.
            logger.warning(f"Sheet append failed: {e}")


def _truncate(value: str) -> str:
    if value is None:
        return ""
    if len(value) <= MAX_CELL_CHARS:
        return value
    return value[: MAX_CELL_CHARS - 20] + "...[truncated]"
