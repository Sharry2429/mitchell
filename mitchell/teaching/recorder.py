"""Action recorder and parameter generalization engine for teaching mode."""

import re
from typing import Any, Dict, List, Tuple
from pydantic import BaseModel, Field


class RecordedAction(BaseModel):
    """Single observed user action during teaching."""

    index: int
    action_type: str  # tool | agent | command
    target: str
    params: Dict[str, Any]
    timestamp: float


class ActionRecorder:
    """Records human demonstrations and automatically parameterizes constants into template variables."""

    def __init__(self) -> None:
        self.actions: List[RecordedAction] = []

    def add_action(self, action_type: str, target: str, params: Dict[str, Any], timestamp: float) -> RecordedAction:
        """Record an observed action."""
        act = RecordedAction(
            index=len(self.actions) + 1,
            action_type=action_type,
            target=target,
            params=params,
            timestamp=timestamp,
        )
        self.actions.append(act)
        return act

    def generalize_parameters(self) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Analyze recorded actions and parameterize dynamic values (URLs, search terms, text inputs).
        Returns parameterized step dicts and parameter schema.
        """
        parameterized_steps: List[Dict[str, Any]] = []
        schema_props: Dict[str, Any] = {}
        required_props: List[str] = []

        for act in self.actions:
            step_params = dict(act.params)
            for k, v in act.params.items():
                if isinstance(v, str) and len(v) > 0:
                    if v.startswith("http://") or v.startswith("https://"):
                        var_name = "url"
                        step_params[k] = f"{{{{{var_name}}}}}"
                        schema_props[var_name] = {"type": "string", "description": "Target URL"}
                        if var_name not in required_props:
                            required_props.append(var_name)
                    elif k in ("text", "query", "message", "input") and len(v.split()) > 0:
                        var_name = k
                        step_params[k] = f"{{{{{var_name}}}}}"
                        schema_props[var_name] = {"type": "string", "description": f"Input {k}"}
                        if var_name not in required_props:
                            required_props.append(var_name)

            parameterized_steps.append({
                "step_index": act.index,
                "name": f"{act.target}_step",
                "action_type": act.action_type,
                "target": act.target,
                "params": step_params,
                "on_fail": "abort",
            })

        param_schema = {
            "type": "object",
            "properties": schema_props,
            "required": required_props,
        }

        return parameterized_steps, param_schema

    def clear(self) -> None:
        """Reset recorded actions."""
        self.actions.clear()


__all__ = ["RecordedAction", "ActionRecorder"]
