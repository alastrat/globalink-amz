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
  fetchLatestBaileysVersion,
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

// LID (Linked ID) to phone number mapping cache
// Baileys v7 uses LID JIDs (e.g. 12345@lid) instead of phone JIDs for some contacts
const lidToPhone = {};

// --- WhatsApp Connection ---
async function connectWhatsApp() {
  const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);
  const { version } = await fetchLatestBaileysVersion();
  console.log("[bridge] Using WA version:", version);

  sock = makeWASocket({
    auth: {
      creds: state.creds,
      keys: makeCacheableSignalKeyStore(state.keys, logger),
    },
    version,
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

      // Build LID→phone mapping from our own identity
      if (sock.user) {
        const phoneUser = sock.user.id?.split(":")[0];
        const lidUser = sock.user.lid?.split(":")[0];
        if (lidUser && phoneUser) {
          lidToPhone[lidUser] = phoneUser;
          console.log(`[bridge] LID mapping: ${lidUser} → ${phoneUser}`);
        }
      }

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

      // Resolve sender: translate LID to phone number if needed
      const { phoneNumber, replyJid } = await resolveJid(remoteJid);

      // Check allowlist
      if (ALLOWED_NUMBERS.length > 0) {
        const allowed = ALLOWED_NUMBERS.some(
          (n) => phoneNumber.endsWith(n) || n.endsWith(phoneNumber)
        );
        if (!allowed) {
          console.log(`[bridge] Blocked message from ${phoneNumber} (JID: ${remoteJid}, not in allowlist)`);
          continue;
        }
      }

      console.log(`[bridge] Message from ${phoneNumber}: ${content}`);

      try {
        const response = await fetch(`${FBA_AGENT_URL}/webhook/incoming`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            from_number: phoneNumber,
            message: content,
          }),
        });

        if (!response.ok) {
          console.error(`[bridge] FBA agent returned ${response.status}`);
        }
      } catch (err) {
        console.error("[bridge] Failed to reach FBA agent:", err.message);
        await sock.sendMessage(replyJid, {
          text: "Agent is temporarily unavailable. Please try again.",
        }).catch(() => {});
      }
    }
  });
}

/**
 * Resolve a JID to a phone number.
 * Baileys v7 may use LID JIDs (e.g. 12345@lid) instead of phone JIDs.
 * We try multiple methods to resolve to a phone number.
 */
async function resolveJid(jid) {
  // Already a phone JID
  if (jid.endsWith("@s.whatsapp.net")) {
    const phone = jid.replace("@s.whatsapp.net", "");
    return { phoneNumber: phone, replyJid: jid };
  }

  // LID JID - try to resolve
  if (jid.endsWith("@lid")) {
    const lidUser = jid.split("@")[0].split(":")[0];

    // Check local cache
    if (lidToPhone[lidUser]) {
      const phone = lidToPhone[lidUser];
      return { phoneNumber: phone, replyJid: `${phone}@s.whatsapp.net` };
    }

    // Try Baileys signal repository
    try {
      const pn = await sock.signalRepository?.lidMapping?.getPNForLID(jid);
      if (pn) {
        const phone = pn.split("@")[0].split(":")[0];
        lidToPhone[lidUser] = phone;
        console.log(`[bridge] Resolved LID ${lidUser} → ${phone}`);
        return { phoneNumber: phone, replyJid: `${phone}@s.whatsapp.net` };
      }
    } catch (err) {
      // Signal repository lookup failed, continue with fallback
    }

    // Try auth store files for LID mappings
    try {
      const fs = require("fs");
      const path = require("path");
      const files = fs.readdirSync(AUTH_DIR);
      for (const file of files) {
        if (file.startsWith("lid-mapping-") && file.endsWith("_reverse.json")) {
          const data = JSON.parse(fs.readFileSync(path.join(AUTH_DIR, file), "utf8"));
          // The reverse mapping file maps LID → phone
          if (data && typeof data === "object") {
            for (const [key, value] of Object.entries(data)) {
              const k = String(key).split("@")[0].split(":")[0];
              const v = String(value).split("@")[0].split(":")[0];
              if (k === lidUser) {
                lidToPhone[lidUser] = v;
                console.log(`[bridge] Resolved LID ${lidUser} → ${v} (from auth store)`);
                return { phoneNumber: v, replyJid: `${v}@s.whatsapp.net` };
              }
            }
          }
        }
        // Also check non-reverse mapping files (phone → LID)
        if (file.startsWith("lid-mapping-") && !file.endsWith("_reverse.json")) {
          const phone = file.replace("lid-mapping-", "").replace(".json", "");
          const data = JSON.parse(fs.readFileSync(path.join(AUTH_DIR, file), "utf8"));
          const mappedLid = String(data).split("@")[0].split(":")[0];
          if (mappedLid === lidUser) {
            lidToPhone[lidUser] = phone;
            console.log(`[bridge] Resolved LID ${lidUser} → ${phone} (from phone mapping)`);
            return { phoneNumber: phone, replyJid: `${phone}@s.whatsapp.net` };
          }
        }
      }
    } catch (err) {
      // Auth store lookup failed
    }

    // Fallback: return the LID as-is (will likely fail allowlist but at least logs it)
    console.log(`[bridge] Could not resolve LID: ${jid}`);
    return { phoneNumber: lidUser, replyJid: jid };
  }

  // Unknown format
  const raw = jid.split("@")[0];
  return { phoneNumber: raw, replyJid: jid };
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
