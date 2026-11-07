import random
from pathlib import Path, PurePosixPath

import pytest

from clickmorph.core import natural_key, natural_sorted


@pytest.mark.parametrize(
    ("items", "expected"),
    [
        (["page10", "page2", "page1"], ["page1", "page2", "page10"]),
        (["10", "9", "100", "1"], ["1", "9", "10", "100"]),
        (["banana", "apple", "Cherry"], ["apple", "banana", "Cherry"]),
        (["b", "A", "a", "B"], ["A", "a", "B", "b"]),
        (["p1", "p01", "p2", "p001"], ["p001", "p01", "p1", "p2"]),
        (["v1.10", "v1.9", "v1.2"], ["v1.2", "v1.9", "v1.10"]),
        (["img 12 (3)", "img 12 (10)", "img 2 (1)"], ["img 2 (1)", "img 12 (3)", "img 12 (10)"]),
        (["10a", "9b", "a10", "a9"], ["9b", "10a", "a9", "a10"]),
        (["é10", "é9", "e1"], ["e1", "é9", "é10"]),
        (["", "a"], ["", "a"]),
    ],
)
def test_ordering(items: list[str], expected: list[str]) -> None:
    assert natural_sorted(items) == expected


def test_page_numbers_like_explorer() -> None:
    names = [f"scan page{n}.pdf" for n in [1, 2, 3, 10, 11, 20, 100]]
    shuffled = names[:]
    random.Random(42).shuffle(shuffled)
    assert natural_sorted(shuffled) == names


def test_paths_sort_by_name_then_folder() -> None:
    paths = [
        PurePosixPath("b/page2.pdf"),
        PurePosixPath("a/page10.pdf"),
        PurePosixPath("a/page2.pdf"),
    ]
    assert natural_sorted(paths) == [
        PurePosixPath("a/page2.pdf"),
        PurePosixPath("b/page2.pdf"),
        PurePosixPath("a/page10.pdf"),
    ]


def test_keeps_item_type(tmp_path: Path) -> None:
    result = natural_sorted([tmp_path / "b2", tmp_path / "b1"])
    assert all(isinstance(p, Path) for p in result)
    assert [p.name for p in result] == ["b1", "b2"]


def test_deterministic_regardless_of_input_order() -> None:
    items = ["Straße", "STRASSE", "strasse", "p01", "p1", "A", "a"]
    reference = natural_sorted(items)
    for seed in range(20):
        shuffled = items[:]
        random.Random(seed).shuffle(shuffled)
        assert natural_sorted(shuffled) == reference


def test_huge_numbers() -> None:
    assert natural_sorted(["x99999999999999999999", "x100000000000000000000"]) == [
        "x99999999999999999999",
        "x100000000000000000000",
    ]


def test_key_equal_names_only_differ_in_tiebreak() -> None:
    assert natural_key("p01")[0] == natural_key("p1")[0]
    assert natural_key("p01") != natural_key("p1")
