from __future__ import annotations

from pathlib import Path

from genai_red_teaming_accelerator.foundry_cli import main

ROOT = Path(__file__).parents[1]
CONFIG = str(ROOT / "configs/foundry.yaml")


def test_validate_and_list_are_offline(capsys) -> None:
    assert main(["validate", "--config", CONFIG]) == 0
    assert "Configured scans: 4" in capsys.readouterr().out

    assert main(["list", "--config", CONFIG]) == 0
    output = capsys.readouterr().out
    assert "openai\tmodel\tready" in output
    assert "anthropic\tmodel\tblocked" in output


def test_run_requires_explicit_authorization(monkeypatch, capsys) -> None:
    monkeypatch.delenv("REDTEAM_SCOPE_APPROVED", raising=False)

    assert main(["run", "openai", "--config", CONFIG, "--no-wait"]) == 2
    assert "required after authorization" in capsys.readouterr().err


def test_blocked_scan_fails_before_submission(monkeypatch, capsys) -> None:
    monkeypatch.setenv("REDTEAM_SCOPE_APPROVED", "true")

    assert main(["run", "anthropic", "--config", CONFIG, "--no-wait"]) == 2
    assert "not ready" in capsys.readouterr().err
