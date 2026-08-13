from __future__ import annotations

from pathlib import Path

import pytest

from genai_red_teaming_accelerator.foundry_config import (
    FoundryConfig,
    FoundryModelTarget,
    FoundryScan,
    get_scan,
    load_foundry_config,
)

ROOT = Path(__file__).parents[1]


def test_checked_in_foundry_config_describes_real_deployments() -> None:
    config = load_foundry_config(ROOT / "configs/foundry.yaml")

    assert set(config.scans) == {"openai", "mistral", "anthropic", "agent"}
    openai = config.scans["openai"].target
    mistral = config.scans["mistral"].target
    assert isinstance(openai, FoundryModelTarget)
    assert (openai.publisher, openai.deployment, openai.model, openai.version) == (
        "OpenAI",
        "grta-openai",
        "gpt-5-mini",
        "2025-08-07",
    )
    assert isinstance(mistral, FoundryModelTarget)
    assert (mistral.publisher, mistral.deployment) == ("Mistral AI", "grta-mistral")
    assert not config.scans["anthropic"].target.ready
    assert not config.scans["agent"].target.ready


def test_foundry_provider_names_are_not_an_enum() -> None:
    config = FoundryConfig(
        project_endpoint="https://project.services.ai.azure.com/api/projects/example",
        scans={
            "customer-model": FoundryScan(
                target=FoundryModelTarget(
                    type="model",
                    provider="customer-provider",
                    publisher="Customer Publisher",
                    deployment="customer-deployment",
                    model="customer-model",
                    version="7",
                ),
                risk_categories=["violence"],
                attack_strategies=["Base64"],
            )
        },
    )

    target = config.scans["customer-model"].target
    assert isinstance(target, FoundryModelTarget)
    assert target.publisher == "Customer Publisher"


def test_foundry_project_endpoint_rejects_and_redacts_embedded_credentials() -> None:
    with pytest.raises(ValueError, match="must not embed credentials") as captured:
        FoundryConfig(
            project_endpoint="https://alice:topsecret@project.services.ai.azure.com/api/projects/example",
            scans={
                "customer-model": FoundryScan(
                    target=FoundryModelTarget(
                        type="model",
                        provider="customer-provider",
                        publisher="Customer Publisher",
                        deployment="customer-deployment",
                        model="customer-model",
                        version="7",
                    ),
                    risk_categories=["violence"],
                )
            },
        )

    assert "alice" not in str(captured.value)
    assert "topsecret" not in str(captured.value)


def test_foundry_project_endpoint_requires_https() -> None:
    with pytest.raises(ValueError, match="must use HTTPS"):
        FoundryConfig(
            project_endpoint="http://project.services.ai.azure.com/api/projects/example",
            scans={
                "customer-model": FoundryScan(
                    target=FoundryModelTarget(
                        type="model",
                        provider="customer-provider",
                        publisher="Customer Publisher",
                        deployment="customer-deployment",
                        model="customer-model",
                        version="7",
                    ),
                    risk_categories=["violence"],
                )
            },
        )


def test_execution_requires_authorization_and_workload_consent(monkeypatch: pytest.MonkeyPatch) -> None:
    config = load_foundry_config(ROOT / "configs/foundry.yaml")
    monkeypatch.delenv("REDTEAM_SCOPE_APPROVED", raising=False)

    with pytest.raises(ValueError, match="authorization"):
        get_scan(config, "openai", require_ready=True)

    monkeypatch.setenv("REDTEAM_SCOPE_APPROVED", "true")
    config.allow_provider_managed_workload = False
    with pytest.raises(ValueError, match="provider_managed"):
        get_scan(config, "openai", require_ready=True)


def test_blocked_target_fails_before_network_access(monkeypatch: pytest.MonkeyPatch) -> None:
    config = load_foundry_config(ROOT / "configs/foundry.yaml")
    monkeypatch.setenv("REDTEAM_SCOPE_APPROVED", "true")

    with pytest.raises(ValueError, match="not ready"):
        get_scan(config, "anthropic", require_ready=True)
