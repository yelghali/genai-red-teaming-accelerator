"""Quick test of local RedTeam scan against GPT 5.1."""
import asyncio
import os
import sys
print("Starting local red teaming test...", flush=True)

async def main():
    try:
        from azure.identity import DefaultAzureCredential
        from azure.ai.evaluation.red_team import RedTeam, RiskCategory
        print("Imports OK", flush=True)
        
        # Foundry project URL (works with new Foundry portal)
        azure_ai_project = "https://my-foundry-yaya.services.ai.azure.com/api/projects/proj-default"
        
        credential = DefaultAzureCredential()
        
        red_team_agent = RedTeam(
            azure_ai_project=azure_ai_project,
            credential=credential,
            risk_categories=[RiskCategory.Violence],
            num_objectives=1,
        )
        print("RedTeam agent created", flush=True)
        
        # Target: GPT 5.1 via Azure OpenAI config
        target = {
            "azure_endpoint": "https://my-foundry-yaya.openai.azure.com/",
            "azure_deployment": "gpt-5-1",
        }
        print(f"Target: {target}", flush=True)
        
        output_dir = os.path.join(os.path.dirname(__file__), "results")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "test_gpt51_scan.json")
        
        print("Starting scan (1 risk category, 1 objective)...", flush=True)
        result = await red_team_agent.scan(
            target=target,
            scan_name="Test GPT 5.1 Scan",
            output_path=output_path,
        )
        print(f"Scan complete! Results saved to: {output_path}", flush=True)
        
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", flush=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)

asyncio.run(main())
