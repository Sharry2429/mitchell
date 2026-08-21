"""Persistent Skill Library for storing, indexing, and retrieving procedural workflows."""

import json
from typing import Any, Dict, List, Optional

from mitchell.core.event_log import event_log
from mitchell.core.logging import logger
from mitchell.memory.database import memory_db
from mitchell.memory.vector_store import vector_store
from mitchell.skills.schema import Skill, SkillStep


class SkillLibrary:
    """Persistent store and semantic search catalog for Mitchell Skills."""

    def __init__(self) -> None:
        self.db = memory_db
        self.vector_store = vector_store
        self._seed_builtin_skills()

    def _seed_builtin_skills(self) -> None:
        """Seed foundational multi-pillar skills if library is empty."""
        if self.list_skills():
            return

        # 1. Web research & snapshot
        skill_web = Skill(
            name="web_research_and_snapshot",
            description="Navigate to a web URL, inspect page content, and capture a text snapshot.",
            tags=["browser", "research", "web"],
            source="builtin",
            required_tools=["browser_goto", "browser_snapshot"],
            parameters_schema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Target website URL"}
                },
                "required": ["url"],
            },
            steps=[
                SkillStep(
                    step_index=1,
                    name="navigate_to_page",
                    action_type="tool",
                    target="browser_goto",
                    params={"url": "{{url}}"},
                    on_fail="abort",
                ),
                SkillStep(
                    step_index=2,
                    name="extract_snapshot",
                    action_type="tool",
                    target="browser_snapshot",
                    params={},
                    on_fail="ignore",
                ),
            ],
            confidence=0.95,
        )
        self.save_skill(skill_web)

        # 2. Windows notepad note creator
        skill_win = Skill(
            name="windows_quick_notepad",
            description="Launch Notepad and write notes onto desktop.",
            tags=["windows", "desktop", "notes"],
            source="builtin",
            required_tools=["windows_launch_app", "windows_type_text"],
            parameters_schema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to write into Notepad"}
                },
                "required": ["text"],
            },
            steps=[
                SkillStep(
                    step_index=1,
                    name="launch_notepad",
                    action_type="tool",
                    target="windows_launch_app",
                    params={"cmd": "notepad.exe"},
                    on_fail="abort",
                ),
                SkillStep(
                    step_index=2,
                    name="type_notes",
                    action_type="tool",
                    target="windows_type_text",
                    params={"text": "{{text}}", "title": "Notepad"},
                    on_fail="retry",
                ),
            ],
            confidence=0.9,
        )
        self.save_skill(skill_win)

    def save_skill(self, skill: Skill) -> Skill:
        """Persist or update a skill in the SQLite database and index in vector store."""
        skill_dict = skill.model_dump(mode="json")
        skill_json = json.dumps(skill_dict)
        tags_json = json.dumps(skill.tags)

        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO skills (
                    id, name, version, description, tags_json, source, skill_json,
                    confidence, executions, successes, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(name) DO UPDATE SET
                    version = excluded.version,
                    description = excluded.description,
                    tags_json = excluded.tags_json,
                    source = excluded.source,
                    skill_json = excluded.skill_json,
                    confidence = excluded.confidence,
                    executions = excluded.executions,
                    successes = excluded.successes,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    skill.id,
                    skill.name,
                    skill.version,
                    skill.description,
                    tags_json,
                    skill.source,
                    skill_json,
                    skill.confidence,
                    skill.stats.executions,
                    skill.stats.successes,
                ),
            )
            conn.commit()

        # Vector Index
        self.vector_store.index(
            entity_type="skill",
            entity_id=skill.name,
            text=f"Skill: {skill.name} | Tags: {', '.join(skill.tags)} | Description: {skill.description}",
        )

        logger.info("Saved Skill '{}' (v{}) into library", skill.name, skill.version)
        event_log.log_event(
            "skill_saved",
            source="skill_library",
            data={"skill_name": skill.name, "version": skill.version, "source": skill.source},
        )
        return skill

    def get_skill(self, name_or_id: str) -> Optional[Skill]:
        """Retrieve skill by name or id."""
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT skill_json FROM skills WHERE name = ? OR id = ?",
                (name_or_id, name_or_id),
            )
            row = cursor.fetchone()
            if not row:
                return None
            try:
                data = json.loads(row["skill_json"])
                return Skill.model_validate(data)
            except Exception as e:
                logger.error("Failed to deserialize skill '{}': {}", name_or_id, e)
                return None

    def list_skills(self) -> List[Skill]:
        """List all registered skills."""
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT skill_json FROM skills ORDER BY name")
            rows = cursor.fetchall()

        skills: List[Skill] = []
        for row in rows:
            try:
                skills.append(Skill.model_validate(json.loads(row["skill_json"])))
            except Exception:
                continue
        return skills

    def search_skills(self, query: str, top_k: int = 5) -> List[Skill]:
        """Find matching skills using vector similarity search."""
        matches = self.vector_store.search(query=query, entity_type="skill", top_k=top_k)
        skills: List[Skill] = []
        for match in matches:
            skill = self.get_skill(match["entity_id"])
            if skill:
                skills.append(skill)
        return skills

    def update_stats(self, name: str, success: bool, duration_s: float) -> None:
        """Update runtime success rate and duration for a skill."""
        skill = self.get_skill(name)
        if not skill:
            return

        old_execs = skill.stats.executions
        skill.stats.executions += 1
        if success:
            skill.stats.successes += 1
        else:
            skill.stats.failures += 1

        skill.stats.avg_duration_s = round(
            (skill.stats.avg_duration_s * old_execs + duration_s) / skill.stats.executions,
            2,
        )

        # Update calibrated confidence
        ratio = skill.stats.successes / skill.stats.executions
        skill.confidence = round(0.5 + 0.5 * ratio, 2)

        self.save_skill(skill)


skill_library = SkillLibrary()

__all__ = ["SkillLibrary", "skill_library"]
