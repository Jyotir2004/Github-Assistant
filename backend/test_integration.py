import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app.config import settings
from backend.app.services.github_service import github_service
from backend.app.services.llm_service import llm_service
from backend.app.rag.vectorstore import vector_store
from backend.app.agents.code_agent import code_agent

async def run_tests():
    print("1. Checking config...")
    assert settings.GITHUB_TOKEN.startswith("github_pat_"), "Invalid GitHub Token"
    assert settings.GROQ_API_KEY.startswith("gsk_"), "Invalid Groq Key"
    print(f"   Config OK! Model: {settings.GROQ_MODEL}")

    print("2. Testing GitHub API...")
    user = await github_service.get_authenticated_user()
    print(f"   GitHub User OK: {user.get('login')}")
    repos = await github_service.get_user_repositories(per_page=5)
    print(f"   GitHub Repos OK. Count: {len(repos)}, First repo: {repos[0]['name'] if repos else 'None'}")

    print("3. Testing Groq LLM inference...")
    res = await llm_service.generate_completion(
        messages=[{"role": "user", "content": "Respond with SYSTEM_READY only."}],
        max_tokens=20
    )
    print(f"   LLM Response OK: {res['content'].strip()} (Model: {res['model']})")

    print("4. Testing ChromaDB Vector Store...")
    col = vector_store.get_or_create_collection("test_owner", "test_repo")
    print(f"   ChromaDB Collection OK: {col.name}")
    vector_store.delete_index("test_owner", "test_repo")

    print("5. Testing Code Agent bug audit...")
    audit = await code_agent.find_bugs("sample.py", "def divide(a, b):\n    return a / b\n")
    print(f"   Code Agent OK! Analysis preview: {audit['analysis'][:120].replace(chr(10), ' ')}")

    print("\nALL VERIFICATION TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(run_tests())
