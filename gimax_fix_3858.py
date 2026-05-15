# archestra/agents/catalog.py
"""
Agent template catalog for quick-start agent deployment.
Provides pre-built agent templates with system prompts, model configs,
tool assignments, and MCP server installation support.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from archestra.agents.base import AgentConfig, AgentTemplate
from archestra.mcp.server import MCPServerConfig, install_mcp_server
from archestra.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class CatalogEntry:
    """A single entry in the agent template catalog."""
    id: str
    name: str
    description: str
    system_prompt: str
    model: str
    tools: List[str] = field(default_factory=list)
    mcp_servers: List[MCPServerConfig] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_agent_config(self) -> AgentConfig:
        """Convert catalog entry to an AgentConfig."""
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
    def from_dict(cls, data: Dict[str, Any]) -> "CatalogEntry":
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            system_prompt=data["system_prompt"],
            model=data["model"],
            tools=data.get("tools", []),
            mcp_servers=[MCPServerConfig(**s) for s in data.get("mcp_servers", [])],
            metadata=data.get("metadata", {}),
        )


class AgentCatalog:
    """
    Catalog of pre-built agent templates.
    Supports loading from YAML/JSON, searching, and one-click deployment.
    """

    def __init__(self, entries: Optional[List[CatalogEntry]] = None):
        self._entries: Dict[str, CatalogEntry] = {}
        if entries:
            for entry in entries:
                self._entries[entry.id] = entry

    # -----------------------------------------------------------------------
    # Loading / persistence
    # -----------------------------------------------------------------------

    @classmethod
    def load_yaml(cls, path: Path) -> "AgentCatalog":
        """Load catalog from a YAML file."""
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        return cls._from_list(data.get("templates", []))

    @classmethod
    def load_json(cls, path: Path) -> "AgentCatalog":
        """Load catalog from a JSON file."""
        with open(path, "r") as f:
            data = json.load(f)
        return cls._from_list(data.get("templates", []))

    @classmethod
    def _from_list(cls, items: List[Dict[str, Any]]) -> "AgentCatalog":
        entries = [CatalogEntry.from_dict(item) for item in items]
        return cls(entries)

    def save_yaml(self, path: Path) -> None:
        """Save catalog to a YAML file."""
        data = {"templates": [e.to_dict() for e in self._entries.values()]}
        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False)

    def save_json(self, path: Path) -> None:
        """Save catalog to a JSON file."""
        data = {"templates": [e.to_dict() for e in self._entries.values()]}
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    # -----------------------------------------------------------------------
    # Query
    # -----------------------------------------------------------------------

    def get(self, template_id: str) -> Optional[CatalogEntry]:
        return self._entries.get(template_id)

    def list_templates(self) -> List[CatalogEntry]:
        return list(self._entries.values())

    def search(self, query: str) -> List[CatalogEntry]:
        """Simple substring search on name and description."""
        q = query.lower()
        return [
            e for e in self._entries.values()
            if q in e.name.lower() or q in e.description.lower()
        ]

    def add(self, entry: CatalogEntry) -> None:
        if entry.id in self._entries:
            logger.warning("Overwriting existing template: %s", entry.id)
        self._entries[entry.id] = entry

    def remove(self, template_id: str) -> bool:
        return self._entries.pop(template_id, None) is not None

    # -----------------------------------------------------------------------
    # Deployment
    # -----------------------------------------------------------------------

    def deploy(self, template_id: str, tool_registry: Optional[ToolRegistry] = None) -> AgentTemplate:
        """
        Deploy an agent from the catalog.
        Installs MCP servers and registers tools in one step.
        Returns an AgentTemplate ready to be instantiated.
        """
        entry = self.get(template_id)
        if entry is None:
            raise ValueError(f"Template '{template_id}' not found in catalog.")

        # Install MCP servers
        for mcp_cfg in entry.mcp_servers:
            logger.info("Installing MCP server: %s", mcp_cfg.name)
            install_mcp_server(mcp_cfg)

        # Register tools if a registry is provided
        if tool_registry:
            for tool_name in entry.tools:
                if tool_name not in tool_registry:
                    logger.warning("Tool '%s' not found in registry, skipping.", tool_name)

        # Build and return the agent template
        agent_config = entry.to_agent_config()
        return AgentTemplate(config=agent_config)

    def __len__(self) -> int:
        return len(self._entries)

    def __iter__(self):
        return iter(self._entries.values())


# ---------------------------------------------------------------------------
# Built-in quickstart catalog
# ---------------------------------------------------------------------------

def get_default_catalog() -> AgentCatalog:
    """Return the default built-in catalog with pre-defined templates."""
    entries = [
        CatalogEntry(
            id="assistant",
            name="General Assistant",
            description="A helpful general-purpose assistant with web search and file tools.",
            system_prompt="You are a helpful assistant. Answer questions concisely and accurately.",
            model="gpt-4o",
            tools=["web_search", "read_file", "write_file"],
            mcp_servers=[
                MCPServerConfig(name="filesystem", command="npx", args=["-y", "@modelcontextprotocol/server-filesystem"]),
            ],
        ),
        CatalogEntry(
            id="coder",
            name="Code Assistant",
            description="An expert coding assistant with code execution and analysis tools.",
            system_prompt="You are an expert software engineer. Help users write, debug, and review code.",
            model="claude-3-opus",
            tools=["execute_python", "read_file", "write_file", "search_code"],
            mcp_servers=[
                MCPServerConfig(name="filesystem", command="npx", args=["-y", "@modelcontextprotocol/server-filesystem"]),
                MCPServerConfig(name="github", command="npx", args=["-y", "@modelcontextprotocol/server-github"]),
            ],
        ),
        CatalogEntry(
            id="researcher",
            name="Research Assistant",
            description="A research-oriented agent with web scraping and data analysis capabilities.",
            system_prompt="You are a research assistant. Gather information, analyze data, and produce summaries.",
            model="gpt-4o",
            tools=["web_search", "web_scrape", "read_file", "write_file", "analyze_data"],
            mcp_servers=[
                MCPServerConfig(name="filesystem", command="npx", args=["-y", "@modelcontextprotocol/server-filesystem"]),
                MCPServerConfig(name="brave-search", command="npx", args=["-y", "@modelcontextprotocol/server-brave-search"]),
            ],
        ),
    ]
    return AgentCatalog(entries)
