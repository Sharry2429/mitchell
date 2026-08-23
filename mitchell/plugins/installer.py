"""Plugin installer for downloading, scaffolding, and registering plugins from marketplaces or git."""

import json
import shutil
from pathlib import Path
from typing import Any, Dict, Optional

from mitchell.core.event_log import event_log
from mitchell.core.logging import logger
from mitchell.mcp_client.hub import mcp_hub
from mitchell.plugins.loader import plugin_loader
from mitchell.plugins.manifest import PluginManifest
from mitchell.plugins.marketplace import plugin_marketplace
from mitchell.skills.library import skill_library


class PluginInstaller:
    """Installs plugins from Claude official marketplace, GitHub repositories, or local directories."""

    def __init__(self, plugins_dir: Optional[Path] = None) -> None:
        self.root_dir = Path(__file__).resolve().parent.parent.parent
        self.plugins_dir = plugins_dir or (self.root_dir / ".mitchell" / "plugins")
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        self.marketplace = plugin_marketplace
        self.loader = plugin_loader

    def install(self, source: str, marketplace: Optional[str] = None) -> Dict[str, Any]:
        """Install a plugin from marketplace name (e.g. 'github@claude-plugins-official'), URL, or local path."""
        clean_name = source.split("@")[0].strip().lower()
        target_dir = self.plugins_dir / clean_name

        # Case 1: Local directory path
        local_path = Path(source)
        if local_path.exists() and local_path.is_dir():
            manifest_file = local_path / "plugin.json"
            claude_manifest = local_path / ".claude-plugin" / "plugin.json"
            if manifest_file.exists() or claude_manifest.exists():
                # Copy to plugins_dir if not already there
                if local_path.resolve() != target_dir.resolve():
                    if target_dir.exists():
                        shutil.rmtree(target_dir)
                    shutil.copytree(local_path, target_dir)
                manifest = self.loader.load_plugin_from_directory(target_dir)
                if manifest:
                    self._post_install_setup(target_dir, manifest)
                    return {"success": True, "message": f"Installed local plugin '{manifest.name}'", "manifest": manifest.model_dump()}

        # Case 2: Marketplace Catalog Plugin
        catalog_entry = self.marketplace.get_plugin_info(clean_name)
        if catalog_entry:
            target_dir.mkdir(parents=True, exist_ok=True)
            claude_dir = target_dir / ".claude-plugin"
            claude_dir.mkdir(parents=True, exist_ok=True)
            skills_dir = target_dir / "skills"
            skills_dir.mkdir(parents=True, exist_ok=True)

            manifest_data = {
                "name": catalog_entry.name,
                "version": catalog_entry.version,
                "description": catalog_entry.description,
                "author": catalog_entry.author,
                "marketplace": catalog_entry.marketplace,
                "tags": catalog_entry.tags,
                "entry_point": "plugin.py",
            }

            # If MCP server is recommended, write MCP config
            mcp_data = {}
            if catalog_entry.has_mcp and catalog_entry.recommended_command:
                cmd_parts = catalog_entry.recommended_command.split()
                cmd = cmd_parts[0]
                args = cmd_parts[1:]
                mcp_data = {
                    "mcpServers": {
                        catalog_entry.name: {
                            "command": cmd,
                            "args": args,
                        }
                    }
                }
                (target_dir / ".mcp.json").write_text(json.dumps(mcp_data, indent=2), encoding="utf-8")
                manifest_data["mcp_servers"] = mcp_data["mcpServers"]

            # Write standard plugin.json and .claude-plugin/plugin.json
            (target_dir / "plugin.json").write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")
            (claude_dir / "plugin.json").write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

            # Write standard procedural SKILL.md
            skill_md = [
                "---",
                f"name: {catalog_entry.name}_workflow",
                f"version: {catalog_entry.version}",
                f"description: Standard procedural workflow for {catalog_entry.name}.",
                f"tags: [{', '.join(catalog_entry.tags)}]",
                "---",
                "",
                f"# {catalog_entry.name.title()} Official Plugin Workflow",
                "",
                catalog_entry.description,
                "",
                "## Execution Steps",
                f"1. Initialize connection: `mcp_{catalog_entry.name}_status()`",
                f"2. Execute requested action: `mcp_{catalog_entry.name}_action()`",
            ]
            (skills_dir / "SKILL.md").write_text("\n".join(skill_md), encoding="utf-8")

            # Write minimal plugin.py entrypoint
            py_code = [
                f'"""Mitchell & Claude Code Plugin: {catalog_entry.name}"""',
                'from mitchell.tools.registry import Tool',
                '',
                f'def tool_{catalog_entry.name.replace("-", "_")}_status() -> str:',
                f'    return "Plugin {catalog_entry.name} is active and ready."',
                '',
                'status_tool = Tool(',
                f'    name="{catalog_entry.name.replace("-", "_")}_plugin_status",',
                f'    description="Check status of {catalog_entry.name} plugin",',
                f'    function=tool_{catalog_entry.name.replace("-", "_")}_status,',
                ')',
                '',
                'TOOLS = [status_tool]',
            ]
            (target_dir / "plugin.py").write_text("\n".join(py_code), encoding="utf-8")

            # Load into system
            manifest = self.loader.load_plugin_from_directory(target_dir)
            if manifest:
                self._post_install_setup(target_dir, manifest)
                logger.info("Successfully installed marketplace plugin '{}'", manifest.name)
                return {
                    "success": True,
                    "message": f"Successfully installed '{catalog_entry.name}' (v{catalog_entry.version}) from {catalog_entry.marketplace}",
                    "manifest": manifest.model_dump(),
                }

        # Case 3: Git URL (e.g. https://github.com/...)
        if source.startswith("http://") or source.startswith("https://") or source.startswith("git@"):
            try:
                import subprocess
                repo_name = source.rstrip("/").split("/")[-1].replace(".git", "")
                git_target = self.plugins_dir / repo_name
                if git_target.exists():
                    shutil.rmtree(git_target)
                subprocess.run(["git", "clone", "--depth", "1", source, str(git_target)], check=True, capture_output=True)
                manifest = self.loader.load_plugin_from_directory(git_target)
                if manifest:
                    self._post_install_setup(git_target, manifest)
                    return {"success": True, "message": f"Cloned and installed plugin '{manifest.name}'", "manifest": manifest.model_dump()}
            except Exception as e:
                logger.error("Failed to git clone plugin from '{}': {}", source, e)
                return {"success": False, "error": f"Failed to clone repository: {e}"}

        return {"success": False, "error": f"Plugin '{source}' not found in catalog or filesystem"}

    def _post_install_setup(self, plugin_dir: Path, manifest: PluginManifest) -> None:
        """Register associated skills and MCP servers for an installed plugin."""
        # 1. Discover skills
        skills_dir = plugin_dir / "skills"
        if skills_dir.exists():
            skill_library.discover_and_load_skills(skills_dir)

        # 2. Check for .mcp.json or manifest mcp_servers
        mcp_file = plugin_dir / ".mcp.json"
        if mcp_file.exists():
            try:
                mcp_data = json.loads(mcp_file.read_text(encoding="utf-8"))
                mcp_hub.load_from_manifest(mcp_data)
            except Exception as e:
                logger.warning("Failed to load plugin MCP file: {}", e)
        elif manifest.mcp_servers:
            mcp_hub.load_from_manifest({"mcpServers": manifest.mcp_servers})

        event_log.log_event(
            "plugin_installed",
            source="plugin_installer",
            data={"plugin_name": manifest.name, "version": manifest.version},
        )

    def uninstall(self, plugin_name: str) -> Dict[str, Any]:
        """Uninstall a plugin, stopping its MCP servers and removing files."""
        clean_name = plugin_name.split("@")[0].strip().lower()
        target_dir = self.plugins_dir / clean_name

        # Stop associated MCP server if active
        mcp_hub.remove_server(clean_name)

        # Unregister from loader
        if clean_name in self.loader.loaded_plugins:
            self.loader.loaded_plugins.pop(clean_name, None)

        if target_dir.exists():
            shutil.rmtree(target_dir, ignore_errors=True)
            logger.info("Uninstalled plugin '{}'", clean_name)
            event_log.log_event("plugin_uninstalled", source="plugin_installer", data={"plugin_name": clean_name})
            return {"success": True, "message": f"Successfully uninstalled plugin '{clean_name}'"}

        return {"success": False, "error": f"Plugin '{clean_name}' directory not found"}


plugin_installer = PluginInstaller()

__all__ = ["PluginInstaller", "plugin_installer"]
