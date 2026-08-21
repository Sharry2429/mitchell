"""Skill schema definition for Mitchell procedural workflows."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class SkillStep(BaseModel):
    """Single executable step within a Skill."""

    step_index: int = Field(default=1, description="Execution sequence index")
    name: str = Field(..., description="Short name of the step")
    action_type: Literal["tool", "agent", "python", "fast_intent"] = Field(
        default="tool",
        description="Execution target type",
    )
    target: str = Field(..., description="Tool name, Hive agent ID, or function to invoke")
    params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters with template substitution support (e.g. {{url}}, {{query}})",
    )
    on_fail: Literal["abort", "retry", "fallback", "ignore"] = Field(
        default="abort",
        description="Policy if step execution fails",
    )
    fallback_target: Optional[str] = Field(
        default=None,
        description="Alternative tool or action if on_fail is fallback",
    )


class SkillStats(BaseModel):
    """Runtime statistics for a skill."""

    executions: int = Field(default=0)
    successes: int = Field(default=0)
    failures: int = Field(default=0)
    avg_duration_s: float = Field(default=0.0)


class Skill(BaseModel):
    """Complete executable Mitchell procedural skill."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = Field(..., description="Unique skill name identifier")
    version: str = Field(default="1.0.0", description="Semver version string")
    description: str = Field(..., description="Detailed description of what the skill accomplishes")
    tags: List[str] = Field(default_factory=list, description="Categorization tags")
    source: Literal["organic", "teaching", "installed", "builtin"] = Field(
        default="organic",
        description="Origin of the skill",
    )
    source_refs: List[str] = Field(default_factory=list, description="Reference URLs, docs, or prompts")
    preconditions: List[str] = Field(default_factory=list, description="Preconditions required before run")
    required_tools: List[str] = Field(default_factory=list, description="Required tool names")
    parameters_schema: Dict[str, Any] = Field(
        default_factory=dict,
        description="JSON schema for skill input parameters",
    )
    steps: List[SkillStep] = Field(default_factory=list, description="Sequential steps to execute")
    success_criteria: List[str] = Field(default_factory=list, description="Verifiable success indicators")
    confidence: float = Field(default=0.8, description="Skill confidence rating")
    stats: SkillStats = Field(default_factory=SkillStats)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


__all__ = ["Skill", "SkillStep", "SkillStats"]
