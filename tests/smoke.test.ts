import { describe, it } from "node:test";
import assert from "node:assert";

describe("smoke test", () => {
  it("should pass", () => {
    assert.strictEqual(1 + 1, 2);
  });
});
