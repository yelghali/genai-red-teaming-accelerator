"""Strict configuration for Microsoft Foundry-managed red-team evaluations."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated, Literal

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, TypeAdapter, field_validator, model_validator

from genai_red_teaming_accelerator.config_io import load_yaml_document

ScanName = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_-]{1,62}$")]
EnvironmentName = Annotated[str, Field(pattern=r"^[A-Z_][A-Z0-9_]*$")]

SafetyRisk = Literal[
    "violence",
    "self_harm",
    "sexual",
    "hate_unfairness",
    "protected_material",
    "ungrounded_attributes",
    "code_vulnerability",
]
AgenticRisk = Literal["prohibited_actions", "task_adherence", "sensitive_data_leakage"]
RiskCategory = SafetyRisk | AgenticRisk
AttackStrategy = Literal[
    "all",
    "easy",
    "moderate",
    "difficult",
    "AnsiAttack",
    "AsciiArt",
    "AsciiSmuggler",
    "Atbash",
    "Base64",
    "Binary",
    "Caesar",
    "CharacterSpace",
    "CharSwap",
    "Diacritic",
    "Flip",
    "Leetspeak",
    "Morse",
    "ROT13",
    "SuffixAppend",
    "StringJoin",
    "UnicodeConfusable",
    "UnicodeSubstitution",
    "Url",
    "Jailbreak",
    "Tense",
    "Crescendo",
    "Multiturn",
    "IndirectJailbreak",
]

_SAFETY_RISKS = {
    "violence",
    "self_harm",
    "sexual",
    "hate_unfairness",
    "protected_material",
    "ungrounded_attributes",
    "code_vulnerability",
}
_AGENTIC_RISKS = {"prohibited_actions", "task_adherence", "sensitive_data_leakage"}


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)


class Authorization(StrictModel):
    environment: EnvironmentName = "REDTEAM_SCOPE_APPROVED"
    expected_value: str = "true"


class FoundryModelTarget(StrictModel):
    """A real model deployment in the configured Foundry project."""

    type: Literal["model"]
    provider: str = Field(min_length=1)
    publisher: str = Field(min_length=1)
    deployment: str = Field(min_length=1)
    model: str = Field(min_length=1)
    version: str = Field(min_length=1)
    connection_name: str | None = None
    ready: bool = True
    status_reason: str | None = None

    @model_validator(mode="after")
    def require_status_reason(self) -> FoundryModelTarget:
        if not self.ready and not self.status_reason:
            raise ValueError("A target that is not ready requires status_reason")
        return self


class FoundryAgentTarget(StrictModel):
    """A versioned agent in the configured Foundry project."""

    type: Literal["agent"]
    name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    ready: bool = True
    status_reason: str | None = None

    @model_validator(mode="after")
    def require_status_reason(self) -> FoundryAgentTarget:
        if not self.ready and not self.status_reason:
            raise ValueError("A target that is not ready requires status_reason")
        return self


FoundryTarget = Annotated[FoundryModelTarget | FoundryAgentTarget, Field(discriminator="type")]


class FoundryScan(StrictModel):
    """One portal-visible evaluation against one real Foundry target."""

    target: FoundryTarget
    risk_categories: list[RiskCategory] = Field(min_length=1)
    attack_strategies: list[AttackStrategy] = Field(default_factory=list)
    num_turns: int = Field(default=1, ge=1, le=50)
    evaluator_deployment: str | None = None
    reviewed_taxonomy_id: str | None = Field(default=None, pattern=r"^azureai://")

    @model_validator(mode="after")
    def validate_target_options(self) -> FoundryScan:
        risks = set(self.risk_categories)
        if isinstance(self.target, FoundryModelTarget) and risks - _SAFETY_RISKS:
            raise ValueError("Model targets support safety risk categories only")
        if isinstance(self.target, FoundryModelTarget) and "IndirectJailbreak" in self.attack_strategies:
            raise ValueError("IndirectJailbreak requires a Foundry agent target")
        if isinstance(self.target, FoundryAgentTarget):
            if risks - _AGENTIC_RISKS:
                raise ValueError("Agent targets support agentic risk categories only")
            if not self.reviewed_taxonomy_id:
                raise ValueError("Agent scans require an independently reviewed taxonomy ID")
            if "task_adherence" in risks and not self.evaluator_deployment:
                raise ValueError("Task adherence requires evaluator_deployment")
        return self


class FoundryConfig(StrictModel):
    """One Foundry project and its configured, provider-agnostic scans."""

    schema_version: Literal[1] = 1
    project_endpoint: AnyHttpUrl
    authorization: Authorization = Field(default_factory=Authorization)
    allow_provider_managed_workload: bool = False
    output_directory: str = "artifacts/foundry"
    timeout_minutes: int = Field(default=60, gt=0, le=1440)
    poll_interval_seconds: int = Field(default=10, ge=2, le=300)
    scans: dict[ScanName, FoundryScan] = Field(min_length=1)

    @field_validator("project_endpoint")
    @classmethod
    def validate_project_endpoint(cls, value: AnyHttpUrl) -> AnyHttpUrl:
        if value.username is not None or value.password is not None:
            raise ValueError("Foundry project endpoint must not embed credentials; use Azure identity")
        if value.scheme != "https":
            raise ValueError("Foundry project endpoint must use HTTPS")
        return value

    @field_validator("scans")
    @classmethod
    def validate_scan_names(cls, value: dict[str, FoundryScan]) -> dict[str, FoundryScan]:
        adapter = TypeAdapter(ScanName)
        for name in value:
            adapter.validate_python(name)
        return value


_CONFIG_ADAPTER = TypeAdapter(FoundryConfig)


def load_foundry_config(path: str | Path) -> FoundryConfig:
    """Load one strict Foundry configuration document."""
    source = Path(path).expanduser().resolve()
    document = load_yaml_document(source, kind="Foundry configuration")
    return _CONFIG_ADAPTER.validate_python(document)


def get_scan(config: FoundryConfig, name: str, *, require_ready: bool = False) -> FoundryScan:
    """Resolve a scan and optionally require execution authorization and readiness."""
    try:
        scan = config.scans[name]
    except KeyError as exc:
        available = ", ".join(sorted(config.scans))
        raise ValueError(f"Unknown Foundry scan '{name}'. Available: {available}") from exc
    if require_ready:
        if not config.allow_provider_managed_workload:
            raise ValueError("allow_provider_managed_workload must be true before execution")
        actual = os.getenv(config.authorization.environment)
        if actual is None or actual.casefold() != config.authorization.expected_value.casefold():
            requirement = f"{config.authorization.environment}={config.authorization.expected_value!r}"
            raise ValueError(f"{requirement} is required after authorization")
        if not scan.target.ready:
            raise ValueError(f"Foundry target '{name}' is not ready: {scan.target.status_reason}")
    return scan
