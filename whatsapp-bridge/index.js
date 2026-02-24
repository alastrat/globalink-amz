const { Client, LocalAuth } = require("whatsapp-web.js");
const qrcode = require("qrcode-terminal");
const express = require("express");

// --- Config ---
const FBA_AGENT_URL = process.env.FBA_AGENT_URL || "http://fba-agent:8000";
const OWNER_NUMBER = process.env.OWNER_WHATSAPP_NUMBER || "";
const PORT = parseInt(process.env.BRIDGE_PORT || "3001", 10);
const ALLOWED_NUMBERS = (process.env.ALLOWED_NUMBERS || OWNER_NUMBER)
  .split(",")
  .map((n) => n.trim())
  .filter(Boolean);

// --- WhatsApp Client ---
const client = new Client({
  authStrategy: new LocalAuth({ dataPath: "/data/whatsapp-auth" }),
  puppeteer: {
    headless: true,
    args: [
      "--no-sandbox",
      "--disable-setuid-sandbox",
      "--disable-dev-shm-usage",
      "--disable-gpu",
      "--single-process",
    ],
  },
});

let isReady = false;

client.on("qr", (qr) => {
  console.log("\n========================================");
  console.log("  Scan this QR code with WhatsApp:");
  console.log("  (Phone > Settings > Linked Devices)");
  console.log("========================================\n");
  qrcode.generate(qr, { small: true });
});

client.on("ready", () => {
  isReady = true;
  console.log("[bridge] WhatsApp client ready!");
  if (OWNER_NUMBER) {
    const chatId = formatChatId(OWNER_NUMBER);
    client
      .sendMessage(chatId, "FBA Agent is online and ready. Send *help* for commands.")
      .catch(() => {});
  }
});

client.on("authenticated", () => {
  console.log("[bridge] WhatsApp authenticated (session saved)");
});

client.on("auth_failure", (msg) => {
  console.error("[bridge] WhatsApp auth failed:", msg);
});

client.on("disconnected", (reason) => {
  isReady = false;
  console.warn("[bridge] WhatsApp disconnected:", reason);
  console.log("[bridge] Attempting reconnect in 5s...");
  setTimeout(() => client.initialize(), 5000);
});

// --- Incoming WhatsApp messages ---
client.on("message", async (msg) => {
  // Ignore group messages, status updates, and media-only messages
  if (msg.isGroupMsg || msg.isStatus || !msg.body) return;

  const sender = msg.from.replace("@c.us", "");

  // Check allowlist (empty = allow all)
  if (ALLOWED_NUMBERS.length > 0) {
    const allowed = ALLOWED_NUMBERS.some(
      (n) => sender.endsWith(n) || n.endsWith(sender)
    );
    if (!allowed) {
      console.log(`[bridge] Blocked message from ${sender} (not in allowlist)`);
      return;
    }
  }

  console.log(`[bridge] Message from ${sender}: ${msg.body}`);

  try {
    const response = await fetch(`${FBA_AGENT_URL}/webhook/incoming`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        from_number: sender,
        message: msg.body,
      }),
    });

    if (!response.ok) {
      console.error(`[bridge] FBA agent returned ${response.status}`);
    }
  } catch (err) {
    console.error("[bridge] Failed to reach FBA agent:", err.message);
    await msg.reply("Agent is temporarily unavailable. Please try again.");
  }
});

// --- HTTP API for outbound messages ---
const app = express();
app.use(express.json());

app.get("/health", (_req, res) => {
  res.json({
    status: isReady ? "connected" : "disconnected",
    whatsapp: isReady,
  });
});

app.post("/send", async (req, res) => {
  const { to, message } = req.body;
  if (!message) return res.status(400).json({ error: "message required" });
  if (!isReady) return res.status(503).json({ error: "WhatsApp not connected" });

  const target = to || OWNER_NUMBER;
  if (!target) return res.status(400).json({ error: "no recipient" });

  try {
    const chatId = formatChatId(target);
    await client.sendMessage(chatId, message);
    res.json({ status: "sent", to: target });
  } catch (err) {
    console.error("[bridge] Send failed:", err.message);
    res.status(500).json({ error: err.message });
  }
});

// --- Helpers ---
function formatChatId(number) {
  const clean = number.replace(/[^0-9]/g, "");
  return `${clean}@c.us`;
}

// --- Start ---
app.listen(PORT, "0.0.0.0", () => {
  console.log(`[bridge] HTTP API listening on port ${PORT}`);
});

console.log("[bridge] Initializing WhatsApp client...");
client.initialize();
