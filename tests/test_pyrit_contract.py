from __future__ import annotations

import inspect
from importlib.metadata import version

from genai_red_teaming_accelerator.compatibility import PYRIT_VERSION


def test_exact_pyrit_release_is_installed() -> None:
    assert version("pyrit") == PYRIT_VERSION


def test_native_cli_and_target_contracts() -> None:
    from pyrit.prompt_target import HTTPTarget, PlaywrightTarget
    from pyrit.registry import TargetRegistry
    from pyrit.setup import initialize_pyrit_async

    assert "interaction_func" in inspect.signature(PlaywrightTarget).parameters
    assert "http_request" in inspect.signature(HTTPTarget).parameters
    assert "initialization_scripts" in inspect.signature(initialize_pyrit_async).parameters
    assert hasattr(TargetRegistry.get_registry_singleton().instances, "register")


def test_selected_native_scenario_and_technique_exist() -> None:
    from pyrit.registry import ScenarioRegistry
    from pyrit.scenario.scenarios.airt.jailbreak import _extra_default_factories

    assert "airt.jailbreak" in ScenarioRegistry.get_registry_singleton().get_class_names()
    assert "prompt_sending" in _extra_default_factories()
