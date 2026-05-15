# archestra/agent_templates/catalog.py
"""
Agent template catalog for quickstart agent deployment.
Provides pre-built agent templates with system prompts, model configs, tool assignments,
and MCP server installation in a single click.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from pathlib import Path

import yaml

from archestra.agents.base import AgentConfig
from archestra.tools.registry import ToolRegistry
from archestra.mcp.server import MCPServerManager
from archestra.utils.serialization import SerializableMixin

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class AgentTemplate(SerializableMixin):
    """Represents a pre-built agent template."""
    
    id: str
    name: str
    description: str
    system_prompt: str
    model: str
    temperature: float = 0.7
    max_tokens: int = 2048
    tools: List[str] = field(default_factory=list)
    mcp_servers: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    version: str = "1.0.0"
    author: str = "archestra"
    
    def to_agent_config(self) -> AgentConfig:
        """Convert template to an AgentConfig for instantiation."""
        return AgentConfig(
            name=self.name,
            system_prompt=self.system_prompt,
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            tools=self.tools,
        )
    
    def validate(self) -> bool:
        """Validate template fields."""
        if not self.id or not self.name:
            return False
        if not self.system_prompt:
            return False
        if not self.model:
            return False
        return True


class TemplateCatalog:
    """
    Manages the catalog of agent templates.
    Supports loading from YAML/JSON files and programmatic registration.
    """
    
    def __init__(self, catalog_path: Optional[Path] = None):
        self._templates: Dict[str, AgentTemplate] = {}
        self._catalog_path = catalog_path or Path("agent_templates/catalog.yaml")
        self._load_defaults()
        if self._catalog_path.exists():
            self.load_from_file(self._catalog_path)
    
    def _load_defaults(self):
        """Load built-in default templates."""
        defaults = [
            AgentTemplate(
                id="research-assistant",
                name="Research Assistant",
                description="A helpful research assistant with web search and summarization tools.",
                system_prompt="You are a research assistant. Help users find and summarize information.",
                model="gpt-4",
                tools=["web_search", "summarizer"],
                mcp_servers=["mcp-search", "mcp-summary"],
                tags=["research", "productivity"],
            ),
            AgentTemplate(
                id="code-reviewer",
                name="Code Reviewer",
                description="An expert code reviewer that analyzes code quality and suggests improvements.",
                system_prompt="You are an expert code reviewer. Analyze code for bugs, style issues, and improvements.",
                model="gpt-4",
                temperature=0.3,
                tools=["code_analyzer", "linter"],
                mcp_servers=["mcp-code-analysis"],
                tags=["development", "code-quality"],
            ),
            AgentTemplate(
                id="customer-support",
                name="Customer Support Agent",
                description="Handles customer inquiries with empathy and accuracy.",
                system_prompt="You are a customer support agent. Be helpful, empathetic, and accurate.",
                model="gpt-3.5-turbo",
                tools=["ticket_system", "knowledge_base"],
                mcp_servers=["mcp-ticketing", "mcp-knowledge"],
                tags=["support", "customer-service"],
            ),
        ]
        for tmpl in defaults:
            self.register(tmpl)
    
    def register(self, template: AgentTemplate) -> None:
        """Register a template in the catalog."""
        if not template.validate():
            raise ValueError(f"Invalid template: {template.id}")
        self._templates[template.id] = template
        logger.info(f"Registered template: {template.id}")
    
    def get(self, template_id: str) -> Optional[AgentTemplate]:
        """Get a template by ID."""
        return self._templates.get(template_id)
    
    def list_templates(self, tags: Optional[List[str]] = None) -> List[AgentTemplate]:
        """List all templates, optionally filtered by tags."""
        if not tags:
            return list(self._templates.values())
        return [t for t in self._templates.values() if any(tag in t.tags for tag in tags)]
    
    def load_from_file(self, path: Path) -> int:
        """Load templates from a YAML or JSON file. Returns number loaded."""
        if not path.exists():
            logger.warning(f"Catalog file not found: {path}")
            return 0
        
        with open(path, "r") as f:
            if path.suffix in (".yaml", ".yml"):
                data = yaml.safe_load(f)
            elif path.suffix == ".json":
                data = json.load(f)
            else:
                raise ValueError(f"Unsupported file format: {path.suffix}")
        
        count = 0
        for item in data.get("templates", []):
            try:
                template = AgentTemplate(**item)
                self.register(template)
                count += 1
            except Exception as e:
                logger.error(f"Failed to load template: {e}")
        return count
    
    def save_to_file(self, path: Optional[Path] = None) -> None:
        """Save catalog to a YAML file."""
        save_path = path or self._catalog_path
        save_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": "1.0",
            "templates": [asdict(t) for t in self._templates.values()]
        }
        with open(save_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False)
        logger.info(f"Saved catalog to {save_path}")
    
    def deploy_agent(self, template_id: str, tool_registry: ToolRegistry,
                     mcp_manager: MCPServerManager) -> Any:
        """
        One-click deploy: create agent config, assign tools, install MCP servers.
        Returns the agent instance.
        """
        template = self.get(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")
        
        # Register tools
        for tool_name in template.tools:
            if tool_name not in tool_registry.list_tools():
                logger.warning(f"Tool '{tool_name}' not registered, skipping.")
        
        # Install MCP servers
        for server_name in template.mcp_servers:
            try:
                mcp_manager.install(server_name)
                logger.info(f"Installed MCP server: {server_name}")
            except Exception as e:
                logger.error(f"Failed to install MCP server '{server_name}': {e}")
        
        # Create agent config
        config = template.to_agent_config()
        # In a real system, you'd instantiate the agent here
        # For now, return the config as a placeholder
        logger.info(f"Deployed agent from template: {template_id}")
        return config


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------

_catalog_instance: Optional[TemplateCatalog] = None


def get_catalog() -> TemplateCatalog:
    """Get the global catalog instance."""
    global _catalog_instance
    if _catalog_instance is None:
        _catalog_instance = TemplateCatalog()
    return _catalog_instance


def list_available_templates(tags: Optional[List[str]] = None) -> List[Dict]:
    """List available templates as dicts for API responses."""
    catalog = get_catalog()
    templates = catalog.list_templates(tags)
    return [asdict(t) for t in templates]


def deploy_from_template(template_id: str, tool_registry: ToolRegistry,
                         mcp_manager: MCPServerManager) -> Any:
    """Deploy an agent from a template by ID."""
    catalog = get_catalog()
    return catalog.deploy_agent(template_id, tool_registry, mcp_manager)
