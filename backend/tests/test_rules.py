from types import SimpleNamespace
from agentops_api.evaluation.rules import evaluate_case


def test_rule_evaluator_returns_bounded_metric_scores():
    answer = '{"answer":"Paris"}'
    case = SimpleNamespace(
        input='Paris answer', expected_output=answer, actual_output=answer,
        reference_context='Paris answer', expected_tool='lookup_city', actual_tool='lookup_city',
        instructions='under 12 words', structured_schema={'type': 'object', 'required': ['answer'], 'properties': {'answer': {'type': 'string'}}},
    )
    result = evaluate_case(case)
    assert result['score'] == 1.0
    assert result['passed'] is True
    assert set(result['metrics']) == {'correctness', 'relevance', 'contextual_accuracy', 'instruction_following', 'hallucination', 'tool_selection', 'structured_output'}
    assert all(0 <= score <= 1 for score in result['metrics'].values())


def test_rule_evaluator_flags_missing_actual_and_wrong_tool():
    case = SimpleNamespace(input='question', expected_output='answer', actual_output='', reference_context='', expected_tool='search', actual_tool='browser', instructions='', structured_schema=None)
    result = evaluate_case(case, ['correctness', 'tool_selection', 'structured_output'])
    assert result['metrics']['correctness'] == 0
    assert result['metrics']['tool_selection'] == 0
    assert result['metrics']['structured_output'] == 0
