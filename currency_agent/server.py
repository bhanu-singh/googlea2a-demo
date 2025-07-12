from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn
import asyncio
from currency_agent.agent import CurrencyAgent
from currency_agent.executor import CurrencyAgentExecutor

app = FastAPI()

# Instantiate agent and executor
agent = CurrencyAgent(host='localhost', port=5001)
executor = CurrencyAgentExecutor(agent)

@app.post("/a2a")
async def a2a_endpoint(request: Request):
    data = await request.json()
    method = data.get("method")
    params = data.get("params", {})
    session_id = params.get("session_id", "default-session")
    query = params.get("query", "")

    if method == "message/send":
        result = await executor.on_message_send(query, session_id)
        return JSONResponse({"result": result})
    elif method == "message/stream":
        # For demonstration, stream as a list (real SSE would be more complex)
        results = []
        async for chunk in executor.on_message_stream(query, session_id):
            results.append(chunk)
        return JSONResponse({"result": results})
    elif method == "message/send_with_report":
        result = await executor.on_message_send_with_report(query, session_id)
        return JSONResponse({"result": result})
    else:
        return JSONResponse({"error": "Unknown method"}, status_code=400)

if __name__ == "__main__":
    uvicorn.run("currency_agent.server:app", host="0.0.0.0", port=5001, reload=True)
