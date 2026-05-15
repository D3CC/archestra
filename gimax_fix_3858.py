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

from archestra.core.agent import AgentConfig
from archestra.core.mcp import MCPServerConfig
from archestra.core.tools import ToolAssignment

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).parent / "templates"


@dataclass
class AgentTemplate:
    """Represents a pre-built agent template."""

    name: str
    description: str
    system_prompt: str
    model: str
    model_params: Dict[str, Any] = field(default_factory=dict)
    tool_assignments: List[ToolAssignment] = field(default_factory=list)
    mcp_servers: List[MCPServerConfig] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    version: str = "1.0.0"

    def to_agent_config(self) -> AgentConfig:
        """Convert template to an AgentConfig for instantiation."""
        return AgentConfig(
            system_prompt=self.system_prompt,
            model=self.model,
            model_params=self.model_params,
            tool_assignments=self.tool_assignments,
            mcp_servers=self.mcp_servers,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize template to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentTemplate":
        """Deserialize template from dictionary."""
        tool_assignments = [
            ToolAssignment(**ta) if isinstance(ta, dict) else ta
            for ta in data.get("tool_assignments", [])
        ]
        mcp_servers = [
            MCPServerConfig(**mcp) if isinstance(mcp, dict) else mcp
            for mcp in data.get("mcp_servers", [])
        ]
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            system_prompt=data["system_prompt"],
            model=data["model"],
            model_params=data.get("model_params", {}),
            tool_assignments=tool_assignments,
            mcp_servers=mcp_servers,
            tags=data.get("tags", []),
            version=data.get("version", "1.0.0"),
        )


class TemplateCatalog:
    """Manages the catalog of agent templates."""

    def __init__(self, template_dir: Optional[Path] = None):
        self.template_dir = template_dir or TEMPLATE_DIR
        self._templates: Dict[str, AgentTemplate] = {}
        self._load_templates()

    def _load_templates(self) -> None:
        """Load all templates from the template directory."""
        if not self.template_dir.exists():
            logger.warning(f"Template directory {self.template_dir} does not exist.")
            return

        for file_path in self.template_dir.glob("*.{yaml,yml,json}"):
            try:
                with open(file_path, "r") as f:
                    if file_path.suffix in (".yaml", ".yml"):
                        data = yaml.safe_load(f)
                    else:
                        data = json.load(f)

                if isinstance(data, list):
                    for item in data:
                        template = AgentTemplate.from_dict(item)
                        self._templates[template.name] = template
                else:
                    template = AgentTemplate.from_dict(data)
                    self._templates[template.name] = template

                logger.info(f"Loaded template from {file_path.name}")
            except Exception as e:
                logger.error(f"Failed to load template {file_path}: {e}")

    def list_templates(self, tag: Optional[str] = None) -> List[AgentTemplate]:
        """List all templates, optionally filtered by tag."""
        if tag:
            return [t for t in self._templates.values() if tag in t.tags]
        return list(self._templates.values())

    def get_template(self, name: str) -> Optional[AgentTemplate]:
        """Get a specific template by name."""
        return self._templates.get(name)

    def install_template(
        self, name: str, install_mcp: bool = True
    ) -> Optional[AgentConfig]:
        """
        Install a template: return an AgentConfig ready for agent creation.
        Optionally install MCP servers.
        """
        template = self.get_template(name)
        if not template:
            logger.error(f"Template '{name}' not found.")
            return None

        config = template.to_agent_config()

        if install_mcp and template.mcp_servers:
            from archestra.core.mcp import install_mcp_server

            for mcp_server in template.mcp_servers:
                try:
                    install_mcp_server(mcp_server)
                    logger.info(f"Installed MCP server: {mcp_server.name}")
                except Exception as e:
                    logger.error(f"Failed to install MCP server {mcp_server.name}: {e}")

        return config

    def add_template(self, template: AgentTemplate) -> None:
        """Add a new template to the catalog (in-memory)."""
        self._templates[template.name] = template
        logger.info(f"Added template: {template.name}")

    def remove_template(self, name: str) -> bool:
        """Remove a template from the catalog."""
        if name in self._templates:
            del self._templates[name]
            logger.info(f"Removed template: {name}")
            return True
        return False


# Pre-built quickstart templates
def get_default_templates() -> List[AgentTemplate]:
    """Return a list of default quickstart templates."""
    return [
        AgentTemplate(
            name="research-assistant",
            description="A research assistant that can search the web and summarize findings.",
            system_prompt="You are a helpful research assistant. Use web search tools to find "
                          "information and provide concise summaries.",
            model="gpt-4",
            model_params={"temperature": 0.3},
            tool_assignments=[
                ToolAssignment(name="web_search", config={"engine": "google"}),
                ToolAssignment(name="web_scrape", config={"max_pages": 3}),
            ],
            mcp_servers=[
                MCPServerConfig(
                    name="search-mcp",
                    command="npx",
                    args=["@archestra/mcp-server-search"],
                ),
            ],
            tags=["quickstart", "research"],
        ),
        AgentTemplate(
            name="code-reviewer",
            description="An agent that reviews code and suggests improvements.",
            system_prompt="You are an expert code reviewer. Analyze code for bugs, style issues, "
                          "and performance improvements.",
            model="gpt-4",
            model_params={"temperature": 0.1},
            tool_assignments=[
                ToolAssignment(name="code_analysis", config={"linters": ["pylint", "eslint"]}),
                ToolAssignment(name="git_diff", config={}),
            ],
            mcp_servers=[
                MCPServerConfig(
                    name="code-review-mcp",
                    command="npx",
                    args=["@archestra/mcp-server-code-review"],
                ),
            ],
            tags=["quickstart", "development"],
        ),
        AgentTemplate(
            name="customer-support",
            description="A customer support agent with knowledge base access.",
            system_prompt="You are a friendly customer support agent. Help users with their "
                          "questions using the knowledge base and ticketing system.",
            model="gpt-3.5-turbo",
            model_params={"temperature": 0.5},
            tool_assignments=[
                ToolAssignment(name="knowledge_base", config={"source": "docs"}),
                ToolAssignment(name="ticketing", config={"system": "zendesk"}),
            ],
            mcp_servers=[
                MCPServerConfig(
                    name="support-mcp",
                    command="npx",
                    args=["@archestra/mcp-server-support"],
                ),
            ],
            tags=["quickstart", "support"],
        ),
    ]


def initialize_catalog(template_dir: Optional[Path] = None) -> TemplateCatalog:
    """Initialize the template catalog with default templates."""
    catalog = TemplateCatalog(template_dir)
    # Add default templates if catalog is empty
    if not catalog.list_templates():
        for template in get_default_templates():
            catalog.add_template(template)
        logger.info("Initialized catalog with default templates.")
    return catalog
