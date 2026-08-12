"""Microsoft Foundry-managed red-team evaluation client."""

from __future__ import annotations

import json
import re
import time
from collections.abc import Callable
from contextlib import AbstractContextManager, contextmanager
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from genai_red_teaming_accelerator.compatibility import require_supported_foundry
from genai_red_teaming_accelerator.foundry_config import (
    FoundryAgentTarget,
    FoundryConfig,
    FoundryModelTarget,
    FoundryScan,
    get_scan,
)

_EVALUATORS: dict[str, tuple[str, str, str | None]] = {
    "violence": ("Violence Content", "builtin.violence", "3"),
    "self_harm": ("Self-Harm Related Content", "builtin.self_harm", "3"),
    "sexual": ("Sexual Content", "builtin.sexual", "3"),
    "hate_unfairness": ("Hate and Unfairness", "builtin.hate_unfairness", "3"),
    "protected_material": ("Protected Materials", "builtin.protected_material", None),
    "ungrounded_attributes": ("Ungrounded Attributes", "builtin.ungrounded_attributes", "3"),
    "code_vulnerability": ("Code Vulnerability", "builtin.code_vulnerability", "3"),
    "prohibited_actions": ("Prohibited Actions", "builtin.prohibited_actions", "1"),
    "task_adherence": ("Task Adherence", "builtin.task_adherence", "1"),
    "sensitive_data_leakage": ("Sensitive Data Leakage", "builtin.sensitive_data_leakage", "1"),
}
_TERMINAL_STATUSES = {"completed", "failed", "canceled", "cancelled"}


@dataclass(slots=True)
class FoundryRunResult:
    """Identifiers and evidence for one portal-visible Foundry run."""

    eval_id: str
    eval_name: str
    run_id: str
    run_name: str
    status: str
    scan_name: str
    target_type: str
    target_provider: str | None
    target_publisher: str | None
    target_deployment: str | None
    target_model: str | None
    target_model_version: str | None
    project_endpoint: str
    report_url: str | None
    labels: dict[str, str]
    deployment: dict[str, Any] | None
    created_at: str
    completed_at: str | None
    output_items: list[Any]
    run: Any
    result_path: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _primitive(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _primitive(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_primitive(item) for item in value]
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        try:
            return _primitive(model_dump(warnings=False))
        except TypeError:
            return _primitive(model_dump())
    for method_name in ("as_dict", "to_dict"):
        method = getattr(value, method_name, None)
        if callable(method):
            return _primitive(method())
    if hasattr(value, "value") and not callable(value.value):
        return _primitive(value.value)
    if hasattr(value, "__dict__"):
        return {key: _primitive(item) for key, item in vars(value).items() if not key.startswith("_")}
    return str(value)


def _status(value: Any) -> str:
    return str(_primitive(value)).lower()


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "-", value).strip("-")[:48] or "scan"


@contextmanager
def _default_client_context(endpoint: str) -> Any:
    from azure.ai.projects import AIProjectClient
    from azure.identity import DefaultAzureCredential

    with (
        DefaultAzureCredential(process_timeout=60) as credential,
        AIProjectClient(endpoint=endpoint, credential=credential, allow_preview=True) as project_client,
        project_client.get_openai_client() as client,
    ):
        yield client


@contextmanager
def _default_project_client_context(endpoint: str) -> Any:
    from azure.ai.projects import AIProjectClient
    from azure.identity import DefaultAzureCredential

    with (
        DefaultAzureCredential(process_timeout=60) as credential,
        AIProjectClient(endpoint=endpoint, credential=credential) as project_client,
    ):
        yield project_client


class FoundryRunner:
    """Create and monitor evaluations that are visible in the Foundry portal."""

    def __init__(
        self,
        *,
        client_context_factory: Callable[[str], AbstractContextManager[Any]] | None = None,
        project_client_context_factory: Callable[[str], AbstractContextManager[Any]] | None = None,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self._client_context_factory = client_context_factory or _default_client_context
        self._project_client_context_factory = project_client_context_factory or _default_project_client_context
        self._sleep = sleep
        self._monotonic = monotonic

    @staticmethod
    def _testing_criteria(scan: FoundryScan) -> list[dict[str, Any]]:
        criteria: list[dict[str, Any]] = []
        for risk in scan.risk_categories:
            label, evaluator, version = _EVALUATORS[risk]
            criterion: dict[str, Any] = {
                "type": "azure_ai_evaluator",
                "name": label,
                "evaluator_name": evaluator,
            }
            if version:
                criterion["evaluator_version"] = version
            if risk == "task_adherence":
                criterion["initialization_parameters"] = {"deployment_name": scan.evaluator_deployment}
            criteria.append(criterion)
        return criteria

    @staticmethod
    def _target_payload(target: FoundryModelTarget | FoundryAgentTarget) -> dict[str, Any]:
        if isinstance(target, FoundryModelTarget):
            from azure.ai.projects.models import AzureAIModelTarget

            deployment = target.deployment
            if target.connection_name:
                deployment = f"{target.connection_name}/{deployment}"
            return AzureAIModelTarget(model=deployment).as_dict()

        from azure.ai.projects.models import AzureAIAgentTarget

        return AzureAIAgentTarget(name=target.name, version=target.version).as_dict()

    @staticmethod
    def _item_generation(scan: FoundryScan) -> dict[str, Any]:
        params: dict[str, Any] = {
            "type": "red_team",
            "num_turns": scan.num_turns,
        }
        if scan.attack_strategies:
            params["attack_strategies"] = scan.attack_strategies
        if isinstance(scan.target, FoundryAgentTarget):
            params["type"] = "red_team_taxonomy"
            params["source"] = {"type": "file_id", "id": scan.reviewed_taxonomy_id}
        return params

    def _verify_model_deployment(self, *, endpoint: str, target: FoundryModelTarget) -> dict[str, Any]:
        if not target.ready:
            raise ValueError(f"Foundry deployment '{target.deployment}' is not ready: {target.status_reason}")
        with self._project_client_context_factory(endpoint) as project_client:
            deployment = _primitive(project_client.deployments.get(target.deployment))
        actual = {
            "name": deployment.get("name"),
            "provider": deployment.get("modelPublisher", deployment.get("model_publisher")),
            "model": deployment.get("modelName", deployment.get("model_name")),
            "version": deployment.get("modelVersion", deployment.get("model_version")),
            "sku": deployment.get("sku"),
        }
        expected = {
            "name": target.deployment,
            "provider": target.publisher,
            "model": target.model,
            "version": target.version,
        }
        mismatches = [key for key, value in expected.items() if str(actual.get(key)) != str(value)]
        if mismatches:
            details = ", ".join(f"{key}={actual.get(key)!r} (expected {expected[key]!r})" for key in mismatches)
            raise ValueError(f"Foundry deployment metadata does not match configuration: {details}")
        return actual

    def _wait_for_run(
        self,
        client: Any,
        *,
        eval_id: str,
        run: Any,
        timeout_minutes: int,
        poll_interval_seconds: int,
    ) -> tuple[Any, str]:
        deadline = self._monotonic() + timeout_minutes * 60
        current = run
        status = _status(current.status)
        while status not in _TERMINAL_STATUSES:
            if self._monotonic() >= deadline:
                return current, "timeout"
            self._sleep(poll_interval_seconds)
            current = client.evals.runs.retrieve(run_id=run.id, eval_id=eval_id)
            status = _status(current.status)
        return current, status

    @staticmethod
    def _persist_result(result: FoundryRunResult, result_path: Path) -> FoundryRunResult:
        result.result_path = str(result_path)
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(json.dumps(result.as_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return result

    @staticmethod
    def _result_metadata(scan: FoundryScan) -> dict[str, str | None]:
        target = scan.target
        if isinstance(target, FoundryModelTarget):
            return {
                "target_provider": target.provider,
                "target_publisher": target.publisher,
                "target_deployment": target.deployment,
                "target_model": target.model,
                "target_model_version": target.version,
            }
        return {
            "target_provider": None,
            "target_publisher": None,
            "target_deployment": None,
            "target_model": None,
            "target_model_version": None,
        }

    def run(
        self,
        *,
        config: FoundryConfig,
        scan_name: str,
        output_directory: str | Path | None = None,
        wait: bool = True,
        labels: dict[str, str] | None = None,
    ) -> FoundryRunResult:
        """Create one real Foundry evaluation and persist its service IDs."""
        require_supported_foundry()
        scan = get_scan(config, scan_name, require_ready=True)
        endpoint = str(config.project_endpoint)
        now = datetime.now(UTC)
        suffix = now.strftime("%Y%m%d-%H%M%S")
        eval_name = f"RTA-{_safe_name(scan_name)}-{suffix}"
        run_name = f"scan-{_safe_name(scan_name)}-{suffix}"
        deployment = None
        if isinstance(scan.target, FoundryModelTarget):
            deployment = self._verify_model_deployment(endpoint=endpoint, target=scan.target)

        with self._client_context_factory(endpoint) as client:
            red_team = client.evals.create(
                name=eval_name,
                data_source_config={"type": "azure_ai_source", "scenario": "red_team"},
                testing_criteria=self._testing_criteria(scan),
            )
            run_kwargs: dict[str, Any] = {
                "eval_id": red_team.id,
                "name": run_name,
                "data_source": {
                    "type": "azure_ai_red_team",
                    "item_generation_params": self._item_generation(scan),
                    "target": self._target_payload(scan.target),
                },
            }
            if labels:
                run_kwargs["metadata"] = labels
            run = client.evals.runs.create(
                **run_kwargs,
            )
            status = _status(run.status)
            if wait:
                run, status = self._wait_for_run(
                    client,
                    eval_id=red_team.id,
                    run=run,
                    timeout_minutes=config.timeout_minutes,
                    poll_interval_seconds=config.poll_interval_seconds,
                )
            output_items: list[Any] = []
            if status == "completed":
                output_items = [
                    _primitive(item) for item in client.evals.runs.output_items.list(run_id=run.id, eval_id=red_team.id)
                ]

        run_primitive = _primitive(run)
        result = FoundryRunResult(
            eval_id=str(red_team.id),
            eval_name=eval_name,
            run_id=str(run.id),
            run_name=run_name,
            status=status,
            scan_name=scan_name,
            target_type=scan.target.type,
            project_endpoint=endpoint,
            report_url=run_primitive.get("report_url") if isinstance(run_primitive, dict) else None,
            labels=dict(labels or {}),
            deployment=deployment,
            created_at=now.isoformat(),
            completed_at=datetime.now(UTC).isoformat() if status in _TERMINAL_STATUSES else None,
            output_items=output_items,
            run=run_primitive,
            **self._result_metadata(scan),
        )
        output = Path(output_directory or config.output_directory).expanduser().resolve()
        return self._persist_result(result, output / f"foundry-run-{_safe_name(result.run_id)}.json")

    def reconcile(
        self,
        *,
        config: FoundryConfig,
        scan_name: str,
        result_path: str | Path,
        wait: bool = False,
    ) -> FoundryRunResult:
        """Refresh an existing run without submitting another evaluation."""
        require_supported_foundry()
        scan = get_scan(config, scan_name, require_ready=True)
        endpoint = str(config.project_endpoint)
        path = Path(result_path).expanduser().resolve()
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Foundry result artifact must contain a JSON object")
        eval_id = str(data.get("eval_id") or "")
        run_id = str(data.get("run_id") or "")
        if not eval_id or not run_id:
            raise ValueError("Foundry result artifact must contain eval_id and run_id")
        if data.get("scan_name") != scan_name or data.get("target_type") != scan.target.type:
            raise ValueError("Foundry result artifact does not match the selected scan")
        expected_metadata = self._result_metadata(scan)
        if any(str(data.get(key)) != str(value) for key, value in expected_metadata.items()):
            raise ValueError("Foundry result artifact target metadata does not match the selected scan")

        deployment = None
        if isinstance(scan.target, FoundryModelTarget):
            deployment = self._verify_model_deployment(endpoint=endpoint, target=scan.target)
        with self._client_context_factory(endpoint) as client:
            run = client.evals.runs.retrieve(run_id=run_id, eval_id=eval_id)
            actual_target = (_primitive(run).get("data_source") or {}).get("target") or {}
            expected_target = self._target_payload(scan.target)
            if any(str(actual_target.get(key)) != str(value) for key, value in expected_target.items()):
                raise ValueError("Foundry run target does not match the selected scan")
            status = _status(run.status)
            if wait:
                run, status = self._wait_for_run(
                    client,
                    eval_id=eval_id,
                    run=run,
                    timeout_minutes=config.timeout_minutes,
                    poll_interval_seconds=config.poll_interval_seconds,
                )
            output_items: list[Any] = []
            if status == "completed":
                output_items = [
                    _primitive(item) for item in client.evals.runs.output_items.list(run_id=run_id, eval_id=eval_id)
                ]

        terminal = status in _TERMINAL_STATUSES
        run_primitive = _primitive(run)
        result = FoundryRunResult(
            eval_id=eval_id,
            eval_name=str(data.get("eval_name") or eval_id),
            run_id=run_id,
            run_name=str(getattr(run, "name", None) or data.get("run_name") or run_id),
            status=status,
            scan_name=scan_name,
            target_type=scan.target.type,
            project_endpoint=endpoint,
            report_url=(run_primitive.get("report_url") if isinstance(run_primitive, dict) else data.get("report_url")),
            labels={str(key): str(value) for key, value in (data.get("labels") or {}).items()},
            deployment=deployment,
            created_at=str(data.get("created_at") or datetime.now(UTC).isoformat()),
            completed_at=(str(data.get("completed_at") or datetime.now(UTC).isoformat()) if terminal else None),
            output_items=output_items,
            run=run_primitive,
            **expected_metadata,
        )
        return self._persist_result(result, path)
