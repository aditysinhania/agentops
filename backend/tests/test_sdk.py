from agentops import AgentOps


def test_sdk_collects_nested_spans_and_preserves_agent_exceptions(monkeypatch):
    client = AgentOps(api_key='ao_live_test', agent_id='agent-1')
    sent = []
    monkeypatch.setattr(client, '_send', sent.append)
    with client.trace('answer', input={'q': 'hello'}) as run:
        with run.span('orchestrate') as root:
            with run.tool_call('search', input='hello') as tool:
                tool.set_output({'count': 1})
            with run.llm_call('completion', model='unit-test') as llm:
                llm.set_output('done')
                llm.set_tokens(2, 1)
        run.set_output('done')
    assert len(sent) == 1
    assert sent[0]['agent_id'] == 'agent-1'
    assert len(sent[0]['spans']) == 3
    assert sent[0]['spans'][0]['parent_span_id'] is None
    assert sent[0]['spans'][1]['parent_span_id'] == sent[0]['spans'][0]['span_id']
    assert sent[0]['spans'][2]['parent_span_id'] == sent[0]['spans'][0]['span_id']
    assert sent[0]['spans'][2]['kind'] == 'llm'
    assert sent[0]['spans'][2]['input_tokens'] == 2


def test_sdk_records_failure_and_does_not_swallow_it(monkeypatch):
    client = AgentOps(api_key='ao_live_test', agent_id='agent-1')
    sent = []
    monkeypatch.setattr(client, '_send', sent.append)
    try:
        with client.trace('failure'):
            raise ValueError('expected test error')
    except ValueError:
        pass
    else:
        raise AssertionError('The SDK must not swallow application exceptions.')
    assert sent[0]['status'] == 'error'
    assert 'expected test error' in sent[0]['error']


def test_sdk_missing_credentials_is_a_safe_noop():
    client = AgentOps(api_key='', agent_id='')
    with client.trace('no-op') as run:
        run.set_output('still runs')


def test_sdk_unreachable_telemetry_endpoint_does_not_raise():
    client = AgentOps(api_key='ao_live_test', agent_id='agent-1', endpoint='http://127.0.0.1:1', timeout=0.1)
    with client.trace('fail-open') as run:
        run.set_output('application work remains successful')
