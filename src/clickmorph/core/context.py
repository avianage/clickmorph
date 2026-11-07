"""The context handed to an operation's ``run`` function."""

from __future__ import annotations

import contextlib
import logging
from collections.abc import Callable, Iterable, Iterator, Sequence
from pathlib import Path

from clickmorph.core.naming import atomic_write, path_key, reserve_output

_log: logging.Logger = logging.getLogger(__name__)


class RunContext:
    """Hands out collision-safe output names and tracks everything it created.

    Operations must obtain every output path through :meth:`output`; the job runner
    rejects outputs that did not come from here and deletes this context's files when a
    run fails.
    """

    __slots__ = ("_cancel", "_created", "_inputs", "_output_dir", "_progress")

    def __init__(
        self,
        inputs: Sequence[Path],
        *,
        output_dir: Path | None = None,
        cancel: Callable[[], bool] | None = None,
        progress: Callable[[int, int], None] | None = None,
    ) -> None:
        self._inputs: tuple[Path, ...] = tuple(inputs)
        self._output_dir: Path | None = output_dir
        self._cancel: Callable[[], bool] | None = cancel
        self._progress: Callable[[int, int], None] | None = progress
        self._created: list[Path] = []

    def output(self, source: Path, suffix: str, *, ext: str | None = None) -> Path:
        """Reserve a collision-safe output name for ``source`` and track it."""
        path = reserve_output(
            source,
            suffix,
            ext=ext,
            directory=self._output_dir,
            taken=self._created,
            inputs=self._inputs,
        )
        self._created.append(path)
        return path

    @contextlib.contextmanager
    def atomic_write(self, final: Path) -> Iterator[Path]:
        """Write to a temp file that replaces the reserved ``final`` on success."""
        if path_key(final) not in {path_key(p) for p in self._created}:
            raise ValueError(f"{final} was not reserved through RunContext.output()")
        with atomic_write(final) as tmp:
            yield tmp

    def cancelled(self) -> bool:
        """Whether the user asked to cancel; long operations should check this regularly."""
        return self._cancel is not None and self._cancel()

    def progress(self, done: int, total: int) -> None:
        """Report progress to whoever is listening (CLI progress bar, toast)."""
        if self._progress is not None:
            self._progress(done, total)

    @property
    def created(self) -> tuple[Path, ...]:
        """Every output path reserved so far, in order."""
        return tuple(self._created)

    def checkpoint(self) -> int:
        """A marker for :meth:`discard_since`."""
        return len(self._created)

    def discard_since(self, mark: int, keep: Iterable[Path] = ()) -> None:
        """Delete files reserved after ``mark``, except those in ``keep``.

        Only paths this context reserved are ever deleted, so inputs and pre-existing
        files are never touched.
        """
        keep_keys = {path_key(p) for p in keep}
        remaining = self._created[:mark]
        for path in self._created[mark:]:
            if path_key(path) in keep_keys:
                remaining.append(path)
                continue
            try:
                path.unlink(missing_ok=True)
            except OSError:
                _log.warning("Could not remove leftover output %s", path, exc_info=True)
        self._created = remaining
