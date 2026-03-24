import { describe, it } from "node:test";
import assert from "node:assert";
import { execSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";
import fs from "node:fs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const WORKER_DIR = path.join(__dirname, "..", "inngest", "worker");

const hasInngestDeps = fs.existsSync(
  path.join(WORKER_DIR, "node_modules", "inngest")
);

function requireWorkerModule(evalCode: string): string {
  return execSync(`node -e "${evalCode}"`, {
    cwd: WORKER_DIR,
    encoding: "utf-8",
  }).trim();
}

describe("api routes file structure", () => {
  it("routes/api.js exists", () => {
    assert.ok(
      fs.existsSync(path.join(WORKER_DIR, "routes", "api.js")),
      "routes/api.js should exist in inngest/worker/"
    );
  });

  it("dashboard/index.html exists", () => {
    assert.ok(
      fs.existsSync(path.join(WORKER_DIR, "dashboard", "index.html")),
      "dashboard/index.html should exist in inngest/worker/"
    );
  });
});

describe("api routes module", () => {
  it("routes/api.js exports an Express router", { skip: !hasInngestDeps && "inngest deps not installed" }, () => {
    const data = JSON.parse(
      requireWorkerModule(
        "const r = require('./routes/api'); console.log(JSON.stringify({ isFunction: typeof r === 'function', hasStack: Array.isArray(r.stack) }))"
      )
    );
    assert.strictEqual(data.isFunction, true, "router should be a function");
    assert.strictEqual(data.hasStack, true, "router should have a stack (Express Router)");
  });
});
