import os
from pydantic import BaseModel, SecretStr
from typing import Literal, Any, AsyncIterable
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv(dotenv_path=os.path.join(os.getcwd(), ".env"))
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

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

class ChatModel:
    def __init__(self, model: str):
        self.model = model
        api_key = SecretStr(GOOGLE_API_KEY) if GOOGLE_API_KEY else None
        self.llm = ChatGoogleGenerativeAI(model=model, api_key=api_key)
    def chat(self, prompt: str) -> str:
        response = self.llm.invoke(prompt)
        return str(response.content) if hasattr(response, 'content') else str(response)

class ReportFormat(BaseModel):
    status: Literal['completed', 'error'] = 'completed'
    report: str

class ReportingAgent:
    SYSTEM_INSTRUCTION = "You are a helpful reporting agent. Summarize currency conversion results."
    RESPONSE_FORMAT_INSTRUCTION = "Respond to the user in the ReportFormat schema."
    SUPPORTED_CONTENT_TYPES = ["application/json"]

    def __init__(self, host: str = 'localhost', port: int = 5002):
        self.model = ChatModel(model='gemini-1.5-flash')
        self.agent_card = self.get_agent_card(host, port)

    @staticmethod
    def get_agent_card(host: str, port: int) -> AgentCard:
        capabilities = AgentCapabilities(streaming=True, pushNotifications=True)
        skill = AgentSkill(
            id='summarize_conversion',
            name='Currency Conversion Report Tool',
            description='Generates a summary report for currency conversion results',
            tags=['report', 'summary', 'currency conversion'],
            examples=['Summarize: 100 USD = 90 EUR'],
        )
        return AgentCard(
            name='Reporting Agent',
            description='Generates reports for currency conversion results',
            url=f'http://{host}:{port}/',
            version='1.0.0',
            defaultInputModes=ReportingAgent.SUPPORTED_CONTENT_TYPES,
            defaultOutputModes=ReportingAgent.SUPPORTED_CONTENT_TYPES,
            capabilities=capabilities,
            skills=[skill],
            authentication=AgentAuthentication(schemes=['public']),
        )

    async def summarize(self, conversion_result: dict, session_id: str) -> dict[str, Any]:
        prompt = (
            f"Summarize the following currency conversion result in a user-friendly report.\n"
            f"Result: {conversion_result}"
        )
        try:
            report = self.model.chat(prompt)
            return ReportFormat(status='completed', report=report).model_dump()
        except Exception as e:
            return ReportFormat(status='error', report=str(e)).model_dump()

    async def stream(self, conversion_result: dict, session_id: str) -> AsyncIterable[dict[str, Any]]:
        yield {'is_task_complete': False, 'content': 'Generating report...'}
        result = await self.summarize(conversion_result, session_id)
        yield result
