"""Mitchell Dynamic Plugin Ecosystem — Hot-reloading, Manifest Validation, Claude compatibility, and Marketplaces."""

from mitchell.plugins.installer import PluginInstaller, plugin_installer
from mitchell.plugins.loader import PluginLoader, plugin_loader
from mitchell.plugins.manifest import PluginManifest
from mitchell.plugins.marketplace import MarketplacePluginEntry, PluginMarketplace, plugin_marketplace

__all__ = [
    "PluginManifest",
    "PluginLoader",
    "plugin_loader",
    "PluginInstaller",
    "plugin_installer",
    "PluginMarketplace",
    "plugin_marketplace",
    "MarketplacePluginEntry",
]

