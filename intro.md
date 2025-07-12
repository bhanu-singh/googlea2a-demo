# Currency & Reporting Agent System: Deep Dive

## Introduction

Welcome to the Currency & Reporting Agent System! This project demonstrates a modern, AI-powered approach to currency conversion and reporting, leveraging advanced language models, API integrations, and modular agent-based design. In this post, we'll explore the system from a high-level overview down to the code-level details, so you can understand both the architecture and the implementation.

---

## High-Level Overview

At its core, this project is composed of two main agents:

1. **Currency Agent**: Handles user queries about currency exchange rates, fetches real-time data from external APIs, and can trigger reporting actions.
2. **Reporting Agent**: Receives conversion results and generates structured reports, which can be used for logging, analytics, or user feedback.

The system is designed to:
- Accept natural language queries (e.g., "What is the exchange rate from USD to EUR?")
- Extract intent and relevant parameters using an LLM (Google Gemini)
- Fetch live exchange rates from a public API
- Optionally, generate a report via a secondary agent
- Respond in a structured, schema-validated format

---

## Low-Level (Component) Approach

### 1. **Agents as Services**
- Each agent (Currency, Reporting) runs as a separate service (with its own server entrypoint).
- Agents communicate via HTTP (REST-like) endpoints.
- Each agent exposes a clear API contract for interoperability.

### 2. **LLM Integration**
- The Currency Agent uses Google Gemini (via `google.generativeai`) to parse user queries and extract currency codes.
- The LLM is also used for reasoning and fallback extraction (with regex as backup).

### 3. **External API Usage**
- Currency rates are fetched from the [Frankfurter API](https://www.frankfurter.app/), a free and reliable source for exchange rates.
- HTTP requests are made asynchronously using `httpx` for performance.

### 4. **LangGraph & LangChain**
- The Currency Agent is built using LangGraph and LangChain, enabling advanced agent workflows, memory, and tool use.
- The agent can reason about which tools to use (e.g., fetch rate, call reporting agent) based on the query.

### 5. **Schema Validation & Response Formatting**
- All responses are validated and formatted using Pydantic models, ensuring consistency and reliability.
- The system supports streaming and push notifications for real-time feedback.

---

## Code-Level Approach

### Directory Structure
```
a2a/
  currency_agent/
    agent.py        # Main logic for currency agent
    executor.py     # Entrypoint for running the agent server
    server.py       # HTTP server for the agent
  reporting_agent/
    agent.py        # Main logic for reporting agent
    executor.py     # Entrypoint for running the reporting agent server
    server.py       # HTTP server for the reporting agent
  requirements.txt  # Python dependencies
  README.md         # Project overview
```

### Key Components

#### 1. **CurrencyAgent Class (`currency_agent/agent.py`)**
- **Initialization**: Sets up the LLM, tools, agent card (metadata), and LangGraph workflow.
- **extract_currencies**: Uses Gemini to extract currency codes from user queries, with regex fallback.
- **invoke / stream**: Handles user queries, invokes the agent workflow, and streams results.
- **invoke_with_reporting**: Orchestrates the full flow: extract currencies, fetch rate, call reporting agent, and return a structured response.

#### 2. **get_exchange_rate Function**
- Asynchronously fetches exchange rates from the Frankfurter API.
- Handles errors gracefully and returns structured data.

#### 3. **call_reporting_agent Function**
- Sends conversion results to the Reporting Agent via HTTP POST.
- Expects a report in response, or returns an error if the call fails.

#### 4. **Pydantic Models**
- Used for all data validation and response formatting (e.g., `ResponseFormat`, `AgentCard`).

#### 5. **LangGraph Integration**
- The agent is wrapped in a LangGraph workflow, enabling memory, tool use, and advanced reasoning.
- Memory is persisted using SQLite for session continuity.

---

## Example Flow

1. **User Query**: "How much is 100 USD in EUR today?"
2. **CurrencyAgent**:
    - Uses Gemini to extract 'USD' and 'EUR'.
    - Calls `get_exchange_rate('USD', 'EUR')`.
    - Receives the latest rate from the Frankfurter API.
    - Optionally, calls the Reporting Agent to generate a report.
    - Returns a structured response: `{"status": "completed", "message": "1 USD = 0.92 EUR", ...}`

---

## Google A2A Protocol: Agent-to-Agent Communication

### What is Google A2A Protocol?

The Google Agent-to-Agent (A2A) protocol is a specification for enabling structured, interoperable communication between autonomous agents. It defines a standard way for agents to exchange messages, invoke methods, and share data, regardless of their internal implementation or technology stack. The protocol is designed to:
- Promote interoperability between agents from different vendors or domains
- Standardize message formats and method invocation
- Enable secure, extensible, and discoverable agent interactions

### How is A2A Used in This Project?

In this project, the A2A protocol is used as the foundation for communication between the **Currency Agent** and the **Reporting Agent**. Here’s how it works:

1. **Message Structure**: When the Currency Agent needs to generate a report, it sends a POST request to the Reporting Agent’s endpoint (`/a2a`) with a JSON payload that follows the A2A method invocation pattern:
    ```json
    {
      "method": "message/send",
      "params": {
        "conversion_result": { ... },
        "session_id": "..."
      }
    }
    ```
    - `method`: Specifies the action to be performed (here, sending a message/report request).
    - `params`: Contains the data required for the method, such as the conversion result and session context.

2. **Standardized Endpoints**: Both agents expose endpoints that conform to the A2A protocol, making it easy to add, swap, or extend agents in the future.

3. **Response Handling**: The Reporting Agent processes the request and responds with a structured result, also following the A2A response format. This ensures that the Currency Agent can reliably interpret the outcome, whether it’s a successful report or an error.

4. **Extensibility**: By adhering to the A2A protocol, new agents (e.g., analytics, notification, or compliance agents) can be added to the ecosystem with minimal integration effort, as long as they support the same protocol.

### What Does the A2A Protocol Bring?

- **Interoperability**: Agents can be developed independently, in different languages or frameworks, as long as they speak the A2A protocol.
- **Discoverability**: Agents can advertise their capabilities and methods, making it easier for other agents to find and use them.
- **Security & Authentication**: The protocol can be extended to support authentication schemes, ensuring secure agent interactions.
- **Consistency**: Standardized message formats reduce ambiguity and integration bugs.

### Example: Two Agents Communicating via A2A

In this project, the workflow below demonstrates A2A in action:

1. **User asks for a currency conversion.**
2. **Currency Agent**:
    - Extracts currencies and fetches the exchange rate.
    - Prepares a `conversion_result` object.
    - Sends a message to the Reporting Agent using the A2A protocol:
      ```json
      {
        "method": "message/send",
        "params": {
          "conversion_result": { ... },
          "session_id": "..."
        }
      }
      ```
3. **Reporting Agent**:
    - Receives the A2A message.
    - Processes the conversion result and generates a report.
    - Responds with a structured result (e.g., `{ "status": "completed", "report": ... }`).
4. **Currency Agent**:
    - Receives the report and includes it in the final response to the user.

This pattern can be extended to any number of agents, each specializing in a different domain, all communicating seamlessly using the A2A protocol.

---

## Conclusion

This project demonstrates a modular, agent-based approach to building intelligent, API-driven services. By combining LLMs, external APIs, and robust Python frameworks, it provides a scalable foundation for more advanced automation and reporting workflows. Whether you're interested in AI agents, currency data, or modern Python architectures, this project offers a practical, extensible example. 