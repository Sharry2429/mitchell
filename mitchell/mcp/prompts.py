"""MCP Prompts Provider for Mitchell AI.

Exposes pre-engineered system prompts for Karpathy Engineering Rigor,
Autonomous Takeover, Deep Research, and Procedural Skill Extraction.
"""

from typing import Any, Dict, List, Optional

from mitchell.core.llm import KARPATHY_SYSTEM_PROMPT
from mitchell.mcp.protocol import MCPPrompt, MCPPromptArgument


class MCPPromptManager:
    """Manages MCP prompt templates for Mitchell AI."""

    def list_prompts(self) -> List[MCPPrompt]:
        """Return list of standard MCP prompts."""
        return [
            MCPPrompt(
                name="karpathy_principles",
                description="Mitchell's core engineering principles: Think Before Acting, Simplicity First, Surgical Changes, Goal-Driven Verification.",
                arguments=[],
            ),
            MCPPrompt(
                name="autonomous_takeover",
                description="Instructions for taking over an entire software project or workflow autonomously with checkpoint approval gates.",
                arguments=[
                    MCPPromptArgument(name="goal", description="High level goal of the project", required=True),
                ],
            ),
            MCPPrompt(
                name="deep_research",
                description="Perplexity-style multi-source scientific and codebase research prompt.",
                arguments=[
                    MCPPromptArgument(name="topic", description="Research subject", required=True),
                ],
            ),
        ]

    def get_prompt(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Render prompt template."""
        args = arguments or {}
        if name == "karpathy_principles":
            return {
                "description": "Mitchell Karpathy Principles System Prompt",
                "messages": [
                    {"role": "system", "content": {"type": "text", "text": KARPATHY_SYSTEM_PROMPT}}
                ],
            }

        elif name == "autonomous_takeover":
            goal = args.get("goal", "Complete the requested project")
            prompt_text = f"""You are Mitchell operating in Autonomous Takeover Mode.
Goal: {goal}

Guidelines:
1. Inspect the workspace, identify key constraints, and establish clear milestones.
2. Coordinate with coding agents (Claude Code, Grok, Antigravity) when necessary.
3. Test every change before marking milestone as complete.
4. Stop for human approval only at designated critical safety checkpoints.
"""
            return {
                "description": f"Autonomous Takeover for: {goal}",
                "messages": [
                    {"role": "system", "content": {"type": "text", "text": prompt_text}}
                ],
            }

        elif name == "deep_research":
            topic = args.get("topic", "General Topic")
            prompt_text = f"""Execute deep, multi-source research on: {topic}
1. Decompose topic into 3-5 search sub-queries.
2. Crawl and extract factual evidence.
3. Reconcile conflicting findings.
4. Format final response with inline citations [1], [2] referencing sources.
"""
            return {
                "description": f"Deep Research Prompt for: {topic}",
                "messages": [
                    {"role": "system", "content": {"type": "text", "text": prompt_text}}
                ],
            }

        return None


mcp_prompt_manager = MCPPromptManager()

__all__ = ["MCPPromptManager", "mcp_prompt_manager"]
