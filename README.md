# Voice Agent Evaluation Playground

A small, model-agnostic evaluation harness for **structured conversation traces**. It measures whether an agent used the expected tool, included a required response phrase, and stayed within a scenario latency budget. It also reports assistant-turn latency percentiles.

This is a personal demo/evaluation utility—not a voice model, production monitoring system, or claim of production use. It does not record audio, call an LLM, or send data anywhere. The included traces are synthetic.

## Quick start

Requires Python 3.11 or newer. No runtime dependencies.

```bash
python -m voice_eval.cli data/sample_traces.jsonl
```

Save a machine-readable report:

```bash
python -m voice_eval.cli data/sample_traces.jsonl --out report.json
```

Run tests:

```bash
python -m unittest discover -s tests -v
```

## Trace format

Each non-empty JSONL line is one scenario. `expected` checks are optional; latencies are milliseconds, and a scenario's total latency is the sum of its assistant-turn latencies.

```json
{
  "scenario_id": "order-status",
  "expected": {
    "tool": "lookup_order",
    "required_phrase": "delivery date",
    "max_latency_ms": 1800
  },
  "turns": [
    {"role": "assistant", "text": "I found the delivery date.", "latency_ms": 620},
    {"role": "tool", "tool_name": "lookup_order", "tool_success": true}
  ]
}
```

## Report metrics

- **Scenario pass rate:** share of scenarios that satisfy all checks declared for them.
- **Tool match/success rate:** expected-tool calls found and marked successful.
- **Required phrase rate:** expected response phrases found in assistant text (case/punctuation insensitive).
- **Assistant-turn p50/p95 latency:** nearest-rank percentiles across supplied assistant-turn latency samples.

A missing latency measurement fails a scenario that declares a latency budget. A trace with no expectations is counted as a passing scenario but does not affect criterion-specific rates. The evaluator deliberately does not claim semantic quality, naturalness, ASR accuracy, safety, or end-to-end audio latency; those need additional data and evaluators.

## Project status

Personal demo MVP. Extend it with scenario suites, richer tool-call assertions, streaming audio/ASR metrics, and adapters for your own trace format as needed. Do not put credentials, customer data, or private conversations in sample traces.
