"""Marketplace catalog manager for Anthropic's claude-plugins-official and custom repositories."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MarketplacePluginEntry(BaseModel):
    """Metadata representing a plugin available in the official or community marketplace."""

    name: str = Field(..., description="Unique plugin name")
    version: str = Field(default="1.0.0", description="Semantic version")
    description: str = Field(..., description="Summary of capabilities")
    marketplace: str = Field(default="claude-plugins-official", description="Source marketplace repository")
    author: str = Field(default="Anthropic / Community", description="Plugin author")
    category: str = Field(default="integration", description="Category e.g. dev, database, web, system")
    tags: List[str] = Field(default_factory=list)
    has_mcp: bool = Field(default=False, description="Whether this plugin includes an MCP server")
    has_skills: bool = Field(default=False, description="Whether this plugin provides procedural skills")
    recommended_command: Optional[str] = Field(default=None, description="Command or package required")


# Pre-seeded official plugins catalog mirrored from anthropics/claude-plugins-official
OFFICIAL_PLUGINS_CATALOG: Dict[str, MarketplacePluginEntry] = {
    "github": MarketplacePluginEntry(
        name="github",
        version="1.2.0",
        description="Official GitHub integration via Model Context Protocol: search repositories, inspect pull requests, read issues, review diffs, and inspect GitHub Actions.",
        marketplace="claude-plugins-official",
        author="Anthropic & GitHub",
        category="dev",
        tags=["git", "github", "vcs", "ci-cd"],
        has_mcp=True,
        has_skills=True,
        recommended_command="npx -y @modelcontextprotocol/server-github",
    ),
    "sqlite": MarketplacePluginEntry(
        name="sqlite",
        version="1.1.0",
        description="Official SQLite database explorer: execute read/write SQL queries, inspect table schemas, analyze table relationships, and generate schema reports.",
        marketplace="claude-plugins-official",
        author="Anthropic",
        category="database",
        tags=["sql", "sqlite", "database", "analytics"],
        has_mcp=True,
        has_skills=True,
        recommended_command="npx -y @modelcontextprotocol/server-sqlite",
    ),
    "postgresql": MarketplacePluginEntry(
        name="postgresql",
        version="1.0.4",
        description="Production PostgreSQL server integration: query databases, introspect schemas, inspect index usage, and run data migrations.",
        marketplace="claude-plugins-official",
        author="Anthropic",
        category="database",
        tags=["sql", "postgres", "database", "backend"],
        has_mcp=True,
        has_skills=False,
        recommended_command="npx -y @modelcontextprotocol/server-postgres",
    ),
    "fetch": MarketplacePluginEntry(
        name="fetch",
        version="1.3.0",
        description="Official web scraping and text extraction plugin: fetch any URL, convert HTML into clean Markdown, extract structured metadata, and respect robots.txt.",
        marketplace="claude-plugins-official",
        author="Anthropic",
        category="web",
        tags=["web", "scraping", "html", "markdown", "research"],
        has_mcp=True,
        has_skills=True,
        recommended_command="uvx mcp-server-fetch",
    ),
    "memory": MarketplacePluginEntry(
        name="memory",
        version="1.2.0",
        description="Knowledge graph-based persistent memory server: construct semantic entities, relations, observations, and retrieve associative context.",
        marketplace="claude-plugins-official",
        author="Anthropic",
        category="system",
        tags=["memory", "knowledge-graph", "triples", "episodic"],
        has_mcp=True,
        has_skills=True,
        recommended_command="npx -y @modelcontextprotocol/server-memory",
    ),
    "docker": MarketplacePluginEntry(
        name="docker",
        version="1.0.2",
        description="Official Docker container management plugin: list running containers, inspect logs, control docker compose stacks, and build images.",
        marketplace="claude-plugins-official",
        author="Anthropic & Community",
        category="dev",
        tags=["docker", "containers", "devops", "cloud"],
        has_mcp=True,
        has_skills=True,
        recommended_command="npx -y @modelcontextprotocol/server-docker",
    ),
    "python-lsp": MarketplacePluginEntry(
        name="python-lsp",
        version="1.1.0",
        description="Python Language Server Protocol intelligence: real-time Pyright AST diagnostics, type validation, go-to-definition, and symbol search.",
        marketplace="claude-plugins-official",
        author="Anthropic",
        category="dev",
        tags=["python", "lsp", "ide", "diagnostics", "ast"],
        has_mcp=True,
        has_skills=True,
        recommended_command="pyright-langserver --stdio",
    ),
    "typescript-lsp": MarketplacePluginEntry(
        name="typescript-lsp",
        version="1.1.0",
        description="TypeScript/JavaScript Language Server Protocol plugin: syntax diagnostics, autocomplete hints, type definitions, and refactoring.",
        marketplace="claude-plugins-official",
        author="Anthropic",
        category="dev",
        tags=["typescript", "javascript", "lsp", "ide"],
        has_mcp=True,
        has_skills=True,
        recommended_command="typescript-language-server --stdio",
    ),
    "filesystem": MarketplacePluginEntry(
        name="filesystem",
        version="1.0.0",
        description="Secure directory file system bridge: sandboxed read/write access to project directories.",
        marketplace="claude-plugins-official",
        author="Anthropic",
        category="system",
        tags=["files", "storage", "fs"],
        has_mcp=True,
        has_skills=False,
        recommended_command="npx -y @modelcontextprotocol/server-filesystem",
    ),
    "puppeteer": MarketplacePluginEntry(
        name="puppeteer",
        version="1.0.1",
        description="Headless Chrome browser automation: execute clicks, fill forms, capture screenshots, and evaluate scripts.",
        marketplace="claude-plugins-official",
        author="Anthropic",
        category="web",
        tags=["browser", "puppeteer", "automation", "e2e"],
        has_mcp=True,
        has_skills=True,
        recommended_command="npx -y @modelcontextprotocol/server-puppeteer",
    ),
}


class PluginMarketplace:
    """Discovers and manages plugin marketplaces including claude-plugins-official and custom repos."""

    def __init__(self) -> None:
        self.marketplaces: Dict[str, str] = {
            "claude-plugins-official": "https://github.com/anthropics/claude-plugins-official",
            "claude-plugins-community": "https://github.com/anthropics/claude-plugins-community",
        }
        self.catalog: Dict[str, MarketplacePluginEntry] = dict(OFFICIAL_PLUGINS_CATALOG)

    def add_marketplace(self, name: str, url: str) -> None:
        """Register a custom plugin marketplace repository."""
        self.marketplaces[name] = url

    def list_marketplaces(self) -> Dict[str, str]:
        """List registered marketplace repositories."""
        return dict(self.marketplaces)

    def search_catalog(self, query: str = "", category: Optional[str] = None) -> List[MarketplacePluginEntry]:
        """Search the marketplace catalog by query or category."""
        results = []
        q = query.lower().strip()
        for entry in self.catalog.values():
            if category and entry.category.lower() != category.lower():
                continue
            if not q or (q in entry.name.lower() or q in entry.description.lower() or any(q in t.lower() for t in entry.tags)):
                results.append(entry)
        return results

    def get_plugin_info(self, plugin_name: str) -> Optional[MarketplacePluginEntry]:
        """Get plugin details from catalog by name."""
        clean_name = plugin_name.split("@")[0].strip().lower()
        return self.catalog.get(clean_name)


plugin_marketplace = PluginMarketplace()

__all__ = ["MarketplacePluginEntry", "PluginMarketplace", "plugin_marketplace", "OFFICIAL_PLUGINS_CATALOG"]
