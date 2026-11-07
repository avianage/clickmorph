"""Output file naming.

Outputs go next to the source as ``<stem>-<suffix><ext>`` (``report-compressed.pdf``).
If that name is taken, `` (1)``, `` (2)``, ... is appended before the extension. A name
is never one of the inputs, and existing files are never replaced: outputs are claimed
by creating an empty placeholder exclusively, then filled through :func:`atomic_write`.
"""

from __future__ import annotations

import contextlib
import os
import tempfile
from collections.abc import Iterable, Iterator
from pathlib import Path

MAX_ATTEMPTS: int = 10_000


def normalize_extension(ext: str) -> str:
    """``"PDF"``, ``".pdf"`` and ``" .Pdf "`` all become ``".pdf"``; ``""`` stays empty."""
    ext = ext.strip().lower()
    if not ext:
        return ""
    return ext if ext.startswith(".") else f".{ext}"


def path_key(path: str | os.PathLike[str]) -> str:
    """Comparison key for paths, case-insensitive on every platform.

    Treating names that differ only in case as equal is deliberately conservative: it
    avoids clashes on case-insensitive file systems even when running elsewhere.
    """
    return os.path.normcase(str(Path(path).absolute())).casefold()


def _exists(path: Path) -> bool:
    return path.exists(follow_symlinks=False)


def _candidates(
    source: Path, suffix: str, ext: str | None, directory: Path | None
) -> Iterator[Path]:
    folder = directory if directory is not None else source.parent
    extension = source.suffix if ext is None else normalize_extension(ext)
    base = f"{source.stem}-{suffix}" if suffix else source.stem
    yield folder / f"{base}{extension}"
    for number in range(1, MAX_ATTEMPTS):
        yield folder / f"{base} ({number}){extension}"


def _first_free(
    source: str | os.PathLike[str],
    suffix: str,
    *,
    ext: str | None,
    directory: str | os.PathLike[str] | None,
    taken: Iterable[str | os.PathLike[str]],
    inputs: Iterable[str | os.PathLike[str]],
    claim: bool,
) -> Path:
    src = Path(source)
    folder = Path(directory) if directory is not None else None
    blocked = {path_key(p) for p in (src, *inputs, *taken)}
    for candidate in _candidates(src, suffix, ext, folder):
        if path_key(candidate) in blocked or _exists(candidate):
            continue
        if claim:
            try:
                candidate.open("xb").close()
            except FileExistsError:  # created by someone else since the check
                continue
        return candidate
    raise FileExistsError(f"No free output name for {src.name!r} after {MAX_ATTEMPTS} attempts")


def output_name(
    source: str | os.PathLike[str],
    suffix: str,
    *,
    ext: str | None = None,
    directory: str | os.PathLike[str] | None = None,
    taken: Iterable[str | os.PathLike[str]] = (),
    inputs: Iterable[str | os.PathLike[str]] = (),
) -> Path:
    """Return the first free output name for ``source`` without creating anything.

    ``ext`` replaces the source extension (``"jpg"`` or ``".jpg"``; ``""`` for none).
    ``directory`` defaults to the source's folder. Names in ``taken`` or ``inputs`` are
    skipped, as is the source itself.
    """
    return _first_free(
        source, suffix, ext=ext, directory=directory, taken=taken, inputs=inputs, claim=False
    )


def reserve_output(
    source: str | os.PathLike[str],
    suffix: str,
    *,
    ext: str | None = None,
    directory: str | os.PathLike[str] | None = None,
    taken: Iterable[str | os.PathLike[str]] = (),
    inputs: Iterable[str | os.PathLike[str]] = (),
) -> Path:
    """Like :func:`output_name`, but claims the name by creating an empty placeholder.

    Creation is exclusive, so concurrent jobs can never receive the same name. The caller
    owns the placeholder and must fill it with :func:`atomic_write` or delete it.
    """
    return _first_free(
        source, suffix, ext=ext, directory=directory, taken=taken, inputs=inputs, claim=True
    )


@contextlib.contextmanager
def atomic_write(final: str | os.PathLike[str]) -> Iterator[Path]:
    """Yield a temporary path in ``final``'s folder; move it onto ``final`` on success.

    ``final`` must be a placeholder from :func:`reserve_output`, so the only file ever
    replaced is one this process created. On error the temporary file is removed and the
    exception propagates; the placeholder is left for the owner to clean up.
    """
    target = Path(final)
    fd, name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".part", dir=target.parent)
    os.close(fd)
    tmp = Path(name)
    try:
        yield tmp
        tmp.replace(target)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
