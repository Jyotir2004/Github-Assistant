from typing import List, Dict, Any, Optional, AsyncGenerator
try:
    from ..services.llm_service import llm_service
    from ..rag.vectorstore import vector_store
except (ImportError, ValueError):
    try:
        from app.services.llm_service import llm_service
        from app.rag.vectorstore import vector_store
    except ImportError:
        from backend.app.services.llm_service import llm_service
        from backend.app.rag.vectorstore import vector_store

class GitHubAgent:
    """Core GitHub AI Assistant Agent for answering questions about the repository, PRs, and issues."""

    def _build_context_prompt(
        self,
        owner: str,
        repo: str,
        rag_snippets: List[Dict[str, Any]],
        current_file_path: Optional[str] = None,
        current_file_content: Optional[str] = None
    ) -> str:
        prompt_parts = [
            f"You are the GitHub AI Assistant for the repository `{owner}/{repo}`.",
            "You have deep knowledge of this codebase, its architecture, functions, and bugs.",
            "When answering questions:",
            "- Always reference specific files and line numbers whenever applicable (e.g. `[src/auth.py:L24-40]`).",
            "- If code changes or fixes are needed, provide precise code blocks with the appropriate language identifier.",
            "- Be concise, accurate, and direct. Avoid generic boilerplate.",
            "- If information is not found in the provided context, state clearly what is missing."
        ]

        # Add active file context if user is viewing a file
        if current_file_path and current_file_content:
            prompt_parts.append(
                f"\n--- Currently Active File: `{current_file_path}` ---\n```\n{current_file_content[:4000]}\n```"
            )

        # Add RAG retrieved chunks
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
        owner: str,
        repo: str,
        message: str,
        history: Optional[List[Dict[str, str]]] = None,
        current_file_path: Optional[str] = None,
        current_file_content: Optional[str] = None,
        use_rag: bool = True,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Synchronous chat with RAG retrieval."""
        rag_snippets = []
        if use_rag:
            # Query vector store for top 4 relevant snippets
            rag_snippets = vector_store.search(owner, repo, message, n_results=4)

        system_instruction = self._build_context_prompt(
            owner, repo, rag_snippets, current_file_path, current_file_content
        )

        messages = [{"role": "system", "content": system_instruction}]

        # Append limited history (last 8 turns)
        if history:
            for turn in history[-8:]:
                role = turn.get("role", "user")
                content = turn.get("content", "")
                if role in ("user", "assistant"):
                    messages.append({"role": role, "content": content})

        # Append latest user query
        messages.append({"role": "user", "content": message})

        result = await llm_service.generate_completion(
            messages=messages,
            model=model,
            temperature=0.2
        )

        return {
            "answer": result["content"],
            "sources": rag_snippets,
            "model_used": result["model"]
        }

    async def stream_chat(
        self,
        owner: str,
        repo: str,
        message: str,
        history: Optional[List[Dict[str, str]]] = None,
        current_file_path: Optional[str] = None,
        current_file_content: Optional[str] = None,
        use_rag: bool = True,
        model: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Streaming chat endpoint for real-time typing effect."""
        rag_snippets = []
        if use_rag:
            rag_snippets = vector_store.search(owner, repo, message, n_results=4)

        system_instruction = self._build_context_prompt(
            owner, repo, rag_snippets, current_file_path, current_file_content
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
