"""FastAPI HTTP server bridging WhatsApp (OpenClaw) and CrewAI agents.

Architecture:
- OpenClaw (port 18789) handles WhatsApp via Baileys
- This app exposes two interfaces:
  1. Port 8000: Internal API (health, webhook, send)
  2. /v1/chat/completions: OpenAI-compatible endpoint for OpenClaw to call
"""
import os
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel

from gateway.whatsapp_handler import parse_command, get_help_message
from gateway.openclaw_client import send_whatsapp_message

app = FastAPI(title="FBA Agent Gateway")

OWNER_PHONE = os.getenv("OWNER_WHATSAPP_NUMBER", "")


class IncomingMessage(BaseModel):
    from_number: str = ""
    message: str = ""


class OutgoingMessage(BaseModel):
    to: str = ""
    message: str = ""


# -- OpenAI-compatible endpoint for OpenClaw --

class ChatMessage(BaseModel):
    role: str = "user"
    content: str = ""

class ChatCompletionRequest(BaseModel):
    model: str = "fba-agent"
    messages: list[ChatMessage] = []

class ChatCompletionChoice(BaseModel):
    index: int = 0
    message: ChatMessage
    finish_reason: str = "stop"

class ChatCompletionResponse(BaseModel):
    id: str = "chatcmpl-fba"
    object: str = "chat.completion"
    choices: list[ChatCompletionChoice] = []


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/v1/chat/completions")
async def openai_compatible_endpoint(req: ChatCompletionRequest, background_tasks: BackgroundTasks):
    """OpenAI-compatible endpoint that OpenClaw calls for AI responses.

    OpenClaw sends user WhatsApp messages here as chat completion requests.
    We parse the command and return a response immediately, queuing heavy work.
    """
    user_message = ""
    for msg in req.messages:
        if msg.role == "user":
            user_message = msg.content
            break

    if not user_message:
        reply = "No message received."
    else:
        command, args = parse_command(user_message)
        if command == "help":
            reply = get_help_message()
        elif command == "skip":
            reply = "Noted. No action taken."
        elif command == "unknown":
            reply = f'Command not recognized: "{user_message}". Send "help" for available commands.'
        else:
            background_tasks.add_task(process_command, command, args)
            reply = f"Processing: {command}..."

    return ChatCompletionResponse(
        choices=[
            ChatCompletionChoice(
                message=ChatMessage(role="assistant", content=reply)
            )
        ]
    )


@app.post("/webhook/incoming")
async def handle_incoming(msg: IncomingMessage, background_tasks: BackgroundTasks):
    """Receive messages from direct webhook and process them."""
    command, args = parse_command(msg.message)

    if command == "help":
        await send_whatsapp_message(msg.from_number, get_help_message())
    elif command == "unknown":
        await send_whatsapp_message(
            msg.from_number,
            f'Command not recognized: "{msg.message}". Send "help" for available commands.'
        )
    else:
        background_tasks.add_task(process_command, command, args, msg.from_number)
        await send_whatsapp_message(msg.from_number, f"Processing: {command}...")

    return {"status": "received"}


@app.post("/api/send")
async def send_message(msg: OutgoingMessage):
    """API endpoint for internal services to send WhatsApp messages."""
    await send_whatsapp_message(msg.to or OWNER_PHONE, msg.message)
    return {"status": "sent"}


async def process_command(command: str, args: list[str], from_number: str = ""):
    """Process a parsed command by invoking the appropriate workflow."""
    target = from_number or OWNER_PHONE
    await send_whatsapp_message(target, f"Processed command: {command} with args: {args}")
