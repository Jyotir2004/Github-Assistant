import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.services.context_manager import context_manager
from app.agents.github_agent import github_agent

async def run_context_tests():
    print("==================================================")
    print(" Testing Multi-Repository Context & Memory Manager")
    print("==================================================")

    # 1. Initialize catalog
    print("\n1. Initializing repository catalog & memory store...")
    await context_manager.initialize()
    repos = await context_manager.get_all_repositories()
    print(f"   Catalog initialized with {len(repos)} repositories.")
    assert len(repos) > 0, "No repositories loaded into memory catalog"

    # 2. Test target repo matching
    print("\n2. Testing intelligent repository intent resolution...")
    
    test_queries = [
        ("what i have used for my_portfolio frontend", "Jyotir2004/my_portfolio"),
        ("what frontend does my-portfolio use?", "Jyotir2004/my_portfolio"),
        ("tell me about ATM-related-task", "Jyotir2004/ATM-related-task"),
        ("how does RAG-Chatbot work?", "Jyotir2004/RAG-Chatbot"),
        ("tell me about FLIPKART-SCRAPPER", "Jyotir2004/FLIPKART-SCRAPPER"),
    ]

    for q, expected in test_queries:
        target = context_manager.find_target_repository(q, current_owner="Jyotir2004", current_repo="Github-Assistant")
        found = target.get("full_name") if target else None
        print(f"   Query: '{q}' -> Matched: {found}")
        assert found == expected, f"Expected {expected}, got {found}"

    # 3. Test tech stack extraction & enriched context
    print("\n3. Testing deep tech stack extraction for my_portfolio...")
    ctx = await context_manager.build_enriched_context("Jyotir2004", "my_portfolio", "what i have used for my_portfolio frontend")
    tech_stack = ctx.get("tech_stack", {})
    print(f"   Frontend detected: {tech_stack.get('frontend')}")
    print(f"   Backend detected:  {tech_stack.get('backend')}")
    print(f"   Languages:         {tech_stack.get('primary_languages')}")
    print(f"   Files analyzed:    {ctx.get('file_count')}")

    assert any("next" in f.lower() for f in tech_stack.get("frontend", [])), "Next.js should be detected in frontend"
    assert any("tailwind" in f.lower() for f in tech_stack.get("frontend", [])), "Tailwind CSS should be detected in frontend"

    # 4. Test end-to-end chat with auto repo switching
    print("\n4. Testing end-to-end agent chat with auto repo switching...")
    chat_res = await github_agent.chat(
        owner="Jyotir2004",
        repo="Github-Assistant",
        message="what i have used for my_portfolio frontend"
    )

    print(f"   Repo switched:  {chat_res.get('repo_switched')}")
    print(f"   Active repo:    {chat_res.get('active_repo')}")
    print(f"   Model used:     {chat_res.get('model_used')}")
    assert chat_res.get("repo_switched") is True, "repo_switched should be True"
    assert chat_res.get("active_repo") == "Jyotir2004/my_portfolio", "active_repo should be Jyotir2004/my_portfolio"
    answer_text = chat_res.get("answer", "").lower()
    assert "next" in answer_text, "Answer should mention Next.js"
    assert "tailwind" in answer_text, "Answer should mention Tailwind"

    print("\n==================================================")
    print(" ALL MULTI-REPO CONTEXT & MEMORY TESTS PASSED SUCCESSFUL!")
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(run_context_tests())
