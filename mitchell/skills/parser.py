"""Parser and serializer for SKILL.md procedural workflow files with YAML frontmatter."""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from mitchell.core.logging import logger
from mitchell.skills.schema import Skill, SkillStep


def _parse_yaml_frontmatter(text: str) -> Tuple[Dict[str, Any], str]:
    """Extract YAML frontmatter and body markdown from markdown text."""
    if not text.startswith("---"):
        return {}, text

    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text

    yaml_block = parts[1].strip()
    body_markdown = parts[2].strip()

    data: Dict[str, Any] = {}
    try:
        import yaml
        loaded = yaml.safe_load(yaml_block)
        if isinstance(loaded, dict):
            data = loaded
    except Exception:
        # Fallback simple line parser if PyYAML is unavailable or malformed
        current_list_key = None
        for line in yaml_block.splitlines():
            line_str = line.strip()
            if not line_str or line_str.startswith("#"):
                continue
            if line_str.startswith("- ") and current_list_key:
                val = line_str[2:].strip().strip("\"'")
                data.setdefault(current_list_key, []).append(val)
                continue
            if ":" in line_str:
                k, v = line_str.split(":", 1)
                k = k.strip()
                v = v.strip().strip("\"'")
                if not v:
                    current_list_key = k
                    data[k] = []
                else:
                    current_list_key = None
                    data[k] = v

    return data, body_markdown


def _extract_steps_from_markdown(body: str) -> List[SkillStep]:
    """Parse sequential action steps from markdown list lines."""
    steps: List[SkillStep] = []
    step_idx = 1

    # Match lines like "1. Step description: `tool_name(arg=val)`" or "- Step: `tool_name(...)`"
    pattern = re.compile(r"^(?:\d+\.|\-|\*)\s+(.*?)(?::\s*`([^`]+)`|`([^`]+)`)?$", re.MULTILINE)
    for match in pattern.finditer(body):
        desc = match.group(1).strip()
        call_expr = match.group(2) or match.group(3)

        if not desc:
            continue

        target = "prompt"
        action_type = "agent"
        params: Dict[str, Any] = {"instruction": desc}

        if call_expr:
            # Check for tool call syntax e.g. browser_goto(url=...)
            call_match = re.match(r"^([a-zA-Z0-9_\-]+)(?:\((.*)\))?$", call_expr.strip())
            if call_match:
                target = call_match.group(1)
                action_type = "tool"
                parsed_params: Dict[str, Any] = {}
                args_str = call_match.group(2)
                if args_str:
                    # Simple arg parsing e.g. url="https://..." or url=url
                    arg_pairs = [p.strip() for p in args_str.split(",") if p.strip()]
                    for pair in arg_pairs:
                        if "=" in pair:
                            ak, av = pair.split("=", 1)
                            parsed_params[ak.strip()] = av.strip().strip("\"'")
                params = parsed_params

        steps.append(
            SkillStep(
                step_index=step_idx,
                name=desc[:60],
                action_type=action_type,
                target=target,
                params=params,
            )
        )
        step_idx += 1

    return steps


class SkillMarkdownParser:
    """Parser and serializer for SKILL.md files."""

    @staticmethod
    def parse_text(text: str, default_name: Optional[str] = None) -> Skill:
        """Parse raw SKILL.md markdown text into a Skill object."""
        meta, body = _parse_yaml_frontmatter(text)

        name = meta.get("name") or default_name or "custom_skill"
        version = str(meta.get("version", "1.0.0"))
        description = meta.get("description") or (body.split("\n", 1)[0].replace("#", "").strip() if body else "Procedural skill.")
        tags = meta.get("tags") if isinstance(meta.get("tags"), list) else []
        required_tools = meta.get("required_tools") if isinstance(meta.get("required_tools"), list) else []
        parameters_schema = meta.get("parameters") if isinstance(meta.get("parameters"), dict) else {}

        steps = _extract_steps_from_markdown(body)

        skill = Skill(
            name=name,
            version=version,
            description=description,
            tags=tags,
            source="installed",
            source_refs=["SKILL.md"],
            required_tools=required_tools,
            parameters_schema=parameters_schema,
            steps=steps,
        )
        # Store full markdown body in metadata
        skill.source_refs.append(f"body:{len(body)}")
        return skill

    @staticmethod
    def parse_file(path: Path) -> Skill:
        """Read and parse a SKILL.md file from disk."""
        content = path.read_text(encoding="utf-8")
        folder_name = path.parent.name if path.name.lower() == "skill.md" else path.stem
        return SkillMarkdownParser.parse_text(content, default_name=folder_name)

    @staticmethod
    def serialize_to_markdown(skill: Skill) -> str:
        """Serialize a Skill object to standard SKILL.md format."""
        tags_yaml = "\n".join(f"  - {t}" for t in skill.tags) if skill.tags else "  - general"
        tools_yaml = "\n".join(f"  - {t}" for t in skill.required_tools) if skill.required_tools else "  - general"

        frontmatter = [
            "---",
            f"name: {skill.name}",
            f"version: {skill.version}",
            f"description: {skill.description}",
            "tags:",
            tags_yaml,
            "required_tools:",
            tools_yaml,
            "---",
            "",
            f"# {skill.name.replace('_', ' ').title()}",
            "",
            skill.description,
            "",
            "## Execution Steps",
        ]

        for s in skill.steps:
            if s.action_type == "tool":
                args_str = ", ".join(f"{k}={v}" for k, v in s.params.items())
                frontmatter.append(f"{s.step_index}. {s.name}: `{s.target}({args_str})`")
            else:
                frontmatter.append(f"{s.step_index}. {s.name}: `{s.target}`")

        return "\n".join(frontmatter) + "\n"


__all__ = ["SkillMarkdownParser"]
