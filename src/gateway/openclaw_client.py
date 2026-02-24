"""Client for sending outbound WhatsApp messages via the bridge."""
import os
import httpx


BRIDGE_URL = os.getenv("WHATSAPP_BRIDGE_URL", "http://whatsapp-bridge:3001")


async def send_whatsapp_message(to: str, message: str):
    """Send a message via the WhatsApp bridge HTTP API."""
    async with httpx.AsyncClient() as client:
        try:
            await client.post(
                f"{BRIDGE_URL}/send",
                json={"to": to, "message": message},
                timeout=10,
            )
        except httpx.RequestError:
            print(f"[bridge] Failed to send message to {to}: {message[:100]}...")
