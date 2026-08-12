"""Create target instances registered for native PyRIT commands."""

from __future__ import annotations

import asyncio
import json
import os
import re
from collections.abc import Callable
from contextlib import suppress
from typing import Any
from urllib.parse import quote, urlsplit

from genai_red_teaming_accelerator.compatibility import require_supported_pyrit
from genai_red_teaming_accelerator.pyrit_config import (
    HeaderValue,
    HttpTarget,
    OpenAITarget,
    PlaywrightAuthAction,
    PlaywrightClickAction,
    PlaywrightFillAction,
    PlaywrightPressAction,
    PlaywrightTarget,
    PlaywrightWaitAction,
    SecretRef,
    TargetDefinition,
    _response_path_segments,
)


def _resolve_secret(reference: SecretRef) -> str:
    value = os.getenv(reference.name)
    if not value:
        raise ValueError(f"Required environment variable '{reference.name}' is not set")
    resolved = f"{reference.prefix}{value}"
    if "\r" in resolved or "\n" in resolved:
        raise ValueError(f"Environment variable '{reference.name}' cannot contain line breaks")
    return resolved


def _resolve_headers(values: dict[str, HeaderValue]) -> dict[str, str]:
    return {name: _resolve_secret(value) if isinstance(value, SecretRef) else value for name, value in values.items()}


def _response_callback(path: str | None) -> Callable[..., Any] | None:
    if not path:
        return None
    segments = _response_path_segments(path)

    def extract(*, response: Any) -> str:
        current: Any = response.json()
        for segment in segments:
            current = current[int(segment)] if isinstance(current, list) else current[segment]
        return current if isinstance(current, str) else json.dumps(current)

    extract.__name__ = "configured_json_response_extractor"
    return extract


def _encode_http_prompt(value: str, encoding: str) -> str:
    if encoding == "json_string":
        return json.dumps(value, ensure_ascii=False)[1:-1]
    if encoding == "json_value":
        return json.dumps(value, ensure_ascii=False)
    if encoding == "url":
        return quote(value, safe="")
    return value


def _create_openai_target(spec: OpenAITarget) -> Any:
    from pyrit.prompt_target import OpenAIChatTarget, OpenAIResponseTarget

    credential = None
    if spec.auth == "identity":
        try:
            from azure.identity import DefaultAzureCredential, get_bearer_token_provider
        except ImportError as exc:
            raise RuntimeError("Identity authentication requires the project's 'foundry' extra") from exc
        for variable in ("AZURE_CLIENT_ID", "AZURE_TENANT_ID", "AZURE_CLIENT_SECRET"):
            if os.environ.get(variable) == "":
                os.environ.pop(variable)
        credential = DefaultAzureCredential(process_timeout=60)
        assert spec.token_scope is not None
        api_key: Any = get_bearer_token_provider(credential, spec.token_scope)
    else:
        assert spec.api_key is not None
        api_key = _resolve_secret(spec.api_key)

    common: dict[str, Any] = {
        "endpoint": str(spec.endpoint),
        "model_name": spec.model,
        "api_key": api_key,
        "max_requests_per_minute": spec.max_requests_per_minute,
    }
    headers = _resolve_headers(spec.headers)
    if headers:
        common["headers"] = json.dumps(headers)
    if spec.temperature is not None:
        common["temperature"] = spec.temperature

    if spec.api == "chat":
        if spec.max_tokens is not None:
            common["max_completion_tokens"] = spec.max_tokens
        target = OpenAIChatTarget(**common)
    else:
        if spec.max_tokens is not None:
            common["max_output_tokens"] = spec.max_tokens
        target = OpenAIResponseTarget(**common)

    if credential:
        target._accelerator_resources = (credential,)  # type: ignore[attr-defined]
    return target


def _create_http_target(spec: HttpTarget) -> Any:
    from pyrit.prompt_target import HTTPTarget

    class ConfiguredHTTPTarget(HTTPTarget):
        """Encode the prompt for the configured request context before substitution."""

        def _inject_prompt_into_request(self, request: Any) -> str:
            encoded = _encode_http_prompt(str(request.converted_value), spec.prompt_encoding)
            return re.compile(self.prompt_regex_string).sub(lambda _: encoded, self.http_request)

    parsed = urlsplit(str(spec.url))
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"
    headers = {"Host": parsed.netloc, **_resolve_headers(spec.headers)}
    if not any(name.casefold() == "content-type" for name in headers):
        headers["Content-Type"] = "application/json"
    request = "\r\n".join([f"{spec.method} {path} HTTP/1.1", *[f"{name}: {value}" for name, value in headers.items()]])
    request = f"{request}\r\n\r\n{spec.body_template}"

    return ConfiguredHTTPTarget(
        http_request=request,
        prompt_regex_string=re.escape(spec.prompt_placeholder),
        use_tls=parsed.scheme == "https",
        callback_function=_response_callback(spec.response_json_path),
        max_requests_per_minute=spec.max_requests_per_minute,
        timeout=spec.timeout_seconds,
    )


async def _run_playwright_auth_steps(page: Any, steps: list[PlaywrightAuthAction]) -> None:
    """Execute ordered, secret-safe browser authentication actions."""
    for step in steps:
        locator = page.locator(step.selector)
        if isinstance(step, PlaywrightFillAction):
            await locator.fill(_resolve_secret(step.value))
        elif isinstance(step, PlaywrightClickAction):
            await locator.click()
        elif isinstance(step, PlaywrightPressAction):
            await locator.press(step.key)
        elif isinstance(step, PlaywrightWaitAction):
            await locator.wait_for(state=step.state)
        else:  # pragma: no cover - the discriminated configuration union is exhaustive
            raise TypeError(f"Unsupported Playwright authentication action: {type(step).__name__}")


async def _create_playwright_target(spec: PlaywrightTarget) -> Any:
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise RuntimeError("Playwright support requires the project's 'playwright' extra and browser binaries") from exc

    from pyrit.prompt_target import PlaywrightTarget as NativePlaywrightTarget

    manager = await async_playwright().start()
    browser = None
    context = None
    try:
        browser = await getattr(manager, spec.browser).launch(headless=spec.headless)
        context = await browser.new_context()
        page = await context.new_page()
        page.set_default_timeout(spec.timeout_ms)
        await page.goto(str(spec.url), wait_until="domcontentloaded")
        await _run_playwright_auth_steps(page, spec.auth_steps)
        if spec.selectors.ready:
            await page.locator(spec.selectors.ready).wait_for(state="visible")
    except BaseException:
        if context is not None:
            with suppress(Exception):
                await context.close()
        if browser is not None:
            with suppress(Exception):
                await browser.close()
        with suppress(Exception):
            await manager.stop()
        raise

    interaction_lock = asyncio.Lock()

    async def interact(page: Any, message: Any) -> str:
        # Native PlaywrightTarget owns one page; concurrent scenario workers must not interleave page operations.
        async with interaction_lock:
            text = "\n".join(str(piece.converted_value) for piece in message.get_pieces_by_type(data_type="text"))
            images = [str(piece.converted_value) for piece in message.get_pieces_by_type(data_type="image_path")]
            if text:
                await page.locator(spec.selectors.prompt_input).fill(text)
            if images:
                if not spec.selectors.file_input:
                    raise ValueError("An image was supplied but selectors.file_input is not configured")
                await page.locator(spec.selectors.file_input).set_input_files(images)

            responses = page.locator(spec.selectors.response)
            previous_count = await responses.count()
            previous_text = await responses.last.inner_text() if previous_count else ""
            await page.locator(spec.selectors.submit).click()
            deadline = asyncio.get_running_loop().time() + (spec.timeout_ms / 1000)
            last_text = previous_text
            stable_reads = 0
            while asyncio.get_running_loop().time() < deadline:
                count = await responses.count()
                if count:
                    current = await responses.last.inner_text()
                    if (count > previous_count or current != previous_text) and current.strip():
                        stable_reads = stable_reads + 1 if current == last_text else 0
                        last_text = current
                        if stable_reads >= 2:
                            return current
                await asyncio.sleep(0.25)
            raise TimeoutError(f"No completed response appeared within {spec.timeout_ms} ms")

    target = NativePlaywrightTarget(
        interaction_func=interact,
        page=page,
        max_requests_per_minute=spec.max_requests_per_minute,
    )
    target._accelerator_resources = (manager, browser, context)  # type: ignore[attr-defined]
    return target


async def create_target_async(definition: TargetDefinition) -> Any:
    """Build one configured native PyRIT target without sending a request."""
    require_supported_pyrit()
    spec = definition.target
    if isinstance(spec, OpenAITarget):
        return _create_openai_target(spec)
    if isinstance(spec, HttpTarget):
        return _create_http_target(spec)
    if isinstance(spec, PlaywrightTarget):
        return await _create_playwright_target(spec)
    raise TypeError(f"Unsupported target specification: {type(spec).__name__}")
