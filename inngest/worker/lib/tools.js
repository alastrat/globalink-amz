const { execSync } = require("child_process");

const TOOLS_DIR = process.env.TOOLS_DIR || "/tools";

/**
 * Execute a Python tool script and return parsed JSON output.
 * @param {string} script - Script filename (e.g., "sp-api-query.py")
 * @param {string[]} args - Command arguments
 * @param {object} [opts] - Options
 * @param {number} [opts.timeout=60000] - Timeout in ms
 * @returns {object} Parsed JSON output
 */
function execTool(script, args = [], { timeout = 60000 } = {}) {
  const escapedArgs = args.map((a) => `'${String(a).replace(/'/g, "'\\''")}'`);
  const cmd = `python3 ${TOOLS_DIR}/${script} ${escapedArgs.join(" ")}`;

  try {
    const result = execSync(cmd, {
      encoding: "utf-8",
      timeout,
      env: { ...process.env, PYTHONIOENCODING: "utf-8" },
    });

    return JSON.parse(result.trim());
  } catch (err) {
    const output = err.stdout || err.stderr || err.message;
    console.error(`Tool error [${script} ${args.join(" ")}]:`, output);

    // Try to parse error JSON from tool output
    try {
      return JSON.parse(output.trim());
    } catch {
      return { error: `Tool execution failed: ${output.substring(0, 500)}` };
    }
  }
}

module.exports = { execTool };
