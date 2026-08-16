"""
Phase 1 verification semantics — Level 0 and Level 1.
Verification must fail closed: empty output, tool errors, and unmet
environment assertions all fail it.
"""
from mitchell.core.result import MCPResult
from mitchell.core.tasks import TaskStep
from mitchell.core.verify import verify_step


def _step(**args):
    return TaskStep(description="build", args=args)


def _msgs(content="ok", tool_error=False, last_content=None):
    last_content = content if last_content is None else last_content
    msgs = [{"role": "user", "content": "run step"}]
    if content is not None:
        msgs.append({"role": "assistant", "content": content})
    if tool_error:
        msgs.append(
            {
                "role": "tool",
                "tool_call_id": "c1",
                "name": "x",
                "content": "Error executing tool: boom",
            }
        )
    return msgs


# ---- Level 0 ----

def test_l0_passes_with_output_and_no_tool_error():
    assert verify_step(_step(), _msgs(content="finished")) is True


def test_l0_fails_when_no_output():
    assert verify_step(_step(), _msgs(content="")) is False


def test_l0_fails_when_tool_errored():
    assert verify_step(_step(), _msgs(content="finished", tool_error=True)) is False


# ---- Level 1 ----

def test_l1_file_exists_passes(monkeypatch, tmp_path):
    target = tmp_path / "build.txt"
    target.write_text("ok")
    monkeypatch.setattr(
        "mitchell.core.verify.verify_file_exists",
        lambda path: MCPResult.success(data=None) if path == str(target) else MCPResult.fail(),
    )
    assert verify_step(_step(expect_file_exists=str(target)), _msgs(content="done")) is True


def test_l1_missing_file_fails(monkeypatch, tmp_path):
    # The build claims a file exists that the real tool never created.
    missing = tmp_path / "missing.txt"
    monkeypatch.setattr(
        "mitchell.core.verify.verify_file_exists",
        lambda path: MCPResult.fail(error="not found"),
    )
    assert verify_step(_step(expect_file_exists=str(missing)), _msgs(content="done")) is False
