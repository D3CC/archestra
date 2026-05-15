# archestra/agent_templates/catalog.py
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
    id: str
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
        tools = [ToolAssignment(**t) if isinstance(t, dict) else t for t in data.get("tools", [])]
        mcp_servers = [MCPServerConfig(**s) if isinstance(s, dict) else s for s in data.get("mcp_servers", [])]
        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            system_prompt=data["system_prompt"],
            model=data["model"],
            tools=tools,
            mcp_servers=mcp_servers,
            metadata=data.get("metadata", {}),
        )


# ---------------------------------------------------------------------------
# Catalog loader
# ---------------------------------------------------------------------------

class AgentTemplateCatalog:
    """Manages a collection of agent templates loaded from files or registry."""

    def __init__(self, templates: Optional[Dict[str, AgentTemplate]] = None):
        self._templates: Dict[str, AgentTemplate] = templates or {}

    @classmethod
    def from_directory(cls, path: Path) -> "AgentTemplateCatalog":
        """Load all YAML/JSON template files from a directory."""
        catalog = cls()
        if not path.exists():
            logger.warning("Template directory %s does not exist.", path)
            return catalog
        for file_path in path.iterdir():
            if file_path.suffix in (".yaml", ".yml", ".json"):
                try:
                    template = cls._load_template_file(file_path)
                    catalog.add(template)
                except Exception as exc:
                    logger.error("Failed to load template from %s: %s", file_path, exc)
        return catalog

    @staticmethod
    def _load_template_file(file_path: Path) -> AgentTemplate:
        with open(file_path, "r", encoding="utf-8") as f:
            if file_path.suffix == ".json":
                data = json.load(f)
            else:
                data = yaml.safe_load(f)
        return AgentTemplate.from_dict(data)

    def add(self, template: AgentTemplate) -> None:
        """Register a template in the catalog."""
        if template.id in self._templates:
            logger.warning("Overwriting existing template with id '%s'", template.id)
        self._templates[template.id] = template

    def get(self, template_id: str) -> Optional[AgentTemplate]:
        """Retrieve a template by its id."""
        return self._templates.get(template_id)

    def list_templates(self) -> List[AgentTemplate]:
        """Return all registered templates."""
        return list(self._templates.values())

    def remove(self, template_id: str) -> bool:
        """Remove a template by id. Returns True if removed."""
        return self._templates.pop(template_id, None) is not None

    def deploy(self, template_id: str) -> AgentConfig:
        """One-click deploy: return an AgentConfig ready for agent creation."""
        template = self.get(template_id)
        if template is None:
            raise ValueError(f"Template '{template_id}' not found in catalog.")
        logger.info("Deploying agent from template '%s' (%s)", template_id, template.name)
        return template.to_agent_config()

    def to_dict(self) -> Dict[str, Any]:
        return {tid: tmpl.to_dict() for tid, tmpl in self._templates.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentTemplateCatalog":
        templates = {tid: AgentTemplate.from_dict(tdata) for tid, tdata in data.items()}
        return cls(templates=templates)


# ---------------------------------------------------------------------------
# Built-in quickstart templates
# ---------------------------------------------------------------------------

def load_builtin_catalog() -> AgentTemplateCatalog:
    """Return a catalog with a set of common quickstart templates."""
    catalog = AgentTemplateCatalog()

    # Template: Customer Support Agent
    catalog.add(AgentTemplate(
        id="customer-support",
        name="Customer Support Agent",
        description="Handles common customer inquiries with empathy and accuracy.",
        system_prompt=(
            "You are a helpful customer support agent. Answer questions politely, "
            "provide accurate information, and escalate if needed."
        ),
        model="gpt-4",
        tools=[
            ToolAssignment(name="search_knowledge_base", parameters={}),
            ToolAssignment(name="create_ticket", parameters={"priority": "medium"}),
        ],
        mcp_servers=[
            MCPServerConfig(url="http://localhost:8000/mcp/kb", name="knowledge-base"),
        ],
        metadata={"category": "support", "version": "1.0.0"},
    ))

    # Template: Code Review Assistant
    catalog.add(AgentTemplate(
        id="code-reviewer",
        name="Code Review Assistant",
        description="Reviews code diffs for style, bugs, and security issues.",
        system_prompt=(
            "You are an expert code reviewer. Analyze the provided diff, "
            "point out potential bugs, style violations, and security concerns."
        ),
        model="gpt-4-turbo",
        tools=[
            ToolAssignment(name="run_linter", parameters={"linter": "flake8"}),
            ToolAssignment(name="fetch_repository", parameters={}),
        ],
        mcp_servers=[
            MCPServerConfig(url="http://localhost:8001/mcp/lint", name="linter"),
        ],
        metadata={"category": "development", "version": "1.0.0"},
    ))

    # Template: Data Analyst
    catalog.add(AgentTemplate(
        id="data-analyst",
        name="Data Analyst Agent",
        description="Analyzes datasets and generates summaries and visualizations.",
        system_prompt=(
            "You are a data analyst. Given a dataset, provide insights, "
            "summary statistics, and suggest visualizations."
        ),
        model="gpt-4",
        tools=[
            ToolAssignment(name="query_database", parameters={}),
            ToolAssignment(name="generate_chart", parameters={"type": "bar"}),
        ],
        mcp_servers=[
            MCPServerConfig(url="http://localhost:8002/mcp/data", name="data-query"),
        ],
        metadata={"category": "analytics", "version": "1.0.0"},
    ))

    return catalog


# ---------------------------------------------------------------------------
# Convenience function for one-click deploy
# ---------------------------------------------------------------------------

def quickstart_deploy(template_id: str, catalog: Optional[AgentTemplateCatalog] = None) -> AgentConfig:
    """
    Deploy an agent from a template in a single call.
    Uses built-in catalog if none provided.
    """
    if catalog is None:
        catalog = load_builtin_catalog()
    return catalog.deploy(template_id)
