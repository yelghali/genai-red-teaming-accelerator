"""Quick test of cloud red teaming API."""
import sys
print("Starting test...", flush=True)

try:
    from azure.identity import DefaultAzureCredential
    print("Imported DefaultAzureCredential", flush=True)
    
    credential = DefaultAzureCredential()
    token = credential.get_token("https://cognitiveservices.azure.com/.default")
    print(f"Got token (length: {len(token.token)})", flush=True)
    
    # Try with the Foundry project endpoint
    from azure.ai.projects import AIProjectClient
    print("Imported AIProjectClient", flush=True)
    
    endpoint = "https://my-foundry-yaya.services.ai.azure.com/api/projects/proj-default"
    with AIProjectClient(endpoint=endpoint, credential=credential) as project_client:
        client = project_client.get_openai_client()
        print(f"Client created via AIProjectClient", flush=True)
    
    # Try creating a red team
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
    print(f"Red team created: {red_team.id}", flush=True)
    
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}", flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)
