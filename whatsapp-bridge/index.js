/**
 * WhatsApp Bridge - Baileys-based
 *
 * Lightweight bridge that connects WhatsApp (via Baileys) to the FBA Agent API.
 * - Receives WhatsApp messages → forwards to FBA agent at /webhook/incoming
 * - Exposes /send endpoint for outbound messages from FBA agent
 * - Exposes /health endpoint for Docker health checks
 */
const {
  default: makeWASocket,
  useMultiFileAuthState,
  makeCacheableSignalKeyStore,
  DisconnectReason,
  Browsers,
} = require("@whiskeysockets/baileys");
const pino = require("pino");
const express = require("express");

// --- Config ---
const FBA_AGENT_URL = process.env.FBA_AGENT_URL || "http://fba-agent:8000";
const OWNER_NUMBER = process.env.OWNER_WHATSAPP_NUMBER || "";
const PORT = parseInt(process.env.BRIDGE_PORT || "3001", 10);
const AUTH_DIR = process.env.AUTH_DIR || "/data/whatsapp-auth";
const ALLOWED_NUMBERS = (process.env.ALLOWED_NUMBERS || OWNER_NUMBER)
  .split(",")
  .map((n) => n.trim())
  .filter(Boolean);

const logger = pino({ level: "warn" });
let sock = null;
let isReady = false;

// --- WhatsApp Connection ---
async function connectWhatsApp() {
  const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);

  sock = makeWASocket({
    auth: {
      creds: state.creds,
      keys: makeCacheableSignalKeyStore(state.keys, logger),
    },
    printQRInTerminal: false,
    logger,
    browser: Browsers.macOS("Chrome"),
  });

  sock.ev.on("connection.update", (update) => {
    const { connection, lastDisconnect, qr } = update;

    if (qr) {
      console.log("[bridge] QR code requested - auth credentials missing or expired.");
      console.log("[bridge] Run the auth script first: npx tsx src/whatsapp-auth.ts");
    }

    if (connection === "close") {
      isReady = false;
      const reason = lastDisconnect?.error?.output?.statusCode;
      const shouldReconnect = reason !== DisconnectReason.loggedOut;
      console.log(`[bridge] Disconnected (reason: ${reason}). Reconnect: ${shouldReconnect}`);

      if (shouldReconnect) {
        console.log("[bridge] Reconnecting in 3s...");
        setTimeout(connectWhatsApp, 3000);
      } else {
        console.error("[bridge] Logged out. Re-run auth script to re-authenticate.");
        process.exit(1);
      }
    }

    if (connection === "open") {
      isReady = true;
      console.log("[bridge] Connected to WhatsApp!");

      // Send startup message to owner
      if (OWNER_NUMBER) {
        const jid = formatJid(OWNER_NUMBER);
        sock.sendMessage(jid, { text: "FBA Agent is online and ready. Send *help* for commands." })
          .catch(() => {});
      }
    }
  });

  sock.ev.on("creds.update", saveCreds);

  // --- Incoming messages ---
  sock.ev.on("messages.upsert", async ({ messages }) => {
    for (const msg of messages) {
      if (!msg.message) continue;
      const remoteJid = msg.key.remoteJid;
      if (!remoteJid || remoteJid === "status@broadcast") continue;

      // Skip group messages
      if (remoteJid.endsWith("@g.us")) continue;

      // Skip own outgoing messages
      if (msg.key.fromMe) continue;

      // Extract text content
      const content =
        msg.message?.conversation ||
        msg.message?.extendedTextMessage?.text ||
        msg.message?.imageMessage?.caption ||
        msg.message?.videoMessage?.caption ||
        "";

      if (!content) continue;

      const sender = remoteJid.replace("@s.whatsapp.net", "");

      // Check allowlist
      if (ALLOWED_NUMBERS.length > 0) {
        const allowed = ALLOWED_NUMBERS.some(
          (n) => sender.endsWith(n) || n.endsWith(sender)
        );
        if (!allowed) {
          console.log(`[bridge] Blocked message from ${sender} (not in allowlist)`);
          continue;
        }
      }

      console.log(`[bridge] Message from ${sender}: ${content}`);

      try {
        const response = await fetch(`${FBA_AGENT_URL}/webhook/incoming`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            from_number: sender,
            message: content,
          }),
        });

        if (!response.ok) {
          console.error(`[bridge] FBA agent returned ${response.status}`);
        }
      } catch (err) {
        console.error("[bridge] Failed to reach FBA agent:", err.message);
        await sock.sendMessage(remoteJid, {
          text: "Agent is temporarily unavailable. Please try again.",
        }).catch(() => {});
      }
    }
  });
}

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
    const jid = formatJid(target);
    await sock.sendMessage(jid, { text: message });
    res.json({ status: "sent", to: target });
  } catch (err) {
    console.error("[bridge] Send failed:", err.message);
    res.status(500).json({ error: err.message });
  }
});

// --- Helpers ---
function formatJid(number) {
  const clean = number.replace(/[^0-9]/g, "");
  return `${clean}@s.whatsapp.net`;
}

// --- Start ---
app.listen(PORT, "0.0.0.0", () => {
  console.log(`[bridge] HTTP API listening on port ${PORT}`);
});

console.log("[bridge] Initializing WhatsApp (Baileys)...");
connectWhatsApp().catch((err) => {
  console.error("[bridge] Fatal:", err);
  process.exit(1);
});
