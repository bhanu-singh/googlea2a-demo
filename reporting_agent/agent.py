import os
from collections.abc import AsyncIterable
from typing import Any, Literal

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

memory = MemorySaver()


@tool
def generate_currency_report(conversion_result: dict, session_id: str = "default-session"):
    """Generate a detailed report for currency conversion results.

    Args:
        conversion_result: The currency conversion result data containing from, to, rate, and raw data
        session_id: Session identifier for the request

    Returns:
        A dictionary containing the generated report or error information
    """
    try:
        from_currency = conversion_result.get('from', 'N/A')
        to_currency = conversion_result.get('to', 'N/A')
        rate = conversion_result.get('rate', 'N/A')
        raw_data = conversion_result.get('raw', {})
        
        # Generate a comprehensive report
        report = f"""
Currency Conversion Report
========================

Conversion Details:
- From: {from_currency}
- To: {to_currency}
- Exchange Rate: {rate}
- Date: {raw_data.get('date', 'N/A')}

Analysis:
This conversion shows the current exchange rate between {from_currency} and {to_currency}.
The rate of {rate} means that 1 {from_currency} equals {rate} {to_currency}.

Raw API Response:
{raw_data}

Session ID: {session_id}
Report Generated Successfully
"""
        
        return {
            'status': 'completed',
            'report': report.strip(),
            'summary': f"Generated report for {from_currency} to {to_currency} conversion"
        }
    except Exception as e:
        return {
            'status': 'error',
            'report': f'Error generating report: {str(e)}',
            'summary': 'Report generation failed'
        }


@tool
def format_conversion_summary(conversion_result: dict):
    """Format a brief summary of the conversion result.
    
    Args:
        conversion_result: The currency conversion result data
        
    Returns:
        A formatted summary string
    """
    try:
        from_currency = conversion_result.get('from', 'N/A')
        to_currency = conversion_result.get('to', 'N/A')
        rate = conversion_result.get('rate', 'N/A')
        
        summary = f"Conversion Summary: 1 {from_currency} = {rate} {to_currency}"
        return {'summary': summary, 'status': 'completed'}
    except Exception as e:
        return {'summary': f'Error formatting summary: {str(e)}', 'status': 'error'}


class ResponseFormat(BaseModel):
    """Respond to the user in this format."""

    status: Literal['input_required', 'completed', 'error'] = 'input_required'
    message: str


class ReportingAgent:
    """ReportingAgent - a specialized assistant for generating currency conversion reports."""

    SYSTEM_INSTRUCTION = (
        'You are a specialized assistant for generating currency conversion reports. '
        "Your sole purpose is to use the 'generate_currency_report' and 'format_conversion_summary' tools to create reports about currency conversions. "
        'If the user asks about anything other than currency reporting or conversion summaries, '
        'politely state that you cannot help with that topic and can only assist with currency reporting queries. '
        'Do not attempt to answer unrelated questions or use tools for other purposes.'
    )

    FORMAT_INSTRUCTION = (
        'Set response status to input_required if the user needs to provide more information to complete the request. '
        'Set response status to error if there is an error while processing the request. '
        'Set response status to completed if the request is complete.'
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
        self.tools = [generate_currency_report, format_conversion_summary]

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
                yield {
                    'is_task_complete': False,
                    'require_user_input': False,
                    'content': 'Generating currency conversion report...',
                }
            elif isinstance(message, ToolMessage):
                yield {
                    'is_task_complete': False,
                    'require_user_input': False,
                    'content': 'Processing report data...',
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

    SUPPORTED_CONTENT_TYPES = ['text', 'text/plain', 'application/json']
