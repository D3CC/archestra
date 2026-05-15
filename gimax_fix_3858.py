# archestra/agents/template_catalog.py
"""
Agent template catalog module providing pre-built agent templates
for quickstart deployment with MCP server integration.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from archestra.agents.base import AgentConfig
from archestra.mcp.server import MCPServerConfig
from archestra.utils.serialization import SerializableMixin

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class AgentTemplate(SerializableMixin):
    """Represents a pre-built agent template for quickstart deployment."""
    name: str
    description: str
    system_prompt: str
    model: str
    tools: List[str] = field(default_factory=list)
    mcp_servers: List[MCPServerConfig] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    version: str = "1.0.0"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_agent_config(self) -> AgentConfig:
        """Convert template to an AgentConfig for instantiation."""
        return AgentConfig(
            name=self.name,
            system_prompt=self.system_prompt,
            model=self.model,
            tools=self.tools,
            mcp_servers=[s.to_dict() for s in self.mcp_servers],
            metadata={**self.metadata, "template_version": self.version},
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentTemplate":
        mcp_servers = [MCPServerConfig.from_dict(s) for s in data.pop("mcp_servers", [])]
        return cls(mcp_servers=mcp_servers, **data)


# ---------------------------------------------------------------------------
# Catalog loader
# ---------------------------------------------------------------------------

class TemplateCatalog:
    """Manages the catalog of agent templates, loading from bundled or custom sources."""

    def __init__(self, catalog_path: Optional[Path] = None):
        self._templates: Dict[str, AgentTemplate] = {}
        if catalog_path:
            self.load_from_file(catalog_path)
        else:
            self._load_bundled()

    def _load_bundled(self) -> None:
        """Load built-in quickstart templates."""
        bundled = _get_bundled_templates()
        for tmpl in bundled:
            self._templates[tmpl.name] = tmpl
        logger.info(f"Loaded {len(bundled)} bundled templates")

    def load_from_file(self, path: Path) -> None:
        """Load templates from a JSON file."""
        if not path.exists():
            raise FileNotFoundError(f"Catalog file not found: {path}")
        with open(path, "r") as f:
            data = json.load(f)
        for item in data:
            tmpl = AgentTemplate.from_dict(item)
            self._templates[tmpl.name] = tmpl
        logger.info(f"Loaded {len(data)} templates from {path}")

    def get_template(self, name: str) -> Optional[AgentTemplate]:
        """Retrieve a template by name."""
        return self._templates.get(name)

    def list_templates(self, tag: Optional[str] = None) -> List[AgentTemplate]:
        """List all templates, optionally filtered by tag."""
        if tag:
            return [t for t in self._templates.values() if tag in t.tags]
        return list(self._templates.values())

    def add_template(self, template: AgentTemplate) -> None:
        """Add a custom template to the catalog (in-memory)."""
        self._templates[template.name] = template
        logger.info(f"Added template: {template.name}")

    def remove_template(self, name: str) -> bool:
        """Remove a template by name. Returns True if removed."""
        return self._templates.pop(name, None) is not None


# ---------------------------------------------------------------------------
# Bundled quickstart templates
# ---------------------------------------------------------------------------

def _get_bundled_templates() -> List[AgentTemplate]:
    """Return a curated list of quickstart agent templates."""
    return [
        AgentTemplate(
            name="customer-support-bot",
            description="Handles common customer inquiries with FAQ lookup and ticket creation.",
            system_prompt=(
                "You are a helpful customer support agent. Answer questions based on the "
                "provided FAQ database. If unable to resolve, create a support ticket."
            ),
            model="gpt-4o-mini",
            tools=["faq_search", "ticket_creator"],
            mcp_servers=[
                MCPServerConfig(
                    name="faq-server",
                    command="python",
                    args=["-m", "archestra.mcp.servers.faq_server"],
                    env={"FAQ_DB_PATH": "/data/faq.json"},
                ),
                MCPServerConfig(
                    name="ticket-server",
                    command="python",
                    args=["-m", "archestra.mcp.servers.ticket_server"],
                ),
            ],
            tags=["customer-support", "quickstart"],
            metadata={"difficulty": "beginner", "category": "support"},
        ),
        AgentTemplate(
            name="code-review-assistant",
            description="Reviews pull requests for code quality, security, and style issues.",
            system_prompt=(
                "You are an expert code reviewer. Analyze the provided diff and comment on "
                "potential bugs, security vulnerabilities, and style violations."
            ),
            model="claude-3-opus",
            tools=["code_diff_analyzer", "lint_runner"],
            mcp_servers=[
                MCPServerConfig(
                    name="lint-server",
                    command="docker",
                    args=["run", "--rm", "-v", "/workspace:/workspace", "linter:latest"],
                ),
            ],
            tags=["developer-tools", "code-review"],
            metadata={"difficulty": "intermediate", "category": "development"},
        ),
        AgentTemplate(
            name="data-analyst",
            description="Analyzes CSV/JSON data and generates visualizations.",
            system_prompt=(
                "You are a data analyst assistant. Load the provided dataset, perform "
                "exploratory analysis, and generate charts to answer user questions."
            ),
            model="gpt-4o",
            tools=["data_loader", "chart_generator", "statistical_analyzer"],
            mcp_servers=[
                MCPServerConfig(
                    name="data-server",
                    command="python",
                    args=["-m", "archestra.mcp.servers.data_server"],
                    env={"DATA_DIR": "/data"},
                ),
            ],
            tags=["data-science", "analytics"],
            metadata={"difficulty": "intermediate", "category": "data"},
        ),
    ]


# ---------------------------------------------------------------------------
# Convenience function for one-click deployment
# ---------------------------------------------------------------------------

def deploy_from_template(
    template_name: str,
    catalog: Optional[TemplateCatalog] = None,
    overrides: Optional[Dict[str, Any]] = None,
) -> AgentConfig:
    """
    Deploy an agent from a template with optional overrides.
    Returns an AgentConfig ready for instantiation.
    """
    if catalog is None:
        catalog = TemplateCatalog()
    template = catalog.get_template(template_name)
    if template is None:
        raise ValueError(f"Template '{template_name}' not found in catalog")
    config = template.to_agent_config()
    if overrides:
        for key, value in overrides.items():
            if hasattr(config, key):
                setattr(config, key, value)
    logger.info(f"Deployed agent config from template '{template_name}'")
    return config
