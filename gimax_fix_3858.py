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

from archestra.agents.base import AgentConfig, AgentTemplate
from archestra.mcp.server import MCPServerConfig
from archestra.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class CatalogEntry:
    """A single entry in the agent template catalog."""
    id: str
    name: str
    description: str
    category: str
    system_prompt: str
    model: str
    tools: List[str] = field(default_factory=list)
    mcp_servers: List[MCPServerConfig] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    version: str = "1.0.0"

    def to_agent_config(self) -> AgentConfig:
        """Convert catalog entry to an AgentConfig for instantiation."""
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
        mcp_servers = [MCPServerConfig(**s) for s in data.pop("mcp_servers", [])]
        return cls(mcp_servers=mcp_servers, **data)


class AgentTemplateCatalog:
    """
    Catalog of pre-built agent templates.
    Supports loading from JSON, searching, and one-click deployment.
    """

    def __init__(self, entries: Optional[List[CatalogEntry]] = None):
        self._entries: Dict[str, CatalogEntry] = {}
        if entries:
            for entry in entries:
                self._entries[entry.id] = entry

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    @classmethod
    def load_from_file(cls, path: Path) -> "AgentTemplateCatalog":
        """Load catalog from a JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        entries = [CatalogEntry.from_dict(item) for item in data]
        logger.info("Loaded %d catalog entries from %s", len(entries), path)
        return cls(entries)

    @classmethod
    def load_builtin(cls) -> "AgentTemplateCatalog":
        """Load the built-in catalog shipped with the package."""
        builtin_path = Path(__file__).parent / "catalog_builtin.json"
        if builtin_path.exists():
            return cls.load_from_file(builtin_path)
        # Fallback: return a minimal default catalog
        return cls(_default_entries())

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get(self, entry_id: str) -> Optional[CatalogEntry]:
        return self._entries.get(entry_id)

    def list_entries(self) -> List[CatalogEntry]:
        return list(self._entries.values())

    def search(self, query: str, category: Optional[str] = None) -> List[CatalogEntry]:
        """Search entries by name, description, or tags."""
        query = query.lower()
        results = []
        for entry in self._entries.values():
            if category and entry.category != category:
                continue
            if (query in entry.name.lower()
                    or query in entry.description.lower()
                    or any(query in tag.lower() for tag in entry.tags)):
                results.append(entry)
        return results

    def by_category(self, category: str) -> List[CatalogEntry]:
        return [e for e in self._entries.values() if e.category == category]

    # ------------------------------------------------------------------
    # Deployment
    # ------------------------------------------------------------------

    def deploy(self, entry_id: str, tool_registry: ToolRegistry) -> AgentTemplate:
        """
        One-click deploy: create an AgentTemplate from a catalog entry,
        install MCP servers, and register tools.
        """
        entry = self.get(entry_id)
        if not entry:
            raise ValueError(f"Catalog entry '{entry_id}' not found.")

        # Install MCP servers (simulated)
        for mcp_cfg in entry.mcp_servers:
            logger.info("Installing MCP server: %s", mcp_cfg.name)
            # In production, this would call mcp_server.install()
            # For now we just log and assume success.

        # Register tools if needed
        for tool_name in entry.tools:
            if not tool_registry.has(tool_name):
                logger.warning("Tool '%s' not registered; skipping.", tool_name)

        # Build and return the agent template
        agent_config = entry.to_agent_config()
        return AgentTemplate(config=agent_config)

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_json(self, path: Optional[Path] = None) -> Optional[str]:
        """Serialize catalog to JSON string or file."""
        data = [entry.to_dict() for entry in self._entries.values()]
        if path:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return None
        return json.dumps(data, indent=2)


# ---------------------------------------------------------------------------
# Built-in default entries
# ---------------------------------------------------------------------------

def _default_entries() -> List[CatalogEntry]:
    """Return a minimal set of built-in templates."""
    return [
        CatalogEntry(
            id="assistant",
            name="General Assistant",
            description="A helpful general-purpose assistant with web search and file tools.",
            category="general",
            system_prompt="You are a helpful assistant. Answer concisely and accurately.",
            model="gpt-4o",
            tools=["web_search", "read_file", "write_file"],
            mcp_servers=[
                MCPServerConfig(name="filesystem", command="npx", args=["-y", "@modelcontextprotocol/server-filesystem"]),
            ],
            tags=["quickstart", "general"],
        ),
        CatalogEntry(
            id="coder",
            name="Code Assistant",
            description="Specialized in code generation, review, and debugging.",
            category="developer",
            system_prompt="You are an expert software engineer. Write clean, well-documented code.",
            model="gpt-4o",
            tools=["execute_python", "read_file", "write_file", "git_operations"],
            mcp_servers=[
                MCPServerConfig(name="filesystem", command="npx", args=["-y", "@modelcontextprotocol/server-filesystem"]),
                MCPServerConfig(name="github", command="npx", args=["-y", "@modelcontextprotocol/server-github"]),
            ],
            tags=["developer", "coding"],
        ),
        CatalogEntry(
            id="researcher",
            name="Research Assistant",
            description="Performs deep research with web search and document analysis.",
            category="research",
            system_prompt="You are a research assistant. Gather and synthesize information from multiple sources.",
            model="gpt-4o",
            tools=["web_search", "read_file", "summarize"],
            mcp_servers=[
                MCPServerConfig(name="filesystem", command="npx", args=["-y", "@modelcontextprotocol/server-filesystem"]),
            ],
            tags=["research", "quickstart"],
        ),
    ]


# ---------------------------------------------------------------------------
# Convenience factory
# ---------------------------------------------------------------------------

def get_catalog() -> AgentTemplateCatalog:
    """Return the default catalog (built-in)."""
    return AgentTemplateCatalog.load_builtin()
