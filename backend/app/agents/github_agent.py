from typing import List, Dict, Any, Optional, AsyncGenerator
try:
    from ..services.llm_service import llm_service
    from ..rag.vectorstore import vector_store
    from ..services.context_manager import context_manager
except (ImportError, ValueError):
    try:
        from app.services.llm_service import llm_service
        from app.rag.vectorstore import vector_store
        from app.services.context_manager import context_manager
    except ImportError:
        from backend.app.services.llm_service import llm_service
        from backend.app.rag.vectorstore import vector_store
        from backend.app.services.context_manager import context_manager

class GitHubAgent:
    """Core GitHub AI Assistant Agent for answering questions about repositories, code, architecture, and tech stacks."""

    def _build_context_prompt(
        self,
        target_owner: str,
        target_repo: str,
        enriched_context: Dict[str, Any],
        rag_snippets: List[Dict[str, Any]],
        current_file_path: Optional[str] = None,
        current_file_content: Optional[str] = None
    ) -> str:
        prompt_parts = [
            f"You are the GitHub AI Assistant. You have full context and memory of all repositories in the user's GitHub account.",
            f"You are currently analyzing and answering questions for repository `{target_owner}/{target_repo}`.",
            "You have deep knowledge of this codebase, its architecture, functions, dependencies, and file layout.",
            "",
            "CORE INSTRUCTIONS:",
            "- If the user asks what was used for frontend, backend, database, styling, or libraries in this repo, provide an authoritative, detailed answer citing the exact frameworks (e.g. Next.js, React, Tailwind CSS, Vite, TypeScript, FastAPI, etc.) found in `package.json`, `requirements.txt`, or config files.",
            "- Always reference specific file paths (e.g. `package.json`, `next.config.ts`, `src/app/page.tsx`) and line numbers whenever possible.",
            "- When code changes, fixes, or explanations are needed, provide clear code snippets with proper language identifiers.",
            "- Be concise, accurate, and direct."
        ]

        # Injected Global Repository Catalog (Memory of all repos)
        global_catalog = enriched_context.get("global_catalog_summary", "")
        if global_catalog:
            prompt_parts.append(
                f"\n--- User's GitHub Repositories Memory Catalog ---\n"
                f"{global_catalog[:3000]}"
            )

        # Injected Tech Stack Summary for Target Repo
        tech_stack = enriched_context.get("tech_stack", {})
        if tech_stack:
            tech_lines = []
            if tech_stack.get("frontend"):
                tech_lines.append(f"- Frontend: {', '.join(tech_stack['frontend'])}")
            if tech_stack.get("backend"):
                tech_lines.append(f"- Backend: {', '.join(tech_stack['backend'])}")
            if tech_stack.get("build_tools"):
                tech_lines.append(f"- Build Tools: {', '.join(tech_stack['build_tools'])}")
            if tech_stack.get("primary_languages"):
                tech_lines.append(f"- Languages: {', '.join(tech_stack['primary_languages'])}")
            if tech_lines:
                prompt_parts.append(
                    f"\n--- Detected Tech Stack for `{target_owner}/{target_repo}` ---\n" + "\n".join(tech_lines)
                )

        # Injected Key Files (e.g. package.json, next.config, requirements.txt)
        key_files = enriched_context.get("key_files", {})
        if key_files:
            prompt_parts.append("\n--- Key Project Configuration & Manifest Files ---")
            for filename, content in key_files.items():
                prompt_parts.append(f"\n[File: `{filename}`]:\n```\n{content[:2500]}\n```")

        # Injected File Tree
        file_paths = enriched_context.get("file_paths", [])
        if file_paths:
            files_display = "\n".join(f"- {p}" for p in file_paths[:60])
            prompt_parts.append(f"\n--- Repository File Tree (Total {enriched_context.get('file_count', len(file_paths))} files) ---\n{files_display}")

        # Active file if open
        if current_file_path and current_file_content:
            prompt_parts.append(
                f"\n--- Currently Active File in Editor: `{current_file_path}` ---\n```\n{current_file_content[:4000]}\n```"
            )

        # ChromaDB RAG Snippets
        if rag_snippets:
            prompt_parts.append("\n--- Relevant Codebase Context (Retrieved from ChromaDB) ---")
            for idx, item in enumerate(rag_snippets, 1):
                prompt_parts.append(
                    f"\n[Snippet #{idx}] File: `{item['file_path']}` (Lines {item['start_line']}-{item['end_line']}, Relevance: {item['score']}):\n"
                    f"```\n{item['snippet']}\n```"
                )

        return "\n".join(prompt_parts)

    async def chat(
        self,
        owner: Optional[str] = None,
        repo: Optional[str] = None,
        message: str = "",
        history: Optional[List[Dict[str, str]]] = None,
        current_file_path: Optional[str] = None,
        current_file_content: Optional[str] = None,
        use_rag: bool = True,
        model: Optional[str] = None,
        branch: Optional[str] = "main"
    ) -> Dict[str, Any]:
        """Synchronous chat with multi-repo context and intelligent repository switching."""
        # 1. Initialize context memory catalog if needed
        await context_manager.get_all_repositories()

        # 2. Identify target repository from user query, history, or current selection
        target_repo_info = context_manager.find_target_repository(
            query=message,
            current_owner=owner,
            current_repo=repo,
            history=history
        )

        repo_switched = False
        target_owner = owner or ""
        target_repo = repo or ""

        if target_repo_info:
            target_full = target_repo_info.get("full_name", "")
            if "/" in target_full:
                t_owner, t_repo = target_full.split("/", 1)
                if owner and repo and (t_owner.lower() != owner.lower() or t_repo.lower() != repo.lower()):
                    repo_switched = True
                elif not owner or not repo:
                    repo_switched = True
                target_owner = t_owner
                target_repo = t_repo

        # 3. Retrieve enriched context (file tree, manifest contents, tech stack, catalog)
        enriched_context = {}
        rag_snippets = []
        if target_owner and target_repo:
            enriched_context = await context_manager.build_enriched_context(
                target_owner=target_owner,
                target_repo=target_repo,
                query=message,
                branch=branch
            )
            if use_rag:
                rag_snippets = vector_store.search(target_owner, target_repo, message, n_results=4)

        system_instruction = self._build_context_prompt(
            target_owner, target_repo, enriched_context, rag_snippets, current_file_path, current_file_content
        )

        messages = [{"role": "system", "content": system_instruction}]

        if history:
            for turn in history[-8:]:
                role = turn.get("role", "user")
                content = turn.get("content", "")
                if role in ("user", "assistant"):
                    messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": message})

        result = await llm_service.generate_completion(
            messages=messages,
            model=model,
            temperature=0.2
        )

        return {
            "answer": result["content"],
            "sources": rag_snippets,
            "model_used": result["model"],
            "active_repo": f"{target_owner}/{target_repo}" if (target_owner and target_repo) else None,
            "repo_switched": repo_switched,
            "switched_repo": target_repo_info if repo_switched else None,
            "detected_repo": f"{target_owner}/{target_repo}" if (target_owner and target_repo) else None
        }

    async def stream_chat(
        self,
        owner: Optional[str] = None,
        repo: Optional[str] = None,
        message: str = "",
        history: Optional[List[Dict[str, str]]] = None,
        current_file_path: Optional[str] = None,
        current_file_content: Optional[str] = None,
        use_rag: bool = True,
        model: Optional[str] = None,
        branch: Optional[str] = "main"
    ) -> AsyncGenerator[str, None]:
        """Streaming chat endpoint for real-time typing effect with enriched context."""
        await context_manager.get_all_repositories()

        target_repo_info = context_manager.find_target_repository(
            query=message,
            current_owner=owner,
            current_repo=repo,
            history=history
        )

        target_owner = owner or ""
        target_repo = repo or ""

        if target_repo_info:
            target_full = target_repo_info.get("full_name", "")
            if "/" in target_full:
                t_owner, t_repo = target_full.split("/", 1)
                target_owner = t_owner
                target_repo = t_repo

        enriched_context = {}
        rag_snippets = []
        if target_owner and target_repo:
            enriched_context = await context_manager.build_enriched_context(
                target_owner=target_owner,
                target_repo=target_repo,
                query=message,
                branch=branch
            )
            if use_rag:
                rag_snippets = vector_store.search(target_owner, target_repo, message, n_results=4)

        system_instruction = self._build_context_prompt(
            target_owner, target_repo, enriched_context, rag_snippets, current_file_path, current_file_content
        )

        messages = [{"role": "system", "content": system_instruction}]
        if history:
            for turn in history[-8:]:
                role = turn.get("role", "user")
                content = turn.get("content", "")
                if role in ("user", "assistant"):
                    messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": message})

        async for chunk in llm_service.stream_completion(messages=messages, model=model, temperature=0.2):
            yield chunk


    async def analyze_issue_or_pr(
        self,
        owner: str,
        repo: str,
        item: Dict[str, Any],
        rag_snippets: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Analyzes a GitHub issue or PR, diagnosing the problem and proposing solutions."""
        is_pr = item.get("is_pr", False)
        item_type = "Pull Request" if is_pr else "Issue"

        system_prompt = (
            f"You are a Senior Staff Engineer reviewing a GitHub {item_type} for `{owner}/{repo}`.\n"
            "Analyze the title, body, and comments.\n"
            "Provide:\n"
            "1. **Executive Summary**: Clear problem diagnosis or PR intention.\n"
            "2. **Impact & Root Cause**: Where in the codebase this occurs.\n"
            "3. **Proposed Action / Implementation Plan**: Concrete code changes or review feedback.\n"
            "4. **Verification & Testing Steps**: How to test the change."
        )

        user_content = (
            f"Reviewing {item_type} #{item.get('number')}: **{item.get('title')}**\n"
            f"State: {item.get('state')}\n"
            f"Author: {item.get('user', {}).get('login', 'unknown')}\n\n"
            f"Description:\n```\n{item.get('body') or 'No description provided.'}\n```\n"
        )

        if rag_snippets:
            user_content += "\nRelevant Code Context from Repo:\n"
            for snip in rag_snippets[:3]:
                user_content += f"- `{snip['file_path']}`: {snip['snippet'][:500]}\n"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

        result = await llm_service.generate_completion(messages=messages, temperature=0.2)
        return {
            "number": item.get("number"),
            "title": item.get("title"),
            "analysis": result["content"],
            "model_used": result["model"]
        }

github_agent = GitHubAgent()
