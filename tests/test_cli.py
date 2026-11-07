from typer.testing import CliRunner

from clickmorph import __version__
from clickmorph.cli.main import app

runner = CliRunner()


def test_version_flag_prints_version() -> None:
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.output.strip() == f"cm {__version__}"
