"""Mitchell Self-Evolution Subsystem — Introspection, Synthesis, Self-Patching & Testing."""

from mitchell.evolution.engine import SelfEvolutionEngine, evolution_engine
from mitchell.evolution.inspector import CodeInspector, code_inspector
from mitchell.evolution.patcher import SelfPatcher, self_patcher
from mitchell.evolution.synthesizer import ToolSynthesizer, tool_synthesizer

__all__ = [
    "CodeInspector", "code_inspector",
    "ToolSynthesizer", "tool_synthesizer",
    "SelfPatcher", "self_patcher",
    "SelfEvolutionEngine", "evolution_engine",
]
