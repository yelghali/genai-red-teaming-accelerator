from __future__ import annotations

from pathlib import Path

from genai_red_teaming_accelerator.redteam_cli import main

ROOT = Path(__file__).parents[1]
CONFIG = str(ROOT / "configs/redteam.yaml")


def test_validate_list_and_plan_do_not_execute_models(capsys) -> None:
    assert main(["validate", "--config", CONFIG]) == 0
    assert "Configured tests: 3" in capsys.readouterr().out

    assert main(["list", "--config", CONFIG]) == 0
    listing = capsys.readouterr().out
    assert "baseline-pyrit\tpyrit\tbaseline\topenai" in listing
    assert "baseline-foundry\tfoundry\tbaseline\topenai" in listing

    assert main(["plan", "baseline-foundry", "--config", CONFIG, "--json"]) == 0
    plan = capsys.readouterr().out
    assert '"engine": "foundry"' in plan
    assert '"objective_count": "service_managed"' in plan
