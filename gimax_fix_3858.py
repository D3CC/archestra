# archestra/agents/catalog.py
"""
Agent template catalog for quickstart agent deployment.
Provides pre-built agent templates with system prompts, model configs,
tool assignments, and MCP server installation in a single click.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from archestra.agents.base import AgentConfig, Agent
from archestra.mcp.server import MCPServerConfig, install_mcp_server
from archestra.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data models
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

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentTemplate":
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            system_prompt=data["system_prompt"],
            model=data["model"],
            tools=data.get("tools", []),
            mcp_servers=[MCPServerConfig(**s) for s in data.get("mcp_servers", [])],
            metadata=data.get("metadata", {}),
        )


# ---------------------------------------------------------------------------
# Catalog loader
# ---------------------------------------------------------------------------

class AgentTemplateCatalog:
    """
    Manages a collection of agent templates loaded from YAML/JSON files.
    Supports discovery, retrieval, and one-click deployment.
    """

    def __init__(self, catalog_path: Optional[Path] = None):
        self._templates: Dict[str, AgentTemplate] = {}
        if catalog_path:
            self.load_from_path(catalog_path)

    def load_from_path(self, path: Path) -> None:
        """Load all template definitions from a directory or single file."""
        if path.is_dir():
            for file_path in sorted(path.iterdir()):
                if file_path.suffix in (".yaml", ".yml", ".json"):
                    self._load_file(file_path)
        elif path.is_file():
            self._load_file(path)
        else:
            raise FileNotFoundError(f"Catalog path does not exist: {path}")

    def _load_file(self, file_path: Path) -> None:
        try:
            with open(file_path, "r") as f:
                if file_path.suffix == ".json":
                    data = json.load(f)
                else:
                    data = yaml.safe_load(f)

            if isinstance(data, list):
                for item in data:
                    template = AgentTemplate.from_dict(item)
                    self._templates[template.name] = template
            elif isinstance(data, dict):
                template = AgentTemplate.from_dict(data)
                self._templates[template.name] = template
            else:
                logger.warning("Unexpected format in %s, skipping", file_path)
        except Exception as exc:
            logger.error("Failed to load template from %s: %s", file_path, exc)

    def list_templates(self) -> List[AgentTemplate]:
        """Return all available templates."""
        return list(self._templates.values())

    def get_template(self, name: str) -> Optional[AgentTemplate]:
        """Retrieve a template by name."""
        return self._templates.get(name)

    def deploy_template(
        self,
        template_name: str,
        tool_registry: Optional[ToolRegistry] = None,
        install_mcp: bool = True,
    ) -> Agent:
        """
        Deploy an agent from a template in one click.
        Installs MCP servers and assigns tools.
        """
        template = self.get_template(template_name)
        if not template:
            raise ValueError(f"Template '{template_name}' not found in catalog.")

        # 1. Install MCP servers if requested
        if install_mcp:
            for mcp_config in template.mcp_servers:
                logger.info("Installing MCP server: %s", mcp_config.name)
                install_mcp_server(mcp_config)

        # 2. Build agent configuration
        agent_config = AgentConfig(
            system_prompt=template.system_prompt,
            model=template.model,
            tools=template.tools,
        )

        # 3. Create agent instance
        agent = Agent(config=agent_config)

        # 4. Register tools if a registry is provided
        if tool_registry:
            for tool_name in template.tools:
                tool = tool_registry.get_tool(tool_name)
                if tool:
                    agent.register_tool(tool)
                else:
                    logger.warning("Tool '%s' not found in registry, skipping.", tool_name)

        return agent


# ---------------------------------------------------------------------------
# Built-in quickstart templates
# ---------------------------------------------------------------------------

BUILTIN_TEMPLATES = [
    AgentTemplate(
        name="research-assistant",
        description="A research assistant that can search the web and summarize findings.",
        system_prompt="You are a helpful research assistant. Use web search and summarization tools to answer questions.",
        model="gpt-4o",
        tools=["web_search", "summarize"],
        mcp_servers=[
            MCPServerConfig(name="web-search", command="python", args=["-m", "mcp_web_search"]),
        ],
    ),
    AgentTemplate(
        name="code-reviewer",
        description="Reviews code changes and suggests improvements.",
        system_prompt="You are an expert code reviewer. Analyze code diffs and provide constructive feedback.",
        model="gpt-4o",
        tools=["code_analysis", "lint"],
        mcp_servers=[
            MCPServerConfig(name="code-analyzer", command="python", args=["-m", "mcp_code_analyzer"]),
        ],
    ),
    AgentTemplate(
        name="customer-support",
        description="Handles customer inquiries with empathy and accuracy.",
        system_prompt="You are a friendly customer support agent. Resolve issues and escalate when necessary.",
        model="gpt-4o-mini",
        tools=["ticket_lookup", "knowledge_base"],
        mcp_servers=[],
    ),
]


def load_builtin_catalog() -> AgentTemplateCatalog:
    """Create a catalog with built-in quickstart templates."""
    catalog = AgentTemplateCatalog()
    for template in BUILTIN_TEMPLATES:
        catalog._templates[template.name] = template
    return catalog
