from pathlib import Path

import pytest

from clickmorph.core import atomic_write, naming, output_name, reserve_output


def touch(path: Path, content: bytes = b"x") -> Path:
    path.write_bytes(content)
    return path


def test_suffix_next_to_source(tmp_path: Path) -> None:
    src = touch(tmp_path / "report.pdf")
    assert output_name(src, "compressed") == tmp_path / "report-compressed.pdf"


def test_output_name_creates_nothing(tmp_path: Path) -> None:
    src = touch(tmp_path / "report.pdf")
    output_name(src, "compressed")
    assert sorted(p.name for p in tmp_path.iterdir()) == ["report.pdf"]


@pytest.mark.parametrize("ext", ["jpg", ".jpg", ".JPG", " jpg "])
def test_extension_override(tmp_path: Path, ext: str) -> None:
    src = touch(tmp_path / "scan.pdf")
    assert output_name(src, "page1", ext=ext) == tmp_path / "scan-page1.jpg"


def test_no_suffix_with_new_extension(tmp_path: Path) -> None:
    src = touch(tmp_path / "photo.heic")
    assert output_name(src, "", ext="jpg") == tmp_path / "photo.jpg"


def test_no_suffix_same_extension_never_returns_input(tmp_path: Path) -> None:
    src = touch(tmp_path / "photo.jpg")
    assert output_name(src, "") == tmp_path / "photo (1).jpg"


def test_source_extension_case_preserved(tmp_path: Path) -> None:
    src = touch(tmp_path / "Photo.JPG")
    assert output_name(src, "small") == tmp_path / "Photo-small.JPG"


def test_custom_directory(tmp_path: Path) -> None:
    src = touch(tmp_path / "report.pdf")
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    assert output_name(src, "compressed", directory=out_dir) == out_dir / "report-compressed.pdf"


def test_collisions_count_up(tmp_path: Path) -> None:
    src = touch(tmp_path / "report.pdf")
    touch(tmp_path / "report-compressed.pdf")
    assert output_name(src, "compressed") == tmp_path / "report-compressed (1).pdf"
    touch(tmp_path / "report-compressed (1).pdf")
    assert output_name(src, "compressed") == tmp_path / "report-compressed (2).pdf"


def test_collision_fills_first_gap(tmp_path: Path) -> None:
    src = touch(tmp_path / "report.pdf")
    touch(tmp_path / "report-compressed.pdf")
    touch(tmp_path / "report-compressed (2).pdf")
    assert output_name(src, "compressed") == tmp_path / "report-compressed (1).pdf"


def test_existing_directory_counts_as_taken(tmp_path: Path) -> None:
    src = touch(tmp_path / "report.pdf")
    (tmp_path / "report-compressed.pdf").mkdir()
    assert output_name(src, "compressed") == tmp_path / "report-compressed (1).pdf"


def test_taken_names_skipped(tmp_path: Path) -> None:
    src = touch(tmp_path / "report.pdf")
    taken = [tmp_path / "report-compressed.pdf", tmp_path / "report-compressed (1).pdf"]
    assert output_name(src, "compressed", taken=taken) == tmp_path / "report-compressed (2).pdf"


def test_taken_is_case_insensitive(tmp_path: Path) -> None:
    src = touch(tmp_path / "report.pdf")
    taken = [tmp_path / "REPORT-COMPRESSED.PDF"]
    assert output_name(src, "compressed", taken=taken) == tmp_path / "report-compressed (1).pdf"


def test_inputs_never_returned_even_if_missing(tmp_path: Path) -> None:
    src = touch(tmp_path / "a.pdf")
    other_input = tmp_path / "a-merged.pdf"  # not on disk; must still be avoided
    assert output_name(src, "merged", inputs=[other_input]) == tmp_path / "a-merged (1).pdf"


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("report.v2.pdf", "report.v2-compressed.pdf"),
        ("archive.tar.gz", "archive.tar-compressed.gz"),
        ("README", "README-compressed"),
        ("my report (final).pdf", "my report (final)-compressed.pdf"),
    ],
)
def test_awkward_names(tmp_path: Path, name: str, expected: str) -> None:
    src = touch(tmp_path / name)
    assert output_name(src, "compressed") == tmp_path / expected


def test_unicode_names(tmp_path: Path) -> None:
    src = touch(tmp_path / "résumé 日本.pdf")
    assert output_name(src, "compressed") == tmp_path / "résumé 日本-compressed.pdf"


def test_source_unchanged(tmp_path: Path) -> None:
    src = touch(tmp_path / "report.pdf", b"original")
    reserve_output(src, "compressed")
    assert src.read_bytes() == b"original"


# --- reservation ---------------------------------------------------------------------


def test_reserve_creates_empty_placeholder(tmp_path: Path) -> None:
    src = touch(tmp_path / "report.pdf")
    out = reserve_output(src, "compressed")
    assert out == tmp_path / "report-compressed.pdf"
    assert out.is_file()
    assert out.stat().st_size == 0


def test_two_reservations_differ(tmp_path: Path) -> None:
    src = touch(tmp_path / "report.pdf")
    first = reserve_output(src, "compressed")
    second = reserve_output(src, "compressed")
    assert first != second
    assert second == tmp_path / "report-compressed (1).pdf"


def test_reserve_survives_race(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Pretend nothing exists, so the exclusive create is what detects the clash.
    src = touch(tmp_path / "report.pdf")
    rival = touch(tmp_path / "report-compressed.pdf", b"someone else's")
    monkeypatch.setattr(naming, "_exists", lambda path: False)
    out = reserve_output(src, "compressed")
    assert out == tmp_path / "report-compressed (1).pdf"
    assert rival.read_bytes() == b"someone else's"


def test_gives_up_eventually(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    src = touch(tmp_path / "report.pdf")
    monkeypatch.setattr(naming, "MAX_ATTEMPTS", 3)
    for name in ["report-c.pdf", "report-c (1).pdf", "report-c (2).pdf"]:
        touch(tmp_path / name)
    with pytest.raises(FileExistsError):
        output_name(src, "c")


# --- atomic writes -------------------------------------------------------------------


def test_atomic_write_commits(tmp_path: Path) -> None:
    out = reserve_output(touch(tmp_path / "a.pdf"), "x")
    with atomic_write(out) as tmp:
        assert tmp.parent == out.parent
        assert tmp != out
        tmp.write_bytes(b"result")
    assert out.read_bytes() == b"result"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["a-x.pdf", "a.pdf"]


def test_atomic_write_error_leaves_no_temp(tmp_path: Path) -> None:
    out = reserve_output(touch(tmp_path / "a.pdf"), "x")
    with pytest.raises(RuntimeError), atomic_write(out) as tmp:
        tmp.write_bytes(b"half")
        raise RuntimeError("fail")
    assert out.read_bytes() == b""  # placeholder untouched, left for its owner
    assert sorted(p.name for p in tmp_path.iterdir()) == ["a-x.pdf", "a.pdf"]
