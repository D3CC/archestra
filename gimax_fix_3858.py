# archestra/agents/catalog.py
"""
Agent template catalog for quickstart deployment.
Provides pre-built agent configurations with system prompts, model settings,
tool assignments, and MCP server installation in a single click.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from archestra.agents.base import AgentConfig
from archestra.tools.registry import ToolRegistry
from archestra.mcp.installer import MCPInstaller
from archestra.exceptions import CatalogError

logger = logging.getLogger(__name__)


@dataclass
class AgentTemplate:
    """Represents a pre-built agent template."""
    name: str
    description: str
    system_prompt: str
    model: str
    tools: List[str] = field(default_factory=list)
    mcp_servers: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_agent_config(self) -> AgentConfig:
        """Convert template to AgentConfig for instantiation."""
        return AgentConfig(
            name=self.name,
            system_prompt=self.system_prompt,
            model=self.model,
            tools=self.tools,
            metadata=self.metadata,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentTemplate":
        """Deserialize from dictionary."""
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            system_prompt=data["system_prompt"],
            model=data["model"],
            tools=data.get("tools", []),
            mcp_servers=data.get("mcp_servers", []),
            metadata=data.get("metadata", {}),
        )


class AgentCatalog:
    """
    Catalog of pre-built agent templates.
    Supports loading from YAML/JSON files and programmatic registration.
    """

    def __init__(self, tool_registry: Optional[ToolRegistry] = None):
        self._templates: Dict[str, AgentTemplate] = {}
        self._tool_registry = tool_registry or ToolRegistry()
        self._mcp_installer = MCPInstaller()

    def register_template(self, template: AgentTemplate) -> None:
        """Register a new agent template."""
        if template.name in self._templates:
            logger.warning(f"Overwriting existing template: {template.name}")
        self._templates[template.name] = template
        logger.info(f"Registered template: {template.name}")

    def get_template(self, name: str) -> AgentTemplate:
        """Retrieve a template by name."""
        if name not in self._templates:
            raise CatalogError(f"Template '{name}' not found in catalog")
        return self._templates[name]

    def list_templates(self) -> List[Dict[str, Any]]:
        """List all available templates with summary info."""
        return [
            {
                "name": t.name,
                "description": t.description,
                "model": t.model,
                "tool_count": len(t.tools),
                "mcp_count": len(t.mcp_servers),
            }
            for t in self._templates.values()
        ]

    def deploy_agent(self, template_name: str) -> AgentConfig:
        """
        Deploy an agent from a template: install MCP servers and return config.
        """
        template = self.get_template(template_name)
        logger.info(f"Deploying agent from template: {template.name}")

        # Install MCP servers
        for server_url in template.mcp_servers:
            try:
                self._mcp_installer.install(server_url)
                logger.info(f"Installed MCP server: {server_url}")
            except Exception as e:
                raise CatalogError(
                    f"Failed to install MCP server '{server_url}': {e}"
                ) from e

        # Validate tools exist in registry
        for tool_name in template.tools:
            if not self._tool_registry.has_tool(tool_name):
                raise CatalogError(
                    f"Tool '{tool_name}' not found in registry"
                )

        return template.to_agent_config()

    def load_from_file(self, filepath: str) -> int:
        """
        Load templates from a YAML or JSON file.
        Returns number of templates loaded.
        """
        path = Path(filepath)
        if not path.exists():
            raise CatalogError(f"File not found: {filepath}")

        with open(path, "r") as f:
            if path.suffix in (".yaml", ".yml"):
                data = yaml.safe_load(f)
            elif path.suffix == ".json":
                data = json.load(f)
            else:
                raise CatalogError(f"Unsupported file format: {path.suffix}")

        templates_data = data if isinstance(data, list) else data.get("templates", [])
        count = 0
        for item in templates_data:
            template = AgentTemplate.from_dict(item)
            self.register_template(template)
            count += 1
        return count

    def save_to_file(self, filepath: str) -> None:
        """Save all templates to a YAML file."""
        templates_list = [t.to_dict() for t in self._templates.values()]
        data = {"templates": templates_list}
        path = Path(filepath)
        with open(path, "w") as f:
            if path.suffix in (".yaml", ".yml"):
                yaml.dump(data, f, default_flow_style=False)
            elif path.suffix == ".json":
                json.dump(data, f, indent=2)
            else:
                raise CatalogError(f"Unsupported file format: {path.suffix}")


# Pre-built quickstart templates
QUICKSTART_TEMPLATES = [
    AgentTemplate(
        name="code-assistant",
        description="AI coding assistant with code analysis and generation tools",
        system_prompt="You are an expert software engineer. Help users write, review, and debug code.",
        model="gpt-4",
        tools=["code_analyzer", "code_generator", "debugger"],
        mcp_servers=["https://mcp.archestra.ai/code-tools"],
        metadata={"category": "development", "version": "1.0"},
    ),
    AgentTemplate(
        name="data-analyst",
        description="Data analysis agent with SQL and visualization tools",
        system_prompt="You are a data analyst. Help users query databases and create visualizations.",
        model="gpt-4",
        tools=["sql_executor", "chart_generator", "data_cleaner"],
        mcp_servers=["https://mcp.archestra.ai/data-tools"],
        metadata={"category": "data", "version": "1.0"},
    ),
    AgentTemplate(
        name="customer-support",
        description="Customer support agent with ticketing and knowledge base tools",
        system_prompt="You are a helpful customer support agent. Assist users with their inquiries.",
        model="gpt-3.5-turbo",
        tools=["ticket_manager", "knowledge_base", "sentiment_analyzer"],
        mcp_servers=["https://mcp.archestra.ai/support-tools"],
        metadata={"category": "support", "version": "1.0"},
    ),
]


def initialize_catalog(tool_registry: Optional[ToolRegistry] = None) -> AgentCatalog:
    """Create catalog and register quickstart templates."""
    catalog = AgentCatalog(tool_registry=tool_registry)
    for template in QUICKSTART_TEMPLATES:
        catalog.register_template(template)
    return catalog
