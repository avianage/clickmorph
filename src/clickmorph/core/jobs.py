"""Running an operation as a job: validation, per-file error handling, cleanup, logging."""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from clickmorph.core.context import RunContext
from clickmorph.core.joblog import JobLog
from clickmorph.core.naming import path_key
from clickmorph.core.natsort import natural_sorted
from clickmorph.core.operation import Operation, SelectionMode

_log: logging.Logger = logging.getLogger(__name__)

CANCELLED: str = "Cancelled"


class NotApplicableError(ValueError):
    """The operation does not accept this selection. A caller bug, not a file failure."""


class OutputError(RuntimeError):
    """An operation returned an output that breaks the output rules."""


@dataclass(frozen=True, slots=True)
class Failure:
    input: Path
    error: str
    kind: str
    """Exception class name, or ``"Cancelled"``."""


@dataclass(frozen=True, slots=True)
class JobResult:
    job_id: str
    operation_id: str
    inputs: tuple[Path, ...]
    outputs: tuple[Path, ...]
    failures: tuple[Failure, ...]
    duration_s: float

    @property
    def ok(self) -> bool:
        return not self.failures


def _check_outputs(
    produced: object, inputs: Sequence[Path], reserved: Sequence[Path]
) -> list[Path]:
    if not isinstance(produced, list | tuple):
        raise OutputError(f"run() must return a list of paths, got {type(produced).__name__}")
    input_keys = {path_key(p) for p in inputs}
    reserved_keys = {path_key(p) for p in reserved}
    outputs: list[Path] = []
    for item in produced:
        if not isinstance(item, Path):
            raise OutputError(f"run() returned a non-path output: {item!r}")
        key = path_key(item)
        if key in input_keys:
            raise OutputError(f"run() returned an input file as output: {item}")
        if key not in reserved_keys:
            raise OutputError(f"Output {item} was not reserved through ctx.output()")
        if not item.is_file():
            raise OutputError(f"Output {item} was not written")
        outputs.append(item)
    return outputs


def _failures(batch: Sequence[Path], exc: BaseException) -> list[Failure]:
    message = str(exc) or type(exc).__name__
    return [Failure(path, message, type(exc).__name__) for path in batch]


def run_job(
    operation: Operation,
    inputs: Sequence[str | Path],
    options: Mapping[str, object] | None = None,
    *,
    log: JobLog | None = None,
    cancel: Callable[[], bool] | None = None,
    progress: Callable[[int, int], None] | None = None,
    output_dir: Path | None = None,
) -> JobResult:
    """Run ``operation`` on ``inputs`` and return what happened.

    Raises :class:`NotApplicableError` if the selection does not fit, and
    :class:`~clickmorph.core.operation.OptionError` for invalid options. Errors raised by
    the operation itself are caught (``Exception`` only) and reported per file; whatever a
    failed run created is deleted.
    """
    paths = [Path(p) for p in inputs]
    if not operation.accepts(paths):
        raise NotApplicableError(
            f"{operation.id!r} does not apply to this selection of {len(paths)} file(s)"
        )
    resolved = operation.resolve_options(options)
    if operation.mode is SelectionMode.MANY_INTO_ONE:
        paths = natural_sorted(paths)

    job_id = uuid.uuid4().hex
    started = datetime.now(UTC)
    start = time.perf_counter()
    ctx = RunContext(paths, output_dir=output_dir, cancel=cancel, progress=progress)
    batches = [[p] for p in paths] if operation.mode is SelectionMode.EACH else [paths]
    outputs: list[Path] = []
    failures: list[Failure] = []

    for index, batch in enumerate(batches):
        if ctx.cancelled():
            for remaining in batches[index:]:
                failures.extend(Failure(p, CANCELLED, CANCELLED) for p in remaining)
            break
        mark = ctx.checkpoint()
        try:
            produced = operation.run(list(batch), dict(resolved), ctx)
            accepted = _check_outputs(produced, paths, ctx.created[mark:])
        except Exception as exc:
            ctx.discard_since(mark)
            failures.extend(_failures(batch, exc))
        else:
            ctx.discard_since(mark, keep=accepted)  # drop reserved-but-unused names
            outputs.extend(accepted)
        ctx.progress(index + 1, len(batches))

    result = JobResult(
        job_id=job_id,
        operation_id=operation.id,
        inputs=tuple(paths),
        outputs=tuple(outputs),
        failures=tuple(failures),
        duration_s=time.perf_counter() - start,
    )
    if log is not None:
        _write_log(log, result, resolved, started)
    return result


def _write_log(
    log: JobLog, result: JobResult, options: Mapping[str, object], started: datetime
) -> None:
    record: dict[str, object] = {
        "job_id": result.job_id,
        "started": started.isoformat(timespec="milliseconds"),
        "operation": result.operation_id,
        "options": dict(options),
        "inputs": [str(p.absolute()) for p in result.inputs],
        "outputs": [str(p.absolute()) for p in result.outputs],
        "failures": [
            {"input": str(f.input.absolute()), "error": f.error, "kind": f.kind}
            for f in result.failures
        ],
        "duration_s": round(result.duration_s, 6),
    }
    try:
        log.append(record)
    except OSError:
        # The outputs exist either way; a broken log must not turn success into failure.
        _log.warning("Could not write job log %s", log.path, exc_info=True)
