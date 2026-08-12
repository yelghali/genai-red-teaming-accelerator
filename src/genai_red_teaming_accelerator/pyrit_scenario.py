"""Thin scenario adapter over PyRIT's native Foundry RedTeamAgent scenario."""

from __future__ import annotations

from inspect import signature
from typing import TYPE_CHECKING, Any, TypeVar

from pyrit.models.parameter import Parameter
from pyrit.scenario.scenarios.foundry.red_team_agent import RedTeamAgent

if TYPE_CHECKING:
    from collections.abc import Sequence

    from pyrit.converter import Converter
    from pyrit.executor.attack.core.attack_strategy import AttackStrategy
    from pyrit.scenario.core.scenario_technique import ScenarioTechnique
    from pyrit.scenario.scenarios.foundry.red_team_agent import FoundryComposite, FoundryTechnique

AttackStrategyT = TypeVar("AttackStrategyT", bound="AttackStrategy[Any, Any]")


class ConfiguredRedTeamAgent(RedTeamAgent):
    """Expose bounded multi-turn depth without reimplementing PyRIT attack loops."""

    @classmethod
    def additional_parameters(cls) -> list[Parameter]:
        return [
            Parameter(
                name="max_turns",
                description="Maximum turns for native PyRIT attacks that expose max_turns.",
                param_type=int,
                default=5,
            )
        ]

    def _resolve_scenario_techniques(
        self,
        *,
        scenario_techniques: Sequence[FoundryTechnique | FoundryComposite] | None,
    ) -> list[ScenarioTechnique]:
        # PyRIT's upstream scenario treats [] like None and expands the EASY default.
        # Preserve [] so a caller can request a true baseline-only run.
        if scenario_techniques == []:
            self._scenario_composites = []
            return []
        return super()._resolve_scenario_techniques(scenario_techniques=scenario_techniques)

    def _get_attack(
        self,
        *,
        attack_type: type[AttackStrategyT],
        converters: list[Converter],
        attack_kwargs: dict[str, Any] | None = None,
    ) -> AttackStrategyT:
        kwargs = dict(attack_kwargs or {})
        if "max_turns" in signature(attack_type.__init__).parameters:
            max_turns = int(self.params.get("max_turns", 5))
            if not 1 <= max_turns <= 50:
                raise ValueError("max_turns must be between 1 and 50")
            kwargs["max_turns"] = max_turns
        return super()._get_attack(attack_type=attack_type, converters=converters, attack_kwargs=kwargs)
