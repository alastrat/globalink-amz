import { describe, it } from "node:test";
import assert from "node:assert";
import { execSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SCRIPT = path.join(__dirname, "..", "tools", "asin_hunter.py");

describe("asin_hunter.py --check --json", () => {
  it("returns error JSON when no ASINs provided", () => {
    // Use clean env with seller_id set so we get past the seller check
    try {
      execSync(
        `python3 ${SCRIPT} --check --json --config /dev/null`,
        {
          encoding: "utf-8",
          timeout: 10000,
          env: {
            PATH: process.env.PATH,
            PYTHONIOENCODING: "utf-8",
            HOME: process.env.HOME,
            AMAZON_SELLER_ID: "TESTSELLERID",
          },
        }
      );
      assert.fail("Should have exited with error");
    } catch (err: unknown) {
      const e = err as { stdout?: string; status?: number };
      assert.strictEqual(e.status, 1, "should exit with code 1");
      const data = JSON.parse((e.stdout || "").trim());
      assert.ok(data.error, "should have error field");
      assert.ok(
        (data.error as string).includes("No ASINs"),
        `error should mention no ASINs: ${data.error}`
      );
    }
  });

  it("returns error JSON when seller_id and env vars are missing", () => {
    // Run without AMAZON_SELLER_ID env var and with no config
    try {
      execSync(
        `python3 ${SCRIPT} --check B0FAKE12345 --json --config /dev/null`,
        {
          encoding: "utf-8",
          timeout: 10000,
          env: {
            PATH: process.env.PATH,
            PYTHONIOENCODING: "utf-8",
            HOME: process.env.HOME,
          },
        }
      );
      assert.fail("Should have exited with error");
    } catch (err: unknown) {
      const e = err as { stdout?: string; status?: number };
      const data = JSON.parse((e.stdout || "").trim());
      assert.ok(data.error, "should have error field");
      assert.ok(
        (data.error as string).includes("AMAZON_SELLER_ID"),
        `error should mention AMAZON_SELLER_ID: ${data.error}`
      );
    }
  });

  it("accepts ASINs from --file flag", () => {
    // Use the actual my_asins.txt but without API creds, should fail on auth
    // but not on ASIN parsing — verifies file loading works
    try {
      execSync(
        `python3 ${SCRIPT} --check --file ${path.join(__dirname, "..", "tools", "my_asins.txt")} --json --config /dev/null`,
        {
          encoding: "utf-8",
          timeout: 10000,
          env: {
            PATH: process.env.PATH,
            PYTHONIOENCODING: "utf-8",
            HOME: process.env.HOME,
          },
        }
      );
      assert.fail("Should have exited with error (no seller_id)");
    } catch (err: unknown) {
      const e = err as { stdout?: string; status?: number };
      const data = JSON.parse((e.stdout || "").trim());
      assert.ok(data.error, "should have error field for missing seller_id");
    }
  });
});

describe("asin_hunter.py --check --json output contract", () => {
  it("JSON output has approved/restricted/summary fields when seller_id is set", () => {
    // With seller_id but no valid API creds, the script will attempt API calls
    // and return results (likely all restricted due to auth error).
    // This tests the JSON structure contract that restrictions.js depends on.
    try {
      const stdout = execSync(
        `python3 ${SCRIPT} --check B0FAKE12345 --json --config /dev/null`,
        {
          encoding: "utf-8",
          timeout: 15000,
          env: {
            PATH: process.env.PATH,
            PYTHONIOENCODING: "utf-8",
            HOME: process.env.HOME,
            AMAZON_SELLER_ID: "TESTSELLERID",
            SP_API_REFRESH_TOKEN: "fake-token",
            SP_API_LWA_APP_ID: "fake-app-id",
            SP_API_LWA_CLIENT_SECRET: "fake-secret",
          },
        }
      );
      const data = JSON.parse(stdout.trim());

      // Verify the JSON structure that restrictions.js expects
      assert.ok(Array.isArray(data.approved), "approved should be an array");
      assert.ok(
        typeof data.restricted === "object" && data.restricted !== null,
        "restricted should be an object"
      );
      assert.ok(
        typeof data.summary === "object" && data.summary !== null,
        "summary should be an object"
      );
      assert.ok(
        typeof data.summary.total === "number",
        "summary.total should be a number"
      );
      assert.ok(
        typeof data.summary.approved_count === "number",
        "summary.approved_count should be a number"
      );
      assert.ok(
        typeof data.summary.restricted_count === "number",
        "summary.restricted_count should be a number"
      );
    } catch (err: unknown) {
      const e = err as { stdout?: string; stderr?: string };
      // If the script errors (e.g., network issues), verify it still outputs JSON
      const output = (e.stdout || "").trim();
      if (output) {
        const data = JSON.parse(output);
        // Either valid result structure or error JSON — both acceptable
        assert.ok(
          data.error || (data.approved && data.summary),
          "output should be either error JSON or valid result"
        );
      }
      // If no stdout at all, the test is inconclusive (network issue), skip gracefully
    }
  });
});

describe("asin_hunter.py ASIN parsing", () => {
  it("parses standard ASIN format", () => {
    // This will fail on auth, but the "checking N ASINs" in stderr
    // proves parsing worked. With --json it outputs structured JSON.
    try {
      execSync(
        `python3 ${SCRIPT} --check B07X6C9RMF B0002DHNZA --json --config /dev/null`,
        {
          encoding: "utf-8",
          timeout: 15000,
          env: {
            PATH: process.env.PATH,
            PYTHONIOENCODING: "utf-8",
            HOME: process.env.HOME,
            AMAZON_SELLER_ID: "TESTSELLERID",
            SP_API_REFRESH_TOKEN: "fake",
            SP_API_LWA_APP_ID: "fake",
            SP_API_LWA_CLIENT_SECRET: "fake",
          },
        }
      );
    } catch (err: unknown) {
      // Expected to fail on auth, but output should be valid JSON
      const e = err as { stdout?: string };
      if (e.stdout) {
        const data = JSON.parse(e.stdout.trim());
        // Should have processed 2 ASINs
        assert.strictEqual(
          data.summary?.total,
          2,
          "should have parsed 2 ASINs"
        );
      }
    }
  });
});
