from typing import Dict, Any, Optional
try:
    from ..services.llm_service import llm_service
except (ImportError, ValueError):
    try:
        from app.services.llm_service import llm_service
    except ImportError:
        from backend.app.services.llm_service import llm_service

class CodeAgent:
    """Agent responsible for code analysis, bug detection, optimization, and test generation."""

    async def explain_code(self, file_path: str, code: str, custom_instructions: Optional[str] = None) -> Dict[str, Any]:
        system_prompt = (
            "You are an expert software engineer and code reviewer. "
            "Your task is to explain the provided code clearly and thoroughly.\n"
            "Structure your explanation with:\n"
            "1. **High-Level Purpose**: What problem this file/function solves.\n"
            "2. **Key Components & Logic**: Breakdown of major classes, functions, algorithms.\n"
            "3. **Data Flow & Dependencies**: Inputs, outputs, external imports.\n"
            "4. **Edge Cases & Nuances**: Important implementation details to be aware of."
        )

        user_content = f"### File: `{file_path}`\n\n```\n{code}\n```"
        if custom_instructions:
            user_content += f"\n\n**Additional instructions:** {custom_instructions}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

        result = await llm_service.generate_completion(messages=messages, temperature=0.2)
        return {
            "action": "explain",
            "file_path": file_path,
            "analysis": result["content"],
            "model_used": result["model"]
        }

    async def find_bugs(self, file_path: str, code: str) -> Dict[str, Any]:
        system_prompt = (
            "You are an expert static analysis and security auditing AI agent. "
            "Analyze the given code for potential bugs, logical errors, security risks, "
            "memory/resource leaks, boundary errors, or unhandled exceptions.\n"
            "Format your response in Markdown with:\n"
            "1. **Executive Summary**: Overall health and risk rating (Low / Medium / High / Critical).\n"
            "2. **Detected Issues**: List each bug with:\n"
            "   - Severity level\n"
            "   - Location (approximate line or function)\n"
            "   - Why it is a problem\n"
            "   - How to fix it\n"
            "3. **Recommended Fixed Code**: Complete, corrected code snippet ready to paste."
        )

        user_content = f"Auditing file: `{file_path}`\n\n```\n{code}\n```"
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

        result = await llm_service.generate_completion(messages=messages, temperature=0.1)
        return {
            "action": "find_bugs",
            "file_path": file_path,
            "analysis": result["content"],
            "model_used": result["model"]
        }

    async def generate_unit_tests(self, file_path: str, code: str) -> Dict[str, Any]:
        system_prompt = (
            "You are a test-driven development (TDD) and QA specialist. "
            "Generate comprehensive, robust unit tests for the provided code.\n"
            "Requirements:\n"
            "1. Detect the programming language and use the standard testing framework (e.g. pytest/unittest for Python, Jest/Vitest for JS/TS, Go test for Go, etc.).\n"
            "2. Cover normal happy paths, boundary conditions, edge cases, and expected error handling / exceptions.\n"
            "3. Include mock setups if external network or database calls exist.\n"
            "4. Provide runnable test code with instructions on how to execute them."
        )

        user_content = f"Generate unit tests for file: `{file_path}`\n\n```\n{code}\n```"
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

        result = await llm_service.generate_completion(messages=messages, temperature=0.2)
        return {
            "action": "generate_tests",
            "file_path": file_path,
            "analysis": result["content"],
            "model_used": result["model"]
        }

    async def optimize_code(self, file_path: str, code: str) -> Dict[str, Any]:
        system_prompt = (
            "You are a performance engineering and refactoring expert. "
            "Analyze the given code for performance bottlenecks, algorithmic complexity, "
            "readability, and modern language idioms.\n"
            "Provide:\n"
            "1. Complexity Analysis (Time and Space before vs after)\n"
            "2. Specific Bottlenecks & Refactoring Opportunities\n"
            "3. Optimized Code Solution with explanation of enhancements"
        )

        user_content = f"Optimize file: `{file_path}`\n\n```\n{code}\n```"
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

        result = await llm_service.generate_completion(messages=messages, temperature=0.2)
        return {
            "action": "optimize",
            "file_path": file_path,
            "analysis": result["content"],
            "model_used": result["model"]
        }

code_agent = CodeAgent()
