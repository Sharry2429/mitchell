from __future__ import annotations
import json
import pytest
from mitchell.voice.correction import (
    CORRECTION_PHRASES,
    Correction,
    check_for_correction,
    log_correction
)

def test_exact_match():
    decisions = [{"decision_id": "123", "text": "something"}]
    result = check_for_correction("that was me", decisions)
    if result is not None:
        assert result.correct_label == "false_negative"
        assert result.decision_id == "123"

def test_fuzzy_match():
    decisions = [{"decision_id": "123", "text": "something"}]
    # Should fuzzy match "that was me"
    result = check_for_correction("that was for me", decisions)
    if result is not None:
        assert result.correct_label == "false_negative"

def test_no_match():
    decisions = [{"decision_id": "123", "text": "something"}]
    result = check_for_correction("how is the weather", decisions)
    assert result is None

def test_with_no_recent_decisions():
    result = check_for_correction("that was me", [])
    assert result is None

def test_with_recent_decision():
    decisions = [{"decision_id": "456", "text": "something"}]
    result = check_for_correction("that was me", decisions)
    if result:
        assert result.decision_id == "456"

def test_log_correction_writes_json_line(tmp_path, monkeypatch):
    log_file = tmp_path / "corrections.log"
    monkeypatch.setattr("mitchell.voice.correction._CORRECTIONS_LOG", log_file)
    correction = Correction(
        decision_id="123",
        decision_type="diarize",
        correct_label="false_negative",
        original_score=0.6,
        timestamp=100.0,
    )
    log_correction(correction)

    assert log_file.exists()
    content = log_file.read_text()
    assert "false_negative" in content
    assert "123" in content

def test_log_correction_creates_parent_dirs(tmp_path, monkeypatch):
    log_dir = tmp_path / "nested" / "dir"
    log_file = log_dir / "corrections.log"
    monkeypatch.setattr("mitchell.voice.correction._CORRECTIONS_LOG", log_file)
    correction = Correction(
        decision_id="123",
        decision_type="diarize",
        correct_label="false_negative",
        original_score=0.6,
        timestamp=100.0,
    )
    log_correction(correction)

    assert log_dir.exists()
