"""Unit and integration test suite for Mitchell Code Action & Git Automation."""

import json
from pathlib import Path
import pytest

from mitchell.action.conflict_resolver import ConflictResolver, conflict_resolver
from mitchell.action.pr_reviewer import PRReviewer, pr_reviewer
from mitchell.action.smart_commit import SmartCommitEngine, smart_commit
from mitchell.action.workflow_generator import WorkflowGenerator, workflow_generator
from mitchell.manager.intent import parse_fast_intent
from mitchell.tools.action_tools import (
    tool_git_action_generate_workflow,
    tool_git_action_resolve_conflicts,
    tool_git_action_review,
    tool_git_action_smart_commit,
)


# ── 1. PR Reviewer Tests ──────────────────────────────────────────────────────

def test_pr_reviewer_clean_diff():
    """Verify reviewer returns APPROVE on empty diff."""
    reviewer = PRReviewer()
    report = reviewer.review_diff(diff_text="")
    assert report.verdict == "APPROVE"
    assert "clean" in report.summary.lower()


def test_pr_reviewer_diff_parsing(tmp_path):
    """Test diff parsing with file changes, stats, and markdown formatting."""
    reviewer = PRReviewer(root_dir=tmp_path)
    sample_diff = """diff --git a/mitchell/core/test.py b/mitchell/core/test.py
new file mode 100644
index 0000000..e69de29
--- /dev/null
+++ b/mitchell/core/test.py
@@ -0,0 +1,5 @@
+def test_func():
+    return True
"""
    # Create valid python file
    p_file = tmp_path / "mitchell" / "core" / "test.py"
    p_file.parent.mkdir(parents=True, exist_ok=True)
    p_file.write_text("def test_func():\n    return True\n", encoding="utf-8")

    report = reviewer.review_diff(diff_text=sample_diff)
    assert report.verdict in ("APPROVE", "COMMENT")
    assert report.insertions == 2
    assert "mitchell/core/test.py" in report.files_changed

    md = reviewer.format_markdown_report(report)
    assert "Mitchell Code Action Review" in md
    assert "test.py" in md


def test_pr_reviewer_security_secret_detection(tmp_path):
    """Test security heuristic flags hardcoded credentials."""
    reviewer = PRReviewer(root_dir=tmp_path)
    leak_diff = """diff --git a/config.py b/config.py
--- a/config.py
+++ b/config.py
@@ -1,1 +1,2 @@
+api_key = "sk-live-1234567890abcdef"
"""
    report = reviewer.review_diff(diff_text=leak_diff)
    assert report.verdict == "REQUEST_CHANGES"
    assert any(f.category == "security" for f in report.findings)


# ── 2. Smart Commit Generator Tests ───────────────────────────────────────────

def test_smart_commit_analysis():
    """Test conventional commit categorization and scope extraction."""
    engine = SmartCommitEngine()

    # Test file changes
    proposal_test = engine.analyze_commit(
        files=["tests/test_action.py"],
        diff_text="+def test_something(): pass",
    )
    assert proposal_test.type == "test"
    assert "test" in proposal_test.headline

    # Action / Git feature
    proposal_feat = engine.analyze_commit(
        files=["mitchell/action/pr_reviewer.py"],
        diff_text="+class PRReviewer: pass",
    )
    assert proposal_feat.type == "feat"
    assert proposal_feat.scope == "action"
    assert "action" in proposal_feat.headline


# ── 3. Conflict Resolver Tests ────────────────────────────────────────────────

def test_conflict_resolver_reconciliation():
    """Test parsing and reconciling git merge conflict markers."""
    resolver = ConflictResolver()
    conflicted_text = (
        "import os\n"
        + "<<<<<<< HEAD\n"
        + "import sys\n"
        + "=======\n"
        + "import json\n"
        + ">>>>>>> incoming\n"
        + "\ndef run():\n    pass\n"
    )
    resolved, count = resolver.resolve_text_conflicts(conflicted_text, file_path="sample.py")
    assert count == 1
    assert "<<<<<<<" not in resolved
    assert "=======" not in resolved
    assert ">>>>>>>" not in resolved
    assert "import sys" in resolved
    assert "import json" in resolved


# ── 4. Workflow Generator Tests ───────────────────────────────────────────────

def test_workflow_generator_scaffolding(tmp_path):
    """Test scaffolding of action.yml and CI workflow file."""
    gen = WorkflowGenerator(root_dir=tmp_path)
    res = gen.scaffold_all()

    action_yml = tmp_path / "action.yml"
    workflow_yml = tmp_path / ".github" / "workflows" / "mitchell-code-action.yml"

    assert action_yml.exists()
    assert workflow_yml.exists()
    assert "Mitchell Code Action" in action_yml.read_text(encoding="utf-8")
    assert "Mitchell Code Action CI" in workflow_yml.read_text(encoding="utf-8")


# ── 5. Autonomous Action Tools Tests ──────────────────────────────────────────

def test_autonomous_action_tools(tmp_path):
    """Test autonomous tools registered in ToolRegistry."""
    # 1. Review tool
    rev_raw = tool_git_action_review()
    rev = json.loads(rev_raw)
    assert "verdict" in rev
    assert "markdown_report" in rev

    # 2. Workflow scaffold tool
    wf_raw = tool_git_action_generate_workflow(target_dir=str(tmp_path))
    wf = json.loads(wf_raw)
    assert wf["status"] == "success"
    assert (tmp_path / "action.yml").exists()

    # 3. Conflict resolver tool
    conf_raw = tool_git_action_resolve_conflicts()
    conf = json.loads(conf_raw)
    assert conf["status"] in ("clean", "resolved")


# ── 6. Fast Intent Recognition Tests ──────────────────────────────────────────

def test_fast_intents_for_git_actions():
    """Verify fast intent recognition for git code reviews, smart commits, and conflicts."""
    intent_rev = parse_fast_intent("review diff")
    assert intent_rev is not None
    assert intent_rev.tool_name == "git_action_review"

    intent_com = parse_fast_intent("smart commit")
    assert intent_com is not None
    assert intent_com.tool_name == "git_action_smart_commit"

    intent_conf = parse_fast_intent("resolve conflicts")
    assert intent_conf is not None
    assert intent_conf.tool_name == "git_action_resolve_conflicts"
