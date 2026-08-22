"""Dynamic plugin loader and discovery engine for Mitchell."""

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from mitchell.core.event_log import event_log
from mitchell.core.logging import logger
from mitchell.plugins.manifest import PluginManifest
from mitchell.tools.registry import Tool, tool_registry


class PluginLoader:
    """Discovers, validates, and dynamically loads drop-in plugins from filesystem directories."""

    def __init__(self, plugins_dir: Optional[Path] = None) -> None:
        self.root_dir = Path(__file__).resolve().parent.parent.parent
        self.plugins_dir = plugins_dir or (self.root_dir / ".mitchell" / "plugins")
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        self.loaded_plugins: Dict[str, PluginManifest] = {}
        self.plugin_modules: Dict[str, Any] = {}

    def load_plugin_from_directory(self, dir_path: Path) -> Optional[PluginManifest]:
        """Load and register a single plugin from a directory containing plugin.json."""
        manifest_file = dir_path / "plugin.json"
        if not manifest_file.exists():
            return None

        try:
            raw_data = json.loads(manifest_file.read_text(encoding="utf-8"))
            manifest = PluginManifest.model_validate(raw_data)
        except Exception as e:
            logger.error("Failed to parse plugin manifest at {}: {}", manifest_file, e)
            return None

        entry_file = dir_path / manifest.entry_point
        if not entry_file.exists():
            logger.error("Plugin entry point '{}' not found in {}", manifest.entry_point, dir_path)
            return None

        # Dynamically import module
        module_name = f"mitchell_plugin_{manifest.name}"
        try:
            spec = importlib.util.spec_from_file_location(module_name, str(entry_file))
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = mod
                spec.loader.exec_module(mod)
                self.plugin_modules[manifest.name] = mod

                # If module exposes TOOLS list, register them
                tools_list = getattr(mod, "TOOLS", None)
                if isinstance(tools_list, list):
                    for t in tools_list:
                        if isinstance(t, Tool):
                            tool_registry.register(t)

                self.loaded_plugins[manifest.name] = manifest
                event_log.log_event(
                    "plugin_loaded",
                    source="plugin_loader",
                    data={"plugin_name": manifest.name, "version": manifest.version},
                )
                logger.info("Successfully loaded plugin '{}' (v{})", manifest.name, manifest.version)
                return manifest
        except Exception as e:
            logger.error("Error loading plugin '{}': {}", manifest.name, e)

        return None

    def discover_and_load_all(self) -> List[PluginManifest]:
        """Scan plugins directory and load all discovered valid plugins."""
        loaded = []
        if not self.plugins_dir.exists():
            return loaded

        for item in self.plugins_dir.iterdir():
            if item.is_dir() and (item / "plugin.json").exists():
                manifest = self.load_plugin_from_directory(item)
                if manifest:
                    loaded.append(manifest)

        return loaded

    def list_plugins(self) -> List[Dict[str, Any]]:
        """Return list of currently active loaded plugins."""
        return [
            {
                "name": p.name,
                "version": p.version,
                "description": p.description,
                "author": p.author,
                "tags": p.tags,
            }
            for p in self.loaded_plugins.values()
        ]


plugin_loader = PluginLoader()

__all__ = ["PluginLoader", "plugin_loader"]
