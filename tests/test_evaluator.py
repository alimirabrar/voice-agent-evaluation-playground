import json
import tempfile
import unittest
from pathlib import Path

from voice_eval.evaluator import evaluate, load_jsonl


class VoiceEvaluatorTests(unittest.TestCase):
    def test_sample_data_reports_expected_failures(self):
        root = Path(__file__).resolve().parents[1]
        report = evaluate(load_jsonl(root / "data" / "sample_traces.jsonl"))
        summary = report["summary"]
        self.assertEqual(summary["scenario_count"], 4)
        self.assertEqual(summary["passed_scenarios"], 1)
        self.assertEqual(summary["tool_success_rate"], 2 / 3)
        self.assertEqual(summary["required_phrase_rate"], 2 / 3)
        self.assertEqual(report["cases"][0]["scenario_id"], "order-lookup-success")
        self.assertFalse(report["cases"][3]["passed"])

    def test_phrase_matching_ignores_case_and_punctuation(self):
        report = evaluate([{
            "scenario_id": "phrase",
            "expected": {"required_phrase": "hello, world!"},
            "turns": [{"role": "assistant", "text": "HELLO WORLD."}],
        }])
        self.assertTrue(report["cases"][0]["passed"])

    def test_empty_input_has_null_percentiles_and_zero_rate(self):
        report = evaluate([])
        self.assertEqual(report["summary"]["scenario_pass_rate"], 0.0)
        self.assertIsNone(report["summary"]["assistant_turn_latency_ms"]["p95"])

    def test_loader_reports_bad_json_line(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "bad.jsonl"
            file.write_text('{"ok": true}\nnot-json\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "line 2"):
                load_jsonl(file)

    def test_invalid_latency_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "latency_ms"):
            evaluate([{"turns": [{"role": "assistant", "latency_ms": -1}]}])


if __name__ == "__main__":
    unittest.main()
