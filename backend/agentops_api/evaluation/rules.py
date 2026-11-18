import json
import re
from typing import Any


def _tokens(text: str | None) -> list[str]:
    return re.findall(r"[a-z0-9]+", (text or '').lower())


def _overlap(a: str | None, b: str | None) -> float:
    left, right = set(_tokens(a)), set(_tokens(b))
    if not left or not right:
        return 0.0
    return len(left & right) / max(1, len(left | right))


def evaluate_case(case: Any, requested: list[str] | None = None, *, actual_output: str | None = None) -> dict[str, Any]:
    selected = set(requested or ['correctness', 'relevance', 'contextual_accuracy', 'instruction_following', 'hallucination', 'tool_selection', 'structured_output'])
    actual = (case.actual_output if actual_output is None else actual_output) or ''
    expected = case.expected_output or ''
    metrics: dict[str, float] = {}
    if 'correctness' in selected:
        metrics['correctness'] = _overlap(actual, expected) if expected else (1.0 if actual.strip() else 0.0)
    if 'relevance' in selected:
        metrics['relevance'] = _overlap(actual, case.input) if actual and case.input else (1.0 if actual else 0.0)
    if 'contextual_accuracy' in selected:
        context = case.reference_context or ''
        metrics['contextual_accuracy'] = min(1.0, len(set(_tokens(actual)) & set(_tokens(context))) / max(1, len(set(_tokens(actual))))) if context else (1.0 if actual else 0.0)
    if 'instruction_following' in selected:
        instructions = (case.instructions or '').lower()
        if 'under ' in instructions and ' word' in instructions:
            match = re.search(r'under\s+(\d+)\s+word', instructions)
            limit = int(match.group(1)) if match else 0
            metrics['instruction_following'] = 1.0 if not limit or len(actual.split()) < limit else 0.0
        elif instructions:
            required = [part.strip() for part in re.split(r'[,;\n]', instructions) if len(part.strip()) > 2]
            metrics['instruction_following'] = sum(1 for item in required if item.lower() in actual.lower()) / max(1, len(required))
        else:
            metrics['instruction_following'] = 1.0 if actual.strip() else 0.0
    if 'hallucination' in selected:
        context_words = set(_tokens(case.reference_context or case.expected_output or ''))
        actual_words = set(_tokens(actual))
        metrics['hallucination'] = 1.0 - (len(actual_words - context_words) / max(1, len(actual_words))) if context_words else (1.0 if actual.strip() else 0.0)
    if 'tool_selection' in selected:
        metrics['tool_selection'] = 1.0 if case.expected_tool and case.expected_tool == case.actual_tool else (0.0 if case.expected_tool else 1.0)
    if 'structured_output' in selected:
        if case.structured_schema:
            try:
                parsed = json.loads(actual)
                required = case.structured_schema.get('required', [])
                properties = case.structured_schema.get('properties', {})
                valid = isinstance(parsed, dict) and all(key in parsed for key in required)
                for key, spec in properties.items():
                    if key in parsed and spec.get('type') == 'string' and not isinstance(parsed[key], str):
                        valid = False
                    if key in parsed and spec.get('type') == 'number' and not isinstance(parsed[key], (int, float)):
                        valid = False
                metrics['structured_output'] = 1.0 if valid else 0.0
            except (ValueError, TypeError):
                metrics['structured_output'] = 0.0
        else:
            metrics['structured_output'] = 1.0 if actual.strip() else 0.0
    score = sum(metrics.values()) / max(1, len(metrics))
    return {'score': round(score, 4), 'metrics': {key: round(value, 4) for key, value in metrics.items()}, 'passed': score >= 0.7, 'reasoning': f"Rule-based score from {len(metrics)} requested metric(s); overlap and constraint checks are deterministic heuristics."}
