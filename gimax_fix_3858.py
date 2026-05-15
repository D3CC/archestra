# archestra/agent_templates/catalog.py
"""
Agent template catalog module for quickstart deployment of pre-built agent configurations.
Provides a registry of templates with system prompts, model assignments, tool assignments,
and MCP server installation support.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

from archestra.core.agent import AgentConfig
from archestra.core.mcp import MCPServerConfig
from archestra.core.tools import ToolAssignment

logger = logging.getLogger(__name__)


@dataclass
class AgentTemplate:
    """
    A pre-built agent template with all necessary configuration for quick deployment.
    """
    name: str
    description: str
    system_prompt: str
    model: str
    tools: List[ToolAssignment] = field(default_factory=list)
    mcp_servers: List[MCPServerConfig] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_agent_config(self) -> AgentConfig:
        """Convert template to an AgentConfig for agent instantiation."""
        return AgentConfig(
            system_prompt=self.system_prompt,
            model=self.model,
            tools=self.tools,
            mcp_servers=self.mcp_servers,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize template to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentTemplate":
        """Deserialize template from dictionary."""
        tools = [ToolAssignment(**t) if isinstance(t, dict) else t for t in data.get("tools", [])]
        mcp_servers = [MCPServerConfig(**m) if isinstance(m, dict) else m for m in data.get("mcp_servers", [])]
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            system_prompt=data["system_prompt"],
            model=data["model"],
            tools=tools,
            mcp_servers=mcp_servers,
            metadata=data.get("metadata", {}),
        )


class TemplateCatalog:
    """
    Registry of agent templates. Supports registration, lookup, and deployment.
    """

    def __init__(self):
        self._templates: Dict[str, AgentTemplate] = {}

    def register(self, template: AgentTemplate) -> None:
        """Register a new template in the catalog."""
        if template.name in self._templates:
            logger.warning(f"Overwriting existing template: {template.name}")
        self._templates[template.name] = template
        logger.info(f"Registered template: {template.name}")

    def get(self, name: str) -> Optional[AgentTemplate]:
        """Retrieve a template by name."""
        return self._templates.get(name)

    def list_templates(self) -> List[Dict[str, Any]]:
        """List all registered templates as dictionaries."""
        return [t.to_dict() for t in self._templates.values()]

    def deploy(self, name: str, overrides: Optional[Dict[str, Any]] = None) -> AgentConfig:
        """
        Deploy an agent from a template, optionally overriding fields.
        Returns an AgentConfig ready for agent creation.
        """
        template = self.get(name)
        if template is None:
            raise ValueError(f"Template '{name}' not found in catalog.")

        config = template.to_agent_config()
        if overrides:
            if "system_prompt" in overrides:
                config.system_prompt = overrides["system_prompt"]
            if "model" in overrides:
                config.model = overrides["model"]
            if "tools" in overrides:
                config.tools = [ToolAssignment(**t) if isinstance(t, dict) else t for t in overrides["tools"]]
            if "mcp_servers" in overrides:
                config.mcp_servers = [MCPServerConfig(**m) if isinstance(m, dict) else m for m in overrides["mcp_servers"]]
        return config

    def save_to_file(self, filepath: str) -> None:
        """Serialize catalog to JSON file."""
        data = {name: t.to_dict() for name, t in self._templates.items()}
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Catalog saved to {filepath}")

    @classmethod
    def load_from_file(cls, filepath: str) -> "TemplateCatalog":
        """Load catalog from JSON file."""
        with open(filepath, "r") as f:
            data = json.load(f)
        catalog = cls()
        for name, template_data in data.items():
            template = AgentTemplate.from_dict(template_data)
            catalog._templates[name] = template
        logger.info(f"Catalog loaded from {filepath} with {len(catalog._templates)} templates")
        return catalog


# Pre-built quickstart templates
def get_default_catalog() -> TemplateCatalog:
    """Return a catalog with pre-built quickstart templates."""
    catalog = TemplateCatalog()

    # Template: Customer Support Agent
    catalog.register(AgentTemplate(
        name="customer-support-agent",
        description="A helpful customer support agent with knowledge base and ticket creation tools.",
        system_prompt="You are a friendly customer support agent. Help users with their inquiries, "
                      "search the knowledge base, and create support tickets when needed.",
        model="gpt-4",
        tools=[
            ToolAssignment(name="search_knowledge_base", parameters={}),
            ToolAssignment(name="create_ticket", parameters={"priority": "normal"}),
        ],
        mcp_servers=[
            MCPServerConfig(name="knowledge-base", url="http://localhost:8000/mcp"),
        ],
        metadata={"category": "support", "version": "1.0.0"},
    ))

    # Template: Code Review Assistant
    catalog.register(AgentTemplate(
        name="code-review-assistant",
        description="An AI code reviewer that analyzes pull requests and provides feedback.",
        system_prompt="You are an expert code reviewer. Analyze code changes, suggest improvements, "
                      "and ensure best practices are followed.",
        model="gpt-4-turbo",
        tools=[
            ToolAssignment(name="analyze_code", parameters={"language": "python"}),
            ToolAssignment(name="fetch_pr_diff", parameters={}),
        ],
        mcp_servers=[
            MCPServerConfig(name="github-mcp", url="http://localhost:8001/mcp"),
        ],
        metadata={"category": "development", "version": "1.0.0"},
    ))

    # Template: Data Analyst
    catalog.register(AgentTemplate(
        name="data-analyst",
        description="A data analyst agent that can query databases and generate reports.",
        system_prompt="You are a data analyst. Help users query databases, visualize data, "
                      "and generate insightful reports.",
        model="gpt-4",
        tools=[
            ToolAssignment(name="sql_query", parameters={"database": "default"}),
            ToolAssignment(name="generate_chart", parameters={"type": "bar"}),
        ],
        mcp_servers=[
            MCPServerConfig(name="database-mcp", url="http://localhost:8002/mcp"),
        ],
        metadata={"category": "analytics", "version": "1.0.0"},
    ))

    return catalog
