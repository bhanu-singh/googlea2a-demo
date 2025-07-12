import os
import httpx
from pydantic import BaseModel, SecretStr
from typing import Literal, Any, AsyncIterable
from dotenv import load_dotenv
import google.generativeai as genai
import re
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import AIMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv(dotenv_path=os.path.join(os.getcwd(), ".env"))
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

class ResponseFormat(BaseModel):
    status: str
    message: str

class AgentCapabilities(BaseModel):
    streaming: bool = True
    pushNotifications: bool = True

class AgentSkill(BaseModel):
    id: str
    name: str
    description: str
    tags: list[str]
    examples: list[str]

class AgentAuthentication(BaseModel):
    schemes: list[str]

class AgentCard(BaseModel):
    name: str
    description: str
    url: str
    version: str
    defaultInputModes: list[str]
    defaultOutputModes: list[str]
    capabilities: AgentCapabilities
    skills: list[AgentSkill]
    authentication: AgentAuthentication

async def get_exchange_rate(currency_from: str = 'USD', currency_to: str = 'EUR', currency_date: str = 'latest') -> dict:
    """
    Fetch the exchange rate between two currencies for a given date using the Frankfurter API.

    Args:
        currency_from (str): The source currency code (e.g., 'USD').
        currency_to (str): The target currency code (e.g., 'EUR').
        currency_date (str): The date for the exchange rate (e.g., 'latest' or '2023-01-01').

    Returns:
        dict: The API response containing exchange rate data or an error message.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f'https://api.frankfurter.app/{currency_date}',
                params={'from': currency_from, 'to': currency_to},
            )
            response.raise_for_status()
            data = response.json()
            return data
    except httpx.HTTPError as e:
        return {'error': f'API request failed: {e}'}

async def call_reporting_agent(conversion_result: dict, session_id: str = "default-session") -> dict:
    """LangGraph tool: Call the Reporting Agent to generate a report for a conversion result."""
    import httpx
    async with httpx.AsyncClient() as client:
        response = await client.post(
            'http://localhost:5002/a2a',
            json={
                'method': 'message/send',
                'params': {
                    'conversion_result': conversion_result,
                    'session_id': session_id
                }
            }
        )
        if response.status_code == 200:
            return response.json().get('result', {})
        else:
            return {'status': 'error', 'report': 'Failed to get report from Reporting Agent'}

class CurrencyAgent:
    SYSTEM_INSTRUCTION = "You are a helpful currency conversion agent."
    RESPONSE_FORMAT_INSTRUCTION = "Respond to the user in the ResponseFormat schema."
    SUPPORTED_CONTENT_TYPES = ["text/plain"]

    def __init__(self, host: str = 'localhost', port: int = 8000):
        api_key = SecretStr(GOOGLE_API_KEY) if GOOGLE_API_KEY else None
        self.model = ChatGoogleGenerativeAI(model="gemini-1.5-flash", api_key=api_key)
        self.tools = [get_exchange_rate, call_reporting_agent]
        self.agent_card = self.get_agent_card(host, port)
        # LangGraph integration
        self.memory = MemorySaver()
        self.graph = create_react_agent(
            self.model,
            tools=self.tools,
            checkpointer=self.memory,
            prompt=self.SYSTEM_INSTRUCTION,
            response_format=(self.RESPONSE_FORMAT_INSTRUCTION, ResponseFormat),
        )

    @staticmethod
    def get_agent_card(host: str, port: int) -> AgentCard:
        capabilities = AgentCapabilities(streaming=True, pushNotifications=True)
        skill = AgentSkill(
            id='convert_currency',
            name='Currency Exchange Rates Tool',
            description='Helps with exchange values between various currencies',
            tags=['currency conversion', 'currency exchange'],
            examples=['What is exchange rate between USD and GBP?'],
        )
        return AgentCard(
            name='Currency Agent',
            description='Helps with exchange rates for currencies',
            url=f'http://{host}:{port}/',
            version='1.0.0',
            defaultInputModes=CurrencyAgent.SUPPORTED_CONTENT_TYPES,
            defaultOutputModes=CurrencyAgent.SUPPORTED_CONTENT_TYPES,
            capabilities=capabilities,
            skills=[skill],
            authentication=AgentAuthentication(schemes=['public']),
        )

    def extract_currencies(self, query: str) -> tuple[str, str]:
        prompt = (
            f"""Extract the source and target currency codes from the following query. "
            f"Return as JSON: {{'from': 'USD', 'to': 'EUR'}}.\nQuery: {query}"""
        )
        response = self.model.invoke(prompt)
        print("[DEBUG] Gemini response for currency extraction:", response)
        import json
        try:
            response_text = str(response)
            data = json.loads(response_text.replace("'", '"'))
            currency_from = data.get('from', '')
            currency_to = data.get('to', '')
            if currency_from and currency_to:
                return currency_from, currency_to
        except Exception as e:
            print("[DEBUG] Gemini extraction failed:", e)
        # Fallback: regex extraction for 3-letter currency codes
        matches = re.findall(r'([A-Z]{3})', query)
        if len(matches) >= 2:
            print("[DEBUG] Fallback regex extraction:", matches[:2])
            return matches[0], matches[1]
        return '', ''

    async def invoke(self, query: str, session_id: str) -> dict[str, Any]:
        config: RunnableConfig = {'configurable': {'thread_id': session_id}}
        # Use LangGraph agent for reasoning and tool use
        result = await self.graph.ainvoke({'messages': [('user', query)]}, config)
        return self.get_agent_response(config)

    def get_agent_response(self, config: RunnableConfig) -> dict[str, Any]:
        # Simplified response for now
        return {'status': 'completed', 'message': 'Currency conversion completed'}

    async def stream(self, query: str, session_id: str) -> AsyncIterable[dict[str, Any]]:
        inputs: dict[str, Any] = {'messages': [('user', query)]}
        config: RunnableConfig = {'configurable': {'thread_id': session_id}}
        async for item in self.graph.astream(inputs, config, stream_mode='values'):
            message = item['messages'][-1]
            if isinstance(message, AIMessage) and getattr(message, 'tool_calls', None):
                yield {
                    'is_task_complete': False,
                    'require_user_input': False,
                    'content': 'Looking up the exchange rates...'
                }
            elif isinstance(message, ToolMessage):
                yield {
                    'is_task_complete': False,
                    'require_user_input': False,
                    'content': 'Processing the exchange rates...'
                }
        yield self.get_agent_response(config)

    async def invoke_with_reporting(self, query: str, session_id: str) -> dict[str, Any]:
        currency_from, currency_to = self.extract_currencies(query)
        if currency_from and currency_to:
            data = await get_exchange_rate(currency_from, currency_to)
            if 'error' in data:
                return ResponseFormat(status='error', message=data['error']).model_dump()
            rate = data.get('rates', {}).get(currency_to)
            if rate:
                conversion_result = {
                    'from': currency_from,
                    'to': currency_to,
                    'rate': rate,
                    'raw': data
                }
                # Send to Reporting Agent
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        'http://localhost:5002/a2a',
                        json={
                            'method': 'message/send',
                            'params': {
                                'conversion_result': conversion_result,
                                'session_id': session_id
                            }
                        }
                    )
                    if response.status_code == 200:
                        report = response.json().get('result', {})
                        return {
                            'status': 'completed',
                            'message': f"1 {currency_from} = {rate} {currency_to}",
                            'report': report
                        }
                    else:
                        return ResponseFormat(status='error', message='Failed to get report from Reporting Agent').model_dump()
            else:
                return ResponseFormat(status='error', message="Could not fetch rate.").model_dump()
        else:
            return ResponseFormat(status='input_required', message="Please specify both source and target currencies.").model_dump()
