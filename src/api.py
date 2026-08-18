"""
DriveTalk AI – FastAPI backend

Exposes the LangGraph agent over HTTP so the website (or any frontend)
can have a live "Try it" conversation.

Run:
  uvicorn src.api:app --reload --port 8000
"""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

load_dotenv()

from src.agent import chat as agent_chat
from src.mock_api import reset_store

app = FastAPI(
    title="DriveTalk AI",
    description="AI voice receptionist for auto dealerships",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    history: list[dict[str, Any]] = Field(default_factory=list)


class ChatResponse(BaseModel):
    reply: str
    history: list[dict[str, Any]]


class HealthResponse(BaseModel):
    status: str
    dealership: str
    provider: str


@app.get("/health", response_model=HealthResponse)
def health():
    return {
        "status": "ok",
        "dealership": os.getenv("DEALERSHIP_NAME", "Apex Motors"),
        "provider": os.getenv("LLM_PROVIDER", "openai"),
    }


@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(body: ChatRequest):
    """
    One turn of conversation with the DriveTalk agent.
    Pass previous history to keep context.
    """
    try:
        from langchain_core.messages import AIMessage, HumanMessage

        lc_history = []
        for m in body.history:
            role = m.get("role")
            content = m.get("content", "")
            if role == "user":
                lc_history.append(HumanMessage(content=content))
            elif role == "assistant":
                lc_history.append(AIMessage(content=content))

        reply, new_messages = agent_chat(body.message, lc_history)

        serial_history = []
        for m in new_messages:
            if isinstance(m, HumanMessage):
                serial_history.append({"role": "user", "content": m.content})
            elif isinstance(m, AIMessage) and m.content and not getattr(m, "tool_calls", None):
                serial_history.append({"role": "assistant", "content": m.content})

        return {"reply": reply, "history": serial_history}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/reset")
def reset():
    """Clear mock appointments (useful for demos)."""
    reset_store()
    return {"status": "reset"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.api:app", host="0.0.0.0", port=8000, reload=True)
