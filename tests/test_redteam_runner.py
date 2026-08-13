from __future__ import annotations

from pathlib import Path
from typing import Any

from genai_red_teaming_accelerator.foundry import FoundryRunResult
from genai_red_teaming_accelerator.redteam import PyRITRunResult, RedTeamRunner
from genai_red_teaming_accelerator.redteam_config import load_redteam_config

ROOT = Path(__file__).parents[1]


class FakePyRITRunner:
    def __init__(self) -> None:
        self.call: dict[str, Any] | None = None

    def run(self, **kwargs: Any) -> PyRITRunResult:
        self.call = kwargs
        return PyRITRunResult(
            scenario_result_id="scenario-123",
            status="COMPLETED",
            attacks=3,
            successes=1,
            failures=2,
            errors=0,
            co_pyrit_url="http://127.0.0.1:8014/history",
            labels={"engine": "pyrit"},
        )


class FakeFoundryRunner:
    def __init__(self) -> None:
        self.call: dict[str, Any] | None = None

    def run(self, **kwargs: Any) -> FoundryRunResult:
        self.call = kwargs
        return FoundryRunResult(
            eval_id="eval-123",
            eval_name="eval",
            run_id="run-456",
            run_name="run",
            status="queued",
            scan_name=kwargs["scan_name"],
            target_type="model",
            target_provider="openai",
            target_publisher="OpenAI",
            target_deployment="grta-openai",
            target_model="gpt-5-mini",
            target_model_version="2025-08-07",
            project_endpoint="https://project.example",
            report_url=None,
            labels=kwargs["labels"],
            deployment=None,
            created_at="2026-08-12T00:00:00+00:00",
            completed_at=None,
            output_items=[],
            run={},
        )


def test_selector_delegates_pyrit_without_owning_attack_execution() -> None:
    config = load_redteam_config(ROOT / "configs/redteam.yaml")
    pyrit = FakePyRITRunner()
    runner = RedTeamRunner(pyrit_runner=pyrit, foundry_runner=FakeFoundryRunner())  # type: ignore[arg-type]

    result = runner.run(config=config, test_name="custom-pyrit")

    assert result.engine == "pyrit"
    assert result.result.scenario_result_id == "scenario-123"
    assert pyrit.call is not None
    assert pyrit.call["test"].setup.type == "custom"


def test_selector_overrides_foundry_workload_from_shared_profile() -> None:
    config = load_redteam_config(ROOT / "configs/redteam.yaml")
    foundry = FakeFoundryRunner()
    runner = RedTeamRunner(pyrit_runner=FakePyRITRunner(), foundry_runner=foundry)  # type: ignore[arg-type]

    result = runner.run(config=config, test_name="baseline-foundry")

    assert result.engine == "foundry"
    assert foundry.call is not None
    scan = foundry.call["config"].scans["openai"]
    assert scan.risk_categories == ["violence", "hate_unfairness", "sexual", "self_harm"]
    assert scan.attack_strategies == ["Base64", "Crescendo"]
    assert scan.num_turns == 3
    assert foundry.call["labels"]["use_case"] == "baseline-safety"
    assert foundry.call["labels"]["target"] == "openai"
    assert foundry.call["output_directory"] == (ROOT / "artifacts/foundry").resolve()
    assert foundry.call["wait"] is True
