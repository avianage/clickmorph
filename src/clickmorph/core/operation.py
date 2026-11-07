"""Operation definitions: what an action accepts, its options, and how it runs."""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, cast

from clickmorph.core.naming import normalize_extension

if TYPE_CHECKING:
    from clickmorph.core.context import RunContext

type OptionValue = bool | int | float | str
type OptionKind = type[bool] | type[int] | type[float] | type[str]
type RunFn = Callable[[list[Path], dict[str, OptionValue], RunContext], list[Path]]

_ID_PATTERN: re.Pattern[str] = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")
_KINDS: tuple[OptionKind, ...] = (bool, int, float, str)


class OptionError(ValueError):
    """An option value is unknown, of the wrong type, or out of range."""


class SelectionMode(StrEnum):
    """How an operation consumes the selected files."""

    SINGLE = "single"
    """Exactly one file in, run once."""
    EACH = "each"
    """Any number of files; run once per file, independently."""
    MANY_INTO_ONE = "many_into_one"
    """All files (in natural order) are combined into one run, e.g. merge."""


@dataclass(frozen=True, slots=True)
class Option:
    """A typed operation option. CLI flags and menu choices are generated from these."""

    name: str
    kind: OptionKind
    default: OptionValue
    label: str = ""
    help: str = ""
    choices: tuple[OptionValue, ...] | None = None
    min: float | None = None
    max: float | None = None

    def __post_init__(self) -> None:
        if not self.name.isidentifier():
            raise ValueError(f"Option name {self.name!r} must be a valid identifier")
        if self.kind not in _KINDS:
            raise TypeError(f"Option {self.name!r}: kind must be one of bool, int, float, str")
        object.__setattr__(self, "default", self.validate(self.default))

    def validate(self, value: object) -> OptionValue:
        """Return ``value`` if it is valid for this option, else raise :class:`OptionError`."""
        kind = self.kind
        if kind is float and isinstance(value, int) and not isinstance(value, bool):
            value = float(value)
        if (isinstance(value, bool) and kind is not bool) or not isinstance(value, kind):
            raise OptionError(
                f"Option {self.name!r} expects {kind.__name__}, got {type(value).__name__}"
            )
        if self.choices is not None and value not in self.choices:
            allowed = ", ".join(repr(c) for c in self.choices)
            raise OptionError(f"Option {self.name!r} must be one of {allowed}, got {value!r}")
        if isinstance(value, int | float) and not isinstance(value, bool):
            if self.min is not None and value < self.min:
                raise OptionError(f"Option {self.name!r} must be >= {self.min}, got {value}")
            if self.max is not None and value > self.max:
                raise OptionError(f"Option {self.name!r} must be <= {self.max}, got {value}")
        return cast(OptionValue, value)


@dataclass(frozen=True, slots=True)
class Operation:
    """One action offered in the menu and the CLI."""

    id: str
    """Stable dotted identifier, e.g. ``"pdf.merge"``."""
    label: str
    """Menu label; may contain ``{count}``, e.g. ``"Merge {count} PDFs"``."""
    group: str
    """Menu group / submenu, e.g. ``"PDF"``."""
    extensions: frozenset[str]
    """Accepted input extensions, normalised to lowercase with a dot."""
    mode: SelectionMode
    run: RunFn
    min_files: int = 1
    max_files: int | None = None
    """``None`` means no upper limit."""
    options: tuple[Option, ...] = ()
    heavy: bool = False
    """Reserved for routing expensive jobs to a remote engine later."""

    def __post_init__(self) -> None:
        if not _ID_PATTERN.match(self.id):
            raise ValueError(f"Operation id {self.id!r} must look like 'group.action'")
        extensions = frozenset(normalize_extension(e) for e in self.extensions)
        if not extensions or "" in extensions:
            raise ValueError(f"Operation {self.id!r} needs at least one non-empty extension")
        object.__setattr__(self, "extensions", extensions)
        if self.mode is SelectionMode.SINGLE:
            object.__setattr__(self, "min_files", 1)
            object.__setattr__(self, "max_files", 1)
        if self.min_files < 1:
            raise ValueError(f"Operation {self.id!r}: min_files must be at least 1")
        if self.max_files is not None and self.max_files < self.min_files:
            raise ValueError(f"Operation {self.id!r}: max_files is smaller than min_files")
        names = [option.name for option in self.options]
        if len(names) != len(set(names)):
            raise ValueError(f"Operation {self.id!r} has duplicate option names")

    def menu_label(self, count: int) -> str:
        """The label for a selection of ``count`` files."""
        return self.label.format(count=count)

    def matches(self, count: int, suffixes: Iterable[str]) -> bool:
        """Whether a selection of ``count`` files with these extensions fits (no disk access)."""
        if count < self.min_files:
            return False
        if self.max_files is not None and count > self.max_files:
            return False
        return all(normalize_extension(s) in self.extensions for s in suffixes)

    def accepts(self, paths: Sequence[str | Path]) -> bool:
        """Whether this operation applies to exactly this selection of existing files."""
        files = [Path(p) for p in paths]
        if not files or not all(f.is_file() for f in files):
            return False
        return self.matches(len(files), {f.suffix for f in files})

    def resolve_options(
        self, overrides: Mapping[str, object] | None = None
    ) -> dict[str, OptionValue]:
        """Defaults merged with ``overrides``, each validated."""
        known = {option.name: option for option in self.options}
        given = dict(overrides or {})
        unknown = sorted(set(given) - set(known))
        if unknown:
            raise OptionError(f"Operation {self.id!r} has no option(s): {', '.join(unknown)}")
        return {
            name: option.validate(given[name]) if name in given else option.default
            for name, option in known.items()
        }
