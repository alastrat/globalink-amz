"""Client for sending outbound messages via OpenClaw's hooks API."""
import os
import httpx


OPENCLAW_URL = os.getenv("OPENCLAW_URL", "http://localhost:18789")


async def send_whatsapp_message(to: str, message: str):
    """Send a message via OpenClaw's WhatsApp gateway at port 18789."""
    async with httpx.AsyncClient() as client:
        try:
            await client.post(
                f"{OPENCLAW_URL}/hooks/agent",
                json={"to": to, "message": message},
                timeout=10,
            )
        except httpx.RequestError:
            print(f"[OpenClaw] Failed to send message to {to}: {message[:100]}...")
