"""
LangGraph agent for DriveTalk AI.

Uses tool-calling (ReAct style) so the LLM can check slots, book, reschedule,
and escalate when needed.
"""

from __future__ import annotations

import os
from typing import Annotated, Literal, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

load_dotenv()




from src.mock_api import (
    book_appointment,
    get_available_slots,
    reschedule_appointment,
)


@tool
def check_available_slots(
    preferred_date: str = "",
    service: str = "general service",
    limit: int = 5,
) -> str:
    """
    Check open service appointment slots.
    preferred_date: optional YYYY-MM-DD or leave empty for next available.
    service: e.g. "oil change", "brake inspection", "tire rotation".
    Returns a short list of available date-times and bays.
    """
    slots = get_available_slots(
        service=service or None,
        preferred_date=preferred_date or None,
        limit=limit,
    )
    if not slots:
        return "No open slots found for that criteria. Try another day or leave preferred_date empty."
    lines = [f"- {s['datetime']} ({s['bay']})" for s in slots]
    return "Available slots:\n" + "\n".join(lines)


@tool
def book_service_appointment(
    customer_name: str,
    phone: str,
    vehicle: str,
    service: str,
    datetime_str: str,
    notes: str = "",
) -> str:
    """
    Book a confirmed service appointment.
    datetime_str must be one of the exact values returned by check_available_slots
    (format: YYYY-MM-DD HH:MM).
    Returns confirmation code on success.
    """
    result = book_appointment(
        customer_name=customer_name,
        phone=phone,
        vehicle=vehicle,
        service=service,
        datetime_str=datetime_str,
        notes=notes,
    )
    if result.get("success"):
        return (
            f"SUCCESS. Confirmation code: {result['confirmation_code']}. "
            f"{result['message']} Bay: {result['bay']}."
        )
    return f"FAILED: {result.get('error', 'unknown error')}"


@tool
def reschedule_service_appointment(
    confirmation_code: str,
    new_datetime: str,
) -> str:
    """
    Reschedule an existing appointment to a new open slot.
    new_datetime must come from check_available_slots.
    """
    result = reschedule_appointment(confirmation_code, new_datetime)
    if result.get("success"):
        return (
            f"SUCCESS. {result['message']} New bay: {result['bay']}. "
            f"Code remains {result['confirmation_code']}."
        )
    return f"FAILED: {result.get('error', 'unknown error')}"


@tool
def escalate_to_human(
    reason: str,
    customer_summary: str = "",
    urgency: Literal["low", "medium", "high"] = "medium",
) -> str:
    """
    Escalate the call to a human advisor / service manager.
    Use for: angry customers, complex technical diagnosis, warranty disputes,
    sales questions that need a specialist, or anything outside booking scope.
    """
    
    return (
        f"ESCALATION TRIGGERED (urgency={urgency}). "
        f"Reason: {reason}. Summary: {customer_summary or 'n/a'}. "
        "A human team member will take over shortly. "
        "Please stay on the line or leave a callback number."
    )


TOOLS = [
    check_available_slots,
    book_service_appointment,
    reschedule_service_appointment,
    escalate_to_human,
]




def _get_llm():
    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    model_name = os.getenv("LLM_MODEL", "gpt-4o-mini")

    if provider == "groq":
        from langchain_groq import ChatGroq
        return ChatGroq(model=model_name, temperature=0.3)
    else:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model_name, temperature=0.3)



DEALERSHIP = os.getenv("DEALERSHIP_NAME", "Apex Motors")
LOCATION = os.getenv("DEALERSHIP_LOCATION", "Downtown Service Center")

SYSTEM_PROMPT = f"""You are DriveTalk, the friendly and professional AI voice receptionist for {DEALERSHIP} ({LOCATION}).

Your job:
1. Greet callers warmly and identify what they need (service appointment, reschedule, parts, sales, complaint…).
2. For service booking / reschedule → use the tools to check real slots and confirm bookings.
3. Collect: customer name, phone, vehicle (year/make/model), service type, preferred time.
4. Always confirm the final booking details and give the confirmation code.
5. If the request is outside your scope (complex diagnosis, angry customer, financing, test-drive scheduling that needs a salesperson, legal/warranty dispute) → call escalate_to_human.
6. Keep responses concise and natural for voice (1-3 short sentences). Avoid long lists unless the caller asks.
7. Never invent available times – always call check_available_slots first.
8. Today’s date context is handled by the tools; you can say “tomorrow”, “this Thursday”, etc. and the tools will resolve.

Tone: helpful, calm, dealership-professional, a little warm. You sound like a real service advisor who answers the phone.

If the caller just says “hello” or is silent, introduce yourself and ask how you can help.
"""



class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


def agent_node(state: AgentState):
    llm = _get_llm().bind_tools(TOOLS)
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = llm.invoke(messages)
    return {"messages": [response]}


def should_continue(state: AgentState) -> Literal["tools", "end"]:
    last = state["messages"][-1]
    if isinstance(last, AIMessage) and last.tool_calls:
        return "tools"
    return "end"


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(TOOLS))

    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", "end": END})
    graph.add_edge("tools", "agent")

    return graph.compile()


_agent = None


def get_agent():
    global _agent
    if _agent is None:
        _agent = build_graph()
    return _agent


def chat(user_input: str, history: list | None = None) -> tuple[str, list]:
    """
    One turn of conversation.
    Returns (assistant_text, updated_history).
    """
    agent = get_agent()
    if history is None:
        history = []

    history = history + [HumanMessage(content=user_input)]
    result = agent.invoke({"messages": history})
    new_messages = result["messages"]

    reply = ""
    for msg in reversed(new_messages):
        if isinstance(msg, AIMessage) and msg.content and not msg.tool_calls:
            reply = msg.content
            break
        if isinstance(msg, AIMessage) and msg.content:
            reply = msg.content
            break

    if not reply:
        reply = "I’m transferring you to a team member now. Please hold."

    return reply, new_messages
