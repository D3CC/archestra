// src/catalog/agent-template-catalog.ts
import { z } from 'zod';
import { AgentConfig, AgentTemplate, MCPConfig } from '../types/agent';
import { logger } from '../utils/logger';
import { v4 as uuidv4 } from 'uuid';

// Schema for validating agent template definitions
const AgentTemplateSchema = z.object({
  id: z.string().uuid(),
  name: z.string().min(1).max(100),
  description: z.string().max(500).default(''),
  category: z.enum(['general', 'coding', 'data', 'writing', 'research', 'custom']),
  systemPrompt: z.string().min(1),
  model: z.string().min(1),
  tools: z.array(z.string()).default([]),
  mcpServers: z.array(z.object({
    name: z.string().min(1),
    url: z.string().url(),
    config: z.record(z.unknown()).optional(),
  })).default([]),
  metadata: z.record(z.unknown()).optional(),
});

export type AgentTemplateDefinition = z.infer<typeof AgentTemplateSchema>;

// In-memory catalog store (replace with database in production)
class AgentTemplateCatalog {
  private templates: Map<string, AgentTemplateDefinition> = new Map();

  constructor() {
    this.initializeDefaultTemplates();
  }

  private initializeDefaultTemplates(): void {
    const defaultTemplates: AgentTemplateDefinition[] = [
      {
        id: uuidv4(),
        name: 'Code Assistant Pro',
        description: 'Expert coding assistant with MCP server for code analysis',
        category: 'coding',
        systemPrompt: 'You are an expert software engineer. Help users write, debug, and optimize code. Use the available tools to analyze codebases and suggest improvements.',
        model: 'gpt-4',
        tools: ['code-analyzer', 'git-manager'],
        mcpServers: [
          {
            name: 'code-analysis-server',
            url: 'https://mcp.archestra.ai/code-analysis',
            config: { maxFileSize: 1048576 },
          },
        ],
      },
      {
        id: uuidv4(),
        name: 'Data Analyst',
        description: 'Data analysis specialist with database and visualization tools',
        category: 'data',
        systemPrompt: 'You are a data analyst. Help users explore datasets, run SQL queries, create visualizations, and derive insights from data.',
        model: 'gpt-4',
        tools: ['sql-executor', 'chart-generator', 'data-exporter'],
        mcpServers: [
          {
            name: 'data-connector',
            url: 'https://mcp.archestra.ai/data-connector',
            config: { supportedSources: ['postgresql', 'mysql', 'csv'] },
          },
          {
            name: 'visualization-server',
            url: 'https://mcp.archestra.ai/visualization',
          },
        ],
      },
      {
        id: uuidv4(),
        name: 'Research Assistant',
        description: 'Academic research helper with web search and citation tools',
        category: 'research',
        systemPrompt: 'You are a research assistant. Help users find academic papers, summarize research, generate citations, and organize literature reviews.',
        model: 'gpt-4-turbo',
        tools: ['web-search', 'paper-finder', 'citation-manager'],
        mcpServers: [
          {
            name: 'academic-search',
            url: 'https://mcp.archestra.ai/academic-search',
            config: { apiKey: '${ACADEMIC_API_KEY}' },
          },
        ],
      },
      {
        id: uuidv4(),
        name: 'Content Writer',
        description: 'Creative writing assistant with grammar and style tools',
        category: 'writing',
        systemPrompt: 'You are a professional writer. Help users create engaging content, improve writing style, check grammar, and generate creative pieces.',
        model: 'gpt-4',
        tools: ['grammar-checker', 'style-analyzer', 'plagiarism-checker'],
        mcpServers: [
          {
            name: 'writing-enhancer',
            url: 'https://mcp.archestra.ai/writing-enhancer',
          },
        ],
      },
      {
        id: uuidv4(),
        name: 'General Assistant',
        description: 'Versatile assistant for everyday tasks and questions',
        category: 'general',
        systemPrompt: 'You are a helpful assistant. Answer questions, provide information, and assist with various tasks to the best of your ability.',
        model: 'gpt-3.5-turbo',
        tools: [],
        mcpServers: [],
      },
    ];

    defaultTemplates.forEach(template => {
      this.templates.set(template.id, template);
    });

    logger.info(`Initialized ${defaultTemplates.length} default agent templates`);
  }

  /**
   * Get all available templates, optionally filtered by category
   */
  getTemplates(category?: string): AgentTemplateDefinition[] {
    const allTemplates = Array.from(this.templates.values());
    if (category) {
      return allTemplates.filter(t => t.category === category);
    }
    return allTemplates;
  }

  /**
   * Get a single template by ID
   */
  getTemplate(id: string): AgentTemplateDefinition | undefined {
    return this.templates.get(id);
  }

  /**
   * Register a new custom template
   */
  registerTemplate(template: Omit<AgentTemplateDefinition, 'id'>): AgentTemplateDefinition {
    const validated = AgentTemplateSchema.parse({
      ...template,
      id: uuidv4(),
    });

    this.templates.set(validated.id, validated);
    logger.info(`Registered new template: ${validated.name} (${validated.id})`);
    return validated;
  }

  /**
   * Delete a template by ID
   */
  deleteTemplate(id: string): boolean {
    const deleted = this.templates.delete(id);
    if (deleted) {
      logger.info(`Deleted template: ${id}`);
    }
    return deleted;
  }

  /**
   * Convert a template to a fully configured AgentConfig
   */
  templateToAgentConfig(templateId: string, overrides?: Partial<AgentConfig>): AgentConfig {
    const template = this.getTemplate(templateId);
    if (!template) {
      throw new Error(`Template not found: ${templateId}`);
    }

    const config: AgentConfig = {
      id: uuidv4(),
      name: template.name,
      systemPrompt: template.systemPrompt,
      model: template.model,
      tools: template.tools,
      mcpServers: template.mcpServers.map(server => ({
        name: server.name,
        url: server.url,
        config: server.config || {},
      })),
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    // Apply any overrides
    if (overrides) {
      Object.assign(config, overrides);
    }

    return config;
  }

  /**
   * Install MCP servers for a given template
   */
  async installMCPServers(templateId: string): Promise<MCPConfig[]> {
    const template = this.getTemplate(templateId);
    if (!template) {
      throw new Error(`Template not found: ${templateId}`);
    }

    const installedServers: MCPConfig[] = [];

    for (const server of template.mcpServers) {
      try {
        // Simulate MCP server installation (replace with actual MCP protocol)
        logger.info(`Installing MCP server: ${server.name} at ${server.url}`);
        
        // In production, this would use the MCP protocol to register the server
        const mcpConfig: MCPConfig = {
          name: server.name,
          url: server.url,
          config: server.config || {},
          status: 'installed',
          installedAt: new Date().toISOString(),
        };

        installedServers.push(mcpConfig);
        logger.info(`Successfully installed MCP server: ${server.name}`);
      } catch (error) {
        logger.error(`Failed to install MCP server ${server.name}:`, error);
        throw error;
      }
    }

    return installedServers;
  }
}

// Singleton instance
export const agentTemplateCatalog = new AgentTemplateCatalog();

// Export types
export type { AgentTemplateDefinition };
