// src/catalog/agent-template-catalog.ts
import { z } from 'zod';
import { AgentConfig, AgentTemplate, MCPInstallation } from '../types/agent';
import { logger } from '../utils/logger';
import { MCPManager } from '../mcp/mcp-manager';

// Schema for validating agent template definitions
const AgentTemplateSchema = z.object({
  id: z.string().min(1),
  name: z.string().min(1),
  description: z.string(),
  category: z.enum(['general', 'coding', 'writing', 'data', 'research', 'custom']),
  systemPrompt: z.string().min(1),
  model: z.string().min(1),
  tools: z.array(z.string()),
  mcpServers: z.array(z.object({
    name: z.string().min(1),
    url: z.string().url(),
    config: z.record(z.unknown()).optional(),
  })),
  version: z.string().regex(/^\d+\.\d+\.\d+$/),
  author: z.string().optional(),
  tags: z.array(z.string()).optional(),
});

export type AgentTemplateDefinition = z.infer<typeof AgentTemplateSchema>;

/**
 * Catalog of pre-built agent templates for quickstart
 */
export class AgentTemplateCatalog {
  private templates: Map<string, AgentTemplateDefinition> = new Map();
  private mcpManager: MCPManager;

  constructor(mcpManager: MCPManager) {
    this.mcpManager = mcpManager;
    this.loadBuiltinTemplates();
  }

  /**
   * Load built-in templates that ship with the application
   */
  private loadBuiltinTemplates(): void {
    const builtinTemplates: AgentTemplateDefinition[] = [
      {
        id: 'research-assistant',
        name: 'Research Assistant',
        description: 'A general-purpose research agent with web search and data extraction capabilities.',
        category: 'research',
        systemPrompt: `You are a research assistant. Your goal is to help users find, analyze, and summarize information from various sources. Use the available tools to search the web, extract content, and compile comprehensive reports. Always cite your sources and provide balanced perspectives.`,
        model: 'gpt-4',
        tools: ['web-search', 'content-extractor', 'summarizer'],
        mcpServers: [
          { name: 'web-search', url: 'https://mcp.archestra.ai/web-search/v1', config: { apiKey: '${env:SEARCH_API_KEY}' } },
          { name: 'content-extractor', url: 'https://mcp.archestra.ai/content-extractor/v1' },
        ],
        version: '1.0.0',
        author: 'Archestra Team',
        tags: ['research', 'search', 'summarization'],
      },
      {
        id: 'code-reviewer',
        name: 'Code Reviewer',
        description: 'Expert code review agent with static analysis and best practice enforcement.',
        category: 'coding',
        systemPrompt: `You are an expert code reviewer. Analyze code for bugs, security vulnerabilities, performance issues, and adherence to best practices. Provide constructive feedback with specific line references and suggested fixes. Support multiple programming languages.`,
        model: 'gpt-4',
        tools: ['static-analyzer', 'code-formatter', 'security-scanner'],
        mcpServers: [
          { name: 'static-analyzer', url: 'https://mcp.archestra.ai/static-analysis/v1' },
          { name: 'security-scanner', url: 'https://mcp.archestra.ai/security-scan/v1' },
        ],
        version: '1.0.0',
        author: 'Archestra Team',
        tags: ['coding', 'review', 'security'],
      },
      {
        id: 'content-writer',
        name: 'Content Writer',
        description: 'Creative writing assistant for blogs, articles, and marketing copy.',
        category: 'writing',
        systemPrompt: `You are a creative content writer. Help users craft engaging blog posts, articles, social media content, and marketing copy. Adapt your tone and style based on the target audience and platform. Use SEO best practices and provide multiple variations when appropriate.`,
        model: 'gpt-4',
        tools: ['seo-analyzer', 'grammar-checker', 'tone-analyzer'],
        mcpServers: [
          { name: 'seo-analyzer', url: 'https://mcp.archestra.ai/seo/v1' },
          { name: 'grammar-checker', url: 'https://mcp.archestra.ai/grammar/v1' },
        ],
        version: '1.0.0',
        author: 'Archestra Team',
        tags: ['writing', 'content', 'seo'],
      },
    ];

    for (const template of builtinTemplates) {
      this.register(template);
    }
    logger.info(`Loaded ${builtinTemplates.length} built-in agent templates`);
  }

  /**
   * Register a new agent template
   */
  register(template: AgentTemplateDefinition): void {
    const validation = AgentTemplateSchema.safeParse(template);
    if (!validation.success) {
      throw new Error(`Invalid template definition: ${validation.error.message}`);
    }
    if (this.templates.has(template.id)) {
      throw new Error(`Template with id '${template.id}' already exists`);
    }
    this.templates.set(template.id, validation.data);
    logger.info(`Registered agent template: ${template.id} (${template.name})`);
  }

  /**
   * Get a template by ID
   */
  get(id: string): AgentTemplateDefinition | undefined {
    return this.templates.get(id);
  }

  /**
   * List all available templates, optionally filtered by category
   */
  list(category?: string): AgentTemplateDefinition[] {
    const allTemplates = Array.from(this.templates.values());
    if (category) {
      return allTemplates.filter(t => t.category === category);
    }
    return allTemplates;
  }

  /**
   * Remove a template from the catalog
   */
  unregister(id: string): boolean {
    const removed = this.templates.delete(id);
    if (removed) {
      logger.info(`Unregistered agent template: ${id}`);
    }
    return removed;
  }

  /**
   * Instantiate an agent from a template, installing MCP servers
   */
  async instantiate(templateId: string, overrides?: Partial<AgentConfig>): Promise<AgentConfig> {
    const template = this.templates.get(templateId);
    if (!template) {
      throw new Error(`Template '${templateId}' not found`);
    }

    logger.info(`Instantiating agent from template: ${templateId}`);

    // Install MCP servers
    const mcpInstallations: MCPInstallation[] = [];
    for (const server of template.mcpServers) {
      try {
        const installation = await this.mcpManager.install(server.name, server.url, server.config);
        mcpInstallations.push(installation);
        logger.info(`Installed MCP server: ${server.name}`);
      } catch (error) {
        logger.error(`Failed to install MCP server '${server.name}': ${error}`);
        throw new Error(`Failed to install MCP server '${server.name}': ${error}`);
      }
    }

    // Build agent config from template
    const agentConfig: AgentConfig = {
      id: `${template.id}-${Date.now()}`,
      name: template.name,
      systemPrompt: template.systemPrompt,
      model: template.model,
      tools: template.tools,
      mcpServers: mcpInstallations,
      metadata: {
        templateId: template.id,
        templateVersion: template.version,
        createdAt: new Date().toISOString(),
      },
      ...overrides,
    };

    logger.info(`Agent instantiated: ${agentConfig.id}`);
    return agentConfig;
  }

  /**
   * Search templates by name, description, or tags
   */
  search(query: string): AgentTemplateDefinition[] {
    const lowerQuery = query.toLowerCase();
    return Array.from(this.templates.values()).filter(template => {
      return (
        template.name.toLowerCase().includes(lowerQuery) ||
        template.description.toLowerCase().includes(lowerQuery) ||
        (template.tags && template.tags.some(tag => tag.toLowerCase().includes(lowerQuery)))
      );
    });
  }
}
