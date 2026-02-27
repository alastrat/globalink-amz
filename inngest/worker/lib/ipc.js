const fs = require("fs");
const path = require("path");

const IPC_DIR = process.env.IPC_DIR || "/ipc/messages";
const CHAT_JID = process.env.CHAT_JID || "573002061607@s.whatsapp.net";
const CACHE_DIR = process.env.CACHE_DIR || "/workspace/group/cache";

/**
 * Send a WhatsApp text message via NanoClaw IPC.
 * @param {string} text - Message text to send
 * @param {string} [storeKeyAs] - Optional ASIN/key to store the sent message ID for quoted replies
 */
function sendProgress(text, storeKeyAs) {
  try {
    const filename = `msg-${Date.now()}-${Math.random().toString(36).slice(2, 8)}.json`;
    const msg = {
      type: "message",
      chatJid: CHAT_JID,
      text,
      sender: "inngest",
      groupFolder: "owner",
      timestamp: Date.now(),
    };
    if (storeKeyAs) msg.storeKeyAs = storeKeyAs;

    fs.mkdirSync(IPC_DIR, { recursive: true });
    fs.writeFileSync(path.join(IPC_DIR, filename), JSON.stringify(msg));
  } catch (err) {
    console.error("IPC send error:", err.message);
  }
}

/**
 * Send a WhatsApp image message via NanoClaw IPC.
 * @param {string} imageUrl - URL of the image to send
 * @param {string} caption - Caption text for the image
 * @param {string} [storeKeyAs] - Optional ASIN/key to store the sent message ID for quoted replies
 */
function sendImage(imageUrl, caption, storeKeyAs) {
  try {
    const filename = `msg-${Date.now()}-${Math.random().toString(36).slice(2, 8)}.json`;
    const msg = {
      type: "image",
      chatJid: CHAT_JID,
      imageUrl,
      caption,
      sender: "inngest",
      groupFolder: "owner",
      timestamp: Date.now(),
    };
    if (storeKeyAs) msg.storeKeyAs = storeKeyAs;

    fs.mkdirSync(IPC_DIR, { recursive: true });
    fs.writeFileSync(path.join(IPC_DIR, filename), JSON.stringify(msg));
  } catch (err) {
    console.error("IPC send image error:", err.message);
  }
}

/**
 * Send a compact product card via WhatsApp and cache the full analysis.
 * The compact card shows: image + Mercado summary + verdict + wa.me link.
 * Full details are cached for on-demand "detalles ASIN" quoted replies.
 * @param {object} product - Product data with all analysis fields
 */
function sendProductCard(product) {
  const {
    title = "Unknown",
    asin = "",
    bsr,
    bsr_category,
    estimated_monthly_sales,
    demand_indicator,
    fba_offer_count = 0,
    fbm_offer_count = 0,
    amazon_is_seller = false,
    buy_box_price,
    wholesale_cost,
    roi,
    profit_per_unit,
    main_image_url,
  } = product;

  // Profitability verdict
  const verdict = roi == null
    ? "\u2753 SIN COSTO"
    : roi >= 30
      ? "\u2705 RENTABLE"
      : roi >= 15
        ? "\u26A0\uFE0F MARGINAL"
        : "\u274C NO RENTABLE";

  const caption = [
    `*${title}*`,
    `https://amazon.com/dp/${asin}`,
    "",
    `*Mercado*`,
    `\u2022 BSR: ${bsr != null ? bsr.toLocaleString() : "N/A"} en ${bsr_category || "N/A"}`,
    `\u2022 Demanda: ${demand_indicator || "N/A"} (~${estimated_monthly_sales || 0} uds/mes)`,
    `\u2022 Vendedores FBA: ${fba_offer_count} | FBM: ${fbm_offer_count}`,
    `\u2022 Amazon vende: ${amazon_is_seller ? "S\u00ed" : "No"}`,
    `\u2022 Buy Box: $${buy_box_price != null ? buy_box_price.toFixed(2) : "N/A"}`,
    "",
    `${verdict} | ROI: ${roi != null ? roi.toFixed(1) + "%" : "N/A"} | Ganancia: ${profit_per_unit != null ? "$" + profit_per_unit.toFixed(2) + "/ud" : "N/A"}`,
    "",
    `\uD83D\uDC49 https://wa.me/573011982530?text=detalles%20${asin}`,
  ].join("\n");

  // Send image with compact caption (storeKeyAs saves message ID mapped to ASIN)
  if (main_image_url) {
    sendImage(main_image_url, caption, asin);
  } else {
    sendProgress(caption, asin);
  }

  // Cache full analysis for later "detalles" lookup
  try {
    const analysisDir = path.join(CACHE_DIR, "analysis");
    fs.mkdirSync(analysisDir, { recursive: true });
    fs.writeFileSync(
      path.join(analysisDir, `${asin}.json`),
      JSON.stringify(product)
    );
  } catch (err) {
    console.error("Cache analysis error:", err.message);
  }
}

module.exports = { sendProgress, sendImage, sendProductCard };
