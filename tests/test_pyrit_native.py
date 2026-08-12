from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from genai_red_teaming_accelerator.pyrit_config import (
    HttpTarget,
    OpenAITarget,
    PlaywrightTarget,
    PyRITTargetCatalog,
    SecretRef,
    TargetDefinition,
    load_pyrit_catalog,
)
from genai_red_teaming_accelerator.pyrit_targets import (
    _create_http_target,
    _create_openai_target,
    _encode_http_prompt,
    _resolve_headers,
    _response_callback,
    _run_playwright_auth_steps,
)

ROOT = Path(__file__).parents[1]


def test_checked_in_native_target_catalog_is_generic() -> None:
    catalog = load_pyrit_catalog(ROOT / "configs/pyrit/targets.yaml")

    assert {target.name for target in catalog.targets} == {"foundry-openai", "foundry-mistral"}
    assert catalog.scorer_target == "foundry-mistral"
    assert catalog.datasets[0].name == "foundry-canary"
    assert all(isinstance(target.target, OpenAITarget) for target in catalog.targets)


def test_provider_and_model_names_are_configuration_data() -> None:
    catalog = PyRITTargetCatalog(
        scorer_target="customer-model",
        targets=[
            TargetDefinition(
                name="customer-model",
                target=OpenAITarget(
                    type="openai",
                    provider="any-provider",
                    endpoint="https://model.example/v1/",
                    model="any-deployment",
                    auth="api_key",
                    api_key=SecretRef(name="CUSTOMER_MODEL_KEY"),
                ),
            )
        ],
    )

    assert catalog.targets[0].target.provider == "any-provider"
    assert catalog.targets[0].target.model == "any-deployment"


def test_sensitive_http_header_requires_environment_reference() -> None:
    with pytest.raises(ValueError, match="environment reference"):
        HttpTarget(
            type="http",
            url="https://api.example/chat",
            headers={"Authorization": "Bearer literal"},
            body_template='{"message":"{PROMPT}"}',
        )


def test_custom_key_header_requires_environment_reference() -> None:
    with pytest.raises(ValueError, match="environment reference"):
        HttpTarget(
            type="http",
            url="https://api.example/chat",
            headers={"X-Tenant-Key": "literal"},
            body_template='{"message":"{PROMPT}"}',
        )


def test_invalid_json_response_path_fails_during_configuration_validation() -> None:
    with pytest.raises(ValueError, match="response_json_path"):
        HttpTarget(
            type="http",
            url="https://api.example/chat",
            body_template='{"message":"{PROMPT}"}',
            response_json_path="choices[message.content",
        )


def test_environment_header_supports_bearer_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TARGET_API_TOKEN", "test-token")

    headers = _resolve_headers({"Authorization": SecretRef(name="TARGET_API_TOKEN", prefix="Bearer ")})

    assert headers == {"Authorization": "Bearer test-token"}


def test_environment_header_rejects_line_break_injection(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TARGET_API_TOKEN", "test-token\r\nX-Injected: value")

    with pytest.raises(ValueError, match="line breaks"):
        _resolve_headers({"Authorization": SecretRef(name="TARGET_API_TOKEN", prefix="Bearer ")})


def test_json_string_prompt_encoding_preserves_request_structure() -> None:
    prompt = 'quote: "hello"\\path\nnext line'
    encoded = _encode_http_prompt(prompt, "json_string")

    assert json.loads(f'{{"message":"{encoded}"}}') == {"message": prompt}


@pytest.mark.asyncio
async def test_http_target_uses_timeout_and_bracketed_json_response_path(monkeypatch: pytest.MonkeyPatch) -> None:
    from pyrit.setup import initialize_pyrit_async

    await initialize_pyrit_async("SQLite", load_defaults=False, silent=True)
    monkeypatch.setenv("TARGET_API_TOKEN", "test-token")
    spec = HttpTarget(
        type="http",
        url="https://api.example/chat",
        headers={"Authorization": SecretRef(name="TARGET_API_TOKEN", prefix="Bearer ")},
        body_template='{"message":"{PROMPT}"}',
        response_json_path="choices[0].message.content",
        timeout_seconds=12,
    )

    target = _create_http_target(spec)
    callback = _response_callback(spec.response_json_path)

    assert "Authorization: Bearer test-token" in target.http_request
    assert target.httpx_client_kwargs["timeout"] == 12
    assert callback is not None
    response = type(
        "Response",
        (),
        {"json": staticmethod(lambda: {"choices": [{"message": {"content": "answer"}}]})},
    )()
    assert callback(response=response) == "answer"


@pytest.mark.asyncio
async def test_http_target_treats_custom_prompt_placeholder_as_literal_text() -> None:
    from pyrit.setup import initialize_pyrit_async

    await initialize_pyrit_async("SQLite", load_defaults=False, silent=True)
    spec = HttpTarget(
        type="http",
        url="https://api.example/chat",
        body_template='{"message":${PROMPT}}',
        prompt_placeholder="${PROMPT}",
        prompt_encoding="json_value",
    )
    target = _create_http_target(spec)
    request = type("Request", (), {"converted_value": 'hello "world"'})()

    rendered = target._inject_prompt_into_request(request)

    assert json.loads(rendered.split("\r\n\r\n", maxsplit=1)[1]) == {"message": 'hello "world"'}


@pytest.mark.asyncio
async def test_playwright_authentication_steps_are_ordered_and_environment_backed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TARGET_UI_USERNAME", "operator@example.com")
    monkeypatch.setenv("TARGET_UI_PASSWORD", "test-password")
    events: list[tuple[str, ...]] = []

    class FakeLocator:
        def __init__(self, selector: str) -> None:
            self.selector = selector

        async def fill(self, value: str) -> None:
            events.append(("fill", self.selector, value))

        async def click(self) -> None:
            events.append(("click", self.selector))

        async def press(self, key: str) -> None:
            events.append(("press", self.selector, key))

        async def wait_for(self, *, state: str) -> None:
            events.append(("wait_for", self.selector, state))

    class FakePage:
        def locator(self, selector: str) -> FakeLocator:
            return FakeLocator(selector)

    target = PlaywrightTarget.model_validate(
        {
            "type": "playwright",
            "url": "https://chat.example/",
            "selectors": {
                "prompt_input": "#prompt",
                "submit": "#send",
                "response": ".response",
            },
            "auth_steps": [
                {
                    "action": "fill",
                    "selector": "#username",
                    "value": {"source": "env", "name": "TARGET_UI_USERNAME"},
                },
                {
                    "action": "fill",
                    "selector": "#password",
                    "value": {"source": "env", "name": "TARGET_UI_PASSWORD"},
                },
                {"action": "press", "selector": "#password", "key": "Enter"},
                {"action": "click", "selector": "#continue"},
                {"action": "wait_for", "selector": "#prompt", "state": "visible"},
            ],
        }
    )

    await _run_playwright_auth_steps(FakePage(), target.auth_steps)

    assert events == [
        ("fill", "#username", "operator@example.com"),
        ("fill", "#password", "test-password"),
        ("press", "#password", "Enter"),
        ("click", "#continue"),
        ("wait_for", "#prompt", "visible"),
    ]


@pytest.mark.parametrize(
    ("catalog_name", "target_name", "target_type"),
    [
        ("api-targets.yaml", "application-api", HttpTarget),
        ("ui-targets.yaml", "application-ui", PlaywrightTarget),
    ],
)
def test_checked_in_customer_target_examples_are_valid(
    catalog_name: str,
    target_name: str,
    target_type: type[HttpTarget] | type[PlaywrightTarget],
) -> None:
    catalog = load_pyrit_catalog(ROOT / "configs/examples" / catalog_name)

    definition = next(item for item in catalog.targets if item.name == target_name)
    assert isinstance(definition.target, target_type)
    assert isinstance(catalog.targets[0].target, OpenAITarget)


def test_identity_target_uses_configured_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    class FakeCredential:
        def __init__(self, **kwargs: Any) -> None:
            captured["credential_kwargs"] = kwargs

    class FakeTarget:
        def __init__(self, **kwargs: Any) -> None:
            captured["target_kwargs"] = kwargs

    token_provider = lambda: "test-token"  # noqa: E731

    def fake_token_provider(credential: Any, scope: str) -> Any:
        captured["credential"] = credential
        captured["scope"] = scope
        return token_provider

    monkeypatch.setattr("azure.identity.DefaultAzureCredential", FakeCredential)
    monkeypatch.setattr("azure.identity.get_bearer_token_provider", fake_token_provider)
    monkeypatch.setattr("pyrit.prompt_target.OpenAIChatTarget", FakeTarget)

    target = _create_openai_target(
        OpenAITarget(
            type="openai",
            provider="customer-provider",
            endpoint="https://example.services.ai.azure.com/api/projects/example/openai/v1/",
            model="deployment-name",
            auth="identity",
            token_scope="https://ai.azure.com/.default",
        )
    )

    assert captured["credential_kwargs"] == {"process_timeout": 60}
    assert captured["scope"] == "https://ai.azure.com/.default"
    assert captured["target_kwargs"]["api_key"] is token_provider
    assert target._accelerator_resources == (captured["credential"],)


def test_identity_target_ignores_empty_azure_identity_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    for variable in ("AZURE_CLIENT_ID", "AZURE_TENANT_ID", "AZURE_CLIENT_SECRET"):
        monkeypatch.setenv(variable, "")

    class FakeCredential:
        def __init__(self, **kwargs: Any) -> None:
            assert kwargs == {"process_timeout": 60}
            assert "AZURE_CLIENT_ID" not in __import__("os").environ

    class FakeTarget:
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs

    monkeypatch.setattr("azure.identity.DefaultAzureCredential", FakeCredential)

    def fake_token_provider(credential: Any, scope: str):
        assert isinstance(credential, FakeCredential)
        assert scope == "https://ai.azure.com/.default"
        return lambda: "token"

    monkeypatch.setattr("azure.identity.get_bearer_token_provider", fake_token_provider)
    monkeypatch.setattr("pyrit.prompt_target.OpenAIChatTarget", FakeTarget)

    _create_openai_target(
        OpenAITarget(
            type="openai",
            provider="foundry",
            endpoint="https://example.services.ai.azure.com/api/projects/example/openai/v1/",
            model="deployment",
            auth="identity",
            token_scope="https://ai.azure.com/.default",
        )
    )


@pytest.mark.asyncio
async def test_native_pyrit_configuration_registers_real_foundry_targets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pyrit.registry import TargetRegistry
    from pyrit.setup.configuration_loader import ConfigurationLoader

    monkeypatch.chdir(ROOT)
    monkeypatch.setenv("REDTEAM_SCOPE_APPROVED", "true")
    loader = ConfigurationLoader.from_yaml_file(ROOT / "configs/pyrit/pyrit-config.yaml")

    await loader.initialize_pyrit_async()

    registry = TargetRegistry.get_registry_singleton()
    assert registry.instances.get("foundry-openai") is not None
    assert registry.instances.get("foundry-mistral") is not None
    assert registry.instances.get("objective_scorer_chat") is not None


@pytest.mark.asyncio
async def test_native_initializer_uses_rta_selected_api_catalog(monkeypatch: pytest.MonkeyPatch) -> None:
    from pyrit.registry import TargetRegistry
    from pyrit.setup.configuration_loader import ConfigurationLoader

    monkeypatch.chdir(ROOT)
    monkeypatch.setenv("REDTEAM_SCOPE_APPROVED", "true")
    monkeypatch.setenv("RTA_PYRIT_TARGETS", str(ROOT / "configs/examples/api-targets.yaml"))
    monkeypatch.setenv("SCORER_API_KEY", "test-scorer-key")
    monkeypatch.setenv("TARGET_API_TOKEN", "test-target-token")
    monkeypatch.setenv("TARGET_TENANT_KEY", "test-tenant-key")
    loader = ConfigurationLoader.from_yaml_file(ROOT / "configs/pyrit/pyrit-config.yaml")

    await loader.initialize_pyrit_async()

    registry = TargetRegistry.get_registry_singleton()
    assert registry.instances.get("application-api") is not None
    assert registry.instances.get("scorer-model") is not None
