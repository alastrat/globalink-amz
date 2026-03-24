const express = require("express");
const { serve } = require("inngest/express");
const { inngest } = require("./lib/inngest");
const { functions: researchFunctions } = require("./functions/research");
const { checkRestrictions, nightlyAsinAudit } = require("./functions/restrictions");

const app = express();
const PORT = process.env.PORT || 3500;

app.use(express.json());

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

app.listen(PORT, "0.0.0.0", () => {
  console.log(`FBA Inngest worker listening on port ${PORT}`);
  console.log(`Inngest endpoint: http://0.0.0.0:${PORT}/api/inngest`);
});
