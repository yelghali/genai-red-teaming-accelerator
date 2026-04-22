"""Check all red team scans in the project."""
import traceback
try:
    from azure.identity import DefaultAzureCredential
    from azure.ai.projects import AIProjectClient

    cred = DefaultAzureCredential()
    pc = AIProjectClient(
        endpoint="https://my-foundry-yaya.services.ai.azure.com/api/projects/proj-default",
        credential=cred,
    )
    print(f"Project: {pc._config.endpoint}", flush=True)

    # List red teams via beta API
    print("\n--- Red Teams (beta.red_teams.list) ---", flush=True)
    items = list(pc.beta.red_teams.list())
    print(f"Found {len(items)} red teams", flush=True)
    for rt in items:
        print(f"  {rt.name} | {rt.display_name} | status={rt.status} | target={rt.target}", flush=True)

    # Also check the specific scans we created
    print("\n--- Checking specific scans ---", flush=True)
    for name in [
        "ddf1d689-2910-462a-9db5-4d1def6da483",  # easy scan
        "245d40b9-065c-4db1-bac8-1e9c794a7f30",  # first v2 scan
        "634f7a96-297f-43dd-8240-2da73f70f09a",  # test scan
    ]:
        try:
            rt = pc.beta.red_teams.get(name=name)
            print(f"  {name}: status={rt.status}, display={rt.display_name}", flush=True)
        except Exception as e:
            print(f"  {name}: ERROR - {e}", flush=True)

    # Check the manual scan
    print("\n--- Checking evals (openai client) ---", flush=True)
    client = pc.get_openai_client()
    evals_list = list(client.evals.list())
    print(f"Found {len(evals_list)} evals", flush=True)
    for ev in evals_list[:5]:
        print(f"  {ev.id} | {ev.name}", flush=True)

except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}", flush=True)
    traceback.print_exc()
