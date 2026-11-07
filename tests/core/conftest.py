"""Shared fixtures: a throwaway registry of dummy operations and a file factory."""

from collections.abc import Callable
from pathlib import Path

import pytest

from clickmorph.core import Option, OptionValue, Registry, RunContext, SelectionMode


def copy_each(inputs: list[Path], options: dict[str, OptionValue], ctx: RunContext) -> list[Path]:
    outputs: list[Path] = []
    for source in inputs:
        out = ctx.output(source, "copy")
        with ctx.atomic_write(out) as tmp:
            tmp.write_bytes(source.read_bytes())
        outputs.append(out)
    return outputs


def concat(inputs: list[Path], options: dict[str, OptionValue], ctx: RunContext) -> list[Path]:
    out = ctx.output(inputs[0], "merged")
    with ctx.atomic_write(out) as tmp:
        tmp.write_bytes(b"|".join(p.read_bytes() for p in inputs))
    return [out]


def fail_if_bad(inputs: list[Path], options: dict[str, OptionValue], ctx: RunContext) -> list[Path]:
    (source,) = inputs
    out = ctx.output(source, "copy")
    if "bad" in source.name:
        raise ValueError("boom")
    with ctx.atomic_write(out) as tmp:
        tmp.write_bytes(source.read_bytes())
    return [out]


def partial_then_fail(
    inputs: list[Path], options: dict[str, OptionValue], ctx: RunContext
) -> list[Path]:
    out = ctx.output(inputs[0], "merged")
    with ctx.atomic_write(out) as tmp:
        tmp.write_bytes(b"half")
        raise RuntimeError("disk full")


def build_registry() -> Registry:
    reg = Registry()
    reg.register(
        "pdf.merge",
        label="Merge {count} PDFs",
        group="PDF",
        extensions={".pdf"},
        mode=SelectionMode.MANY_INTO_ONE,
        min_files=2,
    )(concat)
    reg.register(
        "pdf.compress",
        label="Compress",
        group="PDF",
        extensions={"pdf"},
        mode=SelectionMode.EACH,
        options=(Option("level", str, "medium", choices=("low", "medium", "high")),),
    )(copy_each)
    reg.register(
        "pdf.info", label="Info", group="PDF", extensions={".pdf"}, mode=SelectionMode.SINGLE
    )(copy_each)
    reg.register(
        "img.to_pdf",
        label="Images to PDF",
        group="Image",
        extensions={".jpg", ".png"},
        mode=SelectionMode.MANY_INTO_ONE,
    )(concat)
    reg.register(
        "tools.copy",
        label="Copy",
        group="Tools",
        extensions={".pdf", ".jpg"},
        mode=SelectionMode.EACH,
        max_files=3,
    )(copy_each)
    reg.register(
        "test.fail_if_bad",
        label="Fail if bad",
        group="Test",
        extensions={".txt"},
        mode=SelectionMode.EACH,
    )(fail_if_bad)
    reg.register(
        "test.partial",
        label="Partial",
        group="Test",
        extensions={".txt"},
        mode=SelectionMode.MANY_INTO_ONE,
    )(partial_then_fail)
    return reg


@pytest.fixture
def registry() -> Registry:
    return build_registry()


@pytest.fixture
def make_files(tmp_path: Path) -> Callable[..., list[Path]]:
    """Create files under ``tmp_path``; each file's content is its own name."""

    def make(*names: str) -> list[Path]:
        paths: list[Path] = []
        for name in names:
            path = tmp_path / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(name.encode())
            paths.append(path)
        return paths

    return make
