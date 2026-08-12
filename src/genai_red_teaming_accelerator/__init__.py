"""Native PyRIT target configuration and Microsoft Foundry evaluation support."""

from genai_red_teaming_accelerator.compatibility import (
    FOUNDRY_PROJECTS_VERSION,
    PYRIT_VERSION,
    require_supported_pyrit,
)

__all__ = ["FOUNDRY_PROJECTS_VERSION", "PYRIT_VERSION", "require_supported_pyrit"]
__version__ = "0.1.0"
