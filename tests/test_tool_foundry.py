"""
Phase 5 — Tool Foundry: detect -> draft -> TEST -> register -> callable.

Deterministic (no Hermes spawn): gap detection from the episodic log, the
Phase 1 test gate (failing tool must not register), and registration makes the
tool callable. The live Hermes-drafted loop is exercised in scripts/prove_foundry.
"""
import json
import os

import pytest

from mitchell.core import memory, memory_store, tool_registry


@pytest.fixture
def iso_db(tmp_path, monkeypatch):
    monkeypatch.setattr(memory_store, "MEMORY_DIR", tmp_path)
    monkeypatch.setattr(memory_store, "DB_PATH", tmp_path / "m.db")
    memory_store.init_db()
    return tmp_path


@pytest.fixture
def iso_foundry(tmp_path, monkeypatch):
    monkeypatch.setattr(tool_registry, "FOUNDRY_DIR", tmp_path / "foundry")
    monkeypatch.setattr(tool_registry, "REGISTRY_FILE", tmp_path / "foundry" / "registry.json")
    return tmp_path


def test_detect_gap_from_episodic_log(iso_db):
    # A repeated step pattern (capability kept hand-rolled) is detected as a gap.
    for _ in range(4):
        memory.log_episode("t", "step", "PASS step: parse csv line", verified=True, pattern_key="parse_csv_line")
    assert tool_registry.detect_gap(min_freq=3) == "parse_csv_line"


def test_detect_gap_respects_min_frequency(iso_db):
    for _ in range(2):
        memory.log_episode("t", "step", "x", verified=True, pattern_key="rare_thing")
    assert tool_registry.detect_gap(min_freq=3) is None


def test_test_tool_gate(tmp_path):
    # Passing test -> gate open; failing test -> gate closed.
    good = tmp_path / "good"; good.mkdir()
    (good / "tool.py").write_text("def t(): return 1\n")
    (good / "test_tool.py").write_text("from tool import t\n\ndef test_t(): assert t()==1\n")
    assert tool_registry.test_tool(str(good))["ok"] is True

    bad = tmp_path / "bad"; bad.mkdir()
    (bad / "tool.py").write_text("def t(): return 1\n")
    (bad / "test_tool.py").write_text("def test_wrong(): assert False\n")
    assert tool_registry.test_tool(str(bad))["ok"] is False


def test_register_only_after_gate_and_become_callable(iso_foundry):
    src = iso_foundry / "src"; src.mkdir()
    (src / "tool.py").write_text("def slugify(text: str) -> str:\n    return text.strip().lower().replace(' ', '-')\n")
    res = tool_registry.test_tool(str(src))
    # No test file -> pytest exits nonzero -> gate closed -> nothing registered.
    assert res["ok"] is False
    assert tool_registry.register_tool("slugify", str(src), "slugify helper") is None

    # Add a real test -> gate open -> registers -> becomes callable.
    (src / "test_tool.py").write_text("from tool import slugify\n\ndef test_slugify():\n    assert slugify('Hello World')=='hello-world'\n")
    assert tool_registry.test_tool(str(src))["ok"] is True
    name = tool_registry.register_tool("slugify", str(src), "slugify helper")
    assert name == "slugify"
    assert "slugify" in tool_registry.list_registered()
    fn = tool_registry.load_foundry_function("slugify")
    assert fn is not None
    assert fn("Hello World") == "hello-world"
