# archestra/agents/template_catalog.py
"""
Agent template catalog module for quickstart agent deployment.
Provides pre-built agent templates with system prompts, models, tool assignments,
and MCP server installation support.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

import yaml

from archestra.agents.base import AgentConfig
from archestra.mcp.server import MCPServerConfig
from archestra.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class AgentTemplate:
    """A pre-built agent template for quickstart deployment."""
    name: str
    description: str
    system_prompt: str
    model: str
    tools: List[str] = field(default_factory=list)
    mcp_servers: List[MCPServerConfig] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_agent_config(self) -> AgentConfig:
        """Convert template to an AgentConfig for agent instantiation."""
        return AgentConfig(
            name=self.name,
            system_prompt=self.system_prompt,
            model=self.model,
            tools=self.tools,
            mcp_servers=self.mcp_servers,
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentTemplate":
        mcp_servers = [
            MCPServerConfig(**srv) if isinstance(srv, dict) else srv
            for srv in data.pop("mcp_servers", [])
        ]
        return cls(mcp_servers=mcp_servers, **data)


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------

class AgentTemplateCatalog:
    """
    Manages a collection of agent templates.
    Supports loading from YAML/JSON, searching, and one-click deployment.
    """

    def __init__(self, templates: Optional[List[AgentTemplate]] = None):
        self._templates: Dict[str, AgentTemplate] = {}
        if templates:
            for t in templates:
                self._templates[t.name] = t

    # ---- Loading ----

    @classmethod
    def from_yaml(cls, path: str) -> "AgentTemplateCatalog":
        """Load catalog from a YAML file."""
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        return cls._from_list(data)

    @classmethod
    def from_json(cls, path: str) -> "AgentTemplateCatalog":
        """Load catalog from a JSON file."""
        with open(path, "r") as f:
            data = json.load(f)
        return cls._from_list(data)

    @classmethod
    def _from_list(cls, data: Any) -> "AgentTemplateCatalog":
        if isinstance(data, list):
            templates = [AgentTemplate.from_dict(item) for item in data]
        elif isinstance(data, dict) and "templates" in data:
            templates = [AgentTemplate.from_dict(item) for item in data["templates"]]
        else:
            raise ValueError("Invalid catalog format: expected list or dict with 'templates' key")
        return cls(templates)

    # ---- Access ----

    def list_templates(self) -> List[Dict[str, Any]]:
        """Return a list of template summaries."""
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

    def get_template(self, name: str) -> Optional[AgentTemplate]:
        """Get a template by name."""
        return self._templates.get(name)

    def add_template(self, template: AgentTemplate) -> None:
        """Add or update a template."""
        self._templates[template.name] = template
        logger.info("Added template '%s'", template.name)

    def remove_template(self, name: str) -> bool:
        """Remove a template by name. Returns True if removed."""
        if name in self._templates:
            del self._templates[name]
            logger.info("Removed template '%s'", name)
            return True
        return False

    # ---- Deployment ----

    def deploy(self, template_name: str, tool_registry: Optional[ToolRegistry] = None) -> AgentConfig:
        """
        One-click deployment: returns an AgentConfig ready for agent creation.
        Optionally validates tools against a ToolRegistry.
        """
        template = self.get_template(template_name)
        if not template:
            raise ValueError(f"Template '{template_name}' not found")

        if tool_registry:
            for tool_name in template.tools:
                if not tool_registry.has_tool(tool_name):
                    logger.warning("Tool '%s' not in registry, will be unavailable", tool_name)

        config = template.to_agent_config()
        logger.info("Deploying agent from template '%s'", template_name)
        return config

    # ---- Serialization ----

    def to_dict(self) -> Dict[str, Any]:
        return {"templates": [t.to_dict() for t in self._templates.values()]}

    def save_yaml(self, path: str) -> None:
        with open(path, "w") as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False)

    def save_json(self, path: str) -> None:
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)


# ---------------------------------------------------------------------------
# Built-in Quickstart Templates
# ---------------------------------------------------------------------------

def get_default_catalog() -> AgentTemplateCatalog:
    """Return a catalog with built-in quickstart templates."""
    templates = [
        AgentTemplate(
            name="customer-support-agent",
            description="Handles customer inquiries with empathy and knowledge base access.",
            system_prompt=(
                "You are a helpful customer support agent. "
                "Answer questions politely, use the knowledge base tool to find answers, "
                "and escalate to a human if needed."
            ),
            model="gpt-4",
            tools=["knowledge_base_search", "ticket_creator"],
            mcp_servers=[
                MCPServerConfig(
                    name="knowledge_base",
                    command="python",
                    args=["-m", "archestra.mcp.servers.knowledge_base"],
                ),
            ],
        ),
        AgentTemplate(
            name="code-reviewer",
            description="Reviews code changes for bugs, style, and security.",
            system_prompt=(
                "You are a senior code reviewer. Analyze the provided diff, "
                "point out potential bugs, style issues, and security vulnerabilities. "
                "Be constructive and concise."
            ),
            model="gpt-4-turbo",
            tools=["static_analysis", "lint_checker"],
            mcp_servers=[
                MCPServerConfig(
                    name="code_analyzer",
                    command="python",
                    args=["-m", "archestra.mcp.servers.code_analyzer"],
                ),
            ],
        ),
        AgentTemplate(
            name="data-analyst",
            description="Analyzes datasets and generates reports.",
            system_prompt=(
                "You are a data analyst. Given a dataset, perform exploratory analysis, "
                "generate visualizations, and summarize key insights."
            ),
            model="gpt-4",
            tools=["pandas_executor", "plot_generator"],
            mcp_servers=[
                MCPServerConfig(
                    name="data_tools",
                    command="python",
                    args=["-m", "archestra.mcp.servers.data_tools"],
                ),
            ],
        ),
    ]
    return AgentTemplateCatalog(templates)
