"""Evaluate structured conversational-agent traces without calling an LLM."""
from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any, Iterable


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with Path(path).open(encoding="utf-8") as stream:
        for line_number, raw in enumerate(stream, start=1):
            if not raw.strip():
                continue
            try:
                item = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_number}: {exc.msg}") from exc
            if not isinstance(item, dict):
                raise ValueError(f"Line {line_number} must contain a JSON object")
            records.append(item)
    return records


def _clean_text(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value).casefold()).strip()


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, math.ceil(percentile * len(ordered)))
    return ordered[rank - 1]


def evaluate(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Score scenarios against expected tool, response phrase, and latency checks.

    Expected fields are optional. A scenario with no expectations is reported as
    passing, but contributes to the scenario count only; it does not affect any
    criterion-specific denominator.
    """
    cases: list[dict[str, Any]] = []
    latencies: list[float] = []
    tool_expected = tool_found = tool_success = 0
    phrase_expected = phrase_found = 0

    for index, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            raise ValueError(f"Scenario {index} must be an object")
        scenario_id = str(record.get("scenario_id", f"scenario-{index}"))
        expected = record.get("expected", {})
        turns = record.get("turns", [])
        if not isinstance(expected, dict) or not isinstance(turns, list):
            raise ValueError(f"Scenario {scenario_id}: expected must be an object and turns a list")
        assistant_turns = [turn for turn in turns if isinstance(turn, dict) and turn.get("role") == "assistant"]
        checks: dict[str, Any] = {}
        criteria: list[bool] = []

        expected_tool = expected.get("tool")
        if expected_tool:
            tool_expected += 1
            matching = [turn for turn in turns if isinstance(turn, dict) and turn.get("tool_name") == expected_tool]
            found = bool(matching)
            succeeded = any(turn.get("tool_success") is True for turn in matching)
            tool_found += int(found)
            tool_success += int(succeeded)
            checks["expected_tool"] = expected_tool
            checks["tool_found"] = found
            checks["tool_succeeded"] = succeeded
            criteria.append(succeeded)

        required_phrase = expected.get("required_phrase")
        if required_phrase:
            phrase_expected += 1
            actual_text = " ".join(str(turn.get("text", "")) for turn in assistant_turns)
            found = _clean_text(required_phrase) in _clean_text(actual_text)
            phrase_found += int(found)
            checks["required_phrase"] = required_phrase
            checks["phrase_found"] = found
            criteria.append(found)

        scenario_latency: float | None = None
        latency_values: list[float] = []
        for turn in assistant_turns:
            value = turn.get("latency_ms")
            if value is None:
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
                raise ValueError(f"Scenario {scenario_id}: latency_ms must be a non-negative number")
            latency_values.append(float(value))
        if latency_values:
            scenario_latency = sum(latency_values)
            latencies.extend(latency_values)
        max_latency = expected.get("max_latency_ms")
        if max_latency is not None:
            if isinstance(max_latency, bool) or not isinstance(max_latency, (int, float)) or max_latency < 0:
                raise ValueError(f"Scenario {scenario_id}: max_latency_ms must be a non-negative number")
            latency_ok = scenario_latency is not None and scenario_latency <= max_latency
            checks["scenario_latency_ms"] = scenario_latency
            checks["max_latency_ms"] = max_latency
            checks["latency_within_budget"] = latency_ok
            criteria.append(latency_ok)

        passed = all(criteria)
        cases.append({"scenario_id": scenario_id, "passed": passed, "checks": checks})

    scenario_count = len(cases)
    return {
        "summary": {
            "scenario_count": scenario_count,
            "passed_scenarios": sum(case["passed"] for case in cases),
            "scenario_pass_rate": (sum(case["passed"] for case in cases) / scenario_count) if scenario_count else 0.0,
            "tool_match_rate": (tool_found / tool_expected) if tool_expected else None,
            "tool_success_rate": (tool_success / tool_expected) if tool_expected else None,
            "required_phrase_rate": (phrase_found / phrase_expected) if phrase_expected else None,
            "tool_expectations": tool_expected,
            "phrase_expectations": phrase_expected,
            "assistant_turn_latency_ms": {
                "sample_count": len(latencies),
                "p50": _percentile(latencies, 0.50),
                "p95": _percentile(latencies, 0.95),
            },
        },
        "cases": cases,
    }
