from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from azure.identity import ClientSecretCredential
from azure.ai.projects import AIProjectClient
import asyncio
import os
from dotenv import load_dotenv
import re
from datetime import datetime
from utils.chat_history_models import (
    ConversationChat,
    ConversationChatInput,
    ConversationChatResponse,
    TokenUsage,
    Agent,
)

app = FastAPI()

load_dotenv()


class AgentRequest(BaseModel):
    agent_id: str
    message: str
    thread_id: str | None = None

    class Config:
        fields = {'agent_id': {'alias': 'agentid'}}
        allow_population_by_field_name = True


def get_project_client():
    credential = ClientSecretCredential(
        tenant_id=os.environ["AZURE_TENANT_ID"],
        client_id=os.environ["AZURE_CLIENT_ID"],
        client_secret=os.environ["AZURE_CLIENT_SECRET"],
    )
    return AIProjectClient(
        credential=credential,
        endpoint=os.environ["AIProjectEndpoint"]
    )


async def run_agent_logic(project_client, agent_id, message, thread_id=None):
    input_time = datetime.utcnow().isoformat()
    agent = project_client.agents.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agente '{agent_id}' no encontrado")

    if not thread_id:
        try:
            thread_response = project_client.agents.create_thread()
        except AttributeError:
            thread_response = project_client.agents.threads.create()
        thread_id = thread_response.id

    project_client.agents.messages.create(
        thread_id=thread_id,
        role="user",
        content=message
    )

    run = project_client.agents.runs.create(
        thread_id=thread_id,
        agent_id=agent.id
    )

    while run.status not in ("completed", "failed"):
        await asyncio.sleep(1)
        run = project_client.agents.runs.get(thread_id=thread_id, run_id=run.id)
        token_usage = None
        if run.usage:
            token_usage = {
                "prompt_tokens": run.usage.get("prompt_tokens"),
                "completion_tokens": run.usage.get("completion_tokens"),
                "total_tokens": run.usage.get("total_tokens")
            }
            print(f"Token usage from run: {token_usage}")

    agent_tools = None
    if run.tools:
        agent_tools = [str(tool) for tool in run.tools]
        print(f"Agent tools from run: {agent_tools}")
    messages = list(project_client.agents.messages.list(thread_id=thread_id))
    assistant_text = "No se encontró respuesta del agente."
    for msg in messages:
        if msg.role == "assistant" and msg.content:
            for part in msg.content:
                if part.get("type") == "text" and "value" in part.get("text", {}):
                    assistant_text = part["text"]["value"]
                    break
            break

    response_time = datetime.utcnow().isoformat()
    return {
        "message": assistant_text,
        "thread_id": thread_id,
        "agent_id": agent_id,
        "agent": agent.name,
        "description": agent.description,
        "token_usage": token_usage,
        "agent_tools": agent_tools,
        "input_time": input_time,
        "response_time": response_time
    }


def clean_response(text: str) -> str:
    """
    Elimina cualquier texto entre corchetes 【】, incluyendo los corchetes.
    """
    return re.sub(r"【.*?】", "", text).strip()


@app.post("/run-agent/")
async def run_agent(req: AgentRequest):
    project_client = get_project_client()

    # Paso 1: ejecutar agente de clasificación (selector)
    selector_result = await run_agent_logic(
        project_client,
        agent_id=os.environ["SELECTOR_AGENT_ID"],
        message=req.message,
        thread_id=req.thread_id
    )
    classification_response = selector_result["message"]
    selector_thread_id = selector_result["thread_id"]

    selector = classification_response.strip().lower()

    # Paso 2: redirigir según la categoría
    if selector == "faq":
        target_agent_id = os.environ["RAG_AGENT_ID"]
    elif selector == "estado de caso":
        target_agent_id = os.environ["CASE_AGENT_ID"]
    else:
        return {
            "message": f"{classification_response.strip()}",
            "threadId": selector_thread_id
        }

    # Ejecutar el agente final y retornar el diccionario completo
    final_result = await run_agent_logic(
        project_client,
        agent_id=target_agent_id,
        message=req.message,
        thread_id=selector_thread_id
    )

    final_result["message"] = clean_response(final_result["message"])
    save_interaction_to_cosmos(req, final_result)
    return {
        "message": final_result["message"],
        "threadId": final_result["thread_id"],
    }


def save_interaction_to_cosmos(req, result):
    chat_input = ConversationChatInput(
        message=req.message,
        datetime=result.get("input_time"),
    )
    agent_obj = Agent(
        agent_id=result.get("agent_id"),
        agent_name=result.get("agent"),
        agent_description=result.get("description"),
    )
    token_usage_obj = None
    if result.get("token_usage"):
        token_usage_obj = TokenUsage(**result["token_usage"])
    chat_response = ConversationChatResponse(
        agent_id=result.get("agent_id"),
        agent=agent_obj,
        agent_tools=result.get("agent_tools"),
        content=result.get("message"),
        datetime=result.get("response_time"),
        token_usage=token_usage_obj,
    )
    chat = ConversationChat(
        session_id=result.get("thread_id"),
        token_usage=token_usage_obj,
        request=chat_input,
        response=chat_response,
    )
    chat.save()
    print(f"Chat saved with session_id: {chat.session_id}")
    return chat
