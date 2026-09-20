import assert from "node:assert/strict";
import test from "node:test";
import { resolve } from "node:path";
import type { ExtensionAPI, ToolDefinition } from "@earendil-works/pi-coding-agent";
import {
  MCP_SERVER_DIR,
  createMcpToolExecutor,
  getMcpServerCommand,
  registerTempoTools,
  toPiToolResult,
  type McpToolClient,
  type McpToolResult,
} from "../index.ts";

test("starts one lazy MCP connection and forwards tool calls unchanged", async () => {
  const calls: Array<{ name: string; arguments: Record<string, unknown> }> = [];
  const result: McpToolResult = {
    content: [{ type: "text", text: "Worklog created" }],
    structuredContent: { worklogId: 42 },
  };
  let starts = 0;
  let closes = 0;
  const client: McpToolClient = {
    async callTool(input) {
      calls.push(input);
      return result;
    },
    async close() {
      closes += 1;
    },
  };
  const executor = createMcpToolExecutor(async () => {
    starts += 1;
    return client;
  });
  const args = { issue_key: "SCHE-1", time_spent_hours: 2 };

  const [first, second] = await Promise.all([
    executor.callTool("log_tempo_work", args),
    executor.callTool("search_jira_issues", { project_key: "SCHE" }),
  ]);

  assert.equal(starts, 1);
  assert.strictEqual(first, result);
  assert.strictEqual(second, result);
  assert.deepEqual(calls.sort((left, right) => left.name.localeCompare(right.name)), [
    { name: "log_tempo_work", arguments: args },
    { name: "search_jira_issues", arguments: { project_key: "SCHE" } },
  ]);

  const piResult = toPiToolResult(result);
  assert.strictEqual(piResult.content, result.content);
  assert.strictEqual(piResult.details, result);

  await executor.close();
  await executor.close();
  assert.equal(closes, 1);
});

test("registers the four native Tempo tools with server-compatible schemas", async () => {
  const tools: ToolDefinition[] = [];
  const calls: Array<{ name: string; args: Record<string, unknown> }> = [];
  const result: McpToolResult = { content: [{ type: "text", text: "ok" }] };
  const executor = {
    async callTool(name: string, args: Record<string, unknown>) {
      calls.push({ name, args });
      return result;
    },
    async close() {},
  };
  const pi = {
    registerTool(tool: ToolDefinition) {
      tools.push(tool);
    },
  } as unknown as ExtensionAPI;

  registerTempoTools(pi, executor);

  assert.deepEqual(tools.map((tool) => tool.name), [
    "tempo_log_work",
    "tempo_search_jira_issues",
    "tempo_search_jira_projects",
    "tempo_get_historical_git_activity",
  ]);
  assert.match(tools[0]!.description, /Tempo worklog/);
  assert.deepEqual(Object.keys((tools[0]!.parameters as { properties: object }).properties), [
    "issue_key",
    "time_spent_hours",
    "date",
    "description_en",
    "start_time",
  ]);

  const args = { project_key: "SCHE", max_results: 5 };
  const toolResult = await tools[1]!.execute("call-1", args, undefined, undefined, {} as never);
  assert.strictEqual(toolResult.details, result);
  assert.deepEqual(calls, [{ name: "search_jira_issues", args }]);
});

test("builds the stdio command from the extension location", () => {
  const command = getMcpServerCommand();

  assert.equal(command.command, "uv");
  assert.deepEqual(command.args, ["run", "--directory", MCP_SERVER_DIR, "server.py"]);
  assert.match(MCP_SERVER_DIR, /mcp-server$/);
  assert.notEqual(MCP_SERVER_DIR, resolve(process.cwd(), "mcp-server"));
});
