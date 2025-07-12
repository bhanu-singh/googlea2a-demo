from currency_agent.agent import CurrencyAgent
from typing import Any, AsyncIterable

class CurrencyAgentExecutor:
    def __init__(self, agent: CurrencyAgent):
        self.agent = agent

    async def on_message_send(self, query: str, session_id: str) -> dict[str, Any]:
        return await self.agent.invoke(query, session_id)

    async def on_message_stream(self, query: str, session_id: str) -> AsyncIterable[dict[str, Any]]:
        async for chunk in self.agent.stream(query, session_id):
            yield chunk

    async def on_message_send_with_report(self, query: str, session_id: str) -> dict[str, Any]:
        return await self.agent.invoke_with_reporting(query, session_id)
