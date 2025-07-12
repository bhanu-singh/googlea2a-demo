from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn
import asyncio
from reporting_agent.agent import ReportingAgent
from reporting_agent.executor import ReportingAgentExecutor

app = FastAPI()

# Instantiate agent and executor
agent = ReportingAgent(host='localhost', port=5002)
executor = ReportingAgentExecutor(agent)

@app.post("/a2a")
async def a2a_endpoint(request: Request):
    data = await request.json()
    method = data.get("method")
    params = data.get("params", {})
    session_id = params.get("session_id", "default-session")
    conversion_result = params.get("conversion_result", {})

    if method == "message/send":
        result = await executor.on_message_send(conversion_result, session_id)
        return JSONResponse({"result": result})
    elif method == "message/stream":
        # For demonstration, stream as a list (real SSE would be more complex)
        results = []
        async for chunk in executor.on_message_stream(conversion_result, session_id):
            results.append(chunk)
        return JSONResponse({"result": results})
    else:
        return JSONResponse({"error": "Unknown method"}, status_code=400)

if __name__ == "__main__":
    uvicorn.run("reporting_agent.server:app", host="0.0.0.0", port=5002, reload=True)
