from __future__ import annotations
import json
from pathlib import Path
import pytest
from unittest.mock import patch
from mitchell.voice.learner import (
    retune_thresholds,
    extract_patterns,
    reset_thresholds,
    reset_patterns,
    reset_corrections,
    get_stats
)

@pytest.fixture
def mock_paths(tmp_path, monkeypatch):
    monkeypatch.setattr("mitchell.voice.learner._THRESHOLDS_PATH", tmp_path / "thresholds.json")
    monkeypatch.setattr("mitchell.voice.learner._PATTERNS_PATH", tmp_path / "patterns.json")
    monkeypatch.setattr("mitchell.voice.learner._CORRECTIONS_LOG", tmp_path / "corrections.log")
    monkeypatch.setattr("mitchell.voice.learner._VOICE_DIR", tmp_path)
    return tmp_path


def write_thresholds(path, match, floor):
    with open(path, "w") as f:
        json.dump({"match_threshold": match, "ambiguous_floor": floor}, f)


def write_corrections(path, entries):
    """Write full correction records matching correction.py's log format:
    requires decision_type + original_score so retune_thresholds can use them."""
    with open(path, "w") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")


def fp(score=0.9):
    return {"decision_id": "d1", "decision_type": "diarize",
            "correct_label": "false_positive", "original_score": score, "timestamp": 100.0}


def fn(score=0.6):
    return {"decision_id": "d2", "decision_type": "diarize",
            "correct_label": "false_negative", "original_score": score, "timestamp": 100.0}


def test_retune_thresholds_no_corrections(mock_paths):
    write_thresholds(mock_paths / "thresholds.json", 0.75, 0.55)
    res = retune_thresholds()
    assert res["match_threshold"] == 0.75
    assert res["ambiguous_floor"] == 0.55

def test_retune_thresholds_false_positive_nudges_match_up(mock_paths):
    write_thresholds(mock_paths / "thresholds.json", 0.75, 0.55)
    write_corrections(mock_paths / "corrections.log", [fp(0.72)])
    res = retune_thresholds()
    assert res["match_threshold"] > 0.75

def test_retune_thresholds_false_negative_nudges_floor_down(mock_paths):
    write_thresholds(mock_paths / "thresholds.json", 0.75, 0.55)
    write_corrections(mock_paths / "corrections.log", [fn(0.58)])
    res = retune_thresholds()
    assert res["ambiguous_floor"] < 0.55

def test_nudge_is_bounded(mock_paths):
    write_thresholds(mock_paths / "thresholds.json", 0.75, 0.55)
    write_corrections(mock_paths / "corrections.log", [fp(0.72) for _ in range(10)])
    res = retune_thresholds()
    assert res["match_threshold"] <= 0.75 + 0.02

def test_threshold_never_exceeds_ceiling(mock_paths):
    write_thresholds(mock_paths / "thresholds.json", 0.89, 0.55)
    write_corrections(mock_paths / "corrections.log", [fp(0.87) for _ in range(5)])
    res = retune_thresholds()
    assert res["match_threshold"] <= 0.90

def test_match_threshold_stays_above_floor(mock_paths):
    write_thresholds(mock_paths / "thresholds.json", 0.56, 0.55)
    write_corrections(mock_paths / "corrections.log", [fn(0.5) for _ in range(5)])
    res = retune_thresholds()
    assert res["match_threshold"] > res["ambiguous_floor"]

def test_extract_patterns_less_than_3(mock_paths):
    write_corrections(mock_paths / "corrections.log", [
        {"decision_type": "context_gate", "correct_label": "false_positive",
         "utterance_text": "hey john how are you", "timestamp": 1.0},
        {"decision_type": "context_gate", "correct_label": "false_positive",
         "utterance_text": "hey john how are you", "timestamp": 2.0},
    ])
    res = extract_patterns()
    assert "xyz" not in res.get("patterns", {})

def test_extract_patterns_3_or_more(mock_paths):
    write_corrections(mock_paths / "corrections.log", [
        {"decision_type": "context_gate", "correct_label": "false_positive",
         "utterance_text": "hey john how are you", "timestamp": 1.0}
        for _ in range(3)
    ])
    res = extract_patterns()
    assert "hey john how" in res["patterns"]

def test_reset_thresholds(mock_paths):
    res = reset_thresholds()
    assert res["match_threshold"] == 0.75
    assert res["ambiguous_floor"] == 0.55

def test_reset_corrections(mock_paths):
    write_corrections(mock_paths / "corrections.log", [fp()])
    count = reset_corrections()
    assert count == 1
    assert not (mock_paths / "corrections.log").exists()
