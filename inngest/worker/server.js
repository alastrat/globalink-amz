const express = require("express");
const { serve } = require("inngest/express");
const { inngest } = require("./lib/inngest");
const { functions: researchFunctions } = require("./functions/research");
const { checkRestrictions, nightlyAsinAudit } = require("./functions/restrictions");

const apiRoutes = require("./routes/api");

const app = express();
const PORT = process.env.PORT || 3500;

app.use(express.json());

// Dashboard & API routes (before Inngest so /api/products etc. take priority)
app.use(apiRoutes);

// Health check
app.get("/health", (req, res) => {
  res.json({ status: "ok", timestamp: new Date().toISOString() });
});

// Inngest endpoint — register all functions
const allFunctions = [...researchFunctions, checkRestrictions, nightlyAsinAudit];

app.use(
  "/api/inngest",
  serve({
    client: inngest,
    functions: allFunctions,
  })
);

const { execTool } = require("./lib/tools");
try {
  execTool("research_db.py", ["init"], { timeout: 5000 });
  console.log("Research database initialized");
} catch (err) {
  console.warn("Could not initialize research DB:", err.message);
}

app.listen(PORT, "0.0.0.0", () => {
  console.log(`FBA Inngest worker listening on port ${PORT}`);
  console.log(`Inngest endpoint: http://0.0.0.0:${PORT}/api/inngest`);
});
