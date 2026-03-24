import { describe, it, beforeEach, afterEach } from "node:test";
import assert from "node:assert";
import { execSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";
import fs from "node:fs";
import os from "node:os";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SCRIPT = path.join(__dirname, "..", "tools", "research_db.py");

/** Create a fresh temp directory and return the DB path inside it. */
function freshDbPath(): string {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "research-db-test-"));
  return path.join(dir, "research.db");
}

/** Run research_db.py with the given args and a temp DB. Returns parsed JSON. */
function run(dbPath: string, args: string): unknown {
  const stdout = execSync(`python3 ${SCRIPT} ${args}`, {
    encoding: "utf-8",
    timeout: 10_000,
    env: {
      PATH: process.env.PATH,
      PYTHONIOENCODING: "utf-8",
      HOME: process.env.HOME,
      RESEARCH_DB_PATH: dbPath,
    },
  });
  return JSON.parse(stdout.trim());
}

// ---------- init ----------
describe("research_db.py init", () => {
  let dbPath: string;
  beforeEach(() => { dbPath = freshDbPath(); });
  afterEach(() => { fs.rmSync(path.dirname(dbPath), { recursive: true, force: true }); });

  it("creates database and tables", () => {
    const result = run(dbPath, "init") as { ok: boolean };
    assert.strictEqual(result.ok, true);
    assert.ok(fs.existsSync(dbPath), "DB file should exist after init");
  });

  it("is idempotent (running init twice succeeds)", () => {
    run(dbPath, "init");
    const result = run(dbPath, "init") as { ok: boolean };
    assert.strictEqual(result.ok, true);
  });
});

// ---------- save-restrictions ----------
describe("research_db.py save-restrictions", () => {
  let dbPath: string;
  beforeEach(() => {
    dbPath = freshDbPath();
    run(dbPath, "init");
  });
  afterEach(() => { fs.rmSync(path.dirname(dbPath), { recursive: true, force: true }); });

  it("stores restriction results and creates a run", () => {
    const input = JSON.stringify({
      source: "asin_hunter batch 1",
      approved: ["B000TEST01", "B000TEST02"],
      restricted: {
        B000TEST03: { restricted: true, reasons: ["Brand gating", "Approval required"] },
      },
    });
    const result = run(dbPath, `save-restrictions '${input}'`) as { run_id: number; saved: number };
    assert.ok(typeof result.run_id === "number" && result.run_id > 0, "run_id should be positive integer");
    assert.strictEqual(result.saved, 3, "should save 3 total ASINs");
  });

  it("records approved ASINs with restricted=0 and restricted ASINs with restricted=1", () => {
    const input = JSON.stringify({
      source: "test",
      approved: ["B000APPR01"],
      restricted: {
        B000REST01: { restricted: true, reasons: ["Gated"] },
      },
    });
    run(dbPath, `save-restrictions '${input}'`);

    // Export products to verify
    const exported = run(dbPath, "export-products") as { products: Array<{ asin: string; restricted: number; restriction_reasons: string | null }> };
    const approved = exported.products.find(p => p.asin === "B000APPR01");
    const restricted = exported.products.find(p => p.asin === "B000REST01");

    assert.ok(approved, "approved ASIN should be in export");
    assert.strictEqual(approved!.restricted, 0, "approved ASIN should have restricted=0");

    assert.ok(restricted, "restricted ASIN should be in export");
    assert.strictEqual(restricted!.restricted, 1, "restricted ASIN should have restricted=1");
    assert.ok(restricted!.restriction_reasons, "restricted ASIN should have reasons");
  });
});

// ---------- save-research ----------
describe("research_db.py save-research", () => {
  let dbPath: string;
  beforeEach(() => {
    dbPath = freshDbPath();
    run(dbPath, "init");
  });
  afterEach(() => { fs.rmSync(path.dirname(dbPath), { recursive: true, force: true }); });

  it("stores full product research data", () => {
    const input = JSON.stringify({
      source: "wholesale supplier A",
      products: [
        {
          asin: "B000RES001",
          title: "Test Product One",
          brand: "TestBrand",
          category: "Health & Household",
          bsr_category: "Health & Household",
          buy_box_price: 24.99,
          wholesale_cost: 12.50,
          bsr: 15000,
          fba_offer_count: 5,
          fbm_offer_count: 3,
          amazon_is_seller: 0,
          estimated_monthly_sales: 300,
          demand_indicator: "HIGH",
          referral_fee: 3.75,
          fba_fee: 5.40,
          total_fees: 9.15,
          profit: 3.34,
          roi: 26.7,
          margin: 13.4,
          score: 7.5,
          grade: "B",
          restricted: 0,
          weight_lb: 1.2,
          main_image_url: "https://images-na.ssl-images-amazon.com/images/I/test.jpg",
        },
        {
          asin: "B000RES002",
          title: "Test Product Two",
          brand: "TestBrand2",
          category: "Grocery",
          buy_box_price: 9.99,
          bsr: 50000,
          score: 4.2,
          grade: "D",
          restricted: 1,
        },
      ],
    });
    const result = run(dbPath, `save-research '${input}'`) as { run_id: number; saved: number };
    assert.ok(result.run_id > 0, "run_id should be positive");
    assert.strictEqual(result.saved, 2, "should save 2 products");
  });

  it("upserts product catalog fields on repeated saves", () => {
    const first = JSON.stringify({
      source: "batch 1",
      products: [{ asin: "B000UPS001", title: "Old Title", brand: "OldBrand", score: 5.0, grade: "C" }],
    });
    run(dbPath, `save-research '${first}'`);

    const second = JSON.stringify({
      source: "batch 2",
      products: [{ asin: "B000UPS001", title: "New Title", brand: "NewBrand", score: 8.0, grade: "A" }],
    });
    run(dbPath, `save-research '${second}'`);

    const exported = run(dbPath, "export-products") as { products: Array<{ asin: string; title: string; brand: string; score: number; grade: string }> };
    const product = exported.products.find(p => p.asin === "B000UPS001");
    assert.ok(product, "product should exist");
    assert.strictEqual(product!.title, "New Title", "title should be updated");
    assert.strictEqual(product!.brand, "NewBrand", "brand should be updated");
    // Latest snapshot should have latest score
    assert.strictEqual(product!.grade, "A", "grade should reflect latest snapshot");
  });
});

// ---------- export-products ----------
describe("research_db.py export-products", () => {
  let dbPath: string;
  beforeEach(() => {
    dbPath = freshDbPath();
    run(dbPath, "init");
  });
  afterEach(() => { fs.rmSync(path.dirname(dbPath), { recursive: true, force: true }); });

  it("returns saved products with latest snapshot data", () => {
    const input = JSON.stringify({
      source: "test",
      products: [
        { asin: "B000EXP001", title: "Export Test", brand: "TestBrand", category: "Toys", buy_box_price: 19.99, score: 6.0, grade: "C" },
      ],
    });
    run(dbPath, `save-research '${input}'`);

    const exported = run(dbPath, "export-products") as { products: Array<Record<string, unknown>> };
    assert.ok(Array.isArray(exported.products), "products should be array");
    assert.strictEqual(exported.products.length, 1);
    const p = exported.products[0];
    assert.strictEqual(p.asin, "B000EXP001");
    assert.strictEqual(p.title, "Export Test");
    assert.strictEqual(p.buy_box_price, 19.99);
    assert.strictEqual(p.grade, "C");
  });

  it("returns empty array when no products exist", () => {
    const exported = run(dbPath, "export-products") as { products: unknown[] };
    assert.deepStrictEqual(exported.products, []);
  });
});

// ---------- export-products filters ----------
describe("research_db.py export-products filters", () => {
  let dbPath: string;
  afterEach(() => { fs.rmSync(path.dirname(dbPath), { recursive: true, force: true }); });
  beforeEach(() => {
    dbPath = freshDbPath();
    run(dbPath, "init");
    const input = JSON.stringify({
      source: "test",
      products: [
        { asin: "B000FIL001", title: "Filter A", category: "Toys", grade: "A", restricted: 0, score: 9.0 },
        { asin: "B000FIL002", title: "Filter B", category: "Grocery", grade: "B", restricted: 1, score: 6.0 },
        { asin: "B000FIL003", title: "Filter C", category: "Toys", grade: "D", restricted: 0, score: 3.0 },
      ],
    });
    run(dbPath, `save-research '${input}'`);
  });

  it("filters by --category", () => {
    const result = run(dbPath, "export-products --category Toys") as { products: Array<{ asin: string }> };
    assert.strictEqual(result.products.length, 2);
    const asins = result.products.map(p => p.asin).sort();
    assert.deepStrictEqual(asins, ["B000FIL001", "B000FIL003"]);
  });

  it("filters by --grade", () => {
    const result = run(dbPath, "export-products --grade A") as { products: Array<{ asin: string }> };
    assert.strictEqual(result.products.length, 1);
    assert.strictEqual(result.products[0].asin, "B000FIL001");
  });

  it("filters by --restricted", () => {
    const result = run(dbPath, "export-products --restricted 1") as { products: Array<{ asin: string }> };
    assert.strictEqual(result.products.length, 1);
    assert.strictEqual(result.products[0].asin, "B000FIL002");
  });

  it("combines multiple filters", () => {
    const result = run(dbPath, "export-products --category Toys --grade D") as { products: Array<{ asin: string }> };
    assert.strictEqual(result.products.length, 1);
    assert.strictEqual(result.products[0].asin, "B000FIL003");
  });
});

// ---------- export-runs ----------
describe("research_db.py export-runs", () => {
  let dbPath: string;
  beforeEach(() => {
    dbPath = freshDbPath();
    run(dbPath, "init");
  });
  afterEach(() => { fs.rmSync(path.dirname(dbPath), { recursive: true, force: true }); });

  it("lists recent runs", () => {
    const input1 = JSON.stringify({ source: "batch 1", approved: ["B000R00001"], restricted: {} });
    const input2 = JSON.stringify({ source: "batch 2", approved: ["B000R00002"], restricted: {} });
    run(dbPath, `save-restrictions '${input1}'`);
    run(dbPath, `save-restrictions '${input2}'`);

    const result = run(dbPath, "export-runs") as { runs: Array<{ id: number; source: string }> };
    assert.ok(Array.isArray(result.runs), "runs should be array");
    assert.strictEqual(result.runs.length, 2);
  });

  it("respects --limit flag", () => {
    for (let i = 1; i <= 5; i++) {
      const input = JSON.stringify({ source: `batch ${i}`, approved: [`B000LIM0${i}`], restricted: {} });
      run(dbPath, `save-restrictions '${input}'`);
    }
    const result = run(dbPath, "export-runs --limit 3") as { runs: Array<{ id: number }> };
    assert.strictEqual(result.runs.length, 3);
  });
});

// ---------- export-stats ----------
describe("research_db.py export-stats", () => {
  let dbPath: string;
  beforeEach(() => {
    dbPath = freshDbPath();
    run(dbPath, "init");
  });
  afterEach(() => { fs.rmSync(path.dirname(dbPath), { recursive: true, force: true }); });

  it("returns aggregate KPIs", () => {
    const input = JSON.stringify({
      source: "stats test",
      products: [
        { asin: "B000STA001", category: "Toys", grade: "A", roi: 30.0, score: 8.0, restricted: 0 },
        { asin: "B000STA002", category: "Toys", grade: "B", roi: 20.0, score: 6.0, restricted: 0 },
        { asin: "B000STA003", category: "Grocery", grade: "D", roi: 5.0, score: 3.0, restricted: 1 },
      ],
    });
    run(dbPath, `save-research '${input}'`);

    const stats = run(dbPath, "export-stats") as {
      total_products: number;
      total_runs: number;
      avg_roi: number;
      avg_score: number;
      approved_count: number;
      restricted_count: number;
      grade_distribution: Record<string, number>;
      category_distribution: Record<string, number>;
    };
    assert.strictEqual(stats.total_products, 3);
    assert.strictEqual(stats.total_runs, 1);
    assert.ok(typeof stats.avg_roi === "number", "avg_roi should be a number");
    assert.ok(stats.avg_roi > 0, "avg_roi should be positive");
    assert.ok(typeof stats.avg_score === "number", "avg_score should be a number");
    assert.strictEqual(stats.approved_count, 2);
    assert.strictEqual(stats.restricted_count, 1);
    assert.ok(stats.grade_distribution, "should have grade_distribution");
    assert.strictEqual(stats.grade_distribution["A"], 1);
    assert.strictEqual(stats.grade_distribution["B"], 1);
    assert.strictEqual(stats.grade_distribution["D"], 1);
    assert.ok(stats.category_distribution, "should have category_distribution");
    assert.strictEqual(stats.category_distribution["Toys"], 2);
    assert.strictEqual(stats.category_distribution["Grocery"], 1);
  });

  it("returns zeros when no data exists", () => {
    const stats = run(dbPath, "export-stats") as { total_products: number; total_runs: number };
    assert.strictEqual(stats.total_products, 0);
    assert.strictEqual(stats.total_runs, 0);
  });
});

// ---------- export-history ----------
describe("research_db.py export-history", () => {
  let dbPath: string;
  beforeEach(() => {
    dbPath = freshDbPath();
    run(dbPath, "init");
  });
  afterEach(() => { fs.rmSync(path.dirname(dbPath), { recursive: true, force: true }); });

  it("returns time-series snapshots for an ASIN", () => {
    // Create two runs with the same ASIN to build history
    const input1 = JSON.stringify({
      source: "run 1",
      products: [{ asin: "B000HIS001", title: "History Product", buy_box_price: 19.99, bsr: 10000, score: 5.0, grade: "C" }],
    });
    const input2 = JSON.stringify({
      source: "run 2",
      products: [{ asin: "B000HIS001", title: "History Product", buy_box_price: 21.99, bsr: 8000, score: 6.5, grade: "B" }],
    });
    run(dbPath, `save-research '${input1}'`);
    run(dbPath, `save-research '${input2}'`);

    const history = run(dbPath, "export-history B000HIS001") as { asin: string; snapshots: Array<Record<string, unknown>> };
    assert.strictEqual(history.asin, "B000HIS001");
    assert.ok(Array.isArray(history.snapshots), "snapshots should be array");
    assert.strictEqual(history.snapshots.length, 2, "should have 2 snapshots");
    // Snapshots should be ordered by timestamp (oldest first is fine)
    assert.ok(history.snapshots[0].timestamp, "each snapshot should have timestamp");
  });

  it("returns empty snapshots for unknown ASIN", () => {
    const history = run(dbPath, "export-history B000UNKNOWN") as { asin: string; snapshots: unknown[] };
    assert.strictEqual(history.asin, "B000UNKNOWN");
    assert.deepStrictEqual(history.snapshots, []);
  });
});
