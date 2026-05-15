# archestra/agent_templates/catalog.py
"""
Agent template catalog module for quickstart deployment of pre-built agents.
Provides a registry of agent templates with system prompts, model configs,
tool assignments, and MCP server installation support.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Protocol

from archestra.agents.base import AgentConfig
from archestra.mcp.server import MCPServerSpec
from archestra.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class TemplateInstaller(Protocol):
    """Protocol for installing MCP servers from a template."""

    async def install_mcp_server(self, spec: MCPServerSpec) -> bool:
        ...


@dataclass
class AgentTemplate:
    """Represents a pre-built agent template for quickstart deployment."""

    id: str
    name: str
    description: str
    system_prompt: str
    model: str
    tools: List[str] = field(default_factory=list)
    mcp_servers: List[MCPServerSpec] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize template to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentTemplate":
        """Deserialize template from dictionary."""
        mcp_servers = [MCPServerSpec(**s) if isinstance(s, dict) else s for s in data.pop("mcp_servers", [])]
        return cls(mcp_servers=mcp_servers, **data)


class TemplateCatalog:
    """Registry of agent templates with installation support."""

    def __init__(self, installer: Optional[TemplateInstaller] = None):
        self._templates: Dict[str, AgentTemplate] = {}
        self._installer = installer

    def register(self, template: AgentTemplate) -> None:
        """Register a new agent template."""
        if template.id in self._templates:
            logger.warning("Overwriting existing template: %s", template.id)
        self._templates[template.id] = template
        logger.info("Registered template: %s (%s)", template.name, template.id)

    def get(self, template_id: str) -> Optional[AgentTemplate]:
        """Retrieve a template by ID."""
        return self._templates.get(template_id)

    def list_templates(self) -> List[AgentTemplate]:
        """Return all registered templates."""
        return list(self._templates.values())

    def remove(self, template_id: str) -> bool:
        """Remove a template by ID. Returns True if removed."""
        return self._templates.pop(template_id, None) is not None

    async def install_template(
        self,
        template_id: str,
        tool_registry: ToolRegistry,
        installer: Optional[TemplateInstaller] = None,
    ) -> Optional[AgentConfig]:
        """
        Install a template: register tools, install MCP servers, and return an AgentConfig.
        Returns None if template not found or installation fails.
        """
        template = self.get(template_id)
        if template is None:
            logger.error("Template not found: %s", template_id)
            return None

        effective_installer = installer or self._installer
        if effective_installer is None:
            logger.error("No installer provided for MCP servers")
            return None

        # Install MCP servers
        for mcp_spec in template.mcp_servers:
            success = await effective_installer.install_mcp_server(mcp_spec)
            if not success:
                logger.error("Failed to install MCP server: %s", mcp_spec.name)
                return None

        # Register tools
        for tool_name in template.tools:
            if tool_name not in tool_registry.list_tools():
                logger.warning("Tool '%s' not found in registry, skipping", tool_name)

        # Build agent config
        config = AgentConfig(
            system_prompt=template.system_prompt,
            model=template.model,
            tools=template.tools,
            metadata=template.metadata,
        )
        logger.info("Installed template '%s' as agent config", template_id)
        return config


# Pre-built templates for quickstart
def get_default_catalog() -> TemplateCatalog:
    """Return a catalog with default quickstart templates."""
    catalog = TemplateCatalog()

    catalog.register(
        AgentTemplate(
            id="research-assistant",
            name="Research Assistant",
            description="A helpful research agent with web search and summarization tools.",
            system_prompt="You are a research assistant. Help users find and summarize information.",
            model="gpt-4",
            tools=["web_search", "summarizer"],
            mcp_servers=[
                MCPServerSpec(name="web-search", command="python", args=["-m", "archestra.mcp.servers.web_search"]),
            ],
        )
    )

    catalog.register(
        AgentTemplate(
            id="code-helper",
            name="Code Helper",
            description="An agent that assists with code generation and debugging.",
            system_prompt="You are a coding assistant. Help users write, debug, and understand code.",
            model="gpt-4",
            tools=["code_interpreter", "file_reader"],
            mcp_servers=[
                MCPServerSpec(name="code-exec", command="python", args=["-m", "archestra.mcp.servers.code_exec"]),
            ],
        )
    )

    catalog.register(
        AgentTemplate(
            id="customer-support",
            name="Customer Support Agent",
            description="Handles common customer inquiries with a friendly tone.",
            system_prompt="You are a customer support agent. Be polite, helpful, and concise.",
            model="gpt-3.5-turbo",
            tools=["ticket_system", "knowledge_base"],
            mcp_servers=[
                MCPServerSpec(name="ticket-api", command="python", args=["-m", "archestra.mcp.servers.ticket_api"]),
            ],
        )
    )

    return catalog
