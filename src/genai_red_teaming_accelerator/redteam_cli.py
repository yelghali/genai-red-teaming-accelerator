"""CLI for configuration-selected native PyRIT or Foundry cloud tests."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from genai_red_teaming_accelerator.compatibility import IncompatibleDependencyError
from genai_red_teaming_accelerator.redteam import RedTeamRunner, build_plan, validate_runtime_references
from genai_red_teaming_accelerator.redteam_config import load_redteam_config

_DEFAULT_CONFIG = "configs/redteam.yaml"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rta",
        description="Select native PyRIT or the Microsoft Foundry cloud red-team agent from strict YAML.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="Validate all profiles without model or cloud traffic")
    validate.add_argument("--config", default=_DEFAULT_CONFIG)

    list_tests = subparsers.add_parser("list", help="List configured test profiles without network traffic")
    list_tests.add_argument("--config", default=_DEFAULT_CONFIG)

    plan = subparsers.add_parser("plan", help="Show the native delegation without executing it")
    plan.add_argument("test", nargs="?", help="Test profile; defaults to selected_test")
    plan.add_argument("--config", default=_DEFAULT_CONFIG)
    plan.add_argument("--json", action="store_true", dest="as_json")

    run = subparsers.add_parser("run", help="Execute one authorized test using its configured engine")
    run.add_argument("test", nargs="?", help="Test profile; defaults to selected_test")
    run.add_argument("--config", default=_DEFAULT_CONFIG)
    run.add_argument("--json", action="store_true", dest="as_json")
    return parser


def _print_plan(plan: dict[str, object], *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(plan, indent=2, sort_keys=True))
        return
    print(f"Test: {plan['test']}")
    print(f"Engine: {plan['engine']}")
    print(f"Target binding: {plan['target_binding']}")
    print(json.dumps(plan["delegation"], indent=2, sort_keys=True))


def _print_result(result: object, *, as_json: bool) -> None:
    data = result.as_dict()  # type: ignore[attr-defined]
    if as_json:
        print(json.dumps(data, indent=2, sort_keys=True))
        return
    engine_result = data["result"]
    print(f"Test: {data['test_name']}")
    print(f"Engine: {data['engine']}")
    if data["engine"] == "pyrit":
        print(f"PyRIT scenario result: {engine_result['scenario_result_id']} ({engine_result['status']})")
        print(f"Co-PyRIT: {engine_result['co_pyrit_url']}")
    else:
        print(f"Foundry eval: {engine_result['eval_id']}")
        print(f"Foundry run: {engine_result['run_id']} ({engine_result['status']})")
        print(f"Evidence: {engine_result['result_path']}")
        if engine_result.get("report_url"):
            print(f"Foundry report: {engine_result['report_url']}")
        if data.get("co_pyrit_import"):
            imported = data["co_pyrit_import"]
            print(f"Co-PyRIT snapshots imported: {imported['imported']}")


def main(argv: list[str] | None = None) -> int:
    """Run the thin engine selector and return its process exit code."""
    args = _parser().parse_args(argv)
    try:
        config = load_redteam_config(args.config)
        if args.command == "validate":
            validate_runtime_references(config)
            print(f"Valid red-team configuration: {Path(args.config).resolve()}")
            print(f"Configured tests: {len(config.tests)}")
            print(f"Selected test: {config.selected_test}")
            return 0
        if args.command == "list":
            for name, test in sorted(config.tests.items()):
                marker = " *" if name == config.selected_test else ""
                print(f"{name}\t{test.engine}\t{test.setup.type}\t{test.target}{marker}")
            return 0
        if args.command == "plan":
            _print_plan(build_plan(config, test_name=args.test), as_json=args.as_json)
            return 0
        if args.command == "run":
            result = RedTeamRunner().run(config=config, test_name=args.test)
            _print_result(result, as_json=args.as_json)
            status = result.result.status.casefold()
            return 0 if status not in {"failed", "canceled", "cancelled", "timeout", "error"} else 3
    except (IncompatibleDependencyError, OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
