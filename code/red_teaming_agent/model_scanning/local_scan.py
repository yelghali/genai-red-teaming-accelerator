"""
Local Red Teaming Scans - Azure AI Evaluation SDK (RedTeam)
Runs automated red teaming scans locally using azure-ai-evaluation[redteam] with PyRIT.

Supports scanning models via:
  - Azure OpenAI model config (for GPT models)
  - Custom callbacks (for Mistral, Claude via Azure AI Inference API)

Models:
  - GPT 5.1, GPT 5.3, GPT 5.4
  - Mistral Document AI
  - Claude Sonnet 4.5, Claude Haiku 4.5, Claude Sonnet 4.6

Usage:
  python local_scan.py [--models MODEL1 MODEL2 ...] [--all]

Prerequisites:
  1. az login (already authenticated)
  2. pip install "azure-ai-evaluation[redteam]" azure-identity azure-ai-inference openai
  3. Project must be in a supported region:
     East US 2, France Central, Sweden Central, Switzerland West, US North Central
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime

from azure.identity import DefaultAzureCredential
from azure.ai.evaluation.red_team import RedTeam, RiskCategory, AttackStrategy

# ──────────────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────────────

# Foundry project URL (Option 2 from docs - works with Foundry portal)
AZURE_AI_PROJECT = os.environ.get(
    "AZURE_AI_PROJECT",
    "https://my-foundry-yaya.services.ai.azure.com/api/projects/proj-default"
)

# Azure OpenAI endpoint for GPT models
AZURE_OPENAI_ENDPOINT = os.environ.get(
    "AZURE_OPENAI_ENDPOINT",
    "https://my-foundry-yaya.openai.azure.com/"
)

# Azure AI Inference endpoint for non-OpenAI models (Mistral, Claude)
AZURE_AI_ENDPOINT = os.environ.get(
    "AZURE_AI_ENDPOINT",
    "https://my-foundry-yaya.services.ai.azure.com"
)

# Risk categories to test
RISK_CATEGORIES = [
    RiskCategory.Violence,
    RiskCategory.HateUnfairness,
    RiskCategory.Sexual,
    RiskCategory.SelfHarm,
]

# Number of objectives per risk category
NUM_OBJECTIVES = 5

# Models configuration
MODELS = {
    # OpenAI models: use azure_openai_config as target
    "gpt-5-1": {
        "display_name": "GPT 5.1",
        "type": "azure_openai",
        "deployment": "gpt-5-1",
    },
    "gpt-5-3": {
        "display_name": "GPT 5.3",
        "type": "azure_openai",
        "deployment": "gpt-5-3",
    },
    "gpt-5-4": {
        "display_name": "GPT 5.4",
        "type": "azure_openai",
        "deployment": "gpt-5-4",
    },
    # Non-OpenAI models: use callback via Azure AI Inference
    "mistral-document-ai": {
        "display_name": "Mistral Document AI",
        "type": "inference_callback",
        "deployment": "mistral-document-ai",
    },
    "claude-sonnet-4-5": {
        "display_name": "Claude Sonnet 4.5",
        "type": "inference_callback",
        "deployment": "claude-sonnet-4-5",
    },
    "claude-haiku-4-5": {
        "display_name": "Claude Haiku 4.5",
        "type": "inference_callback",
        "deployment": "claude-haiku-4-5",
    },
    "claude-sonnet-4-6": {
        "display_name": "Claude Sonnet 4.6",
        "type": "inference_callback",
        "deployment": "claude-sonnet-4-6",
    },
}


def build_openai_target(deployment: str) -> dict:
    """Build an Azure OpenAI model config target for RedTeam scan."""
    return {
        "azure_endpoint": AZURE_OPENAI_ENDPOINT,
        "azure_deployment": deployment,
        # No api_key needed — DefaultAzureCredential handles auth via az login
    }


def build_inference_callback(deployment: str):
    """Build a callback function that calls a model via the Azure AI Inference API."""
    from azure.ai.inference import ChatCompletionsClient
    from azure.ai.inference.models import UserMessage

    credential = DefaultAzureCredential()
    endpoint = f"{AZURE_AI_ENDPOINT}/models"

    def callback(query: str) -> str:
        try:
            client = ChatCompletionsClient(endpoint=endpoint, credential=credential)
            response = client.complete(
                messages=[UserMessage(content=query)],
                model=deployment,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"[Error calling {deployment}]: {e}"

    return callback


async def scan_model(
    model_key: str,
    model_config: dict,
    attack_strategies: list,
    output_dir: str,
):
    """Run a local red teaming scan against a single model."""
    display_name = model_config["display_name"]
    model_type = model_config["type"]
    deployment = model_config["deployment"]

    print(f"\n{'='*60}")
    print(f"Local Scan: {display_name} (deployment: {deployment})")
    print(f"Type: {model_type}")
    print(f"{'='*60}")

    # Create the RedTeam agent
    credential = DefaultAzureCredential()
    red_team_agent = RedTeam(
        azure_ai_project=AZURE_AI_PROJECT,
        credential=credential,
        risk_categories=RISK_CATEGORIES,
        num_objectives=NUM_OBJECTIVES,
    )

    # Build the target
    if model_type == "azure_openai":
        target = build_openai_target(deployment)
        print(f"  Target: Azure OpenAI config ({AZURE_OPENAI_ENDPOINT})")
    elif model_type == "inference_callback":
        target = build_inference_callback(deployment)
        print(f"  Target: Inference callback ({AZURE_AI_ENDPOINT})")
    else:
        print(f"  Unknown target type: {model_type}")
        return None

    # Output path
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(output_dir, f"local_scan_{model_key}_{timestamp}.json")

    # Run the scan
    print(f"  Running scan with {len(RISK_CATEGORIES)} risk categories, "
          f"{NUM_OBJECTIVES} objectives each...")
    print(f"  Attack strategies: {[str(s) for s in attack_strategies]}")

    result = await red_team_agent.scan(
        target=target,
        scan_name=f"Local Scan - {display_name}",
        attack_strategies=attack_strategies,
        output_path=output_path,
    )

    print(f"  Scan complete. Results saved to: {output_path}")

    # Print summary if available
    if os.path.exists(output_path):
        with open(output_path) as f:
            scan_data = json.load(f)
        if "redteaming_scorecard" in scan_data:
            scorecard = scan_data["redteaming_scorecard"]
            if "risk_category_summary" in scorecard:
                for summary in scorecard["risk_category_summary"]:
                    print(f"  Overall ASR: {summary.get('overall_asr', 'N/A')}")
                    print(f"    Violence ASR: {summary.get('violence_asr', 'N/A')}")
                    print(f"    Hate/Unfairness ASR: {summary.get('hate_unfairness_asr', 'N/A')}")
                    print(f"    Sexual ASR: {summary.get('sexual_asr', 'N/A')}")
                    print(f"    Self-Harm ASR: {summary.get('self_harm_asr', 'N/A')}")

    return {
        "model": display_name,
        "deployment": deployment,
        "output_path": output_path,
        "status": "completed",
    }


async def main_async(args):
    # Determine which models to scan
    if args.all:
        models_to_scan = MODELS
    elif args.models:
        models_to_scan = {k: MODELS[k] for k in args.models if k in MODELS}
        unknown = [k for k in args.models if k not in MODELS]
        if unknown:
            print(f"Warning: Unknown models ignored: {unknown}")
    else:
        # Default: scan only deployed models (GPT + Mistral)
        models_to_scan = {
            k: v for k, v in MODELS.items()
            if k.startswith("gpt-") or k.startswith("mistral-")
        }

    if not models_to_scan:
        print("No models to scan. Use --models or --all.")
        sys.exit(1)

    # Build attack strategies
    if args.difficulty == "easy":
        attack_strategies = [AttackStrategy.EASY]
    elif args.difficulty == "moderate":
        attack_strategies = [AttackStrategy.EASY, AttackStrategy.MODERATE]
    elif args.difficulty == "hard":
        attack_strategies = [AttackStrategy.EASY, AttackStrategy.MODERATE, AttackStrategy.DIFFICULT]
    elif args.difficulty == "specific":
        attack_strategies = [
            AttackStrategy.CharacterSpace,
            AttackStrategy.ROT13,
            AttackStrategy.UnicodeConfusable,
            AttackStrategy.Compose([AttackStrategy.Base64, AttackStrategy.ROT13]),
        ]
    else:
        attack_strategies = [AttackStrategy.EASY]

    output_dir = os.path.join(os.path.dirname(__file__), "results")
    os.makedirs(output_dir, exist_ok=True)

    print(f"Local Red Teaming Scan")
    print(f"Project: {AZURE_AI_PROJECT}")
    print(f"Models: {', '.join(v['display_name'] for v in models_to_scan.values())}")
    print(f"Risk categories: {len(RISK_CATEGORIES)}")
    print(f"Objectives per category: {NUM_OBJECTIVES}")
    print(f"Difficulty: {args.difficulty}")

    results = []
    for model_key, model_config in models_to_scan.items():
        try:
            result = await scan_model(model_key, model_config, attack_strategies, output_dir)
            if result:
                results.append(result)
        except Exception as e:
            print(f"\n  ERROR scanning {model_config['display_name']}: {e}")
            results.append({
                "model": model_config["display_name"],
                "deployment": model_config["deployment"],
                "status": "error",
                "error": str(e),
            })

    # Save summary
    summary_path = os.path.join(
        output_dir, f"local_scan_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    with open(summary_path, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n{'='*60}")
    print(f"All scans complete. Summary: {summary_path}")
    print(f"{'='*60}")
    for r in results:
        icon = "✓" if r["status"] == "completed" else "✗"
        print(f"  {icon} {r['model']}: {r['status']}")


def main():
    parser = argparse.ArgumentParser(description="Local Red Teaming Scans for AI Models")
    parser.add_argument(
        "--models", nargs="+", default=None,
        help=f"Model keys to scan. Available: {', '.join(MODELS.keys())}"
    )
    parser.add_argument("--all", action="store_true", help="Scan all models")
    parser.add_argument(
        "--difficulty", default="easy",
        choices=["easy", "moderate", "hard", "specific"],
        help="Attack difficulty level (default: easy)"
    )
    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
