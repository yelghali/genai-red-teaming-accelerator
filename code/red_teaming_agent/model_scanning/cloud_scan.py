"""
Cloud Red Teaming Scans - Azure AI Foundry (OpenAI Evals API, Model Target)
Scans multiple models using the OpenAI evals API with azure_ai_model target type.

Matches the portal's manual "Create" flow exactly:
  - eval with evals_target_type=azure_ai_model, scenario=red_team
  - runs with target type=azure_ai_model, per-model deployment
  - safety evaluators: violence, self_harm, sexual, hate_unfairness,
    ungrounded_attributes, code_vulnerability (all v3)

Reference: https://learn.microsoft.com/azure/foundry/how-to/develop/run-ai-red-teaming-cloud

Usage:
  python cloud_scan.py [--models MODEL1 MODEL2 ...] [--all] [--no-wait]
  python cloud_scan.py --models gpt-5-1 --difficulty easy
  python cloud_scan.py --all --difficulty all --no-wait

Prerequisites:
  1. az login
  2. pip install "azure-ai-projects>=2.0.0" azure-identity
  3. Models deployed in the AI Services resource
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime

from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

# ──────────────────────────────────────────────────────────────────────────────
# Configuration — all values from env vars (see .env.sample)
# ──────────────────────────────────────────────────────────────────────────────

AZURE_AI_PROJECT_ENDPOINT = os.environ.get("AZURE_AI_PROJECT_ENDPOINT", "")

NUM_TURNS = int(os.environ.get("RED_TEAM_NUM_TURNS", "1"))
TIMEOUT_MINUTES = int(os.environ.get("RED_TEAM_TIMEOUT_MINUTES", "30"))

# Models to scan — set RED_TEAM_MODELS env var (comma-separated deployment names)
# or pass --models on CLI.
#
# Supported: any chat-completion model deployed in the Foundry project.
#   Works: GPT models, Mistral Large 3 (chat), Mistral Small, etc.
#   Does NOT work: document/OCR models (e.g. mistral-document-ai) — these expect
#   image/PDF input, not text prompts. They complete with 0 results.

# Safety evaluators (matching the working manual scan exactly)
TESTING_CRITERIA = [
    {"type": "azure_ai_evaluator", "name": "Violence-Content-Evaluator",
     "evaluator_name": "builtin.violence", "evaluator_version": "3"},
    {"type": "azure_ai_evaluator", "name": "Self-Harm-Related-Content-Evaluator",
     "evaluator_name": "builtin.self_harm", "evaluator_version": "3"},
    {"type": "azure_ai_evaluator", "name": "Ungrounded-Attributes-Evaluator",
     "evaluator_name": "builtin.ungrounded_attributes", "evaluator_version": "3"},
    {"type": "azure_ai_evaluator", "name": "Sexual-Content-Evaluator",
     "evaluator_name": "builtin.sexual", "evaluator_version": "3"},
    {"type": "azure_ai_evaluator", "name": "Hate-and-Unfairness-Evaluator",
     "evaluator_name": "builtin.hate_unfairness", "evaluator_version": "3"},
    {"type": "azure_ai_evaluator", "name": "Code-Vulnerability-Evaluator",
     "evaluator_name": "builtin.code_vulnerability", "evaluator_version": "3"},
]

# Attack strategies by difficulty
STRATEGY_GROUPS = {
    "easy": ["Base64", "Flip", "Morse"],
    "moderate": ["Tense"],
    "difficult": ["Crescendo", "Multiturn"],
    "all": ["Base64", "Flip", "Morse", "Tense"],
}


def create_red_team_eval(client, name: str):
    """Create the red team eval group (one per batch of runs)."""
    red_team = client.evals.create(
        name=name,
        data_source_config={"type": "azure_ai_source", "scenario": "red_team"},
        testing_criteria=TESTING_CRITERIA,
    )
    print(f"  Created eval: {red_team.id} ({red_team.name})", flush=True)
    return red_team


def create_run(client, eval_id: str, deployment_name: str, attack_strategies: list,
               num_turns: int = 1):
    """Create a run targeting a specific model deployment."""
    run = client.evals.runs.create(
        eval_id=eval_id,
        name=f"scan-{deployment_name}-{datetime.now().strftime('%H%M%S')}",
        data_source={
            "type": "azure_ai_red_team",
            "item_generation_params": {
                "type": "red_team",
                "attack_strategies": attack_strategies,
                "num_turns": num_turns,
            },
            "target": {
                "type": "azure_ai_model",
                "model": deployment_name,
            },
        },
    )
    print(f"  Run created: {run.id} | target={deployment_name} | status={run.status}", flush=True)
    return run


def wait_for_runs(client, eval_id: str, run_ids: list, timeout_minutes: int = 30):
    """Poll all runs until they complete or timeout."""
    start = time.time()
    pending = set(run_ids)

    while pending and time.time() - start < timeout_minutes * 60:
        for rid in list(pending):
            run = client.evals.runs.retrieve(run_id=rid, eval_id=eval_id)
            if run.status in ("completed", "failed", "canceled"):
                elapsed = int(time.time() - start)
                print(f"  {run.name}: {run.status} ({elapsed}s)", flush=True)
                if run.status == "completed" and run.per_testing_criteria_results:
                    for cr in run.per_testing_criteria_results:
                        passed = cr.get("passed", 0)
                        failed = cr.get("failed", 0)
                        total = passed + failed
                        asr = f"{failed}/{total}" if total > 0 else "-"
                        print(f"    {cr.get('name', '?')}: ASR {asr}", flush=True)
                pending.discard(rid)
        if pending:
            elapsed = int(time.time() - start)
            print(f"  ... {len(pending)} runs still in progress ({elapsed}s)", flush=True)
            time.sleep(30)

    if pending:
        print(f"  Timed out with {len(pending)} runs still pending")


def main():
    parser = argparse.ArgumentParser(description="Cloud Red Teaming Scans for AI Models")
    parser.add_argument("--models", nargs="+", default=None,
                        help="Deployment names to scan (env: RED_TEAM_MODELS, comma-separated)")
    parser.add_argument("--no-wait", action="store_true", help="Fire-and-forget")
    parser.add_argument("--difficulty", default=os.environ.get("RED_TEAM_DIFFICULTY", "easy"),
                        choices=["easy", "moderate", "difficult", "all"],
                        help="Attack difficulty (default: easy, env: RED_TEAM_DIFFICULTY)")
    parser.add_argument("--num-turns", type=int, default=NUM_TURNS,
                        help=f"Simulation turns (default: {NUM_TURNS}, env: RED_TEAM_NUM_TURNS)")
    parser.add_argument("--timeout", type=int, default=TIMEOUT_MINUTES,
                        help=f"Timeout in minutes (default: {TIMEOUT_MINUTES})")
    parser.add_argument("--endpoint", default=AZURE_AI_PROJECT_ENDPOINT,
                        help="Foundry project endpoint (env: AZURE_AI_PROJECT_ENDPOINT)")
    args = parser.parse_args()

    if not args.endpoint:
        print("ERROR: AZURE_AI_PROJECT_ENDPOINT env var or --endpoint required.")
        print("  Example: https://<account>.services.ai.azure.com/api/projects/<project>")
        sys.exit(1)

    # Resolve models: CLI --models > env RED_TEAM_MODELS > error
    env_models = os.environ.get("RED_TEAM_MODELS")
    if args.models:
        models_to_scan = {k: k for k in args.models}
    elif env_models:
        keys = [m.strip() for m in env_models.split(",") if m.strip()]
        models_to_scan = {k: k for k in keys}
    else:
        print("ERROR: No models specified. Set RED_TEAM_MODELS env var or use --models.")
        print("  Example: RED_TEAM_MODELS=gpt-5-1,gpt-5-3,gpt-5-4")
        print("  Or: python cloud_scan.py --models gpt-5-1 gpt-5-3")
        sys.exit(1)

    if not models_to_scan:
        print("No models to scan. Use --models or --all.")
        sys.exit(1)

    strategies = STRATEGY_GROUPS[args.difficulty]

    print(f"Red Teaming Cloud Scan (Model Target)")
    print(f"Endpoint: {args.endpoint}")
    print(f"Models: {', '.join(models_to_scan.values())}")
    print(f"Difficulty: {args.difficulty} -> strategies: {strategies}")

    credential = DefaultAzureCredential()
    project_client = AIProjectClient(endpoint=args.endpoint, credential=credential)
    client = project_client.get_openai_client()

    # Step 1: Create one eval group for all runs
    eval_name = f"RedTeam-{args.difficulty}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    red_team = create_red_team_eval(client, eval_name)

    # Step 2: Create a run per model
    runs = []
    for deployment_name, display_name in models_to_scan.items():
        try:
            run = create_run(client, red_team.id, deployment_name, strategies,
                            num_turns=args.num_turns)
            runs.append({"run_id": run.id, "model": display_name,
                         "deployment": deployment_name, "status": run.status})
        except Exception as e:
            print(f"  ERROR creating run for {display_name}: {e}", flush=True)
            runs.append({"model": display_name, "deployment": deployment_name,
                         "status": "error", "error": str(e)})

    # Step 3: Wait for completion
    if not args.no_wait:
        run_ids = [r["run_id"] for r in runs if "run_id" in r]
        if run_ids:
            print(f"\nPolling {len(run_ids)} runs...", flush=True)
            wait_for_runs(client, red_team.id, run_ids, timeout_minutes=args.timeout)

    # Save results
    output_dir = os.path.join(os.path.dirname(__file__), "results")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir,
                               f"cloud_scan_{args.difficulty}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    summary = {"eval_id": red_team.id, "eval_name": eval_name,
               "difficulty": args.difficulty, "strategies": strategies, "runs": runs}
    with open(output_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)

    print(f"\n{'='*60}")
    print(f"Eval: {red_team.id} ({eval_name})")
    print(f"Summary: {output_path}")
    for r in runs:
        icon = "✓" if r["status"] == "completed" else "✗" if r["status"] == "error" else "⏳"
        print(f"  {icon} {r['model']}: {r['status']}")


if __name__ == "__main__":
    main()
