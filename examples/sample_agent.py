"""A small deterministic sample agent. No paid LLM key is needed."""
import os
import time
from agentops import AgentOps

ops = AgentOps()
agent_id = os.getenv('AGENTOPS_AGENT_ID', '')


def answer(question: str) -> str:
    with ops.trace('sample.answer', input=question, metadata={'sample': True}) as run:
        with run.tool_call('knowledge.search', input={'query': question}) as tool:
            tool.set_output({'documents': 1})
        with run.llm_call('response.generate', model='deterministic-sample', input=question) as llm:
            result = f"Sample response for: {question}"
            llm.set_output(result)
            llm.set_tokens(input_tokens=max(1, len(question.split())), output_tokens=max(1, len(result.split())))
        run.set_output(result)
        run.set_token_usage(input_tokens=max(1, len(question.split())), output_tokens=max(1, len(result.split())))
    return result


if __name__ == '__main__':
    if not agent_id:
        raise SystemExit('Set AGENTOPS_AGENT_ID and AGENTOPS_API_KEY after registering an agent and key.')

    print(answer('How does AgentOps improve reliability?'))

    # Allow the background telemetry thread to finish sending.
    time.sleep(2)
