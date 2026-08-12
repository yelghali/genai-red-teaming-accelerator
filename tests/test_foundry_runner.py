from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

from genai_red_teaming_accelerator.foundry import FoundryRunner
from genai_red_teaming_accelerator.foundry_config import load_foundry_config

ROOT = Path(__file__).parents[1]


class FakeOutputItems:
    def list(self, *, run_id: str, eval_id: str):
        assert run_id == "run-456"
        assert eval_id == "eval-123"
        return [SimpleNamespace(id="item-1", score=1)]


class FakeRuns:
    def __init__(self) -> None:
        self.output_items = FakeOutputItems()
        self.created: dict | None = None

    def create(self, **kwargs):
        self.created = kwargs
        return SimpleNamespace(id="run-456", name=kwargs["name"], status="queued")

    def retrieve(self, *, run_id: str, eval_id: str):
        assert self.created is not None
        assert eval_id == "eval-123"
        return SimpleNamespace(
            id=run_id,
            name="completed-run",
            status="completed",
            data_source=self.created["data_source"],
        )


class FakeEvals:
    def __init__(self) -> None:
        self.runs = FakeRuns()
        self.created: dict | None = None

    def create(self, **kwargs):
        self.created = kwargs
        return SimpleNamespace(id="eval-123", name=kwargs["name"])


class FakeClient:
    def __init__(self) -> None:
        self.evals = FakeEvals()


class FakeDeployments:
    values = {
        "grta-openai": ("OpenAI", "gpt-5-mini", "2025-08-07"),
        "grta-mistral": ("Mistral AI", "Mistral-Large-3", "1"),
    }

    def get(self, name: str):
        publisher, model, version = self.values[name]
        return SimpleNamespace(
            name=name,
            model_publisher=publisher,
            model_name=model,
            model_version=version,
            sku={"name": "GlobalStandard", "capacity": 1},
        )


class FakeProjectClient:
    def __init__(self) -> None:
        self.deployments = FakeDeployments()


def _runner(client: FakeClient) -> FoundryRunner:
    @contextmanager
    def context(endpoint: str):
        assert endpoint == "https://grtafd08120131.services.ai.azure.com/api/projects/grta-redteam"
        yield client

    @contextmanager
    def project_context(endpoint: str):
        assert endpoint == "https://grtafd08120131.services.ai.azure.com/api/projects/grta-redteam"
        yield FakeProjectClient()

    return FoundryRunner(
        client_context_factory=context,
        project_client_context_factory=project_context,
        sleep=lambda _: None,
    )


@pytest.mark.parametrize("scan_name", ["openai", "mistral"])
def test_model_run_creates_portal_evaluation_and_saves_items(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    scan_name: str,
) -> None:
    monkeypatch.setenv("REDTEAM_SCOPE_APPROVED", "true")
    config = load_foundry_config(ROOT / "configs/foundry.yaml")
    client = FakeClient()

    result = _runner(client).run(config=config, scan_name=scan_name, output_directory=tmp_path)

    target = config.scans[scan_name].target
    assert result.eval_id == "eval-123"
    assert result.run_id == "run-456"
    assert result.eval_name.startswith("RTA-")
    assert result.status == "completed"
    assert result.target_publisher == target.publisher
    assert result.target_deployment == target.deployment
    assert result.output_items == [{"id": "item-1", "score": 1}]
    assert Path(result.result_path).is_file()
    assert client.evals.runs.created["data_source"]["target"] == {
        "model": target.deployment,
        "type": "azure_ai_model",
    }


def test_reconcile_updates_existing_run_without_resubmission(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("REDTEAM_SCOPE_APPROVED", "true")
    config = load_foundry_config(ROOT / "configs/foundry.yaml")
    client = FakeClient()
    runner = _runner(client)
    submitted = runner.run(config=config, scan_name="openai", output_directory=tmp_path, wait=False)

    refreshed = runner.reconcile(
        config=config,
        scan_name="openai",
        result_path=submitted.result_path,
    )

    assert refreshed.status == "completed"
    assert refreshed.output_items == [{"id": "item-1", "score": 1}]
    assert refreshed.run_id == submitted.run_id
    assert client.evals.created is not None


def test_deployment_metadata_drift_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REDTEAM_SCOPE_APPROVED", "true")
    config = load_foundry_config(ROOT / "configs/foundry.yaml")
    config.scans["openai"].target.version = "unexpected"

    with pytest.raises(ValueError, match="metadata does not match"):
        _runner(FakeClient()).run(
            config=config,
            scan_name="openai",
            output_directory=tmp_path,
            wait=False,
        )
