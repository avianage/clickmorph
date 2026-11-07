# Contributing to ClickMorph

Thanks for helping out! Bug reports, ideas and pull requests are all welcome.

## Contributor License Agreement (CLA)

Before your first pull request can be merged, you must sign the project's Contributor
License Agreement. A bot will comment on your pull request with a link; signing takes a
minute and covers all your future contributions.

The CLA lets the project keep a single copyright holder, so the license can be managed
consistently over time (for example, to offer the code under additional licenses). You
keep the right to use your own contributions however you like.

## Getting started

1. Install [uv](https://docs.astral.sh/uv/).
2. Fork and clone the repository.
3. Set up the environment and git hooks:

   ```console
   uv sync
   uv run pre-commit install
   ```

4. Check that everything passes:

   ```console
   uv run ruff check
   uv run ruff format --check
   uv run pytest
   ```

## Project layout

| Path | Contents |
| --- | --- |
| `src/clickmorph/core/` | Conversion engine. Pure Python and OS-independent. |
| `src/clickmorph/cli/` | The `cm` command (Typer). A thin layer over `core`. |
| `src/clickmorph/shell/` | Windows integration: daemon, context menu, notifications. |
| `native/` | Rust handler for the Windows 11 context menu (planned). |
| `installer/` | Packaging and installers (planned). |
| `tests/` | pytest suite and sample files. |

## Guidelines

- **Never overwrite input files.** Every operation writes a new file with a
  collision-safe name.
- **Keep `core` OS-independent.** No Windows APIs or registry access there; it must pass
  its tests on Linux.
- **Add tests.** Every operation needs at least one test.
- **Use type hints** on all functions and methods.
- **Watch memory use.** Process pages and images one at a time where possible.
- **Check dependency licenses.** No AGPL dependencies (for example PyMuPDF or
  Ghostscript). Prefer MIT, BSD, Apache-2.0, MPL or LGPL.
- Keep pull requests focused on one change, and explain the reason for it in the
  description.

## Reporting bugs

Open an issue using the bug report template. Include your Windows version, the
ClickMorph version (`cm --version`), and, if you can, a sample file that reproduces the
problem. Please don't attach files that contain private information.

## Code of conduct

This project follows the [Code of Conduct](CODE_OF_CONDUCT.md). By taking part, you agree
to follow it.
