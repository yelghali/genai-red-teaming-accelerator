"""Thin engine selection over native PyRIT and Microsoft Foundry APIs."""

from __future__ import annotations

import asyncio
import os
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from genai_red_teaming_accelerator.compatibility import require_supported_pyrit
from genai_red_teaming_accelerator.foundry import FoundryRunner, FoundryRunResult
from genai_red_teaming_accelerator.foundry_config import (
    FoundryConfig,
    FoundryModelTarget,
    FoundryScan,
    load_foundry_config,
)
from genai_red_teaming_accelerator.pyrit_config import load_pyrit_catalog
from genai_red_teaming_accelerator.redteam_config import (
    BaselineSetup,
    CustomSetup,
    RedTeamConfig,
    TestDefinition,
    get_test,
    load_custom_objectives,
)

if TYPE_CHECKING:
    from genai_red_teaming_accelerator.foundry_import import FoundryImportSummary

_FOUNDRY_STRATEGIES = {
    "all": "all",
    "easy": "easy",
    "moderate": "moderate",
    "difficult": "difficult",
    "ansi_attack": "AnsiAttack",
    "ascii_art": "AsciiArt",
    "ascii_smuggler": "AsciiSmuggler",
    "atbash": "Atbash",
    "base64": "Base64",
    "binary": "Binary",
    "caesar": "Caesar",
    "character_space": "CharacterSpace",
    "char_swap": "CharSwap",
    "diacritic": "Diacritic",
    "flip": "Flip",
    "leetspeak": "Leetspeak",
    "morse": "Morse",
    "rot13": "ROT13",
    "suffix_append": "SuffixAppend",
    "string_join": "StringJoin",
    "unicode_confusable": "UnicodeConfusable",
    "unicode_substitution": "UnicodeSubstitution",
    "url": "Url",
    "jailbreak": "Jailbreak",
    "tense": "Tense",
    "multi_turn": "Multiturn",
    "crescendo": "Crescendo",
    "indirect_jailbreak": "IndirectJailbreak",
}


@dataclass(frozen=True, slots=True)
class PyRITRunResult:
    """Small projection of a native PyRIT ScenarioResult."""

    scenario_result_id: str
    status: str
    attacks: int
    successes: int
    failures: int
    errors: int
    co_pyrit_url: str
    labels: dict[str, str]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class UnifiedRunResult:
    """Engine-independent identifiers returned by the selector."""

    test_name: str
    engine: str
    result: PyRITRunResult | FoundryRunResult
    co_pyrit_import: FoundryImportSummary | None = None

    def as_dict(self) -> dict[str, Any]:
        data = self.result.as_dict()
        return {
            "test_name": self.test_name,
            "engine": self.engine,
            "result": data,
            "co_pyrit_import": asdict(self.co_pyrit_import) if self.co_pyrit_import else None,
        }


def _labels(*, test_name: str, test: TestDefinition) -> dict[str, str]:
    labels = {str(key): str(value) for key, value in test.labels.items()}
    labels.update(
        {
            "engine": test.engine,
            "test": test_name,
            "setup": test.setup.type,
            "source": "red_teaming_accelerator",
        }
    )
    return labels


def _foundry_config_for_test(*, config: RedTeamConfig, test: TestDefinition) -> tuple[FoundryConfig, str]:
    """Build a validated Foundry scan copy containing the shared profile workload."""
    assert isinstance(test.setup, BaselineSetup)
    runtime = config.runtimes.foundry
    if runtime is None:
        raise ValueError("Foundry tests require runtimes.foundry")
    source = load_foundry_config(config.resolve_path(runtime.config_file))
    foundry_config = source.model_copy(deep=True)
    scan_name = config.targets[test.target].foundry_scan
    if scan_name is None:
        raise ValueError(f"Foundry test target '{test.target}' requires foundry_scan")
    scan_data = foundry_config.scans[scan_name].model_dump()
    scan_data.update(
        risk_categories=[risk.name for risk in test.setup.risk_categories],
        attack_strategies=[_FOUNDRY_STRATEGIES[strategy] for strategy in test.setup.attack_strategies],
        num_turns=test.setup.max_turns,
    )
    foundry_config.scans[scan_name] = FoundryScan.model_validate(scan_data)
    return foundry_config, scan_name


@contextmanager
def _working_directory(path: Path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


@contextmanager
def _environment_variable(name: str, value: str):
    previous = os.environ.get(name)
    os.environ[name] = value
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = previous


def validate_runtime_references(config: RedTeamConfig) -> None:
    """Validate referenced native files, targets, scans, and custom objectives offline."""
    pyrit_config_path = config.resolve_path(config.runtimes.pyrit.config_file)
    target_catalog_path = config.resolve_path(config.runtimes.pyrit.target_catalog)
    working_directory = config.resolve_path(config.runtimes.pyrit.working_directory)
    for description, path in (
        ("PyRIT configuration", pyrit_config_path),
        ("PyRIT target catalog", target_catalog_path),
    ):
        if not path.is_file():
            raise ValueError(f"{description} does not exist: {path}")
    if not working_directory.is_dir():
        raise ValueError(f"PyRIT working_directory does not exist: {working_directory}")

    pyrit_catalog = load_pyrit_catalog(target_catalog_path)
    foundry_config = None
    if config.runtimes.foundry is not None:
        foundry_config_path = config.resolve_path(config.runtimes.foundry.config_file)
        if not foundry_config_path.is_file():
            raise ValueError(f"Foundry configuration does not exist: {foundry_config_path}")
        foundry_config = load_foundry_config(foundry_config_path)
    pyrit_targets = {definition.name for definition in pyrit_catalog.targets}
    for name, binding in config.targets.items():
        if binding.pyrit_target not in pyrit_targets:
            raise ValueError(f"target '{name}' references unknown PyRIT target '{binding.pyrit_target}'")
        if binding.foundry_scan is not None and foundry_config is None:
            raise ValueError(f"target '{name}' defines foundry_scan but runtimes.foundry is not configured")
        if (
            foundry_config is not None
            and binding.foundry_scan is not None
            and binding.foundry_scan not in foundry_config.scans
        ):
            raise ValueError(f"target '{name}' references unknown Foundry scan '{binding.foundry_scan}'")

    for test in config.tests.values():
        if isinstance(test.setup, CustomSetup):
            load_custom_objectives(config, test.setup)
        if test.engine == "foundry":
            _foundry_config_for_test(config=config, test=test)


def build_plan(config: RedTeamConfig, *, test_name: str | None = None) -> dict[str, Any]:
    """Build an offline, non-executing plan showing the exact native delegation."""
    validate_runtime_references(config)
    name, test = get_test(config, test_name)
    binding = config.targets[test.target]
    labels = _labels(test_name=name, test=test)
    base: dict[str, Any] = {
        "test": name,
        "engine": test.engine,
        "target_binding": test.target,
        "setup": test.setup.type,
        "labels": labels,
        "max_concurrency": test.max_concurrency,
    }

    strategies = list(test.setup.attack_strategies)
    if test.engine == "pyrit":
        datasets: list[str] | None = None
        objective_source: dict[str, Any]
        if isinstance(test.setup, BaselineSetup):
            datasets = [dataset for risk in test.setup.risk_categories for dataset in risk.pyrit_datasets]
            objective_source = {
                "kind": "native_pyrit_datasets",
                "datasets": datasets,
                "objectives_per_risk": test.setup.objective_count.pyrit_per_risk,
            }
        else:
            objectives = load_custom_objectives(config, test.setup)
            objective_source = {
                "kind": "custom_yaml",
                "file": str(config.resolve_path(test.setup.objectives_file)),
                "available": len(objectives.objectives),
                "maximum": test.setup.max_objectives,
            }
        base["delegation"] = {
            "native_api": "pyrit.registry.ScenarioRegistry.create_and_initialize_async",
            "scenario": "accelerator.red_team_agent",
            "upstream_scenario": "foundry.red_team_agent",
            "target": binding.pyrit_target,
            "target_catalog": str(config.resolve_path(config.runtimes.pyrit.target_catalog)),
            "objective_source": objective_source,
            "techniques": strategies,
            "include_baseline": test.setup.include_baseline,
            "max_turns": test.setup.max_turns,
            "result_store": "PyRIT SQLite memory / Co-PyRIT",
            "co_pyrit_url": config.runtimes.pyrit.co_pyrit_url,
        }
        return base

    foundry_config, scan_name = _foundry_config_for_test(config=config, test=test)
    scan = foundry_config.scans[scan_name]
    target = scan.target
    if isinstance(target, FoundryModelTarget):
        deployment = (
            target.deployment if not target.connection_name else f"{target.connection_name}/{target.deployment}"
        )
        target_payload: dict[str, Any] = {"type": "azure_ai_model", "model": deployment}
    else:
        target_payload = {"type": "azure_ai_agent", "name": target.name, "version": target.version}
    assert isinstance(test.setup, BaselineSetup)
    assert config.runtimes.foundry is not None
    base["delegation"] = {
        "native_api": "azure.ai.projects.AIProjectClient.get_openai_client().evals",
        "project_endpoint": str(foundry_config.project_endpoint),
        "configured_scan": scan_name,
        "target": target_payload,
        "risk_categories": [risk.name for risk in test.setup.risk_categories],
        "attack_strategies": [_FOUNDRY_STRATEGIES[strategy] for strategy in strategies],
        "include_baseline": True,
        "objective_count": "service_managed",
        "max_turns": test.setup.max_turns,
        "result_store": "Foundry evaluation/run plus local JSON",
        "output_directory": str(config.resolve_path(config.runtimes.foundry.output_directory)),
        "publish_completed_snapshot_to_co_pyrit": config.runtimes.foundry.publish_to_co_pyrit,
        "capability_note": (
            "The Foundry cloud API does not expose an objective-count input for model runs; "
            "the service owns objective generation and redacts adversarial inputs in results."
        ),
    }
    return base


class PyRITRunner:
    """Delegate a selected test to PyRIT's ScenarioRegistry and attack library."""

    async def _run_async(self, *, config: RedTeamConfig, test_name: str, test: TestDefinition) -> PyRITRunResult:
        require_supported_pyrit()
        from pyrit.models import AttackOutcome, SeedObjective
        from pyrit.registry import ScenarioRegistry
        from pyrit.scenario.core.dataset_configuration import (
            CompoundDatasetAttackConfiguration,
            DatasetAttackConfiguration,
        )
        from pyrit.scenario.scenarios.foundry.red_team_agent import FoundryTechnique
        from pyrit.setup.configuration_loader import ConfigurationLoader

        from genai_red_teaming_accelerator.pyrit_scenario import ConfiguredRedTeamAgent

        runtime = config.runtimes.pyrit
        config_path = config.resolve_path(runtime.config_file)
        target_catalog_path = config.resolve_path(runtime.target_catalog)
        working_directory = config.resolve_path(runtime.working_directory)
        with (
            _working_directory(working_directory),
            _environment_variable("RTA_PYRIT_TARGETS", str(target_catalog_path)),
        ):
            loader = ConfigurationLoader.from_yaml_file(config_path)
            await loader.initialize_pyrit_async()

            registry = ScenarioRegistry.get_registry_singleton()
            scenario_name = "accelerator.red_team_agent"
            if scenario_name not in registry.get_class_names():
                registry.register_class(ConfiguredRedTeamAgent, name=scenario_name)

            if isinstance(test.setup, BaselineSetup):
                dataset_config = CompoundDatasetAttackConfiguration(
                    configurations=[
                        DatasetAttackConfiguration(
                            dataset_names=risk.pyrit_datasets,
                            max_dataset_size=test.setup.objective_count.pyrit_per_risk,
                        )
                        for risk in test.setup.risk_categories
                    ]
                )
            else:
                objective_file = load_custom_objectives(config, test.setup)
                seeds = [
                    SeedObjective(
                        name=objective.id,
                        value=objective.objective,
                        dataset_name=objective_file.name,
                        harm_categories=objective.harm_categories,
                        source=str(config.resolve_path(test.setup.objectives_file)),
                        metadata=objective.metadata,
                    )
                    for objective in objective_file.objectives
                ]
                dataset_config = DatasetAttackConfiguration(
                    seeds=seeds,
                    max_dataset_size=test.setup.max_objectives,
                )

            technique_by_value = {technique.value: technique for technique in FoundryTechnique}
            selected_techniques = [technique_by_value[strategy] for strategy in test.setup.attack_strategies]
            labels = _labels(test_name=test_name, test=test)
            scenario = await registry.create_and_initialize_async(
                scenario_name,
                scenario_params={"max_turns": test.setup.max_turns},
                objective_target=config.targets[test.target].pyrit_target,
                scenario_techniques=selected_techniques,
                dataset_config=dataset_config,
                memory_labels=labels,
                max_concurrency=test.max_concurrency,
                max_retries=0,
                include_baseline=test.setup.include_baseline,
            )
            result = await scenario.run_async()

        attacks = [attack for group in result.attack_results.values() for attack in group]
        return PyRITRunResult(
            scenario_result_id=str(result.id),
            status=result.scenario_run_state.value,
            attacks=len(attacks),
            successes=sum(attack.outcome is AttackOutcome.SUCCESS for attack in attacks),
            failures=sum(attack.outcome is AttackOutcome.FAILURE for attack in attacks),
            errors=sum(attack.outcome is AttackOutcome.ERROR for attack in attacks),
            co_pyrit_url=runtime.co_pyrit_url,
            labels=labels,
        )

    def run(self, *, config: RedTeamConfig, test_name: str, test: TestDefinition) -> PyRITRunResult:
        return asyncio.run(self._run_async(config=config, test_name=test_name, test=test))


class RedTeamRunner:
    """Select one engine from configuration and delegate without owning attack loops."""

    def __init__(
        self,
        *,
        pyrit_runner: PyRITRunner | None = None,
        foundry_runner: FoundryRunner | None = None,
    ) -> None:
        self._pyrit_runner = pyrit_runner or PyRITRunner()
        self._foundry_runner = foundry_runner or FoundryRunner()

    @staticmethod
    def _publish_foundry_result(result: FoundryRunResult) -> FoundryImportSummary:
        from pyrit.memory import CentralMemory
        from pyrit.setup import initialize_pyrit_async

        from genai_red_teaming_accelerator.foundry_import import import_foundry_result

        try:
            memory = CentralMemory.get_memory_instance()
        except ValueError:
            asyncio.run(initialize_pyrit_async("SQLite", load_defaults=False, silent=True))
            memory = CentralMemory.get_memory_instance()
        return import_foundry_result(result=result, memory=memory)

    def run(self, *, config: RedTeamConfig, test_name: str | None = None) -> UnifiedRunResult:
        """Run one selected profile after complete offline reference validation."""
        validate_runtime_references(config)
        name, test = get_test(config, test_name)
        if test.engine == "pyrit":
            result = self._pyrit_runner.run(config=config, test_name=name, test=test)
            return UnifiedRunResult(test_name=name, engine="pyrit", result=result)

        foundry_config, scan_name = _foundry_config_for_test(config=config, test=test)
        assert config.runtimes.foundry is not None
        result = self._foundry_runner.run(
            config=foundry_config,
            scan_name=scan_name,
            output_directory=config.resolve_path(config.runtimes.foundry.output_directory),
            wait=True,
            labels=_labels(test_name=name, test=test),
        )
        imported = None
        if result.status == "completed" and config.runtimes.foundry.publish_to_co_pyrit:
            imported = self._publish_foundry_result(result)
        return UnifiedRunResult(test_name=name, engine="foundry", result=result, co_pyrit_import=imported)
