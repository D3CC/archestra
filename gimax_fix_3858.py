# archestra/agents/catalog.py
"""
Agent template catalog module.

Provides a quickstart catalog of pre-built agent templates that allow users
to spin up a fully-configured agent (system prompt, model, tool assignments)
and install the agent's MCP servers in a single click.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from archestra.agents.base import AgentConfig
from archestra.mcp.server import MCPServerConfig
from archestra.tools.registry import ToolAssignment

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class AgentTemplate:
    """Represents a pre-built agent template."""

    id: str
    name: str
    description: str
    system_prompt: str
    model: str
    tool_assignments: List[ToolAssignment] = field(default_factory=list)
    mcp_servers: List[MCPServerConfig] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_agent_config(self) -> AgentConfig:
        """Convert this template into an AgentConfig for instantiation."""
        return AgentConfig(
            name=self.name,
            system_prompt=self.system_prompt,
            model=self.model,
            tool_assignments=self.tool_assignments,
            mcp_servers=self.mcp_servers,
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentTemplate":
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            system_prompt=data["system_prompt"],
            model=data["model"],
            tool_assignments=[
                ToolAssignment(**ta) for ta in data.get("tool_assignments", [])
            ],
            mcp_servers=[
                MCPServerConfig(**mcp) for mcp in data.get("mcp_servers", [])
            ],
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
        )


# ---------------------------------------------------------------------------
# Catalog loader
# ---------------------------------------------------------------------------

class AgentTemplateCatalog:
    """
    Manages a collection of AgentTemplate objects loaded from a directory
    of YAML/JSON files.
    """

    def __init__(self, templates_dir: Optional[Path] = None):
        self._templates: Dict[str, AgentTemplate] = {}
        if templates_dir is not None:
            self.load_from_directory(templates_dir)

    def load_from_directory(self, directory: Path) -> None:
        """Load all template definitions from .yaml, .yml, and .json files."""
        if not directory.is_dir():
            raise NotADirectoryError(f"{directory} is not a valid directory.")

        for file_path in sorted(directory.iterdir()):
            if file_path.suffix in (".yaml", ".yml", ".json"):
                try:
                    template = self._load_single_file(file_path)
                    self._templates[template.id] = template
                    logger.info("Loaded template '%s' from %s", template.id, file_path.name)
                except Exception as exc:
                    logger.warning("Failed to load template from %s: %s", file_path.name, exc)

    def _load_single_file(self, file_path: Path) -> AgentTemplate:
        with open(file_path, "r", encoding="utf-8") as f:
            if file_path.suffix == ".json":
                data = json.load(f)
            else:
                data = yaml.safe_load(f)
        if not isinstance(data, dict):
            raise ValueError("Template file must contain a mapping.")
        return AgentTemplate.from_dict(data)

    def get(self, template_id: str) -> Optional[AgentTemplate]:
        return self._templates.get(template_id)

    def list_templates(self, tag: Optional[str] = None) -> List[AgentTemplate]:
        if tag is None:
            return list(self._templates.values())
        return [t for t in self._templates.values() if tag in t.tags]

    def install_template(
        self, template_id: str, agent_registry: Any, mcp_installer: Any
    ) -> str:
        """
        One-click install: creates the agent and installs its MCP servers.

        Args:
            template_id: ID of the template to install.
            agent_registry: An object with a register(config) method.
            mcp_installer: An object with an install(server_config) method.

        Returns:
            The name of the created agent.
        """
        template = self.get(template_id)
        if template is None:
            raise KeyError(f"Template '{template_id}' not found.")

        # Install MCP servers first
        for mcp_config in template.mcp_servers:
            mcp_installer.install(mcp_config)
            logger.info("Installed MCP server '%s'", mcp_config.name)

        # Register agent
        agent_config = template.to_agent_config()
        agent_registry.register(agent_config)
        logger.info("Registered agent '%s' from template '%s'", agent_config.name, template_id)
        return agent_config.name


# ---------------------------------------------------------------------------
# Built-in quickstart templates
# ---------------------------------------------------------------------------

def get_default_catalog() -> AgentTemplateCatalog:
    """Return a catalog pre-populated with built-in quickstart templates."""
    catalog = AgentTemplateCatalog()

    # Template: Code Assistant
    catalog._templates["code-assistant"] = AgentTemplate(
        id="code-assistant",
        name="Code Assistant",
        description="A helpful coding assistant with Python and Git tool access.",
        system_prompt="You are an expert software engineer. Help the user write, review, and debug code.",
        model="gpt-4",
        tool_assignments=[
            ToolAssignment(tool_name="python_repl"),
            ToolAssignment(tool_name="git_operations"),
        ],
        mcp_servers=[
            MCPServerConfig(name="filesystem", command="npx", args=["-y", "@modelcontextprotocol/server-filesystem"]),
        ],
        tags=["coding", "developer", "quickstart"],
    )

    # Template: Data Analyst
    catalog._templates["data-analyst"] = AgentTemplate(
        id="data-analyst",
        name="Data Analyst",
        description="Analyze data with SQL and visualization tools.",
        system_prompt="You are a data analyst. Help the user query databases and create visualizations.",
        model="gpt-4",
        tool_assignments=[
            ToolAssignment(tool_name="sql_query"),
            ToolAssignment(tool_name="chart_generator"),
        ],
        mcp_servers=[
            MCPServerConfig(name="sqlite", command="uvx", args=["mcp-server-sqlite", "--db-path", "/tmp/analysis.db"]),
        ],
        tags=["data", "analytics", "quickstart"],
    )

    # Template: Research Assistant
    catalog._templates["research-assistant"] = AgentTemplate(
        id="research-assistant",
        name="Research Assistant",
        description="Gather and summarize information from the web.",
        system_prompt="You are a research assistant. Find relevant information and provide concise summaries.",
        model="gpt-4",
        tool_assignments=[
            ToolAssignment(tool_name="web_search"),
            ToolAssignment(tool_name="web_scraper"),
        ],
        mcp_servers=[
            MCPServerConfig(name="fetch", command="uvx", args=["mcp-server-fetch"]),
        ],
        tags=["research", "web", "quickstart"],
    )

    return catalog


# ---------------------------------------------------------------------------
# Convenience function for one-click install
# ---------------------------------------------------------------------------

def quickstart_install(
    template_id: str,
    agent_registry: Any,
    mcp_installer: Any,
    catalog: Optional[AgentTemplateCatalog] = None,
) -> str:
    """
    One-click install from the default catalog.

    Args:
        template_id: ID of the template.
        agent_registry: Agent registry object.
        mcp_installer: MCP installer object.
        catalog: Optional custom catalog; uses default if None.

    Returns:
        Name of the created agent.
    """
    if catalog is None:
        catalog = get_default_catalog()
    return catalog.install_template(template_id, agent_registry, mcp_installer)
