"""ClickMorph: file tools in the Explorer right-click menu."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__: str = version("clickmorph")
except PackageNotFoundError:  # pragma: no cover - only when running from an uninstalled tree
    __version__ = "0.0.0"

__all__ = ["__version__"]
