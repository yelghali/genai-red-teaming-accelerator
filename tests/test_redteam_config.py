from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from genai_red_teaming_accelerator.redteam import build_plan, validate_runtime_references
from genai_red_teaming_accelerator.redteam_config import (
    CustomSetup,
    load_redteam_config,
)
from genai_red_teaming_accelerator.redteam_config import TestDefinition as RedTeamTestDefinition

ROOT = Path(__file__).parents[1]


def test_checked_in_configuration_selects_both_native_engines() -> None:
    config = load_redteam_config(ROOT / "configs/redteam.yaml")
    validate_runtime_references(config)

    assert config.selected_test == "baseline-pyrit"
    assert {test.engine for test in config.tests.values()} == {"pyrit", "foundry"}
    assert config.targets["openai"].pyrit_target == "foundry-openai"
    assert config.targets["openai"].foundry_scan == "openai"


def test_yaml_parse_errors_do_not_echo_source_secrets(tmp_path: Path) -> None:
    source = tmp_path / "malformed.yaml"
    source.write_text('authorization: "Bearer topsecret\n', encoding="utf-8")

    with pytest.raises(
        ValueError,
        match=r"Could not parse red-team configuration .* at line \d+, column \d+",
    ) as captured:
        load_redteam_config(source)

    assert "topsecret" not in str(captured.value)
    assert captured.value.__cause__ is None


def test_duplicate_yaml_keys_fail_without_echoing_source_values(tmp_path: Path) -> None:
    source = tmp_path / "duplicate.yaml"
    source.write_text(
        'selected_test: "first-secret"\nselected_test: "second-secret"\n',
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match=r"Could not parse red-team configuration .* at line 2, column 1",
    ) as captured:
        load_redteam_config(source)

    message = str(captured.value)
    assert "first-secret" not in message
    assert "second-secret" not in message
    assert captured.value.__cause__ is None


def test_offline_plans_show_native_delegation_and_count_semantics() -> None:
    config = load_redteam_config(ROOT / "configs/redteam.yaml")

    pyrit = build_plan(config, test_name="baseline-pyrit")["delegation"]
    foundry = build_plan(config, test_name="baseline-foundry")["delegation"]
    custom = build_plan(config, test_name="custom-pyrit")["delegation"]

    assert pyrit["native_api"] == "pyrit.registry.ScenarioRegistry.create_and_initialize_async"
    assert pyrit["target"] == "foundry-openai"
    assert pyrit["objective_source"]["objectives_per_risk"] == 1
    assert pyrit["max_turns"] == 3
    assert build_plan(config, test_name="baseline-pyrit")["labels"]["target"] == "openai"
    assert foundry["native_api"] == "azure.ai.projects.AIProjectClient.get_openai_client().evals"
    assert foundry["objective_count"] == "service_managed"
    assert foundry["attack_strategies"] == ["Base64", "Crescendo"]
    assert custom["objective_source"]["available"] == 4


def test_foundry_custom_objectives_fail_instead_of_changing_semantics() -> None:
    with pytest.raises(ValidationError, match="do not accept arbitrary custom objective files"):
        RedTeamTestDefinition(
            engine="foundry",
            target="openai",
            setup=CustomSetup(
                type="custom",
                objectives_file="objectives/custom-policy-checks.yaml",
                attack_strategies=["crescendo"],
            ),
        )


@pytest.mark.parametrize(
    ("config_name", "target_name", "catalog_name"),
    [
        ("api-redteam.yaml", "application-api", "api-targets.yaml"),
        ("ui-redteam.yaml", "application-ui", "ui-targets.yaml"),
    ],
)
def test_pyrit_only_customer_examples_select_their_own_catalog(
    config_name: str,
    target_name: str,
    catalog_name: str,
) -> None:
    config = load_redteam_config(ROOT / "configs/examples" / config_name)

    validate_runtime_references(config)
    plan = build_plan(config)

    assert config.runtimes.foundry is None
    assert plan["delegation"]["target"] == target_name
    assert Path(plan["delegation"]["target_catalog"]).name == catalog_name
