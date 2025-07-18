import os
from collections.abc import AsyncIterable
from typing import Any, Literal
from uuid import uuid4

import httpx
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel
from dotenv import load_dotenv

from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (
    MessageSendParams,
    SendMessageRequest,
)

load_dotenv()

memory = MemorySaver()


@tool
def get_exchange_rate(
    currency_from: str = 'USD',
    currency_to: str = 'EUR',
    currency_date: str = 'latest',
):
    """Use this to get current exchange rate.

    Args:
        currency_from: The currency to convert from (e.g., "USD").
        currency_to: The currency to convert to (e.g., "EUR").
        currency_date: The date for the exchange rate or "latest". Defaults to
            "latest".

    Returns:
        A dictionary containing the exchange rate data, or an error message if
        the request fails.
    """
    try:
        response = httpx.get(
            f'https://api.frankfurter.app/{currency_date}',
            params={'from': currency_from, 'to': currency_to},
        )
        response.raise_for_status()

        data = response.json()
        if 'rates' not in data:
            return {'error': 'Invalid API response format.'}
        return data
    except httpx.HTTPError as e:
        return {'error': f'API request failed: {e}'}
    except ValueError:
        return {'error': 'Invalid JSON response from API.'}


@tool
async def call_reporting_agent(conversion_result: dict, session_id: str = "default-session"):
    """Call the Reporting Agent to generate a report for a conversion result using A2A protocol.
    
    Args:
        conversion_result: The currency conversion result data containing from, to, rate, and raw data
        session_id: Session identifier for the request
        
    Returns:
        A dictionary containing the report or error information
    """
    try:
        reporting_agent_url = 'http://localhost:5002'
        
        async with httpx.AsyncClient(timeout=30.0) as httpx_client:
            # Initialize A2A client for reporting agent
            resolver = A2ACardResolver(
                httpx_client=httpx_client,
                base_url=reporting_agent_url,
            )
            
            # Get the reporting agent card
            agent_card = await resolver.get_agent_card()
            client = A2AClient(httpx_client=httpx_client, agent_card=agent_card)
            
            # Prepare the message for the reporting agent
            import json
            message_text = f"Generate a comprehensive report for this currency conversion: {json.dumps(conversion_result, indent=2)}"
            
            # Create A2A request
            request = SendMessageRequest(
                id=str(uuid4()),
                params=MessageSendParams(
                    message={
                        'role': 'user',
                        'parts': [{'kind': 'text', 'text': message_text}],
                        'messageId': uuid4().hex,
                    }
                )
            )
            
            # Send request to reporting agent
            response = await client.send_message(request)
            result = response.root.result
            
            if result.status.state == 'completed':
                # Extract the report from artifacts
                if hasattr(result, 'artifacts') and result.artifacts:
                    report_content = ""
                    for artifact in result.artifacts:
                        if artifact.parts:
                            for part in artifact.parts:
                                if hasattr(part, 'text'):
                                    report_content += part.text
                    
                    return {
                        'status': 'completed',
                        'report': report_content,
                        'summary': f"Generated report for {conversion_result.get('from', 'N/A')} to {conversion_result.get('to', 'N/A')} conversion",
                        'session_id': session_id
                    }
                else:
                    return {
                        'status': 'completed',
                        'report': 'Report generated but no content available',
                        'summary': 'Report generation completed',
                        'session_id': session_id
                    }
            else:
                return {
                    'status': 'error',
                    'report': f'Reporting agent returned status: {result.status.state}',
                    'summary': 'Report generation failed',
                    'session_id': session_id
                }
                
    except Exception as e:
        return {
            'status': 'error',
            'report': f'Error calling reporting agent: {str(e)}',
            'summary': 'Failed to connect to reporting agent',
            'session_id': session_id
        }


class ResponseFormat(BaseModel):
    """Respond to the user in this format."""

    status: Literal['input_required', 'completed', 'error'] = 'input_required'
    message: str


class CurrencyAgent:
    """CurrencyAgent - a specialized assistant for currency conversions."""

    SYSTEM_INSTRUCTION = (
        'You are a specialized assistant for currency conversions. '
        "Your primary purpose is to use the 'get_exchange_rate' tool to get currency exchange rates, "
        "and then use the 'call_reporting_agent' tool to generate comprehensive reports about the conversions. "
        'Always follow this workflow: 1) Get exchange rate, 2) Call reporting agent with the results. '
        'If the user asks about anything other than currency conversion or exchange rates, '
        'politely state that you cannot help with that topic and can only assist with currency-related queries. '
        'Do not attempt to answer unrelated questions or use tools for other purposes.'
    )

    FORMAT_INSTRUCTION = (
        'Set response status to input_required if the user needs to provide more information to complete the request. '
        'Set response status to error if there is an error while processing the request. '
        'Set response status to completed if the request is complete and both exchange rate and report have been generated.'
    )

    def __init__(self):
        model_source = os.getenv('model_source', 'google')
        if model_source == 'google':
            self.model = ChatGoogleGenerativeAI(model='gemini-2.0-flash')
        else:
            self.model = ChatOpenAI(
                model=os.getenv('TOOL_LLM_NAME'),
                openai_api_key=os.getenv('API_KEY', 'EMPTY'),
                openai_api_base=os.getenv('TOOL_LLM_URL'),
                temperature=0,
            )
        self.tools = [get_exchange_rate, call_reporting_agent]

        self.graph = create_react_agent(
            self.model,
            tools=self.tools,
            checkpointer=memory,
            prompt=self.SYSTEM_INSTRUCTION,
            response_format=(self.FORMAT_INSTRUCTION, ResponseFormat),
        )

    async def stream(self, query, context_id) -> AsyncIterable[dict[str, Any]]:
        inputs = {'messages': [('user', query)]}
        config = {'configurable': {'thread_id': context_id}}

        for item in self.graph.stream(inputs, config, stream_mode='values'):
            message = item['messages'][-1]
            if (
                isinstance(message, AIMessage)
                and message.tool_calls
                and len(message.tool_calls) > 0
            ):
                # Check which tool is being called
                tool_name = message.tool_calls[0].get('name', '')
                if tool_name == 'get_exchange_rate':
                    yield {
                        'is_task_complete': False,
                        'require_user_input': False,
                        'content': 'Looking up the exchange rates...',
                    }
                elif tool_name == 'call_reporting_agent':
                    yield {
                        'is_task_complete': False,
                        'require_user_input': False,
                        'content': 'Generating comprehensive report...',
                    }
                else:
                    yield {
                        'is_task_complete': False,
                        'require_user_input': False,
                        'content': 'Processing your request...',
                    }
            elif isinstance(message, ToolMessage):
                yield {
                    'is_task_complete': False,
                    'require_user_input': False,
                    'content': 'Processing the results...',
                }

        yield self.get_agent_response(config)

    def get_agent_response(self, config):
        current_state = self.graph.get_state(config)
        structured_response = current_state.values.get('structured_response')
        if structured_response and isinstance(
            structured_response, ResponseFormat
        ):
            if structured_response.status == 'input_required':
                return {
                    'is_task_complete': False,
                    'require_user_input': True,
                    'content': structured_response.message,
                }
            if structured_response.status == 'error':
                return {
                    'is_task_complete': False,
                    'require_user_input': True,
                    'content': structured_response.message,
                }
            if structured_response.status == 'completed':
                return {
                    'is_task_complete': True,
                    'require_user_input': False,
                    'content': structured_response.message,
                }

        return {
            'is_task_complete': False,
            'require_user_input': True,
            'content': (
                'We are unable to process your request at the moment. '
                'Please try again.'
            ),
        }

    SUPPORTED_CONTENT_TYPES = ['text', 'text/plain']
