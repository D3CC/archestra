# archestra/agent_templates/catalog.py
"""
Agent template catalog for quickstart agent deployment.
Provides pre-built templates with system prompts, model configs, tool assignments,
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
from archestra.tools.registry import ToolAssignment

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
    tools: List[ToolAssignment] = field(default_factory=list)
    mcp_servers: List[MCPServerConfig] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_agent_config(self) -> AgentConfig:
        """Convert template to an AgentConfig for instantiation."""
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
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            system_prompt=data["system_prompt"],
            model=data["model"],
            tools=[ToolAssignment(**t) for t in data.get("tools", [])],
            mcp_servers=[MCPServerConfig(**s) for s in data.get("mcp_servers", [])],
            metadata=data.get("metadata", {}),
        )


# ---------------------------------------------------------------------------
# Catalog loader
# ---------------------------------------------------------------------------

class TemplateCatalog:
    """Manages loading and querying agent templates from YAML/JSON files."""

    def __init__(self, catalog_path: Optional[Path] = None):
        self._templates: Dict[str, AgentTemplate] = {}
        if catalog_path:
            self.load(catalog_path)

    def load(self, path: Path) -> None:
        """Load templates from a YAML or JSON file."""
        if not path.exists():
            raise FileNotFoundError(f"Catalog file not found: {path}")

        with open(path, "r") as f:
            if path.suffix in (".yaml", ".yml"):
                data = yaml.safe_load(f)
            elif path.suffix == ".json":
                data = json.load(f)
            else:
                raise ValueError(f"Unsupported file format: {path.suffix}")

        for item in data.get("templates", []):
            template = AgentTemplate.from_dict(item)
            self._templates[template.name] = template
        logger.info("Loaded %d templates from %s", len(self._templates), path)

    def get(self, name: str) -> Optional[AgentTemplate]:
        return self._templates.get(name)

    def list_templates(self) -> List[AgentTemplate]:
        return list(self._templates.values())

    def install_template(self, name: str) -> AgentConfig:
        """Retrieve a template and convert to AgentConfig for deployment."""
        template = self.get(name)
        if not template:
            raise KeyError(f"Template '{name}' not found in catalog.")
        return template.to_agent_config()


# ---------------------------------------------------------------------------
# Built-in quickstart templates
# ---------------------------------------------------------------------------

def get_default_catalog() -> TemplateCatalog:
    """Return a catalog with built-in quickstart templates."""
    templates = [
        AgentTemplate(
            name="research-assistant",
            description="A research assistant that can search the web and summarize findings.",
            system_prompt="You are a helpful research assistant. Use web search and summarization tools to answer questions.",
            model="gpt-4o",
            tools=[
                ToolAssignment(name="web_search", config={"engine": "duckduckgo"}),
                ToolAssignment(name="summarize", config={"max_length": 500}),
            ],
            mcp_servers=[
                MCPServerConfig(
                    name="search-mcp",
                    command="uvx",
                    args=["mcp-search"],
                    env={"SEARCH_API_KEY": "default"},
                ),
            ],
            metadata={"category": "productivity", "version": "1.0.0"},
        ),
        AgentTemplate(
            name="code-reviewer",
            description="An agent that reviews code and suggests improvements.",
            system_prompt="You are an expert code reviewer. Analyze code for bugs, style issues, and security vulnerabilities.",
            model="claude-3-opus",
            tools=[
                ToolAssignment(name="static_analysis", config={"linters": ["pylint"]}),
                ToolAssignment(name="git_diff", config={}),
            ],
            mcp_servers=[
                MCPServerConfig(
                    name="code-analysis-mcp",
                    command="npx",
                    args=["@archestra/mcp-code-analysis"],
                ),
            ],
            metadata={"category": "developer", "version": "1.0.0"},
        ),
        AgentTemplate(
            name="customer-support",
            description="Handles common customer inquiries with knowledge base lookup.",
            system_prompt="You are a friendly customer support agent. Use the knowledge base to answer questions and escalate if needed.",
            model="gpt-4o-mini",
            tools=[
                ToolAssignment(name="kb_search", config={"index": "default"}),
                ToolAssignment(name="ticket_create", config={"priority": "normal"}),
            ],
            mcp_servers=[
                MCPServerConfig(
                    name="kb-mcp",
                    command="python",
                    args=["-m", "mcp_kb_server"],
                ),
            ],
            metadata={"category": "business", "version": "1.0.0"},
        ),
    ]

    catalog = TemplateCatalog()
    for t in templates:
        catalog._templates[t.name] = t
    return catalog


# ---------------------------------------------------------------------------
# Convenience function for one-click deployment
# ---------------------------------------------------------------------------

def quickstart_agent(template_name: str, catalog: Optional[TemplateCatalog] = None) -> AgentConfig:
    """Spin up a fully-configured agent from a template in one call."""
    if catalog is None:
        catalog = get_default_catalog()
    return catalog.install_template(template_name)
