import asyncio
import os
import sys

# Ensure backend root in path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.models.schemas import CreateRepoRequest, SyncStatusResponse
from app.services.sync_service import sync_service
from app.main import app
# pyrefly: ignore [missing-import]
from httpx import AsyncClient, ASGITransport

async def test_repo_sync_features():
    print("--- 1. Testing Pydantic Schemas ---")
    req = CreateRepoRequest(
        name="test-new-repo",
        description="A test repository for auto sync",
        private=False,
        auto_init=True,
        auto_index=True
    )
    assert req.name == "test-new-repo"
    assert req.auto_index is True
    print("[OK] CreateRepoRequest schema verified!")

    sync_resp = SyncStatusResponse(
        total_repos=5,
        new_repos_detected=["user/test-new-repo"],
        auto_indexed=["user/test-new-repo"],
        has_new=True,
        is_watcher_running=True
    )
    assert sync_resp.has_new is True
    print("[OK] SyncStatusResponse schema verified!")

    print("\n--- 2. Testing SyncService Registration ---")
    sync_service.known_repo_names.add("test-owner/existing-repo")
    sync_service.register_repo("test-owner/brand-new-repo", auto_index=False)
    assert "test-owner/brand-new-repo" in sync_service.known_repo_names
    print(f"[OK] SyncService register_repo verified! Known count: {len(sync_service.known_repo_names)}")

    print("\n--- 3. Testing API Endpoints via ASGI Client ---")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Test /api/github/sync/status
        resp = await client.get("/api/github/sync/status?auto_index=false")
        assert resp.status_code == 200, f"Sync status failed: {resp.text}"
        data = resp.json()
        print(f"[OK] GET /api/github/sync/status returned status 200. Total repos found: {data.get('total_repos')}")

        # Test /api/github/webhook with repository created event
        webhook_payload = {
            "action": "created",
            "repository": {
                "name": "auto-created-repo",
                "owner": {"login": "test-developer"},
                "default_branch": "main"
            }
        }
        headers = {"X-GitHub-Event": "repository"}
        wh_resp = await client.post("/api/github/webhook", json=webhook_payload, headers=headers)
        assert wh_resp.status_code == 200, f"Webhook failed: {wh_resp.text}"
        wh_data = wh_resp.json()
        print(f"[OK] POST /api/github/webhook (repository.created) returned: {wh_data}")
        assert wh_data.get("status") == "repository_created_and_updated"
        assert wh_data.get("full_name") == "test-developer/auto-created-repo"
        assert "test-developer/auto-created-repo" in sync_service.known_repo_names

        # Test /api/github/webhook with git create event (ref_type = repository)
        create_payload = {
            "ref_type": "repository",
            "repository": {
                "name": "cli-created-repo",
                "owner": {"login": "test-developer"},
                "default_branch": "main"
            }
        }
        wh_resp2 = await client.post("/api/github/webhook", json=create_payload, headers={"X-GitHub-Event": "create"})
        assert wh_resp2.status_code == 200
        wh_data2 = wh_resp2.json()
        print(f"[OK] POST /api/github/webhook (create repository) returned: {wh_data2}")
        assert "test-developer/cli-created-repo" in sync_service.known_repo_names

    print("\nALL NEW REPOSITORY UPDATE & SYNC TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(test_repo_sync_features())
