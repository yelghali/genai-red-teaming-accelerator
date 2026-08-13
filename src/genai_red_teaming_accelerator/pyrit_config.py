"""Configuration used by the native PyRIT target initializer."""

from __future__ import annotations

import re
from ipaddress import ip_address
from pathlib import Path
from typing import Annotated, Literal

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, TypeAdapter, field_validator, model_validator

from genai_red_teaming_accelerator.config_io import load_yaml_document

ProfileName = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_-]{1,62}$")]
EnvironmentName = Annotated[str, Field(pattern=r"^[A-Z_][A-Z0-9_]*$")]
RequestRate = Annotated[int, Field(gt=0)]

_SENSITIVE_HEADERS = {
    "authorization",
    "proxy-authorization",
    "x-api-key",
    "api-key",
    "cookie",
    "set-cookie",
}
_RESERVED_HEADERS = {
    "connection",
    "content-length",
    "host",
    "proxy-connection",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
}
_HEADER_NAME = r"^[!#$%&'*+\-.^_`|~0-9A-Za-z]+$"


class StrictModel(BaseModel):
    """Reject unknown fields so configuration mistakes fail early."""

    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)


class SecretRef(StrictModel):
    """Reference a secret through an environment variable."""

    source: Literal["env"] = "env"
    name: EnvironmentName
    prefix: str = Field(default="", max_length=128)

    @field_validator("prefix")
    @classmethod
    def validate_prefix(cls, value: str) -> str:
        if "\r" in value or "\n" in value:
            raise ValueError("secret prefixes cannot contain line breaks")
        return value


HeaderValue = str | SecretRef


def _is_loopback_host(host: str) -> bool:
    normalized = host.removeprefix("[").removesuffix("]").rstrip(".").casefold()
    if normalized == "localhost" or normalized.endswith(".localhost"):
        return True
    try:
        return ip_address(normalized).is_loopback
    except ValueError:
        return False


def _validate_target_url(value: AnyHttpUrl) -> AnyHttpUrl:
    if value.username is not None or value.password is not None:
        raise ValueError("target URLs must not embed credentials; use an environment-backed secret")
    if value.scheme != "https" and not _is_loopback_host(value.host):
        raise ValueError("target URLs must use HTTPS unless the host is loopback")
    return value


def _response_path_segments(path: str) -> list[str]:
    raw = path.removeprefix("$")
    if raw.startswith("."):
        raw = raw[1:]
    if not raw or raw.endswith(".") or ".." in raw:
        raise ValueError("response_json_path must identify a response field")
    normalized = re.sub(r"\[(\d+)\]", r".\1", raw)
    if "[" in normalized or "]" in normalized:
        raise ValueError(f"Unsupported response_json_path syntax: {path!r}")
    segments = normalized.split(".")
    if any(not segment for segment in segments):
        raise ValueError(f"Unsupported response_json_path syntax: {path!r}")
    return segments


def _validate_headers(headers: dict[str, HeaderValue]) -> None:
    normalized_names: set[str] = set()
    for name, value in headers.items():
        normalized_name = name.casefold()
        if not re.fullmatch(_HEADER_NAME, name):
            raise ValueError(f"Invalid HTTP header name: {name!r}")
        if normalized_name in normalized_names:
            raise ValueError(f"Duplicate HTTP header name ignoring case: {name!r}")
        normalized_names.add(normalized_name)
        if normalized_name in _RESERVED_HEADERS:
            raise ValueError(f"HTTP header '{name}' is managed by the target adapter and cannot be configured")
        if isinstance(value, str) and ("\r" in value or "\n" in value):
            raise ValueError(f"Header '{name}' cannot contain line breaks")
        sensitive = (
            normalized_name in _SENSITIVE_HEADERS
            or normalized_name.endswith("-key")
            or "token" in normalized_name
            or "secret" in normalized_name
        )
        if sensitive and isinstance(value, str):
            raise ValueError(f"Sensitive header '{name}' must use an environment reference")


class OpenAITarget(StrictModel):
    """Any OpenAI-compatible Chat Completions or Responses endpoint."""

    type: Literal["openai"]
    provider: str = Field(min_length=1)
    endpoint: AnyHttpUrl
    model: str = Field(min_length=1)
    api: Literal["chat", "responses"] = "chat"
    auth: Literal["api_key", "identity"] = "api_key"
    api_key: SecretRef | None = None
    token_scope: str | None = Field(default=None, min_length=1)
    headers: dict[str, HeaderValue] = Field(default_factory=dict)
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_tokens: int | None = Field(default=None, gt=0)
    max_requests_per_minute: RequestRate

    @field_validator("endpoint")
    @classmethod
    def validate_endpoint(cls, value: AnyHttpUrl) -> AnyHttpUrl:
        return _validate_target_url(value)

    @model_validator(mode="after")
    def validate_auth(self) -> OpenAITarget:
        if self.auth == "api_key" and self.api_key is None:
            raise ValueError("api_key auth requires an environment-backed api_key")
        if self.auth == "identity" and self.api_key is not None:
            raise ValueError("identity auth must not include api_key")
        if self.auth == "identity" and self.token_scope is None:
            raise ValueError("identity auth requires token_scope")
        if self.auth == "api_key" and self.token_scope is not None:
            raise ValueError("api_key auth must not include token_scope")
        _validate_headers(self.headers)
        return self


class HttpTarget(StrictModel):
    """A templated request for PyRIT's native HTTPTarget."""

    type: Literal["http"]
    url: AnyHttpUrl
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH"] = "POST"
    headers: dict[str, HeaderValue] = Field(default_factory=dict)
    body_template: str = Field(min_length=1)
    prompt_placeholder: str = Field(default="{PROMPT}", min_length=1, max_length=128)
    prompt_encoding: Literal["json_string", "json_value", "url", "raw"] = "json_string"
    response_json_path: str | None = None
    timeout_seconds: float = Field(default=30.0, gt=0, le=300)
    max_requests_per_minute: RequestRate

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: AnyHttpUrl) -> AnyHttpUrl:
        return _validate_target_url(value)

    @model_validator(mode="after")
    def validate_request(self) -> HttpTarget:
        if self.body_template.count(self.prompt_placeholder) != 1:
            raise ValueError("prompt_placeholder must occur exactly once in body_template")
        _validate_headers(self.headers)
        if self.response_json_path is not None:
            _response_path_segments(self.response_json_path)
        return self


class PlaywrightSelectors(StrictModel):
    prompt_input: str = Field(min_length=1)
    submit: str = Field(min_length=1)
    response: str = Field(min_length=1)
    file_input: str | None = None
    ready: str | None = None


class PlaywrightFillAction(StrictModel):
    """Fill one authentication field from an environment-backed value."""

    action: Literal["fill"]
    selector: str = Field(min_length=1)
    value: SecretRef


class PlaywrightClickAction(StrictModel):
    """Click one authentication control."""

    action: Literal["click"]
    selector: str = Field(min_length=1)


class PlaywrightPressAction(StrictModel):
    """Press a key while focused on an authentication control."""

    action: Literal["press"]
    selector: str = Field(min_length=1)
    key: str = Field(min_length=1, max_length=64)


class PlaywrightWaitAction(StrictModel):
    """Wait for an authentication or post-login element state."""

    action: Literal["wait_for"]
    selector: str = Field(min_length=1)
    state: Literal["attached", "detached", "visible", "hidden"] = "visible"


PlaywrightAuthAction = Annotated[
    PlaywrightFillAction | PlaywrightClickAction | PlaywrightPressAction | PlaywrightWaitAction,
    Field(discriminator="action"),
]


class PlaywrightTarget(StrictModel):
    """A declarative browser chat target for PyRIT's native PlaywrightTarget."""

    type: Literal["playwright"]
    url: AnyHttpUrl
    selectors: PlaywrightSelectors
    browser: Literal["chromium", "firefox", "webkit"] = "chromium"
    headless: bool = True
    timeout_ms: int = Field(default=30_000, gt=0, le=300_000)
    auth_steps: list[PlaywrightAuthAction] = Field(default_factory=list, max_length=32)
    max_requests_per_minute: RequestRate

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: AnyHttpUrl) -> AnyHttpUrl:
        return _validate_target_url(value)


TargetSpec = Annotated[OpenAITarget | HttpTarget | PlaywrightTarget, Field(discriminator="type")]


class TargetDefinition(StrictModel):
    name: ProfileName
    tags: list[str] = Field(default_factory=list)
    target: TargetSpec


class ObjectiveDataset(StrictModel):
    name: ProfileName
    objectives: list[Annotated[str, Field(min_length=1, max_length=10_000)]] = Field(min_length=1, max_length=100)


class Authorization(StrictModel):
    environment: EnvironmentName = "REDTEAM_SCOPE_APPROVED"
    expected_value: str = "true"


class PyRITTargetCatalog(StrictModel):
    """Targets and small custom datasets loaded by native PyRIT."""

    schema_version: Literal[1] = 1
    authorization: Authorization = Field(default_factory=Authorization)
    scorer_target: ProfileName
    targets: list[TargetDefinition] = Field(min_length=1)
    datasets: list[ObjectiveDataset] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_references(self) -> PyRITTargetCatalog:
        target_names = [target.name for target in self.targets]
        if len(target_names) != len(set(target_names)):
            raise ValueError("Target names must be unique")
        if self.scorer_target not in target_names:
            raise ValueError("scorer_target must reference a configured target")
        scorer = next(target for target in self.targets if target.name == self.scorer_target)
        if not isinstance(scorer.target, OpenAITarget):
            raise ValueError("scorer_target must be an OpenAI-compatible model target")
        dataset_names = [dataset.name for dataset in self.datasets]
        if len(dataset_names) != len(set(dataset_names)):
            raise ValueError("Dataset names must be unique")
        return self


_CATALOG_ADAPTER = TypeAdapter(PyRITTargetCatalog)


def load_pyrit_catalog(path: str | Path) -> PyRITTargetCatalog:
    """Load and strictly validate one native PyRIT target catalog."""
    source = Path(path).expanduser().resolve()
    document = load_yaml_document(source, kind="PyRIT target catalog")
    return _CATALOG_ADAPTER.validate_python(document)
