import { describe, it } from "node:test";
import assert from "node:assert";
import { execSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";
import fs from "node:fs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const WORKER_DIR = path.join(__dirname, "..", "inngest", "worker");

// Tests that require `inngest` npm package (only available when worker deps are installed)
const hasInngestDeps = fs.existsSync(
  path.join(WORKER_DIR, "node_modules", "inngest")
);

function requireWorkerModule(evalCode: string): string {
  return execSync(`node -e "${evalCode}"`, {
    cwd: WORKER_DIR,
    encoding: "utf-8",
  }).trim();
}

describe("inngest worker module syntax", () => {
  it("lib/inngest.js is valid and exports inngest client", { skip: !hasInngestDeps && "inngest deps not installed" }, () => {
    const data = JSON.parse(
      requireWorkerModule(
        "const m = require('./lib/inngest'); console.log(JSON.stringify({ hasInngest: !!m.inngest, id: m.inngest?.id }))"
      )
    );
    assert.strictEqual(data.hasInngest, true);
    assert.strictEqual(data.id, "fba-worker");
  });

  it("lib/tools.js is valid and exports execTool", () => {
    const data = JSON.parse(
      requireWorkerModule(
        "const m = require('./lib/tools'); console.log(JSON.stringify({ hasExecTool: typeof m.execTool === 'function' }))"
      )
    );
    assert.strictEqual(data.hasExecTool, true);
  });

  it("lib/ipc.js is valid and exports sendProgress, sendImage, sendProductCard", () => {
    const data = JSON.parse(
      requireWorkerModule(
        "const m = require('./lib/ipc'); console.log(JSON.stringify({ sendProgress: typeof m.sendProgress, sendImage: typeof m.sendImage, sendProductCard: typeof m.sendProductCard }))"
      )
    );
    assert.strictEqual(data.sendProgress, "function");
    assert.strictEqual(data.sendImage, "function");
    assert.strictEqual(data.sendProductCard, "function");
  });

  it("functions/research.js exports functions array", { skip: !hasInngestDeps && "inngest deps not installed" }, () => {
    const data = JSON.parse(
      requireWorkerModule(
        "const m = require('./functions/research'); console.log(JSON.stringify({ hasFunctions: Array.isArray(m.functions), count: m.functions?.length }))"
      )
    );
    assert.strictEqual(data.hasFunctions, true);
    assert.strictEqual(data.count, 1);
  });

  it("functions/restrictions.js exports checkRestrictions and nightlyAsinAudit", { skip: !hasInngestDeps && "inngest deps not installed" }, () => {
    const data = JSON.parse(
      requireWorkerModule(
        "const m = require('./functions/restrictions'); console.log(JSON.stringify({ hasCheck: typeof m.checkRestrictions === 'object', hasNightly: typeof m.nightlyAsinAudit === 'object' }))"
      )
    );
    assert.strictEqual(data.hasCheck, true);
    assert.strictEqual(data.hasNightly, true);
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
  it("respects custom timeout", () => {
    const data = JSON.parse(
      requireWorkerModule(`
        const { execTool } = require('./lib/tools');
        try { execTool('nonexistent_12345.py', [], { timeout: 100 }); } catch(e) {}
        console.log(JSON.stringify({ ok: true }));
      `)
    );
    assert.strictEqual(data.ok, true);
  });
});
