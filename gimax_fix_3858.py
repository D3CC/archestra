# archestra/agents/template_catalog.py
"""
Agent template catalog for quickstart agent deployment.
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
    """
    Manages a collection of AgentTemplate objects.
    Supports loading from JSON/YAML files and programmatic registration.
    """

    def __init__(self, templates: Optional[Dict[str, AgentTemplate]] = None):
        self._templates: Dict[str, AgentTemplate] = templates or {}

    # ---- registration ----

    def register(self, template: AgentTemplate) -> None:
        if template.name in self._templates:
            logger.warning("Overwriting existing template '%s'", template.name)
        self._templates[template.name] = template

    def unregister(self, name: str) -> None:
        self._templates.pop(name, None)

    # ---- lookup ----

    def get(self, name: str) -> Optional[AgentTemplate]:
        return self._templates.get(name)

    def list_templates(self) -> List[str]:
        return list(self._templates.keys())

    def search(self, query: str) -> List[AgentTemplate]:
        """Simple substring search on name and description."""
        q = query.lower()
        return [
            t for t in self._templates.values()
            if q in t.name.lower() or q in t.description.lower()
        ]

    # ---- persistence ----

    def save(self, path: Path, fmt: str = "json") -> None:
        """Save catalog to a file (json or yaml)."""
        data = {name: tmpl.to_dict() for name, tmpl in self._templates.items()}
        path.parent.mkdir(parents=True, exist_ok=True)
        if fmt == "json":
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
        elif fmt == "yaml":
            with open(path, "w") as f:
                yaml.dump(data, f, default_flow_style=False)
        else:
            raise ValueError(f"Unsupported format: {fmt}")

    @classmethod
    def load(cls, path: Path, fmt: str = "json") -> "TemplateCatalog":
        """Load catalog from a file."""
        if fmt == "json":
            with open(path) as f:
                data = json.load(f)
        elif fmt == "yaml":
            with open(path) as f:
                data = yaml.safe_load(f)
        else:
            raise ValueError(f"Unsupported format: {fmt}")
        templates = {
            name: AgentTemplate.from_dict(tmpl) for name, tmpl in data.items()
        }
        return cls(templates)

    # ---- built-in templates ----

    @classmethod
    def with_defaults(cls) -> "TemplateCatalog":
        """Create a catalog pre-populated with common agent templates."""
        catalog = cls()
        catalog.register(
            AgentTemplate(
                name="code-assistant",
                description="AI coding assistant with code execution and file I/O tools.",
                system_prompt="You are a helpful coding assistant. Help the user write, debug, and understand code.",
                model="gpt-4",
                tools=[
                    ToolAssignment(name="execute_python"),
                    ToolAssignment(name="read_file"),
                    ToolAssignment(name="write_file"),
                ],
                mcp_servers=[
                    MCPServerConfig(name="filesystem", command="npx", args=["-y", "@modelcontextprotocol/server-filesystem"]),
                ],
                metadata={"category": "development", "version": "1.0.0"},
            )
        )
        catalog.register(
            AgentTemplate(
                name="data-analyst",
                description="Agent specialized in data analysis and visualization.",
                system_prompt="You are a data analyst. Help users explore, clean, and visualize datasets.",
                model="gpt-4",
                tools=[
                    ToolAssignment(name="execute_python"),
                    ToolAssignment(name="read_file"),
                    ToolAssignment(name="web_search"),
                ],
                mcp_servers=[
                    MCPServerConfig(name="sqlite", command="uvx", args=["mcp-server-sqlite", "--db-path", "/tmp/analysis.db"]),
                ],
                metadata={"category": "data-science", "version": "1.0.0"},
            )
        )
        catalog.register(
            AgentTemplate(
                name="customer-support",
                description="Customer support agent with knowledge base and ticketing tools.",
                system_prompt="You are a friendly customer support agent. Help users with their inquiries and escalate when needed.",
                model="gpt-3.5-turbo",
                tools=[
                    ToolAssignment(name="search_knowledge_base"),
                    ToolAssignment(name="create_ticket"),
                    ToolAssignment(name="send_email"),
                ],
                mcp_servers=[],
                metadata={"category": "business", "version": "1.0.0"},
            )
        )
        return catalog


# ---------------------------------------------------------------------------
# Quickstart helper
# ---------------------------------------------------------------------------

def quickstart_agent(template_name: str, catalog: Optional[TemplateCatalog] = None) -> AgentConfig:
    """
    One-click agent setup: fetch template, install MCP servers, return AgentConfig.
    """
    if catalog is None:
        catalog = TemplateCatalog.with_defaults()
    template = catalog.get(template_name)
    if template is None:
        raise ValueError(f"Template '{template_name}' not found. Available: {catalog.list_templates()}")

    # Install MCP servers (simulated – real implementation would call MCP installer)
    for server in template.mcp_servers:
        logger.info("Installing MCP server '%s' with command: %s %s", server.name, server.command, " ".join(server.args))
        # In production: subprocess.run or use archestra.mcp.installer
        # For now we just log and assume success.

    return template.to_agent_config()
