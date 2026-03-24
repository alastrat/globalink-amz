const fs = require("fs");
const path = require("path");
const { inngest } = require("../lib/inngest");
const { execTool } = require("../lib/tools");
const { sendProgress } = require("../lib/ipc");

const TOOLS_DIR = process.env.TOOLS_DIR || "/tools";
const CACHE_DIR = process.env.CACHE_DIR || "/workspace/group/cache";

/**
 * On-demand ASIN restriction check.
 * Triggered by: fba/check-restrictions
 * Payload: { asins: ["B0xxx", "B0yyy", ...] } (max ~20 ASINs)
 */
const checkRestrictions = inngest.createFunction(
  {
    id: "fba/check-restrictions",
    retries: 1,
  },
  { event: "fba/check-restrictions" },
  async ({ event, step }) => {
    const { asins = [] } = event.data || {};

    if (asins.length === 0) {
      sendProgress("[Restricciones] No se proporcionaron ASINs para verificar.");
      return { error: "No ASINs provided" };
    }

    const result = await step.run("check-restrictions", () => {
      sendProgress(
        `[Restricciones] Verificando ${asins.length} ASIN(s)...`
      );
      return execTool(
        "asin_hunter.py",
        ["--check", ...asins, "--json"],
        { timeout: 120000 }
      );
    });

    if (result.error) {
      sendProgress(
        `[Restricciones] Error: ${result.error.substring(0, 200)}`
      );
      return result;
    }

    await step.run("send-results", () => {
      const { approved = [], restricted = {}, summary = {} } = result;

      const lines = ["*Resultado de Restricciones*\n"];

      if (approved.length > 0) {
        lines.push(`\u2705 *APROBADOS (${approved.length}):*`);
        for (const asin of approved) {
          lines.push(`  ${asin} — amazon.com/dp/${asin}`);
        }
      }

      const restrictedEntries = Object.entries(restricted);
      if (restrictedEntries.length > 0) {
        lines.push(`\n\u274C *RESTRINGIDOS (${restrictedEntries.length}):*`);
        for (const [asin, info] of restrictedEntries) {
          const reasons = (info.reasons || []).join("; ");
          lines.push(`  ${asin} — ${reasons || "Sin detalle"}`);
        }
      }

      lines.push(
        `\n*Resumen:* ${summary.approved_count || 0} aprobados, ${summary.restricted_count || 0} restringidos de ${summary.total || 0}`
      );

      sendProgress(lines.join("\n"));
    });

    return result;
  }
);

/**
 * Nightly ASIN audit — runs daily at 6AM UTC (1AM COT).
 * Checks all ASINs in my_asins.txt, compares with previous results, reports changes.
 */
const nightlyAsinAudit = inngest.createFunction(
  {
    id: "fba/nightly-asin-audit",
    retries: 1,
  },
  { cron: "0 6 * * *" },
  async ({ step }) => {
    const asinFile = path.join(TOOLS_DIR, "my_asins.txt");

    const previous = await step.run("load-previous", () => {
      const cachePath = path.join(CACHE_DIR, "restrictions", "last-audit.json");
      try {
        if (fs.existsSync(cachePath)) {
          const data = JSON.parse(fs.readFileSync(cachePath, "utf-8"));
          if (data && Array.isArray(data.approved)) return data;
        }
      } catch (err) {
        console.error("Error loading previous audit:", err.message);
      }
      return null;
    });

    const result = await step.run("check-all-restrictions", () => {
      sendProgress("[Auditoría] Iniciando revisión nocturna de restricciones...");
      return execTool(
        "asin_hunter.py",
        ["--check", "--file", asinFile, "--json"],
        { timeout: 300000 }
      );
    });

    if (result.error) {
      sendProgress(
        `[Auditoría] Error en revisión: ${result.error.substring(0, 200)}`
      );
      return result;
    }

    const changes = await step.run("compare-and-save", () => {
      const { approved = [], restricted = {} } = result;

      const newlyApproved = [];
      const newlyRestricted = [];

      if (previous) {
        const prevApproved = new Set(previous.approved);
        const prevRestricted = new Set(Object.keys(previous.restricted || {}));

        for (const asin of approved) {
          if (prevRestricted.has(asin)) newlyApproved.push(asin);
        }
        for (const asin of Object.keys(restricted)) {
          if (prevApproved.has(asin)) newlyRestricted.push(asin);
        }
      }

      try {
        const restrictionsDir = path.join(CACHE_DIR, "restrictions");
        fs.mkdirSync(restrictionsDir, { recursive: true });
        fs.writeFileSync(
          path.join(restrictionsDir, "last-audit.json"),
          JSON.stringify({ ...result, timestamp: new Date().toISOString() })
        );
      } catch (err) {
        console.error("Error saving audit results:", err.message);
      }

      return { newlyApproved, newlyRestricted };
    });

    await step.run("send-audit-summary", () => {
      const { summary = {} } = result;
      const { newlyApproved = [], newlyRestricted = [] } = changes;
      const restricted = result.restricted || {};

      const lines = [
        "*Auditoría Nocturna de Restricciones*",
        `${new Date().toLocaleDateString("es-CO")}\n`,
        `Total: ${summary.total || 0} ASINs revisados`,
        `\u2705 Aprobados: ${summary.approved_count || 0}`,
        `\u274C Restringidos: ${summary.restricted_count || 0}`,
      ];

      if (newlyApproved.length > 0) {
        lines.push(`\n\uD83C\uDF89 *NUEVOS APROBADOS (${newlyApproved.length}):*`);
        for (const asin of newlyApproved) {
          lines.push(`  ${asin} — amazon.com/dp/${asin}`);
        }
      }

      if (newlyRestricted.length > 0) {
        lines.push(`\n\u26A0\uFE0F *NUEVAS RESTRICCIONES (${newlyRestricted.length}):*`);
        for (const asin of newlyRestricted) {
          const reasons = (restricted[asin]?.reasons || []).join("; ");
          lines.push(`  ${asin} — ${reasons || "Sin detalle"}`);
        }
      }

      if (newlyApproved.length === 0 && newlyRestricted.length === 0) {
        lines.push("\nSin cambios desde la última revisión.");
      }

      sendProgress(lines.join("\n"));
    });

    return {
      ...result.summary,
      changes: {
        newly_approved: changes.newlyApproved.length,
        newly_restricted: changes.newlyRestricted.length,
      },
    };
  }
);

module.exports = { checkRestrictions, nightlyAsinAudit };
