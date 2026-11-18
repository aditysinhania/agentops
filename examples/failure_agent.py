
"""Test AgentOps failure tracking. No paid LLM key is needed."""

import os
import time
from agentops import AgentOps

ops = AgentOps()
agent_id = os.getenv("AGENTOPS_AGENT_ID", "")


def failing_agent(question: str):
    with ops.trace(
        "failure_test.answer",
        input=question,
        metadata={"test": "intentional_failure"}
    ) as run:

        with run.tool_call(
            "knowledge.search",
            input={"query": question}
        ) as tool:
            tool.set_output({"documents": 1})

        # Intentionally simulate an agent failure.
        raise RuntimeError("Simulated agent execution failure")


if __name__ == "__main__":
    if not agent_id:
        raise SystemExit(
            "Set AGENTOPS_AGENT_ID and AGENTOPS_API_KEY first."
        )

    try:
        failing_agent("Test failure tracking in AgentOps")
    except RuntimeError as error:
        print(f"Expected test failure: {error}")

    # Allow background telemetry to finish sending.
    time.sleep(2)

    print("Failure test completed.")
