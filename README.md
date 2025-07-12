# 🏃‍♂️ Execution Steps for Two-Agent A2A System

## Introduction

This project demonstrates a modular, agent-to-agent (A2A) architecture for intelligent automation using the A2A protocol. The system consists of two independent agents: a Currency Agent (Agent A) that performs real-time currency conversion using a large language model (Gemini) and an exchange rate API, and a Reporting Agent (Agent B) that generates human-friendly reports based on the conversion results. Each agent is implemented as a standalone FastAPI service, exposing its capabilities and endpoints via an A2A-compliant interface.

The workflow showcases how agents can collaborate by delegating tasks and exchanging structured artifacts. When a user requests a currency conversion, Agent A processes the request, then automatically calls Agent B to summarize the result. This design pattern enables scalable, composable AI systems where specialized agents can be orchestrated to solve complex tasks, and new capabilities can be added by simply introducing new agents to the network.

## 1. Install Dependencies

Make sure you have all required Python packages installed:

```sh
uv sync
```

This will install all dependencies listed in `pyproject.toml`.

---

## 2. Set Up Your API Key

Create a `.env` file in your project root with your Gemini API key:

```
GOOGLE_API_KEY=your_actual_gemini_api_key_here
```

---

## 3. Start the Reporting Agent (Agent B)

In one terminal, run:

```sh
uv run uvicorn reporting_agent.server:app --host 0.0.0.0 --port 5002 --reload
```
This will start the Reporting Agent on port 5002.

---

## 4. Start the Currency Agent (Agent A)

In another terminal, run:

```sh
uv run uvicorn currency_agent.server:app --host 0.0.0.0 --port 5001 --reload
```
This will start the Currency Agent on port 5001.

---

## 5. Send a Test Request

You can use `curl`, `httpie`, or Postman. Here’s a `curl` example:

```sh
curl -X POST http://localhost:5001/a2a \
  -H "Content-Type: application/json" \
  -d '{
    "method": "message/send_with_report",
    "params": {
      "query": "What is the exchange rate between USD and EUR?",
      "session_id": "test-session"
    }
  }'
```

---

## 6. Expected Output

You should receive a response like:

```json
{
  "result": {
    "status": "completed",
    "message": "1 USD = 0.85 EUR",
    "report": {
      "status": "completed",
      "report": "On July 8th, 2025, 1 US dollar (USD) was equivalent to 0.85 euros (EUR).\n"
    }
  }
}
```

---

## 7. Troubleshooting

- Ensure both servers are running and accessible.
- Check your `.env` file and Gemini API key if you see authentication errors.
- Review terminal logs for error messages if the workflow fails. 