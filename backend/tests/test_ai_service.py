import json

import pytest

from app.services import ai


def test_parse_json_block_variants():
    assert ai.parse_json_block('{"a": 1}') == {"a": 1}
    assert ai.parse_json_block('here you go:\n```json\n{"a": 2}\n```\nthanks') == {"a": 2}
    assert ai.parse_json_block('blah blah {"a": 3, "b": "x"} trailing') == {"a": 3, "b": "x"}
    with pytest.raises(ai.AiResponseError):
        ai.parse_json_block("no json here at all")


def test_validate_solution():
    assert ai.validate_solution({"content_md": "# yes"}) == {"content_md": "# yes"}
    with pytest.raises(ai.AiResponseError):
        ai.validate_solution({"content_md": "   "})
    with pytest.raises(ai.AiResponseError):
        ai.validate_solution({})


def test_validate_grading_clamps_and_coerces():
    d = {
        "score": "150",
        "feedback_md": "Good.",
        "rubric_breakdown": [
            {"criterion": "Part a", "points_awarded": "30", "points_possible": 40, "note": "ok"},
            "garbage",
            {"criterion": "Part b"},
        ],
    }
    out = ai.validate_grading(d, points_possible=100)
    assert out["score"] == 100.0  # clamped
    assert out["feedback_md"] == "Good."
    assert out["rubric_breakdown"][0] == {
        "criterion": "Part a",
        "points_awarded": 30.0,
        "points_possible": 40.0,
        "note": "ok",
    }
    assert out["rubric_breakdown"][1]["points_awarded"] == 0.0  # missing -> 0
    assert len(out["rubric_breakdown"]) == 2  # "garbage" dropped

    assert ai.validate_grading({"score": -5, "feedback_md": ""}, 100) == {
        "score": 0.0,
        "rubric_breakdown": [],
        "feedback_md": "",
    }
    with pytest.raises(ai.AiResponseError):
        ai.validate_grading({"score": 10}, 100)  # no feedback_md


def test_availability_flags(monkeypatch):
    monkeypatch.setattr(ai._settings, "claude_code_oauth_token", "")
    monkeypatch.setattr(ai._settings, "anthropic_api_key", "")
    assert not ai.ai_available()
    assert not ai.solution_generation_available()
    monkeypatch.setattr(ai._settings, "anthropic_api_key", "sk-test")
    assert ai.ai_available()
    monkeypatch.setattr(ai._settings, "ai_solution_generation_enabled", True)
    assert ai.solution_generation_available()
    monkeypatch.setattr(ai._settings, "ai_solution_generation_enabled", False)
    assert ai.ai_available()
    assert not ai.solution_generation_available()


def test_generate_reference_solution_mocked(monkeypatch):
    seen = {}

    def fake_invoke(system, user, files):
        seen["system"], seen["user"], seen["files"] = system, user, files
        return json.dumps({"content_md": "# Solution\n1. ..."}), "transcript"

    monkeypatch.setattr(ai, "_invoke", fake_invoke)
    sol, transcript = ai.generate_reference_solution(
        title="PS 1 — Series", description_md="See the PDF.", points_possible=100
    )
    assert sol == {"content_md": "# Solution\n1. ..."}
    assert transcript == "transcript"
    assert "PS 1 — Series" in seen["user"]


def test_grade_submission_mocked(monkeypatch):
    seen = {}

    def fake_invoke(system, user, files):
        seen["user"], seen["files"] = user, files
        return "```json\n" + json.dumps(
            {
                "score": 88,
                "feedback_md": "Part 2 proof has a gap.",
                "rubric_breakdown": [
                    {"criterion": "P1", "points_awarded": 50, "points_possible": 50, "note": "ok"}
                ],
            }
        ) + "\n```", "T"

    monkeypatch.setattr(ai, "_invoke", fake_invoke)
    g, _ = ai.grade_submission(
        title="PS 3",
        description_md="instructions",
        points_possible=100,
        key_text="# Key",
        submission_text="my proof",
        submission_files={"proof.pdf": b"%PDF"},
    )
    assert g["score"] == 88.0
    assert g["rubric_breakdown"][0]["criterion"] == "P1"
    assert "proof.pdf" in seen["user"]
    assert "100" in seen["user"]  # points possible mentioned
    assert seen["files"] == {"proof.pdf": b"%PDF"}


def test_invoke_raises_without_credential(monkeypatch):
    monkeypatch.setattr(ai._settings, "claude_code_oauth_token", "")
    monkeypatch.setattr(ai._settings, "anthropic_api_key", "")
    with pytest.raises(ai.AiUnavailable):
        ai._invoke("s", "u", {})
