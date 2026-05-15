# archestra/agent_templates/catalog.py
"""
Agent template catalog for quickstart agent deployment.
Provides pre-built agent templates with system prompts, models, tool assignments,
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

TEMPLATE_DIR = Path(__file__).parent / "templates"


@dataclass
class AgentTemplate:
    """Represents a pre-built agent template."""

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
            system_prompt=self.system_prompt,
            model=self.model,
            tools=self.tools,
            mcp_servers=self.mcp_servers,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize template to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentTemplate":
        """Deserialize from dictionary."""
        tools = [ToolAssignment(**t) if isinstance(t, dict) else t for t in data.get("tools", [])]
        mcp_servers = [
            MCPServerConfig(**s) if isinstance(s, dict) else s
            for s in data.get("mcp_servers", [])
        ]
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            system_prompt=data["system_prompt"],
            model=data["model"],
            tools=tools,
            mcp_servers=mcp_servers,
            metadata=data.get("metadata", {}),
        )


class TemplateCatalog:
    """Manages loading, listing, and retrieving agent templates."""

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

    def list_templates(self) -> List[Dict[str, Any]]:
        """Return a list of all available templates as dicts."""
        return [t.to_dict() for t in self._templates.values()]

    def get_template(self, name: str) -> Optional[AgentTemplate]:
        """Retrieve a template by name."""
        return self._templates.get(name)

    def install_template(self, name: str) -> Optional[AgentConfig]:
        """
        Install a template: return an AgentConfig ready for agent creation.
        In a real system, this would also trigger MCP server installation.
        """
        template = self.get_template(name)
        if template is None:
            logger.error(f"Template '{name}' not found.")
            return None
        logger.info(f"Installing template '{name}' with {len(template.mcp_servers)} MCP server(s).")
        # Here we would call MCP server installer, but for now just return config.
        return template.to_agent_config()


# Pre-built templates as YAML files (example content)
TEMPLATES_YAML = """
- name: "code-assistant"
  description: "AI coding assistant with code analysis and generation tools."
  system_prompt: "You are a helpful coding assistant. Provide clear, concise code solutions."
  model: "gpt-4"
  tools:
    - name: "code_analyzer"
      config:
        language: "python"
    - name: "code_generator"
      config:
        style: "pep8"
  mcp_servers:
    - name: "github-mcp"
      url: "http://localhost:8080"
    - name: "linting-mcp"
      url: "http://localhost:8081"

- name: "data-scientist"
  description: "Data analysis and visualization assistant."
  system_prompt: "You are a data scientist assistant. Help with data analysis, visualization, and modeling."
  model: "gpt-4-turbo"
  tools:
    - name: "data_analyzer"
      config:
        max_rows: 1000
    - name: "visualizer"
      config:
        default_chart: "bar"
  mcp_servers:
    - name: "jupyter-mcp"
      url: "http://localhost:8888"
