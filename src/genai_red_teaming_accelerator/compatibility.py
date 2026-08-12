"""Pinned dependency contracts used by runtime adapters."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

PYRIT_VERSION = "1.0.1"
FOUNDRY_PROJECTS_VERSION = "2.4.0"
SUPPORTED_PYTHON = ">=3.11,<3.15"


class IncompatibleDependencyError(RuntimeError):
    """Raised when a runtime dependency differs from its verified contract."""


def installed_version(distribution: str) -> str | None:
    """Return an installed distribution version without importing it."""
    try:
        return version(distribution)
    except PackageNotFoundError:
        return None


def require_supported_pyrit() -> None:
    """Fail before execution when the installed PyRIT contract is unsupported."""
    installed = installed_version("pyrit")
    if installed != PYRIT_VERSION:
        actual = installed or "not installed"
        raise IncompatibleDependencyError(
            f"This accelerator requires pyrit=={PYRIT_VERSION}; found {actual}. "
            "Install the pinned project dependencies before running a scan."
        )


def require_supported_foundry() -> None:
    """Fail before cloud execution when the verified Foundry SDK is unavailable."""
    installed = installed_version("azure-ai-projects")
    if installed != FOUNDRY_PROJECTS_VERSION:
        actual = installed or "not installed"
        raise IncompatibleDependencyError(
            f"Foundry cloud execution requires azure-ai-projects=={FOUNDRY_PROJECTS_VERSION}; found {actual}. "
            "Install the project's 'foundry' extra before running the scan."
        )
