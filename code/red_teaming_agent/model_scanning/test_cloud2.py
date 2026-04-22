"""Quick test of cloud red teaming API via Foundry project."""
import sys
import traceback

print("Starting cloud test...", flush=True)

try:
    from azure.identity import DefaultAzureCredential
    from azure.ai.projects import AIProjectClient

    credential = DefaultAzureCredential()
    endpoint = "https://my-foundry-yaya.services.ai.azure.com/api/projects/proj-default"
    
    project_client = AIProjectClient(endpoint=endpoint, credential=credential)
    client = project_client.get_openai_client()
    print(f"OpenAI client base_url: {client.base_url}", flush=True)

    # Create a minimal red team eval
    red_team = client.evals.create(
        name="Test-RT-GPT51",
        data_source_config={"type": "azure_ai_source", "scenario": "red_team"},
        testing_criteria=[
            {
                "type": "azure_ai_evaluator",
                "name": "Prohibited Actions",
                "evaluator_name": "builtin.prohibited_actions",
                "evaluator_version": "1",
            },
        ],
    )
    print(f"SUCCESS: Red team created: {red_team.id}", flush=True)

except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}", flush=True)
    traceback.print_exc()
    sys.exit(1)
