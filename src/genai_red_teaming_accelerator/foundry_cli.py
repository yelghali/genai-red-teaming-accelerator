"""Small CLI for Foundry-managed evaluations not provided by PyRIT's CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from genai_red_teaming_accelerator.compatibility import IncompatibleDependencyError
from genai_red_teaming_accelerator.foundry import FoundryRunner
from genai_red_teaming_accelerator.foundry_config import load_foundry_config

_DEFAULT_CONFIG = "configs/foundry.yaml"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="foundry-scan",
        description="Run portal-visible Microsoft Foundry evaluations. Use pyrit_scan for native PyRIT scenarios.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="Validate Foundry configuration without network traffic")
    validate.add_argument("--config", default=_DEFAULT_CONFIG)

    list_scans = subparsers.add_parser("list", help="List configured Foundry scans without network traffic")
    list_scans.add_argument("--config", default=_DEFAULT_CONFIG)

    run = subparsers.add_parser("run", help="Create a real Foundry evaluation and run")
    run.add_argument("scan", help="Configured scan name")
    run.add_argument("--config", default=_DEFAULT_CONFIG)
    run.add_argument("--output", help="Override the configured evidence directory")
    run.add_argument("--no-wait", action="store_true", help="Return after submission")
    run.add_argument("--json", action="store_true", dest="as_json")

    status = subparsers.add_parser("status", help="Refresh an existing run without creating another")
    status.add_argument("scan", help="Configured scan name")
    status.add_argument("--config", default=_DEFAULT_CONFIG)
    status.add_argument("--result", required=True, help="Existing foundry-run-<run-id>.json")
    status.add_argument("--wait", action="store_true")
    status.add_argument("--json", action="store_true", dest="as_json")
    return parser


def _print_result(result: object, *, as_json: bool) -> None:
    data = result.as_dict()  # type: ignore[attr-defined]
    if as_json:
        print(json.dumps(data, indent=2, sort_keys=True))
        return
    print(f"Foundry eval: {data['eval_id']}")
    print(f"Foundry run: {data['run_id']} ({data['status']})")
    print(f"Evidence: {data['result_path']}")


def main(argv: list[str] | None = None) -> int:
    """Run the Foundry-only command and return its process exit code."""
    args = _parser().parse_args(argv)
    try:
        config = load_foundry_config(args.config)
        if args.command == "validate":
            print(f"Valid Foundry configuration: {Path(args.config).resolve()}")
            print(f"Configured scans: {len(config.scans)}")
            blocked = [name for name, scan in config.scans.items() if not scan.target.ready]
            if blocked:
                print(f"Not ready: {', '.join(sorted(blocked))}")
            return 0
        if args.command == "list":
            for name, scan in sorted(config.scans.items()):
                state = "ready" if scan.target.ready else f"blocked: {scan.target.status_reason}"
                print(f"{name}\t{scan.target.type}\t{state}")
            return 0
        runner = FoundryRunner()
        if args.command == "run":
            result = runner.run(
                config=config,
                scan_name=args.scan,
                output_directory=args.output,
                wait=not args.no_wait,
            )
            _print_result(result, as_json=args.as_json)
            return 0 if result.status not in {"failed", "canceled", "cancelled", "timeout"} else 3
        if args.command == "status":
            result = runner.reconcile(
                config=config,
                scan_name=args.scan,
                result_path=args.result,
                wait=args.wait,
            )
            _print_result(result, as_json=args.as_json)
            return 0 if result.status not in {"failed", "canceled", "cancelled", "timeout"} else 3
    except (IncompatibleDependencyError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
