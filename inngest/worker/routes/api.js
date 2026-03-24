const { Router } = require("express");
const { execFile } = require("child_process");
const path = require("path");

const router = Router();

const TOOLS_DIR = process.env.TOOLS_DIR || "/tools";
const DASHBOARD_DIR = path.join(__dirname, "..", "dashboard");

// ---------- Input validation patterns ----------
const ASIN_RE = /^B0[A-Z0-9]{8}$/;
const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
const GRADE_RE = /^[A-F]$/;
const RESTRICTED_RE = /^[01]$/;

// ---------- Async DB query helper (non-blocking) ----------
function queryDB(args, timeout = 10000) {
  return new Promise((resolve) => {
    execFile(
      "python3",
      [`${TOOLS_DIR}/research_db.py`, ...args],
      {
        encoding: "utf-8",
        timeout,
        env: { ...process.env, PYTHONIOENCODING: "utf-8" },
      },
      (err, stdout) => {
        if (err) {
          try {
            resolve(JSON.parse(stdout.trim()));
          } catch {
            resolve({ error: stdout || err.message });
          }
          return;
        }
        try {
          resolve(JSON.parse(stdout.trim()));
        } catch {
          resolve({ error: "Invalid JSON from tool" });
        }
      }
    );
  });
}

// ---------- HTTP Basic Auth middleware ----------
function authMiddleware(req, res, next) {
  const user = process.env.DASHBOARD_USER;
  const pass = process.env.DASHBOARD_PASS;

  if (!user || !pass) {
    return res.status(503).json({ error: "Dashboard credentials not configured" });
  }

  const header = req.headers.authorization;
  if (!header || !header.startsWith("Basic ")) {
    res.setHeader("WWW-Authenticate", 'Basic realm="FBA Dashboard"');
    return res.status(401).json({ error: "Authentication required" });
  }

  const decoded = Buffer.from(header.slice(6), "base64").toString("utf-8");
  const [u, ...pParts] = decoded.split(":");
  const p = pParts.join(":");

  if (u !== user || p !== pass) {
    res.setHeader("WWW-Authenticate", 'Basic realm="FBA Dashboard"');
    return res.status(401).json({ error: "Invalid credentials" });
  }

  next();
}

// Apply auth to all dashboard/api routes
router.use("/dashboard", authMiddleware);
router.use("/api/products", authMiddleware);
router.use("/api/runs", authMiddleware);
router.use("/api/stats", authMiddleware);
router.use("/api/product", authMiddleware);

// ---------- Dashboard ----------
router.get("/dashboard", (_req, res) => {
  res.sendFile(path.join(DASHBOARD_DIR, "index.html"));
});

// ---------- API: Products ----------
router.get("/api/products", async (req, res) => {
  const args = ["export-products"];
  const { from, to, category, grade, restricted } = req.query;

  if (from) {
    if (!DATE_RE.test(from)) return res.status(400).json({ error: "Invalid 'from' date format (YYYY-MM-DD)" });
    args.push("--from", from);
  }
  if (to) {
    if (!DATE_RE.test(to)) return res.status(400).json({ error: "Invalid 'to' date format (YYYY-MM-DD)" });
    args.push("--to", to);
  }
  if (category) {
    args.push("--category", String(category));
  }
  if (grade) {
    if (!GRADE_RE.test(grade)) return res.status(400).json({ error: "Invalid grade (A-F)" });
    args.push("--grade", grade);
  }
  if (restricted !== undefined && restricted !== "") {
    if (!RESTRICTED_RE.test(restricted)) return res.status(400).json({ error: "Invalid restricted value (0 or 1)" });
    args.push("--restricted", restricted);
  }

  const result = await queryDB(args);
  res.json(result);
});

// ---------- API: Runs ----------
router.get("/api/runs", async (req, res) => {
  const args = ["export-runs"];
  const { limit } = req.query;

  if (limit !== undefined && limit !== "") {
    const n = Number(limit);
    if (!Number.isInteger(n) || n < 1 || n > 100) {
      return res.status(400).json({ error: "Invalid limit (1-100)" });
    }
    args.push("--limit", String(n));
  }

  const result = await queryDB(args);
  res.json(result);
});

// ---------- API: Stats ----------
router.get("/api/stats", async (req, res) => {
  const args = ["export-stats"];
  const { from, to } = req.query;

  if (from) {
    if (!DATE_RE.test(from)) return res.status(400).json({ error: "Invalid 'from' date format (YYYY-MM-DD)" });
    args.push("--from", from);
  }
  if (to) {
    if (!DATE_RE.test(to)) return res.status(400).json({ error: "Invalid 'to' date format (YYYY-MM-DD)" });
    args.push("--to", to);
  }

  const result = await queryDB(args);
  res.json(result);
});

// ---------- API: Product history ----------
router.get("/api/product/:asin", async (req, res) => {
  const { asin } = req.params;

  if (!ASIN_RE.test(asin)) {
    return res.status(400).json({ error: "Invalid ASIN format" });
  }

  const result = await queryDB(["export-history", asin]);
  res.json(result);
});

module.exports = router;
