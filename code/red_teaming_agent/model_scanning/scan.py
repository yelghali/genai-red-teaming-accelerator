"""
Unified Red Teaming Scanner - Azure AI Foundry
Scans chat models (cloud) AND document/OCR models (local callback) in one script.

Chat models (GPT, Mistral Large 3):
  → Cloud evals API with azure_ai_model target (runs server-side)

Document AI models (Mistral OCR/Document AI):
  → Local RedTeam SDK with custom callback that wraps text prompts as
    embedded-text images, sends to /v1/ocr, and returns extracted text

Usage:
  # Scan chat models only (cloud)
  python scan.py --models gpt-5-1 gpt-5-3 mistral-large-3

  # Scan Document AI only (local callback)
  python scan.py --models mistral-document-ai

  # Scan everything
  python scan.py --models gpt-5-1 gpt-5-3 gpt-5-4 mistral-large-3 mistral-document-ai

  # Env vars
  RED_TEAM_MODELS=gpt-5-1,mistral-large-3,mistral-document-ai python scan.py

Prerequisites:
  pip install "azure-ai-projects>=2.0.0" "azure-ai-evaluation[redteam]" azure-identity Pillow
  az login
"""

import argparse
import asyncio
import base64
import io
import json
import os
import sys
import time
from datetime import datetime

from azure.identity import DefaultAzureCredential

# ──────────────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────────────

AZURE_AI_PROJECT_ENDPOINT = os.environ.get("AZURE_AI_PROJECT_ENDPOINT", "")
NUM_TURNS = int(os.environ.get("RED_TEAM_NUM_TURNS", "1"))
TIMEOUT_MINUTES = int(os.environ.get("RED_TEAM_TIMEOUT_MINUTES", "30"))

# Document AI models that need local callback (OCR, not chat)
DOCAI_MODELS = {"mistral-document-ai"}

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

STRATEGY_GROUPS = {
    "easy": ["Base64", "Flip", "Morse"],
    "moderate": ["Tense"],
    "difficult": ["Crescendo", "Multiturn"],
    "all": ["Base64", "Flip", "Morse", "Tense"],
}

# Local RedTeam strategy mapping
LOCAL_STRATEGY_MAP = {
    "easy": "EASY",
    "moderate": "MODERATE",
    "difficult": "DIFFICULT",
}


# ──────────────────────────────────────────────────────────────────────────────
# Cloud scan (chat models)
# ──────────────────────────────────────────────────────────────────────────────

def cloud_scan(endpoint, models, strategies, num_turns, timeout, no_wait):
    """Scan chat models via cloud evals API."""
    from azure.ai.projects import AIProjectClient

    print(f"\n{'='*60}")
    print(f"CLOUD SCAN — {len(models)} chat model(s)")
    print(f"Models: {', '.join(models)}")
    print(f"Strategies: {strategies}")
    print(f"{'='*60}")

    credential = DefaultAzureCredential()
    project_client = AIProjectClient(endpoint=endpoint, credential=credential)
    client = project_client.get_openai_client()

    eval_name = f"RedTeam-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    red_team = client.evals.create(
        name=eval_name,
        data_source_config={"type": "azure_ai_source", "scenario": "red_team"},
        testing_criteria=TESTING_CRITERIA,
    )
    print(f"  Eval created: {red_team.id}", flush=True)

    runs = []
    for model in models:
        try:
            run = client.evals.runs.create(
                eval_id=red_team.id,
                name=f"scan-{model}-{datetime.now().strftime('%H%M%S')}",
                data_source={
                    "type": "azure_ai_red_team",
                    "item_generation_params": {
                        "type": "red_team",
                        "attack_strategies": strategies,
                        "num_turns": num_turns,
                    },
                    "target": {"type": "azure_ai_model", "model": model},
                },
            )
            print(f"  Run: {run.id} | {model} | {run.status}", flush=True)
            runs.append({"run_id": run.id, "model": model, "status": run.status, "type": "cloud"})
        except Exception as e:
            print(f"  ERROR {model}: {e}", flush=True)
            runs.append({"model": model, "status": "error", "error": str(e), "type": "cloud"})

    if not no_wait:
        pending = {r["run_id"] for r in runs if "run_id" in r}
        start = time.time()
        while pending and time.time() - start < timeout * 60:
            for rid in list(pending):
                run = client.evals.runs.retrieve(run_id=rid, eval_id=red_team.id)
                if run.status in ("completed", "failed", "canceled"):
                    elapsed = int(time.time() - start)
                    print(f"  {run.name}: {run.status} ({elapsed}s)", flush=True)
                    if run.status == "completed" and run.per_testing_criteria_results:
                        for cr in run.per_testing_criteria_results:
                            name = getattr(cr, "name", "?")
                            passed = getattr(cr, "passed", 0)
                            failed = getattr(cr, "failed", 0)
                            total = passed + failed
                            asr = f"{failed}/{total}" if total > 0 else "-"
                            print(f"    {name}: ASR {asr}", flush=True)
                    for r in runs:
                        if r.get("run_id") == rid:
                            r["status"] = run.status
                    pending.discard(rid)
            if pending:
                elapsed = int(time.time() - start)
                print(f"  ... {len(pending)} runs in progress ({elapsed}s)", flush=True)
                time.sleep(30)
        if pending:
            print(f"  Timed out with {len(pending)} runs pending")

    return {"eval_id": red_team.id, "eval_name": eval_name, "runs": runs}


# ──────────────────────────────────────────────────────────────────────────────
# Document AI callback (for local RedTeam scan)
# ──────────────────────────────────────────────────────────────────────────────

def make_docai_callback(endpoint: str, model: str):
    """Create a callback that wraps text prompts as images and sends to Document AI OCR.

    The red team sends adversarial TEXT prompts. This callback:
    1. Renders the text prompt onto an image (simulating a document with that text)
    2. Sends the image to the Mistral Document AI /v1/ocr endpoint
    3. Returns the OCR output (what the model "reads" from the document)

    This tests whether Document AI faithfully extracts adversarial content
    or if it has safety guardrails for content in documents.
    """
    import requests
    from PIL import Image, ImageDraw, ImageFont

    # Extract account/project from endpoint for the OCR URL
    # endpoint = https://<account>.services.ai.azure.com/api/projects/<project>
    parts = endpoint.split("/api/projects/")
    base_url = parts[0]
    project = parts[1] if len(parts) > 1 else "proj-default"
    ocr_url = f"{base_url}/api/projects/{project}/v1/ocr?api-version=2025-11-15-preview"

    credential = DefaultAzureCredential()

    def render_text_to_image(text: str) -> str:
        """Render text onto a white image and return base64 PNG."""
        img = Image.new("RGB", (800, 600), "white")
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("arial.ttf", 16)
        except OSError:
            font = ImageFont.load_default()

        # Word-wrap text
        lines = []
        for line in text.split("\n"):
            while len(line) > 80:
                lines.append(line[:80])
                line = line[80:]
            lines.append(line)

        y = 20
        for line in lines[:30]:
            draw.text((20, y), line, fill="black", font=font)
            y += 22

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()

    def callback(query: str) -> str:
        """Send adversarial text as an image to Document AI and return OCR output."""
        try:
            img_b64 = render_text_to_image(query)
            token = credential.get_token("https://ai.azure.com/.default").token
            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            body = {
                "model": model,
                "document": {
                    "type": "image_url",
                    "image_url": f"data:image/png;base64,{img_b64}",
                },
            }
            r = requests.post(ocr_url, json=body, headers=headers, timeout=60)
            if r.status_code == 200:
                data = r.json()
                # Extract text from OCR response
                pages = data.get("pages", [])
                text_parts = []
                for page in pages:
                    md = page.get("markdown", "")
                    if md:
                        text_parts.append(md)
                return "\n".join(text_parts) if text_parts else "[No text extracted]"
            else:
                return f"[OCR error {r.status_code}: {r.text[:200]}]"
        except Exception as e:
            return f"[Callback error: {e}]"

    return callback


# ──────────────────────────────────────────────────────────────────────────────
# Local scan (Document AI via callback)
# ──────────────────────────────────────────────────────────────────────────────

def local_scan(endpoint, models, difficulty, num_objectives=5):
    """Scan Document AI models locally using RedTeam with custom callback."""
    from azure.ai.evaluation.red_team import RedTeam, RiskCategory, AttackStrategy

    print(f"\n{'='*60}")
    print(f"LOCAL SCAN — {len(models)} document AI model(s)")
    print(f"Models: {', '.join(models)}")
    print(f"Difficulty: {difficulty}")
    print(f"{'='*60}")

    # Map difficulty to local AttackStrategy
    strategy_map = {
        "easy": [AttackStrategy.EASY],
        "moderate": [AttackStrategy.MODERATE],
        "difficult": [AttackStrategy.DIFFICULT],
        "all": [AttackStrategy.EASY, AttackStrategy.MODERATE],
    }
    attack_strategies = strategy_map.get(difficulty, [AttackStrategy.EASY])

    credential = DefaultAzureCredential()
    results = []

    for model in models:
        print(f"\n  Scanning {model} (local callback)...", flush=True)

        callback = make_docai_callback(endpoint, model)

        red_team = RedTeam(
            azure_ai_project=endpoint,
            credential=credential,
            risk_categories=[
                RiskCategory.Violence,
                RiskCategory.HateUnfairness,
                RiskCategory.Sexual,
                RiskCategory.SelfHarm,
            ],
            num_objectives=num_objectives,
        )

        output_dir = os.path.join(os.path.dirname(__file__), "results")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(
            output_dir, f"local_scan_{model}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )

        result = asyncio.run(red_team.scan(
            target=callback,
            scan_name=f"DocAI-{model}-{datetime.now().strftime('%H%M%S')}",
            attack_strategies=attack_strategies,
            output_path=output_path,
        ))

        print(f"  {model}: scan complete → {output_path}", flush=True)
        results.append({
            "model": model,
            "type": "local",
            "status": "completed",
            "output_path": output_path,
        })

    return results


# ──────────────────────────────────────────────────────────────────────────────
# Main — unified entry point
# ──────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Unified Red Teaming Scanner")
    parser.add_argument("--models", nargs="+", default=None,
                        help="Deployment names (env: RED_TEAM_MODELS)")
    parser.add_argument("--no-wait", action="store_true", help="Don't poll cloud runs")
    parser.add_argument("--difficulty", default=os.environ.get("RED_TEAM_DIFFICULTY", "easy"),
                        choices=["easy", "moderate", "difficult", "all"])
    parser.add_argument("--num-turns", type=int, default=NUM_TURNS)
    parser.add_argument("--timeout", type=int, default=TIMEOUT_MINUTES)
    parser.add_argument("--endpoint", default=AZURE_AI_PROJECT_ENDPOINT)
    args = parser.parse_args()

    if not args.endpoint:
        print("ERROR: Set AZURE_AI_PROJECT_ENDPOINT or --endpoint")
        sys.exit(1)

    # Resolve models
    env_models = os.environ.get("RED_TEAM_MODELS")
    if args.models:
        all_models = args.models
    elif env_models:
        all_models = [m.strip() for m in env_models.split(",") if m.strip()]
    else:
        print("ERROR: Set RED_TEAM_MODELS or --models")
        sys.exit(1)

    # Split into cloud (chat) vs local (document AI)
    cloud_models = [m for m in all_models if m not in DOCAI_MODELS]
    local_models = [m for m in all_models if m in DOCAI_MODELS]

    print(f"Unified Red Teaming Scanner")
    print(f"Endpoint: {args.endpoint}")
    if cloud_models:
        print(f"Cloud (chat): {', '.join(cloud_models)}")
    if local_models:
        print(f"Local (docAI): {', '.join(local_models)}")
    print(f"Difficulty: {args.difficulty}")

    all_results = []

    # Cloud scan for chat models
    if cloud_models:
        strategies = STRATEGY_GROUPS[args.difficulty]
        cloud_results = cloud_scan(
            endpoint=args.endpoint,
            models=cloud_models,
            strategies=strategies,
            num_turns=args.num_turns,
            timeout=args.timeout,
            no_wait=args.no_wait,
        )
        all_results.append(cloud_results)

    # Local scan for Document AI models
    if local_models:
        local_results = local_scan(
            endpoint=args.endpoint,
            models=local_models,
            difficulty=args.difficulty,
        )
        all_results.extend(local_results)

    # Save combined summary
    output_dir = os.path.join(os.path.dirname(__file__), "results")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(
        output_dir, f"scan_all_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    with open(output_path, "w") as f:
        json.dump(all_results, f, indent=2, default=str)

    print(f"\n{'='*60}")
    print(f"Summary: {output_path}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
