from typing import Dict, Any, List, Optional
try:
    from ..services.llm_service import llm_service
except (ImportError, ValueError):
    try:
        from app.services.llm_service import llm_service
    except ImportError:
        from backend.app.services.llm_service import llm_service

class DocumentationAgent:
    """Agent responsible for README generation, API documentation, and architecture diagrams."""

    async def generate_readme(
        self,
        owner: str,
        repo: str,
        description: Optional[str] = None,
        file_tree: Optional[List[str]] = None,
        sample_snippets: Optional[str] = None
    ) -> Dict[str, Any]:
        system_prompt = (
            "You are a technical writer and developer advocate who crafts world-class, "
            "production-grade GitHub README.md documents.\n"
            "Requirements:\n"
            "- Include modern shields.io badges (license, python/node version, stars, issues).\n"
            "- Catchy project banner/title and clear value proposition.\n"
            "- Key Features (bulleted with emojis).\n"
            "- Architecture & Directory Tree.\n"
            "- Quick Start & Installation instructions.\n"
            "- Configuration & Environment variables table.\n"
            "- Usage examples with code snippets.\n"
            "- Contributing guidelines & License."
        )

        tree_str = "\n".join(file_tree[:40]) if file_tree else "Standard project structure"
        user_content = (
            f"Generate a full README.md for GitHub repository:\n"
            f"- **Repository:** `{owner}/{repo}`\n"
            f"- **Description:** {description or 'Open source software project'}\n"
            f"- **File Tree Structure:**\n```\n{tree_str}\n```\n"
        )
        if sample_snippets:
            user_content += f"\n- **Sample Code Snippets:**\n```\n{sample_snippets[:2000]}\n```\n"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

        result = await llm_service.generate_completion(messages=messages, temperature=0.3)
        return {
            "doc_type": "readme",
            "markdown_content": result["content"],
            "model_used": result["model"]
        }

    async def generate_architecture_summary(
        self,
        owner: str,
        repo: str,
        file_tree: List[str],
        rag_context: Optional[str] = None
    ) -> Dict[str, Any]:
        system_prompt = (
            "You are a Principal Software Architect. Analyze the repository file structure and "
            "code context to produce an Architecture Blueprint in Markdown.\n"
            "Include:\n"
            "1. Architectural Pattern (e.g. Microservices, Clean Architecture, Layered MVC, Agentic RAG).\n"
            "2. Component Diagram using valid GitHub Mermaid syntax (````mermaid ... ````).\n"
            "3. Data Flow & Request Lifecycle.\n"
            "4. Tech Stack Breakdown & Core Dependencies."
        )

        tree_str = "\n".join(file_tree[:50])
        user_content = (
            f"Analyze architecture for `{owner}/{repo}`:\n"
            f"Files:\n```\n{tree_str}\n```\n"
        )
        if rag_context:
            user_content += f"\nCode Context:\n```\n{rag_context[:3000]}\n```"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

        result = await llm_service.generate_completion(messages=messages, temperature=0.2)
        return {
            "doc_type": "architecture",
            "markdown_content": result["content"],
            "model_used": result["model"]
        }

doc_agent = DocumentationAgent()
