const express = require("express");
const { serve } = require("inngest/express");
const { inngest, functions } = require("./functions/research");

const app = express();
const PORT = process.env.PORT || 3500;

app.use(express.json());

// Health check
app.get("/health", (req, res) => {
  res.json({ status: "ok", timestamp: new Date().toISOString() });
});

// Inngest endpoint
app.use(
  "/api/inngest",
  serve({
    client: inngest,
    functions,
  })
);

app.listen(PORT, "0.0.0.0", () => {
  console.log(`FBA Inngest worker listening on port ${PORT}`);
  console.log(`Inngest endpoint: http://0.0.0.0:${PORT}/api/inngest`);
});
