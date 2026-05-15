# archestra/agents/template_catalog.py

"""
Agent Template Catalog - Quickstart templates for pre-built agents.
Allows users to spin up fully-configured agents with system prompts, models,
tool assignments, and MCP server installations in a single click.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from archestra.agents.base import AgentConfig
from archestra.mcp.server import MCPServerConfig
from archestra.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


@dataclass
class AgentTemplate:
    """Represents a pre-built agent template."""
    name: str
    description: str
    system_prompt: str
    model: str
    tools: List[str] = field(default_factory=list)
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
        """Serialize template to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "system_prompt": self.system_prompt,
            "model": self.model,
            "tools": list(self.tools),
            "mcp_servers": [s.to_dict() for s in self.mcp_servers],
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentTemplate":
        """Deserialize template from dictionary."""
        mcp_servers = [
            MCPServerConfig.from_dict(s) if isinstance(s, dict) else s
            for s in data.get("mcp_servers", [])
        ]
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            system_prompt=data["system_prompt"],
            model=data["model"],
            tools=data.get("tools", []),
            mcp_servers=mcp_servers,
            metadata=data.get("metadata", {}),
        )


class TemplateCatalog:
    """
    Catalog of pre-built agent templates.
    Supports loading from built-in templates, file, or directory.
    """

    def __init__(self, templates: Optional[Dict[str, AgentTemplate]] = None):
        self._templates: Dict[str, AgentTemplate] = templates or {}
        self._load_builtin_templates()

    def _load_builtin_templates(self) -> None:
        """Load built-in quickstart templates."""
        builtins = {
            "research-assistant": AgentTemplate(
                name="Research Assistant",
                description="An agent that helps with research tasks, web searches, and summarization.",
                system_prompt="You are a helpful research assistant. Use web search and data analysis tools to answer questions thoroughly.",
                model="gpt-4",
                tools=["web_search", "web_scrape", "summarize"],
                mcp_servers=[
                    MCPServerConfig(
                        name="web-search",
                        command="npx",
                        args=["-y", "@archestra/mcp-web-search"],
                    ),
                    MCPServerConfig(
                        name="data-analysis",
                        command="npx",
                        args=["-y", "@archestra/mcp-data-analysis"],
                    ),
                ],
                metadata={"category": "productivity", "difficulty": "beginner"},
            ),
            "code-reviewer": AgentTemplate(
                name="Code Reviewer",
                description="An agent that reviews code, suggests improvements, and detects bugs.",
                system_prompt="You are an expert code reviewer. Analyze code for bugs, style issues, and performance improvements.",
                model="gpt-4",
                tools=["code_analysis", "static_analysis", "lint"],
                mcp_servers=[
                    MCPServerConfig(
                        name="code-analysis",
                        command="npx",
                        args=["-y", "@archestra/mcp-code-analysis"],
                    ),
                ],
                metadata={"category": "development", "difficulty": "intermediate"},
            ),
            "customer-support": AgentTemplate(
                name="Customer Support Agent",
                description="Handles customer inquiries, ticket management, and FAQ responses.",
                system_prompt="You are a friendly customer support agent. Help users with their questions and escalate issues when necessary.",
                model="gpt-3.5-turbo",
                tools=["ticket_system", "faq_lookup", "sentiment_analysis"],
                mcp_servers=[
                    MCPServerConfig(
                        name="support-tools",
                        command="npx",
                        args=["-y", "@archestra/mcp-support"],
                    ),
                ],
                metadata={"category": "customer-service", "difficulty": "beginner"},
            ),
        }
        for name, template in builtins.items():
            if name not in self._templates:
                self._templates[name] = template

    def list_templates(self) -> List[Dict[str, Any]]:
        """Return a list of all available templates with metadata."""
        return [
            {
                "id": tid,
                "name": t.name,
                "description": t.description,
                "model": t.model,
                "tool_count": len(t.tools),
                "mcp_server_count": len(t.mcp_servers),
                "metadata": t.metadata,
            }
            for tid, t in self._templates.items()
        ]

    def get_template(self, template_id: str) -> Optional[AgentTemplate]:
        """Retrieve a template by its ID."""
        return self._templates.get(template_id)

    def add_template(self, template_id: str, template: AgentTemplate) -> None:
        """Add or update a template in the catalog."""
        self._templates[template_id] = template
        logger.info(f"Template '{template_id}' added/updated.")

    def remove_template(self, template_id: str) -> bool:
        """Remove a template by ID. Returns True if removed."""
        if template_id in self._templates:
            del self._templates[template_id]
            logger.info(f"Template '{template_id}' removed.")
            return True
        return False

    def save_to_file(self, path: Path) -> None:
        """Save all templates to a JSON file."""
        data = {
            tid: t.to_dict()
            for tid, t in self._templates.items()
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Templates saved to {path}")

    def load_from_file(self, path: Path) -> None:
        """Load templates from a JSON file, merging with existing."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for tid, tdata in data.items():
            template = AgentTemplate.from_dict(tdata)
            self._templates[tid] = template
        logger.info(f"Templates loaded from {path}")

    def instantiate_agent(self, template_id: str, **overrides: Any) -> Optional[AgentConfig]:
        """
        Create an AgentConfig from a template, with optional overrides.
        Returns None if template not found.
        """
        template = self.get_template(template_id)
        if not template:
            logger.warning(f"Template '{template_id}' not found.")
            return None
        config = template.to_agent_config()
        # Apply overrides
        for key, value in overrides.items():
            if hasattr(config, key):
                setattr(config, key, value)
        return config


# Singleton instance for global use
_default_catalog: Optional[TemplateCatalog] = None


def get_default_catalog() -> TemplateCatalog:
    """Get or create the default template catalog."""
    global _default_catalog
    if _default_catalog is None:
        _default_catalog = TemplateCatalog()
    return _default_catalog


def list_available_templates() -> List[Dict[str, Any]]:
    """Convenience function to list all templates from the default catalog."""
    return get_default_catalog().list_templates()


def instantiate_from_template(template_id: str, **overrides: Any) -> Optional[AgentConfig]:
    """Convenience function to instantiate an agent from a template."""
    return get_default_catalog().instantiate_agent(template_id, **overrides)
