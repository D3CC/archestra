# archestra/agent_templates/catalog.py
"""
Agent template catalog for quickstart agent deployment.
Provides pre-built templates with system prompts, model configs, tool assignments,
and MCP server installation definitions.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from archestra.core.agent import AgentConfig
from archestra.core.tools import ToolAssignment
from archestra.mcp.server import MCPServerDefinition

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
    mcp_servers: List[MCPServerDefinition] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_agent_config(self) -> AgentConfig:
        """Convert template to an AgentConfig for agent instantiation."""
        return AgentConfig(
            system_prompt=self.system_prompt,
            model=self.model,
            tools=self.tools,
            mcp_servers=self.mcp_servers,
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentTemplate":
        tools = [ToolAssignment(**t) for t in data.pop("tools", [])]
        servers = [MCPServerDefinition(**s) for s in data.pop("mcp_servers", [])]
        return cls(tools=tools, mcp_servers=servers, **data)


# ---------------------------------------------------------------------------
# Catalog loader
# ---------------------------------------------------------------------------

class TemplateCatalog:
    """Manages a collection of agent templates loaded from a directory or file."""

    def __init__(self, templates: Optional[Dict[str, AgentTemplate]] = None):
        self._templates: Dict[str, AgentTemplate] = templates or {}

    def register(self, template: AgentTemplate) -> None:
        """Register a single template."""
        if template.name in self._templates:
            logger.warning("Overwriting existing template: %s", template.name)
        self._templates[template.name] = template

    def get(self, name: str) -> Optional[AgentTemplate]:
        """Retrieve a template by name."""
        return self._templates.get(name)

    def list_templates(self) -> List[str]:
        """Return names of all registered templates."""
        return list(self._templates.keys())

    def remove(self, name: str) -> None:
        """Remove a template by name."""
        self._templates.pop(name, None)

    def load_from_directory(self, directory: Path) -> int:
        """Load all .yaml/.yml/.json files from a directory as templates."""
        count = 0
        for filepath in directory.iterdir():
            if filepath.suffix in (".yaml", ".yml", ".json"):
                try:
                    template = self._load_file(filepath)
                    self.register(template)
                    count += 1
                except Exception as exc:
                    logger.error("Failed to load template from %s: %s", filepath, exc)
        return count

    def load_from_file(self, filepath: Path) -> AgentTemplate:
        """Load a single template from a file."""
        template = self._load_file(filepath)
        self.register(template)
        return template

    @staticmethod
    def _load_file(filepath: Path) -> AgentTemplate:
        with open(filepath, "r") as f:
            if filepath.suffix == ".json":
                data = json.load(f)
            else:
                data = yaml.safe_load(f)
        return AgentTemplate.from_dict(data)

    def save_to_file(self, template_name: str, filepath: Path) -> None:
        """Save a template to a file (YAML)."""
        template = self.get(template_name)
        if template is None:
            raise ValueError(f"Template '{template_name}' not found.")
        with open(filepath, "w") as f:
            yaml.dump(template.to_dict(), f, default_flow_style=False)

    def to_dict(self) -> Dict[str, Any]:
        return {name: tmpl.to_dict() for name, tmpl in self._templates.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TemplateCatalog":
        templates = {
            name: AgentTemplate.from_dict(tmpl_data)
            for name, tmpl_data in data.items()
        }
        return cls(templates=templates)


# ---------------------------------------------------------------------------
# Built-in quickstart templates
# ---------------------------------------------------------------------------

def get_default_catalog() -> TemplateCatalog:
    """Return a catalog with built-in quickstart templates."""
    catalog = TemplateCatalog()

    # Template 1: Code Reviewer
    catalog.register(AgentTemplate(
        name="code-reviewer",
        description="Reviews code changes and suggests improvements.",
        system_prompt=(
            "You are an expert code reviewer. Analyze the provided code diff or snippet. "
            "Identify potential bugs, style issues, security vulnerabilities, and performance "
            "problems. Provide constructive feedback and suggested fixes."
        ),
        model="gpt-4",
        tools=[
            ToolAssignment(name="run_pylint", config={"threshold": 8.0}),
            ToolAssignment(name="fetch_repo_structure", config={}),
        ],
        mcp_servers=[
            MCPServerDefinition(
                name="github-mcp",
                url="https://mcp.github.com/v1",
                auth_token_env="GITHUB_TOKEN",
            ),
        ],
        metadata={"category": "development", "version": "1.0.0"},
    ))

    # Template 2: Data Analyst
    catalog.register(AgentTemplate(
        name="data-analyst",
        description="Analyzes datasets and generates reports.",
        system_prompt=(
            "You are a data analyst assistant. Given a dataset description or file, "
            "perform exploratory data analysis, generate summary statistics, create "
            "visualizations, and provide actionable insights."
        ),
        model="gpt-4-turbo",
        tools=[
            ToolAssignment(name="run_sql_query", config={"database": "default"}),
            ToolAssignment(name="generate_chart", config={"type": "auto"}),
        ],
        mcp_servers=[
            MCPServerDefinition(
                name="postgres-mcp",
                url="https://mcp.postgres.example.com",
                auth_token_env="PG_MCP_TOKEN",
            ),
        ],
        metadata={"category": "data-science", "version": "1.0.0"},
    ))

    # Template 3: Customer Support
    catalog.register(AgentTemplate(
        name="customer-support",
        description="Handles customer inquiries and tickets.",
        system_prompt=(
            "You are a helpful customer support agent. Respond to customer questions "
            "politely and accurately. Use the knowledge base and ticketing system to "
            "resolve issues. Escalate when necessary."
        ),
        model="gpt-3.5-turbo",
        tools=[
            ToolAssignment(name="search_knowledge_base", config={"max_results": 5}),
            ToolAssignment(name="create_ticket", config={"priority": "normal"}),
        ],
        mcp_servers=[
            MCPServerDefinition(
                name="zendesk-mcp",
                url="https://mcp.zendesk.example.com",
                auth_token_env="ZENDESK_TOKEN",
            ),
        ],
        metadata={"category": "support", "version": "1.0.0"},
    ))

    return catalog


# ---------------------------------------------------------------------------
# Convenience function for one-click deploy
# ---------------------------------------------------------------------------

def deploy_template(template_name: str, catalog: Optional[TemplateCatalog] = None) -> AgentConfig:
    """
    Retrieve a template by name and return its AgentConfig ready for agent creation.
    This is the 'single click' entry point.
    """
    if catalog is None:
        catalog = get_default_catalog()
    template = catalog.get(template_name)
    if template is None:
        raise ValueError(f"Template '{template_name}' not found in catalog.")
    logger.info("Deploying template '%s' with model %s", template_name, template.model)
    return template.to_agent_config()
