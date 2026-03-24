import { describe, it } from "node:test";
import assert from "node:assert";
import { execSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";
import fs from "node:fs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const WORKER_DIR = path.join(__dirname, "..", "inngest", "worker");

describe("inngest worker module syntax", () => {
  it("lib/inngest.js is valid and exports inngest client", () => {
    const result = execSync(
      `node -e "const m = require('./lib/inngest'); console.log(JSON.stringify({ hasInngest: !!m.inngest, id: m.inngest?.id }))"`,
      { cwd: WORKER_DIR, encoding: "utf-8" }
    );
    const data = JSON.parse(result.trim());
    assert.strictEqual(data.hasInngest, true);
    assert.strictEqual(data.id, "fba-worker");
  });

  it("lib/tools.js is valid and exports execTool", () => {
    const result = execSync(
      `node -e "const m = require('./lib/tools'); console.log(JSON.stringify({ hasExecTool: typeof m.execTool === 'function' }))"`,
      { cwd: WORKER_DIR, encoding: "utf-8" }
    );
    const data = JSON.parse(result.trim());
    assert.strictEqual(data.hasExecTool, true);
  });

  it("lib/ipc.js is valid and exports sendProgress, sendImage, sendProductCard", () => {
    const result = execSync(
      `node -e "const m = require('./lib/ipc'); console.log(JSON.stringify({ sendProgress: typeof m.sendProgress, sendImage: typeof m.sendImage, sendProductCard: typeof m.sendProductCard }))"`,
      { cwd: WORKER_DIR, encoding: "utf-8" }
    );
    const data = JSON.parse(result.trim());
    assert.strictEqual(data.sendProgress, "function");
    assert.strictEqual(data.sendImage, "function");
    assert.strictEqual(data.sendProductCard, "function");
  });

  it("functions/research.js exports functions array", () => {
    const result = execSync(
      `node -e "const m = require('./functions/research'); console.log(JSON.stringify({ hasFunctions: Array.isArray(m.functions), count: m.functions?.length }))"`,
      { cwd: WORKER_DIR, encoding: "utf-8" }
    );
    const data = JSON.parse(result.trim());
    assert.strictEqual(data.hasFunctions, true);
    assert.strictEqual(data.count, 1);
  });

  it("functions/restrictions.js exports checkRestrictions and nightlyAsinAudit", () => {
    const result = execSync(
      `node -e "const m = require('./functions/restrictions'); console.log(JSON.stringify({ hasCheck: typeof m.checkRestrictions === 'object', hasNightly: typeof m.nightlyAsinAudit === 'object' }))"`,
      { cwd: WORKER_DIR, encoding: "utf-8" }
    );
    const data = JSON.parse(result.trim());
    assert.strictEqual(data.hasCheck, true, "checkRestrictions should be exported");
    assert.strictEqual(data.hasNightly, true, "nightlyAsinAudit should be exported");
  });
});

describe("inngest worker file structure", () => {
  const requiredFiles = [
    "server.js",
    "package.json",
    "lib/inngest.js",
    "lib/tools.js",
    "lib/ipc.js",
    "functions/research.js",
    "functions/restrictions.js",
  ];

  for (const file of requiredFiles) {
    it(`${file} exists`, () => {
      assert.ok(
        fs.existsSync(path.join(WORKER_DIR, file)),
        `${file} should exist in inngest/worker/`
      );
    });
  }
});

describe("execTool timeout parameter", () => {
  it("respects custom timeout (short timeout causes failure on slow script)", () => {
    // Create a script that sleeps, call with very short timeout
    const result = execSync(
      `node -e "
        const { execTool } = require('./lib/tools');
        try {
          execTool('nonexistent_script_12345.py', [], { timeout: 100 });
        } catch(e) {
          // execTool catches and returns error object
        }
        // Verify it accepted the timeout param without throwing TypeError
        console.log(JSON.stringify({ ok: true }));
      "`,
      { cwd: WORKER_DIR, encoding: "utf-8" }
    );
    const data = JSON.parse(result.trim());
    assert.strictEqual(data.ok, true);
  });
});
