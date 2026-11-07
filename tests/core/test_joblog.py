from pathlib import Path

import pytest

from clickmorph.core import JobLog, default_log_path


def test_round_trip_creates_parent(tmp_path: Path) -> None:
    log = JobLog(tmp_path / "nested" / "dir" / "jobs.jsonl")
    log.append({"job_id": "1", "inputs": ["a.pdf"], "outputs": ["a-x.pdf"]})
    log.append({"job_id": "2", "inputs": ["résumé.pdf"], "outputs": []})
    assert list(log.read()) == [
        {"job_id": "1", "inputs": ["a.pdf"], "outputs": ["a-x.pdf"]},
        {"job_id": "2", "inputs": ["résumé.pdf"], "outputs": []},
    ]


def test_one_line_per_record(tmp_path: Path) -> None:
    log = JobLog(tmp_path / "jobs.jsonl")
    log.append({"a": 1})
    log.append({"b": "line\nbreak"})
    assert len(log.path.read_text(encoding="utf-8").splitlines()) == 2


def test_corrupt_lines_skipped(tmp_path: Path) -> None:
    log = JobLog(tmp_path / "jobs.jsonl")
    log.append({"job_id": "1"})
    with log.path.open("a", encoding="utf-8") as handle:
        handle.write('{"job_id": "trunc\n')
        handle.write("[1, 2]\n")
        handle.write("\n")
    log.append({"job_id": "2"})
    assert [r["job_id"] for r in log.read()] == ["1", "2"]


def test_missing_file_reads_empty(tmp_path: Path) -> None:
    assert list(JobLog(tmp_path / "none.jsonl").read()) == []


def test_env_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLICKMORPH_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    assert default_log_path() == tmp_path / "data" / "jobs.jsonl"
    assert JobLog.default().path == tmp_path / "data" / "jobs.jsonl"


def test_local_app_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLICKMORPH_DATA_DIR", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    assert default_log_path() == tmp_path / "local" / "ClickMorph" / "jobs.jsonl"


def test_xdg_state_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLICKMORPH_DATA_DIR", raising=False)
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    assert default_log_path() == tmp_path / "state" / "clickmorph" / "jobs.jsonl"


def test_home_fallback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for var in ("CLICKMORPH_DATA_DIR", "LOCALAPPDATA", "XDG_STATE_HOME"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    assert default_log_path() == tmp_path / ".local" / "state" / "clickmorph" / "jobs.jsonl"
