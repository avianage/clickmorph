from collections.abc import Callable
from pathlib import Path

import pytest

from clickmorph.core import (
    JobLog,
    NotApplicableError,
    OptionError,
    OptionValue,
    Registry,
    RunContext,
    SelectionMode,
    run_job,
)

MakeFiles = Callable[..., list[Path]]


def names(folder: Path) -> list[str]:
    return sorted(p.name for p in folder.iterdir())


def snapshot(paths: list[Path]) -> dict[Path, bytes]:
    return {p: p.read_bytes() for p in paths}


def test_merge_uses_natural_order(
    registry: Registry, make_files: MakeFiles, tmp_path: Path
) -> None:
    files = make_files("page10.pdf", "page2.pdf", "page1.pdf")
    result = run_job(registry.get("pdf.merge"), files)
    assert result.ok
    assert result.outputs == (tmp_path / "page1-merged.pdf",)
    assert result.outputs[0].read_bytes() == b"page1.pdf|page2.pdf|page10.pdf"
    assert [p.name for p in result.inputs] == ["page1.pdf", "page2.pdf", "page10.pdf"]


def test_each_mode_one_output_per_file(registry: Registry, make_files: MakeFiles) -> None:
    files = make_files("a.pdf", "b.pdf")
    result = run_job(registry.get("pdf.compress"), files, {"level": "high"})
    assert result.ok
    assert [p.name for p in result.outputs] == ["a-copy.pdf", "b-copy.pdf"]
    assert result.outputs[1].read_bytes() == b"b.pdf"


def test_repeat_run_never_overwrites(registry: Registry, make_files: MakeFiles) -> None:
    files = make_files("a.pdf")
    first = run_job(registry.get("pdf.compress"), files)
    second = run_job(registry.get("pdf.compress"), files)
    assert first.outputs[0].name == "a-copy.pdf"
    assert second.outputs[0].name == "a-copy (1).pdf"


def test_inputs_unchanged(registry: Registry, make_files: MakeFiles) -> None:
    files = make_files("a.pdf", "b.pdf", "c.pdf")
    before = snapshot(files)
    run_job(registry.get("pdf.merge"), files)
    run_job(registry.get("pdf.compress"), files)
    assert snapshot(files) == before


def test_per_file_failure_does_not_stop_others(
    registry: Registry, make_files: MakeFiles, tmp_path: Path
) -> None:
    files = make_files("good.txt", "bad.txt", "other.txt")
    result = run_job(registry.get("test.fail_if_bad"), files)
    assert not result.ok
    assert [p.name for p in result.outputs] == ["good-copy.txt", "other-copy.txt"]
    (failure,) = result.failures
    assert failure.input.name == "bad.txt"
    assert failure.kind == "ValueError"
    assert failure.error == "boom"
    assert "bad-copy.txt" not in names(tmp_path)  # placeholder cleaned up


def test_failed_merge_cleans_up(registry: Registry, make_files: MakeFiles, tmp_path: Path) -> None:
    files = make_files("a.txt", "b.txt")
    result = run_job(registry.get("test.partial"), files)
    assert result.outputs == ()
    assert [f.input.name for f in result.failures] == ["a.txt", "b.txt"]
    assert {f.kind for f in result.failures} == {"RuntimeError"}
    assert names(tmp_path) == ["a.txt", "b.txt"]


def test_not_applicable(registry: Registry, make_files: MakeFiles) -> None:
    with pytest.raises(NotApplicableError):
        run_job(registry.get("pdf.merge"), make_files("only.pdf"))
    with pytest.raises(NotApplicableError):
        run_job(registry.get("pdf.compress"), make_files("letter.docx"))


def test_invalid_option(registry: Registry, make_files: MakeFiles, tmp_path: Path) -> None:
    files = make_files("a.pdf")
    with pytest.raises(OptionError):
        run_job(registry.get("pdf.compress"), files, {"level": "extreme"})
    assert names(tmp_path) == ["a.pdf"]


def test_log_record(registry: Registry, make_files: MakeFiles, tmp_path: Path) -> None:
    log = JobLog(tmp_path / "log" / "jobs.jsonl")
    files = make_files("good.txt", "bad.txt")
    result = run_job(registry.get("test.fail_if_bad"), files, log=log)
    (record,) = list(log.read())
    assert record["job_id"] == result.job_id
    assert record["operation"] == "test.fail_if_bad"
    assert record["options"] == {}
    assert record["inputs"] == [str(p) for p in files]
    assert record["outputs"] == [str(tmp_path / "good-copy.txt")]
    assert record["failures"] == [
        {"input": str(tmp_path / "bad.txt"), "error": "boom", "kind": "ValueError"}
    ]
    assert isinstance(record["started"], str)
    assert isinstance(record["duration_s"], float)


def test_log_failure_does_not_fail_job(
    registry: Registry, make_files: MakeFiles, tmp_path: Path
) -> None:
    blocker = tmp_path / "blocker"
    blocker.write_text("not a folder")
    log = JobLog(blocker / "jobs.jsonl")  # parent is a file, so writing fails
    result = run_job(registry.get("pdf.compress"), make_files("a.pdf"), log=log)
    assert result.ok


def test_result_metadata(registry: Registry, make_files: MakeFiles) -> None:
    files = make_files("a.pdf")
    first = run_job(registry.get("pdf.compress"), files)
    second = run_job(registry.get("pdf.compress"), files)
    assert first.duration_s >= 0
    assert first.operation_id == "pdf.compress"
    assert first.job_id != second.job_id


def test_progress_reported(registry: Registry, make_files: MakeFiles) -> None:
    calls: list[tuple[int, int]] = []
    run_job(
        registry.get("pdf.compress"),
        make_files("a.pdf", "b.pdf"),
        progress=lambda done, total: calls.append((done, total)),
    )
    assert calls == [(1, 2), (2, 2)]


def test_cancel_stops_remaining(registry: Registry, make_files: MakeFiles) -> None:
    checks = iter([False, True, True])
    result = run_job(
        registry.get("pdf.compress"),
        make_files("a.pdf", "b.pdf", "c.pdf"),
        cancel=lambda: next(checks),
    )
    assert [p.name for p in result.outputs] == ["a-copy.pdf"]
    assert [(f.input.name, f.kind) for f in result.failures] == [
        ("b.pdf", "Cancelled"),
        ("c.pdf", "Cancelled"),
    ]


def test_output_dir(registry: Registry, make_files: MakeFiles, tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    result = run_job(registry.get("pdf.compress"), make_files("a.pdf"), output_dir=out_dir)
    assert result.outputs == (out_dir / "a-copy.pdf",)


def test_keyboard_interrupt_propagates(make_files: MakeFiles) -> None:
    reg = Registry()

    @reg.register("t.stop", label="S", group="T", extensions={".txt"}, mode=SelectionMode.EACH)
    def stop(inputs: list[Path], options: dict[str, OptionValue], ctx: RunContext) -> list[Path]:
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        run_job(reg.get("t.stop"), make_files("a.txt"))


# --- output rule enforcement ---------------------------------------------------------


def _single_op(
    run: Callable[[list[Path], dict[str, OptionValue], RunContext], list[Path]],
) -> Registry:
    reg = Registry()
    reg.register("t.op", label="T", group="T", extensions={".txt"}, mode=SelectionMode.EACH)(run)
    return reg


def test_returning_input_is_rejected_and_input_kept(make_files: MakeFiles) -> None:
    def evil(inputs: list[Path], options: dict[str, OptionValue], ctx: RunContext) -> list[Path]:
        return [inputs[0]]

    (src,) = make_files("a.txt")
    result = run_job(_single_op(evil).get("t.op"), [src])
    assert result.outputs == ()
    assert result.failures[0].kind == "OutputError"
    assert src.read_bytes() == b"a.txt"


def test_unreserved_output_rejected(make_files: MakeFiles, tmp_path: Path) -> None:
    def sneaky(inputs: list[Path], options: dict[str, OptionValue], ctx: RunContext) -> list[Path]:
        out = tmp_path / "handmade.txt"
        out.write_text("x")
        return [out]

    result = run_job(_single_op(sneaky).get("t.op"), make_files("a.txt"))
    assert result.failures[0].kind == "OutputError"
    assert "not reserved" in result.failures[0].error


def test_unused_reservations_removed(make_files: MakeFiles, tmp_path: Path) -> None:
    def greedy(inputs: list[Path], options: dict[str, OptionValue], ctx: RunContext) -> list[Path]:
        keep = ctx.output(inputs[0], "keep")
        ctx.output(inputs[0], "unused")
        with ctx.atomic_write(keep) as tmp:
            tmp.write_text("kept")
        return [keep]

    result = run_job(_single_op(greedy).get("t.op"), make_files("a.txt"))
    assert result.ok
    assert names(tmp_path) == ["a-keep.txt", "a.txt"]


def test_atomic_write_requires_reservation(make_files: MakeFiles, tmp_path: Path) -> None:
    def rogue(inputs: list[Path], options: dict[str, OptionValue], ctx: RunContext) -> list[Path]:
        with ctx.atomic_write(inputs[0]) as tmp:  # trying to replace the input
            tmp.write_text("overwritten")
        return []

    (src,) = make_files("a.txt")
    result = run_job(_single_op(rogue).get("t.op"), [src])
    assert result.failures[0].kind == "ValueError"
    assert src.read_bytes() == b"a.txt"
    assert names(tmp_path) == ["a.txt"]
