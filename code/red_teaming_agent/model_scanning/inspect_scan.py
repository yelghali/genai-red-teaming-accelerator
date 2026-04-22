"""Inspect the working manual scan to reverse-engineer the format."""
import json
import traceback

try:
    from azure.identity import DefaultAzureCredential
    from azure.ai.projects import AIProjectClient

    cred = DefaultAzureCredential()
    pc = AIProjectClient(
        endpoint="https://my-foundry-yaya.services.ai.azure.com/api/projects/proj-default",
        credential=cred,
    )
    client = pc.get_openai_client()

    eval_id = "eval_843c366991bf4bd3b96ae10a14dae1bb"

    # List runs
    runs = list(client.evals.runs.list(eval_id=eval_id))
    print(f"Found {len(runs)} runs", flush=True)

    # Get the completed run (gpt-4o)
    for r in runs:
        print(f"\n{'='*60}", flush=True)
        print(f"Run: {r.id} | {r.name} | status={r.status}", flush=True)
        # Try to get the data_source from the run
        attrs = [a for a in dir(r) if not a.startswith('_')]
        print(f"Attributes: {attrs}", flush=True)
        if hasattr(r, 'data_source'):
            print(f"data_source: {r.data_source}", flush=True)
        if hasattr(r, 'metadata'):
            print(f"metadata: {r.metadata}", flush=True)
        if hasattr(r, 'model_dump'):
            d = r.model_dump()
            print(json.dumps(d, indent=2, default=str)[:3000], flush=True)

except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}", flush=True)
    traceback.print_exc()
