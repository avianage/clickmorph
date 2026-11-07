from collections.abc import Callable
from pathlib import Path

import pytest

from clickmorph.core import (
    Operation,
    Option,
    OptionError,
    OptionValue,
    Registry,
    RunContext,
    SelectionMode,
)

MakeFiles = Callable[..., list[Path]]


def ids(operations: list[Operation]) -> list[str]:
    return [op.id for op in operations]


def noop(inputs: list[Path], options: dict[str, OptionValue], ctx: RunContext) -> list[Path]:
    return []


# --- applicability -------------------------------------------------------------------


def test_single_pdf(registry: Registry, make_files: MakeFiles) -> None:
    assert ids(registry.applicable(make_files("a.pdf"))) == [
        "pdf.compress",
        "pdf.info",
        "tools.copy",
    ]


def test_three_pdfs_offer_merge(registry: Registry, make_files: MakeFiles) -> None:
    ops = registry.applicable(make_files("a.pdf", "b.pdf", "c.pdf"))
    assert ids(ops) == ["pdf.merge", "pdf.compress", "tools.copy"]
    assert ops[0].menu_label(3) == "Merge 3 PDFs"


def test_max_files_limit(registry: Registry, make_files: MakeFiles) -> None:
    ops = registry.applicable(make_files("a.pdf", "b.pdf", "c.pdf", "d.pdf"))
    assert ids(ops) == ["pdf.merge", "pdf.compress"]


def test_unlimited_max_files(registry: Registry, make_files: MakeFiles) -> None:
    files = make_files(*(f"p{i}.pdf" for i in range(500)))
    assert "pdf.merge" in ids(registry.applicable(files))


def test_docx_alone_matches_nothing(registry: Registry, make_files: MakeFiles) -> None:
    assert registry.applicable(make_files("letter.docx")) == []


def test_mixed_selection_only_ops_accepting_all(registry: Registry, make_files: MakeFiles) -> None:
    assert ids(registry.applicable(make_files("a.pdf", "b.jpg"))) == ["tools.copy"]
    assert ids(registry.applicable(make_files("c.jpg", "d.png"))) == ["img.to_pdf"]


def test_one_foreign_file_spoils_selection(registry: Registry, make_files: MakeFiles) -> None:
    assert registry.applicable(make_files("a.pdf", "b.pdf", "notes.txt", "x.docx")) == []


def test_extension_case_insensitive(registry: Registry, make_files: MakeFiles) -> None:
    ops = registry.applicable(make_files("A.PDF", "b.Pdf"))
    assert "pdf.merge" in ids(ops)


def test_file_without_extension(registry: Registry, make_files: MakeFiles) -> None:
    assert registry.applicable(make_files("README")) == []


def test_folder_in_selection(registry: Registry, make_files: MakeFiles, tmp_path: Path) -> None:
    folder = tmp_path / "folder.pdf"
    folder.mkdir()
    assert registry.applicable([*make_files("a.pdf"), folder]) == []


def test_missing_file(registry: Registry, tmp_path: Path) -> None:
    assert registry.applicable([tmp_path / "ghost.pdf"]) == []


def test_empty_selection(registry: Registry) -> None:
    assert registry.applicable([]) == []


def test_accepts_string_paths(registry: Registry, make_files: MakeFiles) -> None:
    files = [str(p) for p in make_files("a.pdf", "b.pdf")]
    assert "pdf.merge" in ids(registry.applicable(files))


def test_results_grouped_by_first_registration(make_files: MakeFiles) -> None:
    reg = Registry()
    for op_id, group in [("pdf.a", "PDF"), ("tools.b", "Tools"), ("pdf.c", "PDF")]:
        reg.register(op_id, label=op_id, group=group, extensions={".pdf"}, mode=SelectionMode.EACH)(
            noop
        )
    assert ids(reg.applicable(make_files("x.pdf"))) == ["pdf.a", "pdf.c", "tools.b"]


def test_matches_without_disk_access(registry: Registry) -> None:
    merge = registry.get("pdf.merge")
    assert merge.matches(2, {".pdf", ".PDF"})
    assert not merge.matches(1, {".pdf"})
    assert not merge.matches(2, {".pdf", ".docx"})


# --- registration --------------------------------------------------------------------


def test_decorator_returns_operation() -> None:
    reg = Registry()
    op = reg.register("x.y", label="Y", group="X", extensions={"PDF"}, mode=SelectionMode.EACH)(
        noop
    )
    assert isinstance(op, Operation)
    assert op.run is noop
    assert op.extensions == frozenset({".pdf"})
    assert reg.get("x.y") is op
    assert "x.y" in reg
    assert len(reg) == 1
    assert list(reg) == [op]


def test_duplicate_id_rejected() -> None:
    reg = Registry()
    reg.register("x.y", label="Y", group="X", extensions={".pdf"}, mode=SelectionMode.EACH)(noop)
    with pytest.raises(ValueError, match="already registered"):
        reg.register("x.y", label="Y", group="X", extensions={".pdf"}, mode=SelectionMode.EACH)(
            noop
        )


def test_get_unknown() -> None:
    with pytest.raises(KeyError, match="nope"):
        Registry().get("nope.op")


@pytest.mark.parametrize("bad_id", ["merge", "PDF.merge", "pdf.", ".merge", "pdf merge", ""])
def test_invalid_ids(bad_id: str) -> None:
    with pytest.raises(ValueError, match="id"):
        Operation(bad_id, "L", "G", frozenset({".pdf"}), SelectionMode.EACH, noop)


def test_needs_extensions() -> None:
    with pytest.raises(ValueError, match="extension"):
        Operation("a.b", "L", "G", frozenset(), SelectionMode.EACH, noop)


def test_max_below_min() -> None:
    with pytest.raises(ValueError, match="max_files"):
        Operation("a.b", "L", "G", frozenset({".pdf"}), SelectionMode.EACH, noop, 3, 2)


def test_min_at_least_one() -> None:
    with pytest.raises(ValueError, match="min_files"):
        Operation("a.b", "L", "G", frozenset({".pdf"}), SelectionMode.EACH, noop, 0)


def test_single_mode_forces_one_file() -> None:
    op = Operation("a.b", "L", "G", frozenset({".pdf"}), SelectionMode.SINGLE, noop, 2, 5)
    assert (op.min_files, op.max_files) == (1, 1)


def test_duplicate_option_names() -> None:
    options = (Option("level", str, "a"), Option("level", int, 1))
    with pytest.raises(ValueError, match="duplicate"):
        Operation("a.b", "L", "G", frozenset({".pdf"}), SelectionMode.EACH, noop, options=options)


def test_menu_label_without_count() -> None:
    op = Operation("a.b", "Compress", "G", frozenset({".pdf"}), SelectionMode.EACH, noop)
    assert op.menu_label(7) == "Compress"


# --- options -------------------------------------------------------------------------


def _op_with(*options: Option) -> Operation:
    return Operation(
        "a.b", "L", "G", frozenset({".pdf"}), SelectionMode.EACH, noop, options=options
    )


def test_defaults() -> None:
    op = _op_with(Option("level", str, "medium"), Option("quality", int, 80))
    assert op.resolve_options() == {"level": "medium", "quality": 80}
    assert op.resolve_options(None) == {"level": "medium", "quality": 80}


def test_override() -> None:
    op = _op_with(Option("level", str, "medium", choices=("low", "medium", "high")))
    assert op.resolve_options({"level": "high"}) == {"level": "high"}


def test_unknown_option() -> None:
    with pytest.raises(OptionError, match="colour"):
        _op_with(Option("level", str, "medium")).resolve_options({"colour": "red"})


def test_wrong_type() -> None:
    with pytest.raises(OptionError, match="expects int"):
        _op_with(Option("quality", int, 80)).resolve_options({"quality": "80"})


def test_bool_is_not_an_int() -> None:
    with pytest.raises(OptionError, match="expects int"):
        _op_with(Option("quality", int, 80)).resolve_options({"quality": True})


def test_int_is_not_a_bool() -> None:
    with pytest.raises(OptionError, match="expects bool"):
        _op_with(Option("strip", bool, False)).resolve_options({"strip": 1})


def test_int_promoted_to_float() -> None:
    result = _op_with(Option("scale", float, 0.5)).resolve_options({"scale": 1})
    assert result == {"scale": 1.0}
    assert isinstance(result["scale"], float)


def test_choice_rejected() -> None:
    op = _op_with(Option("level", str, "medium", choices=("low", "medium", "high")))
    with pytest.raises(OptionError, match="one of"):
        op.resolve_options({"level": "extreme"})


@pytest.mark.parametrize("value", [0, 101])
def test_range_rejected(value: int) -> None:
    with pytest.raises(OptionError, match="must be"):
        _op_with(Option("quality", int, 80, min=1, max=100)).resolve_options({"quality": value})


@pytest.mark.parametrize("value", [1, 100])
def test_range_bounds_inclusive(value: int) -> None:
    op = _op_with(Option("quality", int, 80, min=1, max=100))
    assert op.resolve_options({"quality": value}) == {"quality": value}


def test_invalid_default_rejected_at_definition() -> None:
    with pytest.raises(OptionError):
        Option("level", str, "extreme", choices=("low", "high"))


def test_unsupported_kind() -> None:
    with pytest.raises(TypeError):
        Option("size", list, [])  # type: ignore[arg-type]


def test_option_name_must_be_identifier() -> None:
    with pytest.raises(ValueError, match="identifier"):
        Option("my-level", str, "a")
