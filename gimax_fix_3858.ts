// src/catalog/catalog.types.ts
export interface AgentTemplate {
  id: string;
  name: string;
  description: string;
  systemPrompt: string;
  model: string;
  tools: ToolAssignment[];
  mcpServers: MCPServerConfig[];
  category: string;
  tags: string[];
  version: string;
  createdAt: Date;
  updatedAt: Date;
}

export interface ToolAssignment {
  toolId: string;
  name: string;
  config?: Record<string, unknown>;
}

export interface MCPServerConfig {
  serverId: string;
  name: string;
  url: string;
  auth?: {
    type: 'none' | 'api-key' | 'oauth2';
    credentials?: Record<string, string>;
  };
}

export interface CatalogQuery {
  category?: string;
  tags?: string[];
  search?: string;
  page?: number;
  limit?: number;
}

export interface CatalogResult {
  templates: AgentTemplate[];
  total: number;
  page: number;
  limit: number;
}
