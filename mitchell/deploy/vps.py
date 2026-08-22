"""Cloud VPS and Systemd service configuration generator for Mitchell."""

from pathlib import Path
from typing import Dict, Optional


class VPSDeployer:
    """Generates systemd service units and reverse proxy configs for 24/7 cloud deployments."""

    def __init__(self, install_dir: str = "/opt/mitchell", user: str = "mitchell") -> None:
        self.install_dir = install_dir
        self.user = user

    def generate_systemd_unit(self, service_type: str = "butler") -> str:
        """Generate a systemd service unit file for Mitchell."""
        cmd = f"{self.install_dir}/venv/bin/mitchell {service_type}"
        return (
            f"[Unit]\n"
            f"Description=Mitchell Autonomous {service_type.capitalize()} Service\n"
            f"After=network.target\n\n"
            f"[Service]\n"
            f"Type=simple\n"
            f"User={self.user}\n"
            f"WorkingDirectory={self.install_dir}\n"
            f"ExecStart={cmd}\n"
            f"Restart=always\n"
            f"RestartSec=5\n"
            f"Environment=PYTHONUNBUFFERED=1\n\n"
            f"[Install]\n"
            f"WantedBy=multi-user.target\n"
        )

    def generate_caddyfile(self, domain: str = "agent.yourdomain.com", studio_port: int = 8500) -> str:
        """Generate a Caddyfile for automatic HTTPS reverse proxy."""
        return (
            f"{domain} {{\n"
            f"    reverse_proxy 127.0.0.1:{studio_port}\n"
            f"    encode gzip zstd\n"
            f"}}\n"
        )


vps_deployer = VPSDeployer()

__all__ = ["VPSDeployer", "vps_deployer"]
