"""FastAPI HTTP server bridging WhatsApp and CrewAI agents.

Architecture:
- WhatsApp bridge (Baileys, port 3001) forwards messages here
- This app on port 8000: health, webhook, send endpoints
- Commands route to DB queries or CrewAI workflows via command_router
"""
import os
import traceback
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel

from gateway.whatsapp_handler import parse_command, get_help_message
from gateway.openclaw_client import send_whatsapp_message
from gateway.command_router import route_command

app = FastAPI(title="FBA Agent Gateway")

OWNER_PHONE = os.getenv("OWNER_WHATSAPP_NUMBER", "")


class IncomingMessage(BaseModel):
    from_number: str = ""
    message: str = ""


class OutgoingMessage(BaseModel):
    to: str = ""
    message: str = ""


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/webhook/incoming")
async def handle_incoming(msg: IncomingMessage, background_tasks: BackgroundTasks):
    """Receive messages from WhatsApp bridge and process them."""
    command, args = parse_command(msg.message)

    if command == "help":
        await send_whatsapp_message(msg.from_number, get_help_message())
    elif command == "skip":
        await send_whatsapp_message(msg.from_number, "Noted. No action taken.")
    elif command == "unknown":
        await send_whatsapp_message(
            msg.from_number,
            f'Command not recognized: "{msg.message}". Send "help" for available commands.',
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
    """Process a parsed command by routing to the appropriate handler."""
    target = from_number or OWNER_PHONE
    try:
        handled = await route_command(command, args, target)
        if not handled:
            await send_whatsapp_message(
                target,
                f'Command "{command}" is not yet implemented.',
            )
    except Exception:
        traceback.print_exc()
        await send_whatsapp_message(
            target,
            f"Error processing {command}. Please try again or send \"help\".",
        )
