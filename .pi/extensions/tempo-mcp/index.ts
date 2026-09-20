import type { AgentToolResult, ExtensionAPI, ToolDefinition } from "@earendil-works/pi-coding-agent";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { Type, type TSchema } from "typebox";

export type McpToolResult = {
  content: Array<{ type: string; [key: string]: unknown }>;
  [key: string]: unknown;
};

export interface McpToolClient {
  callTool(input: { name: string; arguments: Record<string, unknown> }): Promise<McpToolResult>;
  close(): Promise<void>;
}

export interface McpToolExecutor {
  callTool(name: string, args: Record<string, unknown>): Promise<McpToolResult>;
  close(): Promise<void>;
}

export const MCP_SERVER_DIR = resolve(dirname(fileURLToPath(import.meta.url)), "../../../mcp-server");

export function getMcpServerCommand(serverDir = MCP_SERVER_DIR) {
  return {
    command: "uv",
    args: ["run", "--directory", serverDir, "server.py"],
  };
}

async function createMcpClient(): Promise<McpToolClient> {
  const client = new Client(
    { name: "tempo-mcp-pi-extension", version: "0.1.0" },
    { capabilities: {} },
  );
  const command = getMcpServerCommand();
  const transport = new StdioClientTransport(command);

  await client.connect(transport);
  return client as unknown as McpToolClient;
}

export function createMcpToolExecutor(
  createConnection: () => Promise<McpToolClient> = createMcpClient,
): McpToolExecutor {
  let connectionPromise: Promise<McpToolClient> | undefined;
  let closePromise: Promise<void> | undefined;

  async function getConnection(): Promise<McpToolClient> {
    if (!connectionPromise) {
      const attempt = createConnection();
      connectionPromise = attempt;
      try {
        await attempt;
      } catch (error) {
        if (connectionPromise === attempt) connectionPromise = undefined;
        throw error;
      }
    }

    return connectionPromise;
  }

  return {
    async callTool(name, args) {
      const client = await getConnection();
      return client.callTool({ name, arguments: args });
    },
    async close() {
      if (!closePromise) {
        const activeConnection = connectionPromise;
        connectionPromise = undefined;
        closePromise = (async () => {
          if (!activeConnection) return;
          try {
            const client = await activeConnection;
            await client.close();
          } catch {
            // A failed connection has no live client to close.
          }
        })();
      }
      await closePromise;
    },
  };
}

export function toPiToolResult(result: McpToolResult): AgentToolResult<McpToolResult> {
  return {
    content: result.content as unknown as AgentToolResult<McpToolResult>["content"],
    details: result,
  };
}

function createTempoTool<TParams extends TSchema>(
  name: string,
  mcpToolName: string,
  label: string,
  description: string,
  parameters: TParams,
  executor: McpToolExecutor,
): ToolDefinition<TParams, McpToolResult> {
  return {
    name,
    label,
    description,
    parameters,
    async execute(_toolCallId, params) {
      const result = await executor.callTool(mcpToolName, params as Record<string, unknown>);
      return toPiToolResult(result);
    },
  };
}

export function registerTempoTools(pi: ExtensionAPI, executor: McpToolExecutor): void {
  pi.registerTool(createTempoTool(
    "tempo_log_work",
    "log_tempo_work",
    "Log Tempo Work",
    "Create a Tempo worklog for a Jira issue, recording the supplied hours, date, start time, and description.",
    Type.Object({
      issue_key: Type.String({ description: "The Jira issue key, for example SCHE-1." }),
      time_spent_hours: Type.Number({ description: "Hours to log to Tempo." }),
      date: Type.String({ description: "Worklog date in YYYY-MM-DD format." }),
      description_en: Type.String({ description: "Professional technical work description in English." }),
      start_time: Type.Optional(Type.String({
        description: "Work start time in HH:MM:SS format; defaults to 08:00:00.",
        default: "08:00:00",
      })),
    }),
    executor,
  ));

  pi.registerTool(createTempoTool(
    "tempo_search_jira_issues",
    "search_jira_issues",
    "Search Jira Issues",
    "Find recent active Jira issues in a project so the user can select work to log.",
    Type.Object({
      project_key: Type.String({ description: "The Jira project key, for example SCHE." }),
      max_results: Type.Optional(Type.Integer({ description: "Maximum issues to return; defaults to 10.", default: 10 })),
    }),
    executor,
  ));

  pi.registerTool(createTempoTool(
    "tempo_search_jira_projects",
    "search_jira_projects",
    "Search Jira Projects",
    "Find Jira projects by name or key so the user can identify the project for their work.",
    Type.Object({
      query: Type.Optional(Type.String({
        description: "Project name or key search term; defaults to an empty query.",
        default: "",
      })),
      max_results: Type.Optional(Type.Integer({ description: "Maximum projects to return; defaults to 10.", default: 10 })),
    }),
    executor,
  ));

  pi.registerTool(createTempoTool(
    "tempo_get_historical_git_activity",
    "get_historical_git_activity",
    "Get Historical Git Activity",
    "Read the user's commit activity from the supplied local repositories for a requested date range.",
    Type.Object({
      repo_paths: Type.String({ description: "Comma-separated absolute paths to git repositories." }),
      since: Type.String({ description: "Start date or relative time accepted by git log." }),
      until: Type.Optional(Type.String({ description: "End date or relative time; defaults to now.", default: "now" })),
    }),
    executor,
  ));
}

export default function tempoMcpExtension(pi: ExtensionAPI): void {
  const executor = createMcpToolExecutor();
  registerTempoTools(pi, executor);
  pi.on("session_shutdown", async () => {
    await executor.close();
  });
}
