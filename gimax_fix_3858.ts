// src/catalog/agent-template-catalog.ts

import { z } from 'zod';
import { AgentConfig, AgentRole, ModelProvider, ToolAssignment } from '../agent/types';
import { MCPServerConfig } from '../mcp/types';

/**
 * Schema for an agent template in the catalog.
 */
export const AgentTemplateSchema = z.object({
  id: z.string().uuid(),
  name: z.string().min(1).max(100),
  description: z.string().max(500).default(''),
  category: z.enum(['customer-support', 'code-assistant', 'data-analyst', 'personal-assistant', 'custom']),
  systemPrompt: z.string().min(1),
  model: z.object({
    provider: z.nativeEnum(ModelProvider),
    modelId: z.string(),
    temperature: z.number().min(0).max(2).default(0.7),
    maxTokens: z.number().int().positive().default(4096),
  }),
  tools: z.array(z.object({
    toolId: z.string(),
    enabled: z.boolean().default(true),
    config: z.record(z.unknown()).optional(),
  })).default([]),
  mcpServers: z.array(z.object({
    serverId: z.string(),
    enabled: z.boolean().default(true),
    config: z.record(z.unknown()).optional(),
  })).default([]),
  metadata: z.object({
    author: z.string().default('archestra'),
    version: z.string().default('1.0.0'),
    tags: z.array(z.string()).default([]),
    createdAt: z.string().datetime(),
    updatedAt: z.string().datetime(),
  }),
});

export type AgentTemplate = z.infer<typeof AgentTemplateSchema>;

/**
 * Catalog of pre-built agent templates.
 */
export class AgentTemplateCatalog {
  private templates: Map<string, AgentTemplate> = new Map();

  constructor(initialTemplates?: AgentTemplate[]) {
    if (initialTemplates) {
      for (const tmpl of initialTemplates) {
        this.addTemplate(tmpl);
      }
    }
  }

  /**
   * Add a template to the catalog. Validates schema before insertion.
   */
  addTemplate(template: AgentTemplate): void {
    const parsed = AgentTemplateSchema.parse(template);
    if (this.templates.has(parsed.id)) {
      throw new Error(`Template with id '${parsed.id}' already exists.`);
    }
    this.templates.set(parsed.id, parsed);
  }

  /**
   * Retrieve a template by id.
   */
  getTemplate(id: string): AgentTemplate | undefined {
    return this.templates.get(id);
  }

  /**
   * List all templates, optionally filtered by category.
   */
  listTemplates(category?: string): AgentTemplate[] {
    const all = Array.from(this.templates.values());
    if (category) {
      return all.filter(t => t.category === category);
    }
    return all;
  }

  /**
   * Remove a template from the catalog.
   */
  removeTemplate(id: string): boolean {
    return this.templates.delete(id);
  }

  /**
   * Convert a template into a fully-configured AgentConfig and list of MCP server configs.
   */
  instantiateTemplate(templateId: string, overrides?: Partial<AgentTemplate>): { agentConfig: AgentConfig; mcpServers: MCPServerConfig[] } {
    const base = this.getTemplate(templateId);
    if (!base) {
      throw new Error(`Template '${templateId}' not found.`);
    }

    // Merge overrides (deep merge for simplicity)
    const merged: AgentTemplate = {
      ...base,
      ...overrides,
      model: { ...base.model, ...(overrides?.model || {}) },
      tools: overrides?.tools ?? base.tools,
      mcpServers: overrides?.mcpServers ?? base.mcpServers,
      metadata: { ...base.metadata, ...(overrides?.metadata || {}) },
    };

    const agentConfig: AgentConfig = {
      role: AgentRole.ASSISTANT,
      systemPrompt: merged.systemPrompt,
      model: merged.model,
      tools: merged.tools
        .filter(t => t.enabled)
        .map(t => ({
          toolId: t.toolId,
          config: t.config,
        } as ToolAssignment)),
    };

    const mcpServers: MCPServerConfig[] = merged.mcpServers
      .filter(s => s.enabled)
      .map(s => ({
        serverId: s.serverId,
        config: s.config,
      }));

    return { agentConfig, mcpServers };
  }
}

// Built-in quickstart templates
export const DEFAULT_TEMPLATES: AgentTemplate[] = [
  {
    id: 'a1b2c3d4-1234-5678-9abc-def012345678',
    name: 'Customer Support Agent',
    description: 'Handles common customer inquiries with empathy and accuracy.',
    category: 'customer-support',
    systemPrompt: 'You are a helpful customer support agent. Answer questions politely and provide accurate information. If unsure, escalate to a human.',
    model: {
      provider: ModelProvider.OPENAI,
      modelId: 'gpt-4o-mini',
      temperature: 0.5,
      maxTokens: 2048,
    },
    tools: [
      { toolId: 'knowledge-base-search', enabled: true },
      { toolId: 'ticket-creator', enabled: true },
    ],
    mcpServers: [
      { serverId: 'zendesk-mcp', enabled: true, config: { url: 'https://zendesk.example.com/mcp' } },
    ],
    metadata: {
      author: 'archestra',
      version: '1.0.0',
      tags: ['support', 'customer-service'],
      createdAt: '2025-01-01T00:00:00Z',
      updatedAt: '2025-01-01T00:00:00Z',
    },
  },
  {
    id: 'b2c3d4e5-2345-6789-abcd-ef012345679',
    name: 'Code Assistant',
    description: 'Helps write, review, and debug code in multiple languages.',
    category: 'code-assistant',
    systemPrompt: 'You are an expert software engineer. Provide clean, well-documented code. Explain your reasoning.',
    model: {
      provider: ModelProvider.ANTHROPIC,
      modelId: 'claude-3-5-sonnet-20241022',
      temperature: 0.2,
      maxTokens: 8192,
    },
    tools: [
      { toolId: 'code-executor', enabled: true },
      { toolId: 'file-reader', enabled: true },
    ],
    mcpServers: [
      { serverId: 'github-mcp', enabled: true, config: { repo: 'archestra-ai/archestra' } },
    ],
    metadata: {
      author: 'archestra',
      version: '1.0.0',
      tags: ['coding', 'debugging'],
      createdAt: '2025-01-02T00:00:00Z',
      updatedAt: '2025-01-02T00:00:00Z',
    },
  },
];
