# archestra/agent_templates/catalog.py
"""
Agent template catalog for quickstart agent deployment.

Provides a registry of pre-built agent templates with system prompts,
model configurations, tool assignments, and MCP server definitions.
Users can instantiate a fully-configured agent in a single call.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from archestra.agents.base import BaseAgent
from archestra.config import ModelConfig
from archestra.mcp.server import MCPServerDefinition
from archestra.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class AgentTemplate:
    """Template for pre-configured agent creation."""
    name: str
    description: str
    system_prompt: str
    model_config: ModelConfig
    tool_assignments: List[str] = field(default_factory=list)
    mcp_servers: List[MCPServerDefinition] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentTemplate":
        model_cfg = ModelConfig(**data.pop("model_config"))
        mcp_list = [MCPServerDefinition(**s) for s in data.pop("mcp_servers", [])]
        return cls(model_config=model_cfg, mcp_servers=mcp_list, **data)


# ---------------------------------------------------------------------------
# Catalog loader
# ---------------------------------------------------------------------------

class AgentTemplateCatalog:
    """
    Registry of agent templates loaded from YAML/JSON definitions.
    Supports discovery, retrieval, and instantiation of templates.
    """

    def __init__(self, templates: Optional[Dict[str, AgentTemplate]] = None):
        self._templates: Dict[str, AgentTemplate] = templates or {}

    # ---- Loading ----

    @classmethod
    def from_directory(cls, path: Path) -> "AgentTemplateCatalog":
        """Load all template definitions from a directory (recursive)."""
        catalog = cls()
        if not path.is_dir():
            raise ValueError(f"Catalog path is not a directory: {path}")
        for file_path in path.rglob("*"):
            if file_path.suffix in (".yaml", ".yml", ".json"):
                try:
                    template = cls._load_single(file_path)
                    catalog.register(template)
                except Exception as exc:
                    logger.warning("Failed to load template from %s: %s", file_path, exc)
        return catalog

    @classmethod
    def from_list(cls, templates: List[AgentTemplate]) -> "AgentTemplateCatalog":
        catalog = cls()
        for t in templates:
            catalog.register(t)
        return catalog

    @staticmethod
    def _load_single(file_path: Path) -> AgentTemplate:
        with open(file_path, "r", encoding="utf-8") as f:
            if file_path.suffix == ".json":
                data = json.load(f)
            else:
                data = yaml.safe_load(f)
        if not isinstance(data, dict):
            raise ValueError(f"Invalid template format in {file_path}")
        return AgentTemplate.from_dict(data)

    # ---- Registration ----

    def register(self, template: AgentTemplate) -> None:
        if template.name in self._templates:
            logger.info("Overwriting existing template: %s", template.name)
        self._templates[template.name] = template

    def unregister(self, name: str) -> None:
        self._templates.pop(name, None)

    # ---- Query ----

    def list_templates(self) -> List[str]:
        return list(self._templates.keys())

    def get(self, name: str) -> Optional[AgentTemplate]:
        return self._templates.get(name)

    def __contains__(self, name: str) -> bool:
        return name in self._templates

    def __len__(self) -> int:
        return len(self._templates)

    # ---- Instantiation ----

    def instantiate(
        self,
        name: str,
        tool_registry: Optional[ToolRegistry] = None,
        **agent_kwargs: Any,
    ) -> BaseAgent:
        """
        Create a fully-configured agent from a template.

        Args:
            name: Template name.
            tool_registry: Optional tool registry to resolve tool assignments.
            **agent_kwargs: Additional overrides for the agent constructor.

        Returns:
            BaseAgent instance with system prompt, model, tools, and MCP servers.
        """
        template = self.get(name)
        if template is None:
            raise KeyError(f"Template '{name}' not found in catalog.")

        # Resolve tools if registry provided
        tools = []
        if tool_registry:
            for tool_name in template.tool_assignments:
                tool = tool_registry.get(tool_name)
                if tool is None:
                    logger.warning("Tool '%s' not found in registry, skipping.", tool_name)
                else:
                    tools.append(tool)

        # Build agent
        agent = BaseAgent(
            system_prompt=template.system_prompt,
            model_config=template.model_config,
            tools=tools,
            mcp_servers=template.mcp_servers,
            **agent_kwargs,
        )
        return agent


# ---------------------------------------------------------------------------
# Built-in quickstart templates
# ---------------------------------------------------------------------------

def get_default_catalog() -> AgentTemplateCatalog:
    """Return a catalog with a set of built-in quickstart templates."""
    templates = [
        AgentTemplate(
            name="research-assistant",
            description="General-purpose research assistant with web search and summarization.",
            system_prompt=(
                "You are a research assistant. Help users find information, "
                "summarize documents, and answer questions using available tools."
            ),
            model_config=ModelConfig(model="gpt-4o", temperature=0.3),
            tool_assignments=["web_search", "web_scrape", "summarize"],
            mcp_servers=[
                MCPServerDefinition(
                    name="search-mcp",
                    command="python",
                    args=["-m", "archestra.mcp.servers.search"],
                )
            ],
            metadata={"category": "productivity", "version": "1.0"},
        ),
        AgentTemplate(
            name="code-reviewer",
            description="Code review agent that analyzes pull requests and suggests improvements.",
            system_prompt=(
                "You are a senior code reviewer. Analyze code changes, identify bugs, "
                "suggest improvements, and ensure best practices are followed."
            ),
            model_config=ModelConfig(model="gpt-4o", temperature=0.2),
            tool_assignments=["git_diff", "static_analysis", "lint"],
            mcp_servers=[
                MCPServerDefinition(
                    name="github-mcp",
                    command="npx",
                    args=["@modelcontextprotocol/server-github"],
                )
            ],
            metadata={"category": "development", "version": "1.0"},
        ),
        AgentTemplate(
            name="customer-support",
            description="Customer support agent with ticketing and knowledge base access.",
            system_prompt=(
                "You are a customer support agent. Help users with their inquiries, "
                "create tickets, and search the knowledge base for solutions."
            ),
            model_config=ModelConfig(model="gpt-4o-mini", temperature=0.5),
            tool_assignments=["ticket_create", "kb_search", "send_email"],
            mcp_servers=[],
            metadata={"category": "support", "version": "1.0"},
        ),
    ]
    return AgentTemplateCatalog.from_list(templates)


# ---------------------------------------------------------------------------
# Convenience function for single-click agent creation
# ---------------------------------------------------------------------------

def quickstart_agent(
    template_name: str,
    catalog: Optional[AgentTemplateCatalog] = None,
    tool_registry: Optional[ToolRegistry] = None,
    **kwargs: Any,
) -> BaseAgent:
    """
    Spin up a fully-configured agent from a template in one call.

    Args:
        template_name: Name of the template to use.
        catalog: Optional catalog; uses default if not provided.
        tool_registry: Optional tool registry.
        **kwargs: Additional overrides for the agent.

    Returns:
        Configured agent instance.
    """
    if catalog is None:
        catalog = get_default_catalog()
    return catalog.instantiate(template_name, tool_registry=tool_registry, **kwargs)
