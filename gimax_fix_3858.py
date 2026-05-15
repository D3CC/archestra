# archestra/agents/template_catalog.py

"""
Agent Template Catalog - Quickstart pre-built agent templates.
Allows users to spin up a fully-configured agent (system prompt, model, tool assignments)
and install the agent's MCP servers in a single click.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Any

from archestra.agents.base import AgentConfig, Agent
from archestra.tools.registry import ToolRegistry
from archestra.mcp.server import MCPServerConfig, install_mcp_server
from archestra.exceptions import TemplateNotFoundError, TemplateValidationError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class AgentTemplate:
    """Represents a pre-built agent template."""
    id: str
    name: str
    description: str
    system_prompt: str
    model: str
    tools: List[str] = field(default_factory=list)  # tool names
    mcp_servers: List[MCPServerConfig] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentTemplate":
        mcp_servers = [MCPServerConfig(**s) if isinstance(s, dict) else s for s in data.get("mcp_servers", [])]
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


# ---------------------------------------------------------------------------
# Catalog loader
# ---------------------------------------------------------------------------

class TemplateCatalog:
    """
    Manages a collection of agent templates.
    Templates can be loaded from a directory of JSON files or registered programmatically.
    """

    def __init__(self, templates_dir: Optional[Path] = None):
        self._templates: Dict[str, AgentTemplate] = {}
        if templates_dir:
            self.load_from_directory(templates_dir)

    # ---- Registration ----

    def register(self, template: AgentTemplate) -> None:
        """Register a single template."""
        if not template.id:
            raise TemplateValidationError("Template must have an 'id'.")
        self._templates[template.id] = template
        logger.info("Registered template '%s'", template.id)

    def register_many(self, templates: List[AgentTemplate]) -> None:
        for t in templates:
            self.register(t)

    def unregister(self, template_id: str) -> None:
        self._templates.pop(template_id, None)

    # ---- Loading ----

    def load_from_directory(self, directory: Path) -> None:
        """Load all .json template files from a directory."""
        if not directory.is_dir():
            raise TemplateValidationError(f"Not a directory: {directory}")
        for filepath in sorted(directory.glob("*.json")):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                template = AgentTemplate.from_dict(data)
                self.register(template)
            except (json.JSONDecodeError, KeyError, TypeError) as exc:
                logger.warning("Skipping %s: %s", filepath, exc)

    # ---- Query ----

    def list_templates(self) -> List[AgentTemplate]:
        return list(self._templates.values())

    def get(self, template_id: str) -> AgentTemplate:
        template = self._templates.get(template_id)
        if not template:
            raise TemplateNotFoundError(f"Template '{template_id}' not found.")
        return template

    def search(self, query: str) -> List[AgentTemplate]:
        """Simple case-insensitive search over name and description."""
        q = query.lower()
        return [
            t for t in self._templates.values()
            if q in t.name.lower() or q in t.description.lower()
        ]

    # ---- Instantiation ----

    def instantiate_agent(
        self,
        template_id: str,
        tool_registry: Optional[ToolRegistry] = None,
        overrides: Optional[Dict[str, Any]] = None,
    ) -> Agent:
        """
        Create an Agent from a template. Optionally override fields.
        Also installs MCP servers if any.
        """
        template = self.get(template_id)
        config_data = template.to_dict()
        if overrides:
            config_data.update(overrides)

        # Build AgentConfig
        agent_config = AgentConfig(
            system_prompt=config_data.get("system_prompt", template.system_prompt),
            model=config_data.get("model", template.model),
            tools=config_data.get("tools", template.tools),
        )

        # Resolve tool references if registry provided
        if tool_registry:
            resolved_tools = []
            for tool_name in agent_config.tools:
                tool = tool_registry.get(tool_name)
                if tool:
                    resolved_tools.append(tool)
                else:
                    logger.warning("Tool '%s' not found in registry, skipping.", tool_name)
            agent_config.tools = resolved_tools

        agent = Agent(config=agent_config)

        # Install MCP servers
        mcp_servers_data = config_data.get("mcp_servers", template.mcp_servers)
        for mcp_cfg in mcp_servers_data:
            if isinstance(mcp_cfg, dict):
                mcp_cfg = MCPServerConfig(**mcp_cfg)
            try:
                install_mcp_server(mcp_cfg)
                logger.info("Installed MCP server '%s'", mcp_cfg.name)
            except Exception as exc:
                logger.error("Failed to install MCP server '%s': %s", mcp_cfg.name, exc)

        return agent


# ---------------------------------------------------------------------------
# Built-in quickstart templates
# ---------------------------------------------------------------------------

BUILTIN_TEMPLATES = [
    AgentTemplate(
        id="assistant",
        name="General Assistant",
        description="A helpful general-purpose assistant with web search and file tools.",
        system_prompt="You are a helpful assistant. Answer concisely and accurately.",
        model="gpt-4o",
        tools=["web_search", "file_read", "file_write"],
        mcp_servers=[
            MCPServerConfig(name="web-search", command="npx", args=["@mcp/web-search"]),
        ],
    ),
    AgentTemplate(
        id="coder",
        name="Code Assistant",
        description="An AI pair programmer with code execution and git tools.",
        system_prompt="You are an expert software engineer. Help the user write, review, and debug code.",
        model="claude-3-opus",
        tools=["execute_python", "git_commit", "git_diff", "file_read", "file_write"],
        mcp_servers=[
            MCPServerConfig(name="code-exec", command="docker", args=["run", "--rm", "code-executor"]),
        ],
    ),
    AgentTemplate(
        id="researcher",
        name="Research Assistant",
        description="Deep research agent with web scraping, summarization, and citation tools.",
        system_prompt="You are a research assistant. Gather information, summarize findings, and cite sources.",
        model="gpt-4o",
        tools=["web_search", "web_scrape", "summarize", "citation_manager"],
        mcp_servers=[
            MCPServerConfig(name="web-scraper", command="npx", args=["@mcp/web-scraper"]),
        ],
    ),
]


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------

def get_default_catalog() -> TemplateCatalog:
    """Return a catalog pre-loaded with built-in templates."""
    catalog = TemplateCatalog()
    catalog.register_many(BUILTIN_TEMPLATES)
    return catalog
