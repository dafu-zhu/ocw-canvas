"""The AI interface: reference-solution generation + submission grading.

There are three execution backends, selected by which env vars are present:
  1. ``CLAUDE_CODE_OAUTH_TOKEN`` -> the Claude Agent SDK (drives the Claude Code CLI),
     billed to the owner's Claude subscription.  Preferred.
  2. ``ANTHROPIC_API_KEY``        -> the plain Anthropic API (per-token billing).  Fallback.
  3. neither                      -> AI is unavailable; the app still works (manual grading).

Everything in this module is pure and unit-tested **except** ``_invoke`` — the single
function that actually talks to the SDK / API.  Tests monkeypatch ``_invoke``; the
``claude_agent_sdk`` / ``anthropic`` packages are imported lazily *inside* it so this
module imports cleanly without them.
"""
from __future__ import annotations

import json
import mimetypes
import re

from app.config import get_settings

_settings = get_settings()


class AiUnavailable(RuntimeError):
    """No AI credential is configured."""


class AiResponseError(RuntimeError):
    """The model's reply could not be parsed / validated."""


# --------------------------------------------------------------------------- config


def _backend() -> str:
    if _settings.claude_code_oauth_token:
        return "agent_sdk"
    if _settings.anthropic_api_key:
        return "anthropic_api"
    return "none"


def ai_available() -> bool:
    return _backend() != "none"


def solution_generation_available() -> bool:
    return ai_available() and _settings.ai_solution_generation_enabled


def model_id() -> str:
    return _settings.ai_model


# --------------------------------------------------------------------------- prompts

SOLUTION_SYSTEM_PROMPT = (
    "You are an experienced university instructor writing the official reference solution "
    "(answer key) for a problem set. Produce a complete, rigorous, well-explained worked "
    "solution to every part. Use clear mathematical prose and Markdown (LaTeX in $...$ / $$...$$ "
    "is fine). Do not omit steps. Respond with ONLY a JSON object of the form "
    '{"content_md": "<the full worked solution in Markdown>"} and nothing else.'
)

GRADING_SYSTEM_PROMPT = (
    "You are an experienced university grader. You are given a problem set, an answer key, and a "
    "student's submission. Grade the submission against the key with appropriate mathematical "
    "rigor: identify exactly where a proof has a gap, an error, or is incomplete. Be specific and "
    "constructive. Respond with ONLY a JSON object of the form "
    '{"score": <number 0..points_possible>, '
    '"rubric_breakdown": [{"criterion": "<part / aspect>", "points_awarded": <number>, '
    '"points_possible": <number>, "note": "<short justification>"}], '
    '"feedback_md": "<written feedback in Markdown>"} and nothing else.'
)


def build_solution_prompt(*, title: str, description_md: str, points_possible: float) -> str:
    return (
        f"# Problem set: {title}\n\n"
        f"Points possible: {points_possible}\n\n"
        f"## Instructions / source material\n\n{description_md or '(no description provided)'}\n\n"
        "Write the complete reference solution now."
    )


def build_grading_prompt(
    *,
    title: str,
    description_md: str,
    points_possible: float,
    key_text: str,
    key_note: str,
    submission_text: str,
    submission_files: list[str],
) -> str:
    parts = [
        f"# Problem set: {title}",
        f"\nPoints possible: {points_possible}",
        f"\n## Instructions / source material\n\n{description_md or '(no description provided)'}",
    ]
    parts.append("\n## Answer key")
    if key_text.strip():
        parts.append(f"\n{key_text}")
    if key_note.strip():
        parts.append(f"\n{key_note}")
    if not key_text.strip() and not key_note.strip():
        parts.append("\n(no explicit key — grade against standard rigor for this subject)")
    parts.append("\n## Student submission")
    if submission_text.strip():
        parts.append(f"\n### Typed answer\n\n{submission_text}")
    if submission_files:
        joined = ", ".join(submission_files)
        parts.append(
            f"\n### Attached files\n\nThe following files are in your working directory: {joined}. "
            "Read them to grade the submission."
        )
    if not submission_text.strip() and not submission_files:
        parts.append("\n(the student submitted nothing — award 0 and say so)")
    parts.append(
        f"\nGrade now. The total score must be between 0 and {points_possible}."
    )
    return "\n".join(parts)


# --------------------------------------------------------------------------- parsing

_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)
_OBJ_RE = re.compile(r"\{.*\}", re.DOTALL)


def parse_json_block(text: str) -> dict:
    """Extract a single JSON object from ``text`` (handles ```json fences and leading prose)."""
    if text is None:
        raise AiResponseError("empty response")
    candidates: list[str] = []
    m = _FENCE_RE.search(text)
    if m:
        candidates.append(m.group(1))
    stripped = text.strip()
    if stripped.startswith("{"):
        candidates.append(stripped)
    m2 = _OBJ_RE.search(text)
    if m2:
        candidates.append(m2.group(0))
    for c in candidates:
        try:
            obj = json.loads(c)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            return obj
    raise AiResponseError(f"no JSON object found in response: {text[:200]!r}")


def _as_float(v, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def validate_solution(d: dict) -> dict:
    content = d.get("content_md")
    if not isinstance(content, str) or not content.strip():
        raise AiResponseError("solution response missing non-empty 'content_md'")
    return {"content_md": content}


def validate_grading(d: dict, points_possible: float) -> dict:
    if "feedback_md" not in d or not isinstance(d["feedback_md"], str):
        raise AiResponseError("grading response missing 'feedback_md'")
    score = _as_float(d.get("score"), 0.0)
    score = max(0.0, min(float(points_possible), score))
    rubric_in = d.get("rubric_breakdown")
    rubric: list[dict] = []
    if isinstance(rubric_in, list):
        for item in rubric_in:
            if not isinstance(item, dict):
                continue
            rubric.append(
                {
                    "criterion": str(item.get("criterion", "")),
                    "points_awarded": _as_float(item.get("points_awarded"), 0.0),
                    "points_possible": _as_float(item.get("points_possible"), 0.0),
                    "note": str(item.get("note", "")),
                }
            )
    return {"score": score, "rubric_breakdown": rubric, "feedback_md": d["feedback_md"]}


# --------------------------------------------------------------------------- the seam


def _invoke(system_prompt: str, user_prompt: str, files: dict[str, bytes]) -> tuple[str, str]:
    """Run one model turn. Returns (response_text, transcript). The ONLY impure function here."""
    backend = _backend()
    if backend == "none":
        raise AiUnavailable(
            "no AI credential configured (CLAUDE_CODE_OAUTH_TOKEN or ANTHROPIC_API_KEY)"
        )
    if backend == "agent_sdk":
        return _invoke_agent_sdk(system_prompt, user_prompt, files)
    return _invoke_anthropic_api(system_prompt, user_prompt, files)


def _invoke_agent_sdk(
    system_prompt: str, user_prompt: str, files: dict[str, bytes]
) -> tuple[str, str]:
    import asyncio
    import tempfile
    from pathlib import Path

    from claude_agent_sdk import ClaudeAgentOptions, query  # type: ignore

    async def _run() -> str:
        with tempfile.TemporaryDirectory() as cwd:
            for name, data in files.items():
                (Path(cwd) / name).write_bytes(data)
            opts = ClaudeAgentOptions(
                system_prompt=system_prompt,
                cwd=cwd,
                permission_mode="bypassPermissions",
                allowed_tools=["Read", "Glob", "Grep"],
                model=model_id(),
            )
            chunks: list[str] = []
            async for message in query(prompt=user_prompt, options=opts):
                text = getattr(message, "result", None) or getattr(message, "text", None)
                if isinstance(text, str):
                    chunks.append(text)
                else:
                    content = getattr(message, "content", None)
                    if isinstance(content, list):
                        for block in content:
                            bt = getattr(block, "text", None)
                            if isinstance(bt, str):
                                chunks.append(bt)
            return chunks[-1] if chunks else ""

    out = asyncio.run(_run())
    transcript = (
        f"=== SYSTEM ===\n{system_prompt}\n\n=== USER ===\n{user_prompt}\n\n"
        f"(files: {sorted(files)})\n\n=== RESPONSE ===\n{out}\n"
    )
    return out, transcript


def _invoke_anthropic_api(
    system_prompt: str, user_prompt: str, files: dict[str, bytes]
) -> tuple[str, str]:
    import base64

    import anthropic  # type: ignore

    client = anthropic.Anthropic(api_key=_settings.anthropic_api_key)
    content: list[dict] = [{"type": "text", "text": user_prompt}]
    for name, data in files.items():
        ctype = mimetypes.guess_type(name)[0] or "application/octet-stream"
        b64 = base64.standard_b64encode(data).decode("ascii")
        if ctype == "application/pdf":
            content.append(
                {"type": "document", "source": {"type": "base64", "media_type": ctype, "data": b64}}
            )
        elif ctype.startswith("image/"):
            content.append(
                {"type": "image", "source": {"type": "base64", "media_type": ctype, "data": b64}}
            )
        else:
            # Inline as text — best effort for plain-text submissions.
            try:
                text = f"--- {name} ---\n{data.decode('utf-8')}"
            except UnicodeDecodeError:
                text = f"--- {name} --- (binary, {len(data)} bytes; not shown)"
            content.append({"type": "text", "text": text})
    msg = client.messages.create(
        model=model_id(),
        max_tokens=8000,
        system=system_prompt,
        messages=[{"role": "user", "content": content}],
    )
    out = "".join(block.text for block in msg.content if getattr(block, "type", "") == "text")
    transcript = (
        f"=== SYSTEM ===\n{system_prompt}\n\n=== USER ===\n{user_prompt}\n\n"
        f"(files: {sorted(files)})\n\n=== RESPONSE ===\n{out}\n"
    )
    return out, transcript


# --------------------------------------------------------------------------- public ops


def generate_reference_solution(
    *, title: str, description_md: str, points_possible: float
) -> tuple[dict, str]:
    user = build_solution_prompt(
        title=title, description_md=description_md, points_possible=points_possible
    )
    out, transcript = _invoke(SOLUTION_SYSTEM_PROMPT, user, {})
    return validate_solution(parse_json_block(out)), transcript


def grade_submission(
    *,
    title: str,
    description_md: str,
    points_possible: float,
    key_text: str = "",
    key_note: str = "",
    submission_text: str = "",
    submission_files: dict[str, bytes] | None = None,
) -> tuple[dict, str]:
    files = submission_files or {}
    user = build_grading_prompt(
        title=title,
        description_md=description_md,
        points_possible=points_possible,
        key_text=key_text,
        key_note=key_note,
        submission_text=submission_text,
        submission_files=sorted(files),
    )
    out, transcript = _invoke(GRADING_SYSTEM_PROMPT, user, files)
    return validate_grading(parse_json_block(out), points_possible), transcript
