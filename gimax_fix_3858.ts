// src/catalog/agent-template-catalog.ts
import { z } from 'zod';
import { AgentTemplate, AgentTemplateSchema } from './types';
import { MCPManager } from '../mcp/mcp-manager';
import { AgentManager } from '../agents/agent-manager';

/**
 * Pre-built agent template catalog for quickstart agent creation.
 * Each template includes system prompt, model configuration, tool assignments,
 * and associated MCP server definitions.
 */
export class AgentTemplateCatalog {
  private templates: Map<string, AgentTemplate> = new Map();
  private mcpManager: MCPManager;
  private agentManager: AgentManager;

  constructor(mcpManager: MCPManager, agentManager: AgentManager) {
    this.mcpManager = mcpManager;
    this.agentManager = agentManager;
    this.registerDefaults();
  }

  /**
   * Register a new agent template.
   */
  register(template: AgentTemplate): void {
    const parsed = AgentTemplateSchema.parse(template);
    this.templates.set(parsed.id, parsed);
  }

  /**
   * Get a template by ID.
   */
  get(id: string): AgentTemplate | undefined {
    return this.templates.get(id);
  }

  /**
   * List all available templates.
   */
  list(): AgentTemplate[] {
    return Array.from(this.templates.values());
  }

  /**
   * Spin up a fully-configured agent from a template in a single click.
   * Installs MCP servers, creates the agent with system prompt, model, and tools.
   */
  async instantiate(templateId: string, userId: string): Promise<{ agentId: string; mcpServerIds: string[] }> {
    const template = this.templates.get(templateId);
    if (!template) {
      throw new Error(`Template '${templateId}' not found`);
    }

    // Install MCP servers defined in the template
    const mcpServerIds: string[] = [];
    for (const serverDef of template.mcpServers) {
      const serverId = await this.mcpManager.installServer(serverDef, userId);
      mcpServerIds.push(serverId);
    }

    // Create the agent with system prompt, model, and tool assignments
    const agentId = await this.agentManager.createAgent({
      name: template.name,
      systemPrompt: template.systemPrompt,
      model: template.model,
      tools: template.tools,
      mcpServerIds,
      userId,
    });

    return { agentId, mcpServerIds };
  }

  /**
   * Register default quickstart templates.
   */
  private registerDefaults(): void {
    this.register({
      id: 'customer-support-bot',
      name: 'Customer Support Bot',
      description: 'Handles common customer inquiries with empathy and accuracy.',
      systemPrompt: 'You are a helpful customer support agent. Answer questions politely and accurately. If you cannot resolve an issue, escalate to a human.',
      model: 'gpt-4',
      tools: ['ticket-lookup', 'knowledge-base-search', 'escalate-to-human'],
      mcpServers: [
        {
          name: 'ticket-system',
          command: 'npx',
          args: ['@archestra/mcp-ticket-system'],
          env: {},
        },
        {
          name: 'knowledge-base',
          command: 'npx',
          args: ['@archestra/mcp-knowledge-base'],
          env: {},
        },
      ],
    });

    this.register({
      id: 'code-reviewer',
      name: 'Code Reviewer',
      description: 'Reviews pull requests for code quality, security, and best practices.',
      systemPrompt: 'You are an expert code reviewer. Analyze code changes, suggest improvements, and flag potential bugs or security issues.',
      model: 'gpt-4-turbo',
      tools: ['git-diff', 'static-analysis', 'dependency-check'],
      mcpServers: [
        {
          name: 'git-integration',
          command: 'npx',
          args: ['@archestra/mcp-git'],
          env: {},
        },
        {
          name: 'code-analysis',
          command: 'npx',
          args: ['@archestra/mcp-code-analyzer'],
          env: {},
        },
      ],
    });

    this.register({
      id: 'data-analyst',
      name: 'Data Analyst',
      description: 'Queries databases, generates reports, and visualizes data.',
      systemPrompt: 'You are a data analyst assistant. Help users query databases, create visualizations, and interpret results.',
      model: 'gpt-4',
      tools: ['sql-query', 'chart-generator', 'data-export'],
      mcpServers: [
        {
          name: 'database-connector',
          command: 'npx',
          args: ['@archestra/mcp-database'],
          env: {},
        },
        {
          name: 'visualization',
          command: 'npx',
          args: ['@archestra/mcp-chart'],
          env: {},
        },
      ],
    });
  }
}
