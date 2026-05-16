// src/catalog/agent-template-catalog.ts
import { z } from 'zod';
import { McpServerConfig } from '../mcp/types';
import { AgentConfig } from '../agent/types';

/**
 * Pre-built agent template for quickstart deployment.
 */
export interface AgentTemplate {
  id: string;
  name: string;
  description: string;
  category: 'customer-support' | 'data-analysis' | 'coding' | 'general';
  systemPrompt: string;
  model: string;
  tools: string[];
  mcpServers: McpServerConfig[];
  tags: string[];
  version: string;
}

export const AgentTemplateSchema = z.object({
  id: z.string().min(1),
  name: z.string().min(1),
  description: z.string().min(1),
  category: z.enum(['customer-support', 'data-analysis', 'coding', 'general']),
  systemPrompt: z.string().min(1),
  model: z.string().min(1),
  tools: z.array(z.string()),
  mcpServers: z.array(z.object({
    name: z.string(),
    command: z.string(),
    args: z.array(z.string()).optional(),
    env: z.record(z.string()).optional(),
  })),
  tags: z.array(z.string()),
  version: z.string(),
});

/**
 * Catalog of pre-built agent templates.
 */
export class AgentTemplateCatalog {
  private templates: Map<string, AgentTemplate> = new Map();

  constructor(initialTemplates?: AgentTemplate[]) {
    if (initialTemplates) {
      for (const tmpl of initialTemplates) {
        this.register(tmpl);
      }
    }
  }

  /**
   * Register a new template. Overwrites if id exists.
   */
  register(template: AgentTemplate): void {
    const parsed = AgentTemplateSchema.parse(template);
    this.templates.set(parsed.id, parsed);
  }

  /**
   * Retrieve a template by id.
   */
  get(id: string): AgentTemplate | undefined {
    return this.templates.get(id);
  }

  /**
   * List all templates, optionally filtered by category or tags.
   */
  list(filters?: { category?: string; tags?: string[] }): AgentTemplate[] {
    let result = Array.from(this.templates.values());
    if (filters?.category) {
      result = result.filter(t => t.category === filters.category);
    }
    if (filters?.tags && filters.tags.length > 0) {
      result = result.filter(t =>
        filters.tags!.some(tag => t.tags.includes(tag))
      );
    }
    return result;
  }

  /**
   * Remove a template by id.
   */
  remove(id: string): boolean {
    return this.templates.delete(id);
  }

  /**
   * Convert a template to an AgentConfig for deployment.
   */
  toAgentConfig(templateId: string, overrides?: Partial<AgentConfig>): AgentConfig {
    const template = this.get(templateId);
    if (!template) {
      throw new Error(`Template not found: ${templateId}`);
    }
    return {
      name: template.name,
      systemPrompt: template.systemPrompt,
      model: template.model,
      tools: template.tools,
      mcpServers: template.mcpServers,
      ...overrides,
    };
  }
}

// Default quickstart templates
export const DEFAULT_TEMPLATES: AgentTemplate[] = [
  {
    id: 'customer-support-bot',
    name: 'Customer Support Bot',
    description: 'Handles common customer inquiries with empathy and accuracy.',
    category: 'customer-support',
    systemPrompt: 'You are a helpful customer support agent. Answer questions politely and accurately. If you cannot resolve the issue, escalate to a human.',
    model: 'gpt-4o-mini',
    tools: ['ticket-lookup', 'knowledge-base-search'],
    mcpServers: [
      {
        name: 'zendesk-mcp',
        command: 'npx',
        args: ['@zendesk/mcp-server'],
        env: { ZENDESK_SUBDOMAIN: 'example' },
      },
    ],
    tags: ['support', 'customer-service'],
    version: '1.0.0',
  },
  {
    id: 'data-analyst',
    name: 'Data Analyst',
    description: 'Analyzes CSV/JSON data and generates visualizations.',
    category: 'data-analysis',
    systemPrompt: 'You are a data analyst. Help users explore datasets, run statistical analyses, and create charts.',
    model: 'gpt-4o',
    tools: ['python-executor', 'chart-generator'],
    mcpServers: [
      {
        name: 'jupyter-mcp',
        command: 'python',
        args: ['-m', 'jupyter_mcp'],
      },
    ],
    tags: ['data', 'analytics'],
    version: '1.0.0',
  },
  {
    id: 'code-reviewer',
    name: 'Code Reviewer',
    description: 'Reviews pull requests for bugs, style, and security issues.',
    category: 'coding',
    systemPrompt: 'You are a senior code reviewer. Analyze code for correctness, performance, and security. Provide constructive feedback.',
    model: 'claude-3-opus',
    tools: ['git-diff', 'linter', 'security-scanner'],
    mcpServers: [
      {
        name: 'github-mcp',
        command: 'npx',
        args: ['@github/mcp-server'],
        env: { GITHUB_TOKEN: process.env.GITHUB_TOKEN || '' },
      },
    ],
    tags: ['code-review', 'development'],
    version: '1.0.0',
  },
  {
    id: 'general-assistant',
    name: 'General Assistant',
    description: 'A versatile assistant for everyday tasks.',
    category: 'general',
    systemPrompt: 'You are a helpful assistant. Answer questions, summarize information, and help with tasks.',
    model: 'gpt-4o-mini',
    tools: ['web-search', 'calculator'],
    mcpServers: [],
    tags: ['general', 'productivity'],
    version: '1.0.0',
  },
];
