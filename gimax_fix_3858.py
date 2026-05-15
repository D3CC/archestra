# archestra/agent_templates/catalog.py
"""
Agent template catalog for quickstart deployment.
Provides pre-built agent configurations with system prompts, models, tool assignments,
and MCP server installation in a single click.
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
from archestra.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent / "templates"


@dataclass
class AgentTemplate:
    """Represents a pre-built agent template."""

    id: str
    name: str
    description: str
    system_prompt: str
    model: str
    tools: List[str] = field(default_factory=list)
    mcp_servers: List[MCPServerConfig] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_agent_config(self) -> AgentConfig:
        """Convert template to an AgentConfig for instantiation."""
        return AgentConfig(
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
            for srv in data.get("mcp_servers", [])
        ]
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            system_prompt=data["system_prompt"],
            model=data["model"],
            tools=data.get("tools", []),
            mcp_servers=mcp_servers,
            metadata=data.get("metadata", {}),
        )


class TemplateCatalog:
    """Manages the catalog of agent templates."""

    def __init__(self, templates: Optional[Dict[str, AgentTemplate]] = None):
        self._templates: Dict[str, AgentTemplate] = templates or {}

    @classmethod
    def load_from_directory(cls, directory: Path = TEMPLATES_DIR) -> "TemplateCatalog":
        """Load templates from YAML/JSON files in a directory."""
        catalog = cls()
        if not directory.exists():
            logger.warning(f"Templates directory {directory} does not exist.")
            return catalog

        for file_path in directory.iterdir():
            if file_path.suffix in (".yaml", ".yml", ".json"):
                try:
                    with open(file_path, "r") as f:
                        if file_path.suffix == ".json":
                            data = json.load(f)
                        else:
                            data = yaml.safe_load(f)
                    if isinstance(data, list):
                        for item in data:
                            template = AgentTemplate.from_dict(item)
                            catalog.add_template(template)
                    elif isinstance(data, dict):
                        template = AgentTemplate.from_dict(data)
                        catalog.add_template(template)
                except Exception as e:
                    logger.error(f"Failed to load template from {file_path}: {e}")
        return catalog

    def add_template(self, template: AgentTemplate) -> None:
        """Add a template to the catalog."""
        if template.id in self._templates:
            logger.warning(f"Overwriting template with id '{template.id}'")
        self._templates[template.id] = template

    def get_template(self, template_id: str) -> Optional[AgentTemplate]:
        """Retrieve a template by ID."""
        return self._templates.get(template_id)

    def list_templates(self) -> List[AgentTemplate]:
        """Return all templates."""
        return list(self._templates.values())

    def install_template(
        self,
        template_id: str,
        tool_registry: ToolRegistry,
        install_mcp: bool = True,
    ) -> AgentConfig:
        """
        One-click install: get agent config and optionally install MCP servers.
        Returns an AgentConfig ready to be used.
        """
        template = self.get_template(template_id)
        if template is None:
            raise ValueError(f"Template '{template_id}' not found in catalog.")

        # Register tools if needed
        for tool_name in template.tools:
            if tool_name not in tool_registry.list_tools():
                logger.info(f"Tool '{tool_name}' not registered; skipping (assumes pre-registered).")

        # Install MCP servers
        if install_mcp and template.mcp_servers:
            for mcp_config in template.mcp_servers:
                logger.info(f"Installing MCP server: {mcp_config.name}")
                # Actual installation logic would go here (e.g., subprocess, API call)
                # For now, we just log and assume success.
                # mcp_installer.install(mcp_config)

        return template.to_agent_config()

    def to_dict(self) -> Dict[str, Any]:
        return {tid: tmpl.to_dict() for tid, tmpl in self._templates.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TemplateCatalog":
        templates = {
            tid: AgentTemplate.from_dict(tmpl_data)
            for tid, tmpl_data in data.items()
        }
        return cls(templates=templates)


# Built-in quickstart templates
DEFAULT_TEMPLATES = [
    AgentTemplate(
        id="research-assistant",
        name="Research Assistant",
        description="Helps with literature review, summarization, and fact-checking.",
        system_prompt="You are a research assistant. Help users find, summarize, and verify information.",
        model="gpt-4",
        tools=["web_search", "summarizer"],
        mcp_servers=[
            MCPServerConfig(name="search-mcp", command="python", args=["-m", "mcp_search_server"]),
        ],
    ),
    AgentTemplate(
        id="code-reviewer",
        name="Code Reviewer",
        description="Reviews code for bugs, style issues, and security vulnerabilities.",
        system_prompt="You are a senior code reviewer. Analyze code for issues and suggest improvements.",
        model="gpt-4",
        tools=["code_analyzer", "linter"],
        mcp_servers=[
            MCPServerConfig(name="code-mcp", command="python", args=["-m", "mcp_code_server"]),
        ],
    ),
    AgentTemplate(
        id="customer-support",
        name="Customer Support Agent",
        description="Handles common customer inquiries and ticket routing.",
        system_prompt="You are a helpful customer support agent. Resolve issues and escalate when necessary.",
        model="gpt-3.5-turbo",
        tools=["ticket_system", "knowledge_base"],
        mcp_servers=[],
    ),
]


def create_default_catalog() -> TemplateCatalog:
    """Create a catalog with built-in quickstart templates."""
    catalog = TemplateCatalog()
    for template in DEFAULT_TEMPLATES:
        catalog.add_template(template)
    return catalog
