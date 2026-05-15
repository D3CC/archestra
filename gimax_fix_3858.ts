// src/catalog/types.ts
export interface AgentTemplate {
  id: string;
  name: string;
  description: string;
  systemPrompt: string;
  model: string;
  tools: string[];
  mcpServers: MCPServerConfig[];
  category: 'general' | 'coding' | 'data' | 'research' | 'creative';
  tags: string[];
  version: string;
  author?: string;
}

export interface MCPServerConfig {
  name: string;
  command: string;
  args: string[];
  env?: Record<string, string>;
}

export interface CatalogEntry {
  template: AgentTemplate;
  installCount: number;
  rating: number;
  createdAt: Date;
  updatedAt: Date;
}
