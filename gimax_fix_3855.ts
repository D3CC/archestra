// src/mcp-servers/windmill-mcp-apps/server.ts
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  ToolSchema,
} from '@modelcontextprotocol/sdk/types.js';
import { z } from 'zod';
import { zodToJsonSchema } from 'zod-to-json-schema';

// Windmill API client
class WindmillClient {
  private baseUrl: string;
  private apiKey: string;
  private workspaceId: string;

  constructor(baseUrl: string, apiKey: string, workspaceId: string) {
    this.baseUrl = baseUrl.replace(/\/$/, '');
    this.apiKey = apiKey;
    this.workspaceId = workspaceId;
  }

  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}/api/v1${path}`;
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.apiKey}`,
        ...options.headers,
      },
    });

    if (!response.ok) {
      throw new Error(`Windmill API error: ${response.status} ${response.statusText}`);
    }

    return response.json();
  }

  async createWorkflow(name: string, description: string, modules: any[]): Promise<any> {
    const workflow = {
      workspace_id: this.workspaceId,
      name,
      description,
      modules,
      draft_only: false,
    };

    return this.request('/w/create', {
      method: 'POST',
      body: JSON.stringify(workflow),
    });
  }

  async getWorkflow(id: string): Promise<any> {
    return this.request(`/w/${id}`);
  }

  async updateWorkflow(id: string, modules: any[]): Promise<any> {
    return this.request(`/w/${id}`, {
      method: 'PUT',
      body: JSON.stringify({ modules }),
    });
  }

  async runWorkflow(id: string, args: Record<string, any> = {}): Promise<any> {
    return this.request(`/w/${id}/run`, {
      method: 'POST',
      body: JSON.stringify(args),
    });
  }

  async listWorkflows(): Promise<any[]> {
    return this.request(`/workspaces/${this.workspaceId}/w/list`);
  }
}

// Schema definitions
const CreateWorkflowSchema = z.object({
  name: z.string().min(1).describe('Workflow name'),
  description: z.string().describe('Workflow description'),
  modules: z.array(z.any()).describe('Array of workflow modules/nodes'),
});

const UpdateWorkflowSchema = z.object({
  id: z.string().min(1).describe('Workflow ID'),
  modules: z.array(z.any()).describe('Updated modules/nodes'),
});

const RunWorkflowSchema = z.object({
  id: z.string().min(1).describe('Workflow ID'),
  args: z.record(z.any()).optional().describe('Workflow arguments'),
});

const ListWorkflowsSchema = z.object({});

// Tool definitions
const tools = [
  {
    name: 'create_workflow',
    description: 'Create a new workflow in Windmill',
    inputSchema: zodToJsonSchema(CreateWorkflowSchema),
  },
  {
    name: 'update_workflow',
    description: 'Update an existing workflow in Windmill',
    inputSchema: zodToJsonSchema(UpdateWorkflowSchema),
  },
  {
    name: 'run_workflow',
    description: 'Execute a workflow in Windmill',
    inputSchema: zodToJsonSchema(RunWorkflowSchema),
  },
  {
    name: 'list_workflows',
    description: 'List all workflows in the workspace',
    inputSchema: zodToJsonSchema(ListWorkflowsSchema),
  },
];

// MCP App definition for Archestra
const mcpAppDefinition = {
  name: 'windmill-workflow-builder',
  label: 'Windmill Workflow Builder',
  description: 'Create and manage Windmill workflows as interactive MCP Apps',
  icon: 'workflow',
  category: 'automation',
  version: '1.0.0',
  capabilities: {
    interactive: true,
    nodeEditing: true,
    realtimeUpdates: true,
  },
  defaultView: 'canvas',
  supportedActions: ['create', 'update', 'run', 'list'],
};

async function main() {
  // Configuration from environment
  const windmillBaseUrl = process.env.WINDMILL_BASE_URL || 'http://localhost:8000';
  const windmillApiKey = process.env.WINDMILL_API_KEY || '';
  const windmillWorkspaceId = process.env.WINDMILL_WORKSPACE_ID || 'default';

  if (!windmillApiKey) {
    console.error('WINDMILL_API_KEY environment variable is required');
    process.exit(1);
  }

  const client = new WindmillClient(windmillBaseUrl, windmillApiKey, windmillWorkspaceId);

  const server = new Server(
    {
      name: 'windmill-mcp-apps',
      version: '1.0.0',
    },
    {
      capabilities: {
        tools: {},
        resources: {},
        mcpApps: [mcpAppDefinition],
      },
    }
  );

  // Register tool handlers
  server.setRequestHandler(ListToolsRequestSchema, async () => ({
    tools,
  }));

  server.setRequestHandler(CallToolRequestSchema, async (request) => {
    const { name, arguments: args } = request.params;

    try {
      switch (name) {
        case 'create_workflow': {
          const { name: workflowName, description, modules } = CreateWorkflowSchema.parse(args);
          const result = await client.createWorkflow(workflowName, description, modules);
          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify(result, null, 2),
              },
            ],
          };
        }

        case 'update_workflow': {
          const { id, modules } = UpdateWorkflowSchema.parse(args);
          const result = await client.updateWorkflow(id, modules);
          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify(result, null, 2),
              },
            ],
          };
        }

        case 'run_workflow': {
          const { id, args: workflowArgs } = RunWorkflowSchema.parse(args);
          const result = await client.runWorkflow(id, workflowArgs);
          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify(result, null, 2),
              },
            ],
          };
        }

        case 'list_workflows': {
          const workflows = await client.listWorkflows();
          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify(workflows, null, 2),
              },
            ],
          };
        }

        default:
          throw new Error(`Unknown tool: ${name}`);
      }
    } catch (error) {
      if (error instanceof z.ZodError) {
        return {
          content: [
            {
              type: 'text',
              text: `Validation error: ${error.message}`,
            },
          ],
          isError: true,
        };
      }
      return {
        content: [
          {
            type: 'text',
            text: `Error: ${error instanceof Error ? error.message : String(error)}`,
          },
        ],
        isError: true,
      };
    }
  });

  // Connect transport
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('Windmill MCP Apps server running on stdio');
}

main().catch((error) => {
  console.error('Server error:', error);
  process.exit(1);
});
