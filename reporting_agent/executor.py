from reporting_agent.agent import ReportingAgent
from typing import Any, AsyncIterable

class ReportingAgentExecutor:
    def __init__(self, agent: ReportingAgent):
        self.agent = agent

    async def on_message_send(self, conversion_result: dict, session_id: str) -> dict[str, Any]:
        return await self.agent.summarize(conversion_result, session_id)

    async def on_message_stream(self, conversion_result: dict, session_id: str) -> AsyncIterable[dict[str, Any]]:
        async for chunk in self.agent.stream(conversion_result, session_id):
            yield chunk
