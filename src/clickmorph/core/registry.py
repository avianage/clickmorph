"""The operation registry: the single source for the CLI, the menu, and recipes."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator, Sequence
from pathlib import Path

from clickmorph.core.naming import normalize_extension
from clickmorph.core.operation import Operation, Option, RunFn, SelectionMode


class Registry:
    """A collection of operations keyed by id, in registration order."""

    __slots__ = ("_operations",)

    def __init__(self) -> None:
        self._operations: dict[str, Operation] = {}

    def add(self, operation: Operation) -> Operation:
        """Add an already-built operation."""
        if operation.id in self._operations:
            raise ValueError(f"Operation {operation.id!r} is already registered")
        self._operations[operation.id] = operation
        return operation

    def register(
        self,
        id: str,
        *,
        label: str,
        group: str,
        extensions: Iterable[str],
        mode: SelectionMode,
        min_files: int = 1,
        max_files: int | None = None,
        options: Sequence[Option] = (),
        heavy: bool = False,
    ) -> Callable[[RunFn], Operation]:
        """Decorator turning a ``run(inputs, options, ctx)`` function into an operation."""

        def decorator(run: RunFn) -> Operation:
            return self.add(
                Operation(
                    id=id,
                    label=label,
                    group=group,
                    extensions=frozenset(extensions),
                    mode=mode,
                    run=run,
                    min_files=min_files,
                    max_files=max_files,
                    options=tuple(options),
                    heavy=heavy,
                )
            )

        return decorator

    def get(self, id: str) -> Operation:
        try:
            return self._operations[id]
        except KeyError:
            raise KeyError(f"Unknown operation {id!r}") from None

    def all(self) -> list[Operation]:
        return list(self._operations.values())

    def applicable(self, paths: Sequence[str | Path]) -> list[Operation]:
        """Operations that fit this exact selection, grouped by menu group.

        Groups appear in the order they were first registered; operations keep their
        registration order within a group. A selection containing anything that is not
        an existing file (folders, missing paths) matches nothing.
        """
        files = [Path(p) for p in paths]
        if not files or not all(f.is_file() for f in files):
            return []
        suffixes = frozenset(normalize_extension(f.suffix) for f in files)
        group_order: dict[str, int] = {}
        for operation in self._operations.values():
            group_order.setdefault(operation.group, len(group_order))
        matched = [op for op in self._operations.values() if op.matches(len(files), suffixes)]
        return sorted(matched, key=lambda op: group_order[op.group])

    def __contains__(self, id: object) -> bool:
        return id in self._operations

    def __iter__(self) -> Iterator[Operation]:
        return iter(self._operations.values())

    def __len__(self) -> int:
        return len(self._operations)


registry: Registry = Registry()
"""The application-wide registry that built-in operations register into."""

register = registry.register
