# archestra/agents/template_catalog.py

"""
Agent Template Catalog - Quickstart pre-built agent templates.

This module provides a catalog of pre-configured agent templates that users
can deploy with a single click. Each template includes a system prompt,
model configuration, tool assignments, and MCP server installation details.
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
# Data structures
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
        """Convert this template into a fully resolved AgentConfig."""
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
        tools = [ToolAssignment(**t) for t in data.get("tools", [])]
        servers = [MCPServerConfig(**s) for s in data.get("mcp_servers", [])]
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            system_prompt=data["system_prompt"],
            model=data["model"],
            tools=tools,
            mcp_servers=servers,
            metadata=data.get("metadata", {}),
        )


# ---------------------------------------------------------------------------
# Catalog loader
# ---------------------------------------------------------------------------

class TemplateCatalog:
    """Manages a collection of agent templates loaded from a directory or file."""

    def __init__(self, templates: Optional[Dict[str, AgentTemplate]] = None):
        self._templates: Dict[str, AgentTemplate] = templates or {}

    @classmethod
    def from_directory(cls, path: Path) -> "TemplateCatalog":
        """Load all template files (.json, .yaml, .yml) from a directory."""
        catalog = cls()
        if not path.exists():
            logger.warning("Template directory %s does not exist", path)
            return catalog

        for file_path in path.iterdir():
            if file_path.suffix in (".json", ".yaml", ".yml"):
                try:
                    template = cls._load_file(file_path)
                    catalog.add(template)
                except Exception as exc:
                    logger.error("Failed to load template from %s: %s", file_path, exc)
        return catalog

    @staticmethod
    def _load_file(file_path: Path) -> AgentTemplate:
        with open(file_path, "r", encoding="utf-8") as f:
            if file_path.suffix == ".json":
                data = json.load(f)
            else:
                data = yaml.safe_load(f)
        return AgentTemplate.from_dict(data)

    def add(self, template: AgentTemplate) -> None:
        if template.name in self._templates:
            logger.warning("Overwriting existing template: %s", template.name)
        self._templates[template.name] = template

    def get(self, name: str) -> Optional[AgentTemplate]:
        return self._templates.get(name)

    def list_templates(self) -> List[str]:
        return list(self._templates.keys())

    def deploy(self, name: str) -> Optional[AgentConfig]:
        """Resolve a template into a deployable AgentConfig."""
        template = self.get(name)
        if template is None:
            logger.error("Template '%s' not found", name)
            return None
        return template.to_agent_config()

    def to_dict(self) -> Dict[str, Any]:
        return {name: tmpl.to_dict() for name, tmpl in self._templates.items()}


# ---------------------------------------------------------------------------
# Built-in quickstart templates
# ---------------------------------------------------------------------------

def get_default_catalog() -> TemplateCatalog:
    """Return the built-in catalog of quickstart agent templates."""
    catalog = TemplateCatalog()

    # Template 1: Code Reviewer
    catalog.add(AgentTemplate(
        name="code-reviewer",
        description="Reviews pull requests for style, bugs, and security issues.",
        system_prompt=(
            "You are an expert code reviewer. Analyze the provided code diff "
            "and give constructive feedback on style, potential bugs, security "
            "vulnerabilities, and performance improvements."
        ),
        model="gpt-4",
        tools=[
            ToolAssignment(name="fetch_diff", parameters={}),
            ToolAssignment(name="comment_on_pr", parameters={"style": "concise"}),
        ],
        mcp_servers=[
            MCPServerConfig(
                name="github-mcp",
                command="npx",
                args=["-y", "@modelcontextprotocol/server-github"],
                env={"GITHUB_TOKEN": "${GITHUB_TOKEN}"},
            )
        ],
        metadata={"category": "development", "difficulty": "intermediate"},
    ))

    # Template 2: Data Analyst
    catalog.add(AgentTemplate(
        name="data-analyst",
        description="Analyzes CSV/JSON datasets and generates visualizations.",
        system_prompt=(
            "You are a data analyst assistant. Given a dataset, you can compute "
            "summary statistics, detect outliers, and generate plots using Python."
        ),
        model="gpt-4-turbo",
        tools=[
            ToolAssignment(name="run_python", parameters={"timeout": 30}),
            ToolAssignment(name="read_file", parameters={"max_size_mb": 10}),
        ],
        mcp_servers=[
            MCPServerConfig(
                name="filesystem-mcp",
                command="npx",
                args=["-y", "@modelcontextprotocol/server-filesystem"],
                env={},
            )
        ],
        metadata={"category": "data-science", "difficulty": "beginner"},
    ))

    # Template 3: Customer Support
    catalog.add(AgentTemplate(
        name="customer-support",
        description="Handles common customer inquiries and ticket routing.",
        system_prompt=(
            "You are a helpful customer support agent. Answer questions about "
            "our products, escalate issues when needed, and always be polite."
        ),
        model="gpt-3.5-turbo",
        tools=[
            ToolAssignment(name="search_knowledge_base", parameters={}),
            ToolAssignment(name="create_ticket", parameters={"priority": "normal"}),
        ],
        mcp_servers=[
            MCPServerConfig(
                name="zendesk-mcp",
                command="npx",
                args=["-y", "@archestra/server-zendesk"],
                env={"ZENDESK_SUBDOMAIN": "${ZENDESK_SUBDOMAIN}"},
            )
        ],
        metadata={"category": "customer-service", "difficulty": "beginner"},
    ))

    return catalog


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------

def quickstart(name: str, catalog: Optional[TemplateCatalog] = None) -> Optional[AgentConfig]:
    """Deploy a template by name from the default or provided catalog."""
    if catalog is None:
        catalog = get_default_catalog()
    return catalog.deploy(name)
