# archestra/agents/catalog.py
"""
Agent template catalog for quickstart agent creation.
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

from archestra.agents.base import AgentConfig
from archestra.tools.registry import ToolRegistry
from archestra.mcp.server import MCPServerManager

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data model for a template entry
# ---------------------------------------------------------------------------

@dataclass
class AgentTemplate:
    """Represents a single agent template in the catalog."""
    id: str
    name: str
    description: str
    system_prompt: str
    model: str
    tools: List[str] = field(default_factory=list)
    mcp_servers: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_agent_config(self) -> AgentConfig:
        """Convert template to an AgentConfig for instantiation."""
        return AgentConfig(
            name=self.name,
            system_prompt=self.system_prompt,
            model=self.model,
            tools=self.tools,
            metadata=self.metadata,
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentTemplate":
        return cls(**data)


# ---------------------------------------------------------------------------
# Catalog loader and manager
# ---------------------------------------------------------------------------

class AgentTemplateCatalog:
    """
    Manages a collection of pre-built agent templates.
    Supports loading from YAML/JSON files and programmatic registration.
    """

    def __init__(self, templates: Optional[Dict[str, AgentTemplate]] = None):
        self._templates: Dict[str, AgentTemplate] = templates or {}

    # ---- Registration -------------------------------------------------------

    def register(self, template: AgentTemplate) -> None:
        """Register a single template."""
        if template.id in self._templates:
            logger.warning("Overwriting existing template: %s", template.id)
        self._templates[template.id] = template

    def register_many(self, templates: List[AgentTemplate]) -> None:
        """Register multiple templates."""
        for t in templates:
            self.register(t)

    def unregister(self, template_id: str) -> None:
        """Remove a template by id."""
        self._templates.pop(template_id, None)

    # ---- Query --------------------------------------------------------------

    def get(self, template_id: str) -> Optional[AgentTemplate]:
        """Get a template by id."""
        return self._templates.get(template_id)

    def list(self) -> List[AgentTemplate]:
        """Return all registered templates."""
        return list(self._templates.values())

    def find_by_name(self, name: str) -> Optional[AgentTemplate]:
        """Find a template by name (case-insensitive)."""
        for t in self._templates.values():
            if t.name.lower() == name.lower():
                return t
        return None

    def filter_by_tool(self, tool_name: str) -> List[AgentTemplate]:
        """Return templates that include a specific tool."""
        return [t for t in self._templates.values() if tool_name in t.tools]

    # ---- Persistence --------------------------------------------------------

    def load_from_file(self, path: Path) -> int:
        """
        Load templates from a YAML or JSON file.
        Returns number of templates loaded.
        """
        if not path.exists():
            raise FileNotFoundError(f"Catalog file not found: {path}")

        raw = path.read_text(encoding="utf-8")
        if path.suffix in (".yaml", ".yml"):
            data = yaml.safe_load(raw)
        elif path.suffix == ".json":
            data = json.loads(raw)
        else:
            raise ValueError(f"Unsupported file format: {path.suffix}")

        if not isinstance(data, list):
            raise ValueError("Catalog file must contain a list of templates")

        count = 0
        for item in data:
            template = AgentTemplate.from_dict(item)
            self.register(template)
            count += 1
        return count

    def save_to_file(self, path: Path) -> None:
        """Save all templates to a YAML file."""
        data = [t.to_dict() for t in self._templates.values()]
        path.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")

    # ---- Quickstart creation ------------------------------------------------

    def create_agent_from_template(
        self,
        template_id: str,
        tool_registry: ToolRegistry,
        mcp_manager: Optional[MCPServerManager] = None,
        **overrides: Any,
    ) -> AgentConfig:
        """
        Create an AgentConfig from a template, optionally installing MCP servers.
        Overrides can be passed to modify the config (e.g., model, system_prompt).
        """
        template = self.get(template_id)
        if template is None:
            raise ValueError(f"Template not found: {template_id}")

        config = template.to_agent_config()

        # Apply overrides
        for key, value in overrides.items():
            if hasattr(config, key):
                setattr(config, key, value)
            else:
                logger.warning("Ignoring unknown override: %s", key)

        # Validate tools exist in registry
        for tool_name in config.tools:
            if not tool_registry.has(tool_name):
                raise RuntimeError(f"Tool '{tool_name}' not found in registry")

        # Install MCP servers if manager provided
        if mcp_manager is not None and template.mcp_servers:
            for server_def in template.mcp_servers:
                mcp_manager.install(server_def)
                logger.info("Installed MCP server: %s", server_def.get("name", "unknown"))

        return config


# ---------------------------------------------------------------------------
# Built-in default catalog
# ---------------------------------------------------------------------------

def get_default_catalog() -> AgentTemplateCatalog:
    """Return a catalog with a set of sensible default templates."""
    catalog = AgentTemplateCatalog()

    # Template: General Assistant
    catalog.register(AgentTemplate(
        id="general-assistant",
        name="General Assistant",
        description="A versatile assistant for answering questions and performing common tasks.",
        system_prompt="You are a helpful, harmless, and honest assistant.",
        model="gpt-4o",
        tools=["web_search", "calculator"],
        mcp_servers=[
            {"name": "web-search", "url": "https://mcp.example.com/web-search"},
        ],
        metadata={"category": "general", "difficulty": "beginner"},
    ))

    # Template: Code Reviewer
    catalog.register(AgentTemplate(
        id="code-reviewer",
        name="Code Reviewer",
        description="Expert code reviewer that analyzes code quality and suggests improvements.",
        system_prompt="You are an expert software engineer. Review code for bugs, style issues, and performance problems.",
        model="gpt-4o",
        tools=["code_analysis", "git_integration"],
        mcp_servers=[
            {"name": "code-analysis", "url": "https://mcp.example.com/code-analysis"},
        ],
        metadata={"category": "development", "difficulty": "intermediate"},
    ))

    # Template: Data Analyst
    catalog.register(AgentTemplate(
        id="data-analyst",
        name="Data Analyst",
        description="Analyzes data, creates visualizations, and generates reports.",
        system_prompt="You are a data analyst. Help users understand their data through analysis and visualization.",
        model="gpt-4o",
        tools=["python_executor", "data_visualization", "sql_query"],
        mcp_servers=[
            {"name": "data-viz", "url": "https://mcp.example.com/data-viz"},
            {"name": "sql-engine", "url": "https://mcp.example.com/sql"},
        ],
        metadata={"category": "data", "difficulty": "advanced"},
    ))

    return catalog


# ---------------------------------------------------------------------------
# Convenience function for quickstart
# ---------------------------------------------------------------------------

def quickstart_agent(
    template_id: str,
    tool_registry: ToolRegistry,
    mcp_manager: Optional[MCPServerManager] = None,
    catalog: Optional[AgentTemplateCatalog] = None,
    **overrides: Any,
) -> AgentConfig:
    """
    One-liner to create an agent config from a template.
    Uses default catalog if none provided.
    """
    if catalog is None:
        catalog = get_default_catalog()
    return catalog.create_agent_from_template(template_id, tool_registry, mcp_manager, **overrides)
