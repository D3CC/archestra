// src/catalog/agent-template-catalog.ts
import { z } from 'zod';
import { AgentTemplate, AgentTemplateSchema } from './types';
import { MCPManager } from '../mcp/mcp-manager';
import { AgentConfigurator } from '../agent/agent-configurator';
import { logger } from '../utils/logger';

/**
 * Pre-built agent template catalog for quickstart deployments.
 * Each template includes system prompt, model configuration, tool assignments,
 * and associated MCP server definitions.
 */
export class AgentTemplateCatalog {
  private templates: Map<string, AgentTemplate> = new Map();
  private mcpManager: MCPManager;
  private agentConfigurator: AgentConfigurator;

  constructor(mcpManager: MCPManager, agentConfigurator: AgentConfigurator) {
    this.mcpManager = mcpManager;
    this.agentConfigurator = agentConfigurator;
    this.registerDefaults();
  }

  /**
   * Register a new agent template.
   * @throws {Error} if template ID already exists
   */
  register(template: AgentTemplate): void {
    const parsed = AgentTemplateSchema.parse(template);
    if (this.templates.has(parsed.id)) {
      throw new Error(`Template with id '${parsed.id}' already exists`);
    }
    this.templates.set(parsed.id, parsed);
    logger.info(`Registered agent template: ${parsed.id} (${parsed.name})`);
  }

  /**
   * Retrieve a template by ID.
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
   * Deploy an agent from a template in a single click:
   * 1. Install all MCP servers defined in the template
   * 2. Configure the agent with system prompt, model, and tool assignments
   * @returns agent configuration result
   */
  async deploy(templateId: string): Promise<{ agentId: string; mcpServers: string[] }> {
    const template = this.templates.get(templateId);
    if (!template) {
      throw new Error(`Template '${templateId}' not found`);
    }

    logger.info(`Deploying agent from template: ${template.id}`);

    // Step 1: Install MCP servers
    const installedServers: string[] = [];
    for (const serverDef of template.mcpServers) {
      try {
        await this.mcpManager.install(serverDef);
        installedServers.push(serverDef.name);
        logger.info(`Installed MCP server: ${serverDef.name}`);
      } catch (error) {
        logger.error(`Failed to install MCP server '${serverDef.name}': ${error}`);
        throw error;
      }
    }

    // Step 2: Configure agent
    const agentConfig = {
      systemPrompt: template.systemPrompt,
      model: template.model,
      tools: template.tools,
      mcpServers: installedServers,
    };

    const agentId = await this.agentConfigurator.configure(agentConfig);
    logger.info(`Agent configured with id: ${agentId}`);

    return { agentId, mcpServers: installedServers };
  }

  /**
   * Register built-in default templates.
   */
  private registerDefaults(): void {
    const defaults: AgentTemplate[] = [
      {
        id: 'research-assistant',
        name: 'Research Assistant',
        description: 'AI research assistant with web search and document analysis capabilities',
        systemPrompt: 'You are a helpful research assistant. Use web search and document analysis tools to answer questions thoroughly.',
        model: 'gpt-4',
        tools: ['web_search', 'document_reader', 'summarizer'],
        mcpServers: [
          { name: 'web-search-mcp', url: 'https://mcp.archestra.ai/web-search', version: '1.0.0' },
          { name: 'document-analysis-mcp', url: 'https://mcp.archestra.ai/document-analysis', version: '1.0.0' },
        ],
      },
      {
        id: 'code-reviewer',
        name: 'Code Reviewer',
        description: 'Automated code review agent with static analysis and best practice checks',
        systemPrompt: 'You are an expert code reviewer. Analyze code for bugs, security issues, and style violations.',
        model: 'gpt-4-turbo',
        tools: ['static_analysis', 'security_scanner', 'style_checker'],
        mcpServers: [
          { name: 'code-analysis-mcp', url: 'https://mcp.archestra.ai/code-analysis', version: '2.0.0' },
        ],
      },
      {
        id: 'customer-support',
        name: 'Customer Support Agent',
        description: 'Customer support agent with ticket management and knowledge base access',
        systemPrompt: 'You are a friendly customer support agent. Help users resolve issues using the knowledge base and ticketing system.',
        model: 'gpt-3.5-turbo',
        tools: ['ticket_manager', 'knowledge_base', 'sentiment_analysis'],
        mcpServers: [
          { name: 'support-mcp', url: 'https://mcp.archestra.ai/support', version: '1.2.0' },
          { name: 'kb-mcp', url: 'https://mcp.archestra.ai/knowledge-base', version: '1.0.0' },
        ],
      },
    ];

    for (const template of defaults) {
      try {
        this.register(template);
      } catch (error) {
        logger.warn(`Failed to register default template '${template.id}': ${error}`);
      }
    }
  }
}
