"""Natural ("human") ordering of file names: ``page2`` sorts before ``page10``."""

from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import PurePath

type Chunks = tuple[str | int, ...]
type NaturalKey = tuple[Chunks, Chunks, str]

_DIGITS: re.Pattern[str] = re.compile(r"([0-9]+)")


def _chunks(text: str) -> Chunks:
    # re.split with a capturing group alternates text, digits, text, ... so values of the
    # same type always line up at the same positions and compare cleanly.
    parts = _DIGITS.split(text.casefold())
    return tuple(int(part) if index % 2 else part for index, part in enumerate(parts))


def natural_key(value: str | PurePath) -> NaturalKey:
    """Sort key comparing the file name first, then the full path, then the raw string.

    Text is compared case-insensitively and digit runs numerically. The raw string is the
    final tie-breaker, so ordering is deterministic even for names that compare equal
    (``p01`` vs ``p1``, ``A`` vs ``a``).
    """
    if isinstance(value, PurePath):
        name, full = value.name, str(value)
    else:
        name = full = value
    return (_chunks(name), _chunks(full), full)


def natural_sorted[T: (str | PurePath)](items: Iterable[T]) -> list[T]:
    """Return ``items`` in natural order."""
    return sorted(items, key=natural_key)
