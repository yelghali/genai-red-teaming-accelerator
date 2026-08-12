"""Strict configuration for selecting native PyRIT or Foundry cloud execution."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, TypeAdapter, field_validator, model_validator

ProfileName = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_-]{1,62}$")]
LabelKey = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_.-]{0,62}$")]

Engine = Literal["pyrit", "foundry"]
RiskCategory = Literal[
    "violence",
    "self_harm",
    "sexual",
    "hate_unfairness",
    "protected_material",
    "ungrounded_attributes",
    "code_vulnerability",
    "prohibited_actions",
    "task_adherence",
    "sensitive_data_leakage",
]
AttackStrategy = Literal[
    "all",
    "easy",
    "moderate",
    "difficult",
    "ansi_attack",
    "ascii_art",
    "ascii_smuggler",
    "atbash",
    "base64",
    "binary",
    "caesar",
    "character_space",
    "char_swap",
    "diacritic",
    "flip",
    "leetspeak",
    "morse",
    "rot13",
    "suffix_append",
    "string_join",
    "unicode_confusable",
    "unicode_substitution",
    "url",
    "jailbreak",
    "tense",
    "multi_turn",
    "crescendo",
    "indirect_jailbreak",
    "pair",
    "tap",
]

_PYRIT_UNSUPPORTED = {"indirect_jailbreak"}
_FOUNDRY_UNSUPPORTED = {"pair", "tap"}


class StrictModel(BaseModel):
    """Reject unknown fields so misspelled security settings cannot be ignored."""

    model_config = ConfigDict(extra="forbid")


class PyRITRuntime(StrictModel):
    """Files and local UI used by native PyRIT."""

    config_file: str = "pyrit/pyrit-config.yaml"
    target_catalog: str = "pyrit/targets.yaml"
    working_directory: str = ".."
    co_pyrit_url: str = "http://127.0.0.1:8014/history"


class FoundryRuntime(StrictModel):
    """Foundry cloud configuration and optional Co-PyRIT snapshot publication."""

    config_file: str = "foundry.yaml"
    output_directory: str = "../artifacts/foundry"
    publish_to_co_pyrit: bool = True


class Runtimes(StrictModel):
    pyrit: PyRITRuntime = Field(default_factory=PyRITRuntime)
    foundry: FoundryRuntime | None = Field(default_factory=FoundryRuntime)


class TargetBinding(StrictModel):
    """The equivalent target name in each native engine configuration."""

    pyrit_target: ProfileName
    foundry_scan: ProfileName | None = None


class ObjectiveBudget(StrictModel):
    """Objective-count semantics exposed by each engine's public API."""

    pyrit_per_risk: int = Field(default=1, ge=1, le=100)
    foundry: Literal["service_managed"] = "service_managed"


class BaselineRisk(StrictModel):
    """One risk category and the native PyRIT datasets used to represent it."""

    name: RiskCategory
    pyrit_datasets: list[str] = Field(min_length=1)

    @field_validator("pyrit_datasets")
    @classmethod
    def validate_dataset_names(cls, value: list[str]) -> list[str]:
        if any(not item.strip() for item in value):
            raise ValueError("pyrit_datasets cannot contain blank names")
        if len(value) != len(set(value)):
            raise ValueError("pyrit_datasets must be unique within a risk category")
        return value


class BaselineSetup(StrictModel):
    """Curated baseline safety coverage shared by the two engines."""

    type: Literal["baseline"]
    risk_categories: list[BaselineRisk] = Field(min_length=1)
    objective_count: ObjectiveBudget = Field(default_factory=ObjectiveBudget)
    attack_strategies: list[AttackStrategy] = Field(default_factory=list)
    include_baseline: bool = True
    max_turns: int = Field(default=5, ge=1, le=50)

    @model_validator(mode="after")
    def validate_unique_inputs(self) -> BaselineSetup:
        risks = [risk.name for risk in self.risk_categories]
        if len(risks) != len(set(risks)):
            raise ValueError("risk category names must be unique")
        if len(self.attack_strategies) != len(set(self.attack_strategies)):
            raise ValueError("attack_strategies must be unique")
        if not self.include_baseline and not self.attack_strategies:
            raise ValueError("enable include_baseline or select at least one attack strategy")
        return self


class CustomSetup(StrictModel):
    """User-authored YAML objectives executed by native PyRIT."""

    type: Literal["custom"]
    objectives_file: str
    max_objectives: int = Field(default=10, ge=1, le=100)
    attack_strategies: list[AttackStrategy] = Field(default_factory=list)
    include_baseline: bool = True
    max_turns: int = Field(default=5, ge=1, le=50)

    @model_validator(mode="after")
    def validate_unique_strategies(self) -> CustomSetup:
        if not self.objectives_file.strip():
            raise ValueError("objectives_file cannot be blank")
        if len(self.attack_strategies) != len(set(self.attack_strategies)):
            raise ValueError("attack_strategies must be unique")
        if not self.include_baseline and not self.attack_strategies:
            raise ValueError("enable include_baseline or select at least one attack strategy")
        return self


TestSetup = Annotated[BaselineSetup | CustomSetup, Field(discriminator="type")]


class TestDefinition(StrictModel):
    """One selectable test profile delegated to exactly one native engine."""

    engine: Engine
    target: ProfileName
    setup: TestSetup
    labels: dict[LabelKey, Annotated[str, Field(min_length=1, max_length=256)]] = Field(default_factory=dict)
    max_concurrency: int = Field(default=1, ge=1, le=50)

    @model_validator(mode="after")
    def validate_engine_capabilities(self) -> TestDefinition:
        strategies = set(self.setup.attack_strategies)
        if self.engine == "pyrit":
            unsupported = strategies & _PYRIT_UNSUPPORTED
            if unsupported:
                raise ValueError(f"native PyRIT does not expose these selected strategies: {sorted(unsupported)}")
        else:
            unsupported = strategies & _FOUNDRY_UNSUPPORTED
            if unsupported:
                raise ValueError(f"Foundry cloud does not expose these selected strategies: {sorted(unsupported)}")
            if isinstance(self.setup, CustomSetup):
                raise ValueError(
                    "Foundry cloud model runs do not accept arbitrary custom objective files; "
                    "use engine='pyrit', or use a reviewed Foundry agent taxonomy for agentic testing"
                )
            if not self.setup.include_baseline:
                raise ValueError("Foundry cloud always emits baseline probes; include_baseline must be true")
        return self


class RedTeamConfig(StrictModel):
    """Unified, thin engine-selection configuration."""

    schema_version: Literal[1] = 1
    selected_test: ProfileName
    runtimes: Runtimes = Field(default_factory=Runtimes)
    targets: dict[ProfileName, TargetBinding] = Field(min_length=1)
    tests: dict[ProfileName, TestDefinition] = Field(min_length=1)
    _base_directory: Path = PrivateAttr(default=Path.cwd())

    @field_validator("targets", "tests")
    @classmethod
    def validate_profile_names(cls, value: dict[str, object]) -> dict[str, object]:
        adapter = TypeAdapter(ProfileName)
        for name in value:
            adapter.validate_python(name)
        return value

    @model_validator(mode="after")
    def validate_references(self) -> RedTeamConfig:
        if self.selected_test not in self.tests:
            raise ValueError(f"selected_test '{self.selected_test}' does not reference a configured test")
        missing = sorted({test.target for test in self.tests.values()} - set(self.targets))
        if missing:
            raise ValueError(f"tests reference unknown targets: {missing}")
        return self

    def resolve_path(self, value: str) -> Path:
        """Resolve a configuration path relative to the unified file."""
        path = Path(value).expanduser()
        return (path if path.is_absolute() else self._base_directory / path).resolve()


class CustomObjective(StrictModel):
    """One user-authored objective and its non-secret provenance metadata."""

    id: ProfileName
    objective: str = Field(min_length=1, max_length=10_000)
    harm_categories: list[str] = Field(default_factory=list)
    metadata: dict[LabelKey, Annotated[str, Field(min_length=1, max_length=256)]] = Field(default_factory=dict)


class CustomObjectiveFile(StrictModel):
    """Strict YAML document containing custom attack objectives."""

    schema_version: Literal[1] = 1
    name: ProfileName
    description: str | None = Field(default=None, max_length=2_000)
    objectives: list[CustomObjective] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_unique_ids(self) -> CustomObjectiveFile:
        ids = [objective.id for objective in self.objectives]
        if len(ids) != len(set(ids)):
            raise ValueError("custom objective IDs must be unique")
        return self


_CONFIG_ADAPTER = TypeAdapter(RedTeamConfig)
_OBJECTIVE_ADAPTER = TypeAdapter(CustomObjectiveFile)


def _load_yaml(path: Path, *, kind: str) -> object:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(f"Could not read {kind} {path}: {exc}") from exc


def load_redteam_config(path: str | Path) -> RedTeamConfig:
    """Load one unified engine-selection configuration document."""
    source = Path(path).expanduser().resolve()
    config = _CONFIG_ADAPTER.validate_python(_load_yaml(source, kind="red-team configuration"))
    config._base_directory = source.parent
    return config


def load_custom_objectives(config: RedTeamConfig, setup: CustomSetup) -> CustomObjectiveFile:
    """Load the custom objective file referenced by a test setup."""
    source = config.resolve_path(setup.objectives_file)
    return _OBJECTIVE_ADAPTER.validate_python(_load_yaml(source, kind="custom objective file"))


def get_test(config: RedTeamConfig, name: str | None = None) -> tuple[str, TestDefinition]:
    """Resolve an explicit test name or the configuration's selected test."""
    selected = name or config.selected_test
    try:
        return selected, config.tests[selected]
    except KeyError as exc:
        available = ", ".join(sorted(config.tests))
        raise ValueError(f"Unknown test '{selected}'. Available: {available}") from exc
