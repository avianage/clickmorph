"""Append-only job log (JSON lines) recording inputs → outputs, so undo can be built later."""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Iterator, Mapping
from pathlib import Path

_log: logging.Logger = logging.getLogger(__name__)

DATA_DIR_ENV: str = "CLICKMORPH_DATA_DIR"
LOG_FILE_NAME: str = "jobs.jsonl"


def default_data_dir() -> Path:
    """Per-user data folder.

    ``$CLICKMORPH_DATA_DIR`` if set; otherwise ``%LOCALAPPDATA%\\ClickMorph`` when that
    variable exists (Windows), else ``$XDG_STATE_HOME/clickmorph`` (default
    ``~/.local/state/clickmorph``). Only environment variables are read, so this works on
    any OS.
    """
    override = os.environ.get(DATA_DIR_ENV)
    if override:
        return Path(override)
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "ClickMorph"
    xdg_state = os.environ.get("XDG_STATE_HOME")
    base = Path(xdg_state) if xdg_state else Path.home() / ".local" / "state"
    return base / "clickmorph"


def default_log_path() -> Path:
    return default_data_dir() / LOG_FILE_NAME


class JobLog:
    """One JSON object per line, appended with a single write per record."""

    __slots__ = ("path",)

    def __init__(self, path: Path) -> None:
        self.path: Path = Path(path)

    @classmethod
    def default(cls) -> JobLog:
        return cls(default_log_path())

    def append(self, record: Mapping[str, object]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(line)

    def read(self) -> Iterator[dict[str, object]]:
        """Yield records oldest first, skipping lines that are not valid JSON objects."""
        if not self.path.exists():
            return
        with self.path.open(encoding="utf-8") as handle:
            for number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    _log.warning("Skipping corrupt line %d in %s", number, self.path)
                    continue
                if isinstance(record, dict):
                    yield record
                else:
                    _log.warning("Skipping non-object line %d in %s", number, self.path)
