// src/catalog/agent-template-catalog.ts
import { z } from 'zod';
import { AgentConfig, AgentTemplate, MCPConfig } from '../types/agent';
import { logger } from '../utils/logger';

// Schema for validating agent templates
const AgentTemplateSchema = z.object({
  id: z.string().uuid(),
  name: z.string().min(1).max(100),
  description: z.string().max(500).default(''),
  category: z.enum(['customer-support', 'data-analysis', 'devops', 'content-creation', 'research', 'custom']),
  systemPrompt: z.string().min(1),
  model: z.string().default('gpt-4'),
  tools: z.array(z.string()).default([]),
  mcpServers: z.array(z.object({
    name: z.string().min(1),
    url: z.string().url(),
    config: z.record(z.unknown()).optional()
  })).default([]),
  version: z.string().regex(/^\d+\.\d+\.\d+$/).default('1.0.0'),
  createdAt: z.string().datetime().optional(),
  updatedAt: z.string().datetime().optional()
});

export type AgentTemplateType = z.infer<typeof AgentTemplateSchema>;

// In-memory catalog store (replace with database in production)
class AgentTemplateCatalog {
  private templates: Map<string, AgentTemplateType> = new Map();
  private static instance: AgentTemplateCatalog;

  private constructor() {
    this.initializeDefaultTemplates();
  }

  static getInstance(): AgentTemplateCatalog {
    if (!AgentTemplateCatalog.instance) {
      AgentTemplateCatalog.instance = new AgentTemplateCatalog();
    }
    return AgentTemplateCatalog.instance;
  }

  private initializeDefaultTemplates(): void {
    const defaultTemplates: AgentTemplateType[] = [
      {
        id: 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
        name: 'Customer Support Agent',
        description: 'Handles customer inquiries with empathy and accuracy',
        category: 'customer-support',
        systemPrompt: `You are a helpful customer support agent. Your goal is to:
- Respond to customer inquiries promptly and professionally
- Use available tools to look up order status, account info, and FAQs
- Escalate complex issues to human agents when necessary
- Maintain a friendly and empathetic tone`,
        model: 'gpt-4',
        tools: ['order-lookup', 'faq-search', 'ticket-system'],
        mcpServers: [
          {
            name: 'CRM MCP',
            url: 'https://crm-mcp.example.com',
            config: { apiVersion: 'v2' }
          },
          {
            name: 'Ticketing MCP',
            url: 'https://tickets-mcp.example.com'
          }
        ],
        version: '1.0.0'
      },
      {
        id: 'b2c3d4e5-f6a7-8901-bcde-f12345678901',
        name: 'Data Analyst Agent',
        description: 'Analyzes datasets and generates insights',
        category: 'data-analysis',
        systemPrompt: `You are a data analyst agent. Your responsibilities:
- Load and clean datasets using pandas
- Perform statistical analysis and generate visualizations
- Provide clear explanations of findings
- Suggest data-driven recommendations`,
        model: 'gpt-4',
        tools: ['python-executor', 'data-visualization', 'sql-query'],
        mcpServers: [
          {
            name: 'Database MCP',
            url: 'https://db-mcp.example.com',
            config: { maxConnections: 10 }
          }
        ],
        version: '1.0.0'
      },
      {
        id: 'c3d4e5f6-a7b8-9012-cdef-123456789012',
        name: 'DevOps Assistant',
        description: 'Manages infrastructure and deployments',
        category: 'devops',
        systemPrompt: `You are a DevOps assistant. Your capabilities:
- Monitor system health and alert on anomalies
- Execute deployment scripts safely
- Manage cloud resources efficiently
- Provide incident response guidance`,
        model: 'gpt-4',
        tools: ['kubectl', 'terraform', 'monitoring-dashboard'],
        mcpServers: [
          {
            name: 'Kubernetes MCP',
            url: 'https://k8s-mcp.example.com'
          },
          {
            name: 'Cloud MCP',
            url: 'https://cloud-mcp.example.com',
            config: { region: 'us-east-1' }
          }
        ],
        version: '1.0.0'
      }
    ];

    defaultTemplates.forEach(template => {
      this.templates.set(template.id, template);
    });
  }

  async getAllTemplates(): Promise<AgentTemplateType[]> {
    return Array.from(this.templates.values());
  }

  async getTemplateById(id: string): Promise<AgentTemplateType | null> {
    return this.templates.get(id) || null;
  }

  async getTemplatesByCategory(category: string): Promise<AgentTemplateType[]> {
    return Array.from(this.templates.values())
      .filter(t => t.category === category);
  }

  async addTemplate(template: Omit<AgentTemplateType, 'id' | 'createdAt' | 'updatedAt'>): Promise<AgentTemplateType> {
    const validated = AgentTemplateSchema.parse({
      ...template,
      id: crypto.randomUUID(),
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    });

    this.templates.set(validated.id, validated);
    logger.info(`Added agent template: ${validated.name} (${validated.id})`);
    return validated;
  }

  async updateTemplate(id: string, updates: Partial<AgentTemplateType>): Promise<AgentTemplateType | null> {
    const existing = this.templates.get(id);
    if (!existing) return null;

    const updated = AgentTemplateSchema.parse({
      ...existing,
      ...updates,
      id, // ensure id doesn't change
      updatedAt: new Date().toISOString()
    });

    this.templates.set(id, updated);
    logger.info(`Updated agent template: ${updated.name} (${id})`);
    return updated;
  }

  async deleteTemplate(id: string): Promise<boolean> {
    const deleted = this.templates.delete(id);
    if (deleted) {
      logger.info(`Deleted agent template: ${id}`);
    }
    return deleted;
  }

  async instantiateAgent(templateId: string, overrides?: Partial<AgentConfig>): Promise<AgentConfig> {
    const template = await this.getTemplateById(templateId);
    if (!template) {
      throw new Error(`Template not found: ${templateId}`);
    }

    const agentConfig: AgentConfig = {
      systemPrompt: template.systemPrompt,
      model: overrides?.model || template.model,
      tools: overrides?.tools || template.tools,
      mcpServers: template.mcpServers.map(server => ({
        name: server.name,
        url: server.url,
        config: server.config || {}
      })),
      ...overrides
    };

    logger.info(`Instantiated agent from template: ${template.name}`);
    return agentConfig;
  }

  async installMCPServers(templateId: string): Promise<MCPConfig[]> {
    const template = await this.getTemplateById(templateId);
    if (!template) {
      throw new Error(`Template not found: ${templateId}`);
    }

    const installedServers: MCPConfig[] = [];
    for (const server of template.mcpServers) {
      try {
        // Simulate MCP server installation
        const mcpConfig: MCPConfig = {
          name: server.name,
          url: server.url,
          config: server.config || {},
          status: 'installed',
          installedAt: new Date().toISOString()
        };
        installedServers.push(mcpConfig);
        logger.info(`Installed MCP server: ${server.name}`);
      } catch (error) {
        logger.error(`Failed to install MCP server: ${server.name}`, error);
        throw error;
      }
    }

    return installedServers;
  }
}

export const agentTemplateCatalog = AgentTemplateCatalog.getInstance();
