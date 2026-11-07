"""Entry point for the `cm` command."""

from typing import Annotated

import typer

from clickmorph import __version__

app = typer.Typer(
    name="cm",
    help="ClickMorph: convert, compress and merge files from the command line.",
    no_args_is_help=True,
    add_completion=False,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"cm {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-V",
            help="Show the version and exit.",
            callback=_version_callback,
            is_eager=True,
        ),
    ] = False,
) -> None:
    """ClickMorph: convert, compress and merge files from the command line."""


if __name__ == "__main__":  # pragma: no cover
    app()
