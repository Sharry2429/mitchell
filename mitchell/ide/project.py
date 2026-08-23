"""Project management, template scaffolding, and dependency analysis for the Mitchell Agentic IDE."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from mitchell.core.config import settings
from mitchell.core.event_log import event_log
from mitchell.core.logging import logger


class ProjectManifest(BaseModel):
    """Manifest describing an active IDE project."""

    name: str
    root_path: str
    project_type: str = "python"  # 'python' | 'node' | 'web' | 'rust' | 'generic'
    description: str = ""
    entry_point: str = ""
    dependencies: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_opened: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ProjectScaffolder:
    """Creates, scans, and scaffolds projects inside the Mitchell Agentic IDE."""

    TEMPLATES: Dict[str, Dict[str, str]] = {
        "python": {
            "main.py": '"""Main application entry point."""\n\ndef main() -> None:\n    print("Hello from Mitchell Project!")\n\nif __name__ == "__main__":\n    main()\n',
            "README.md": "# Python Project\n\nCreated with Mitchell Agentic IDE.\n",
            "requirements.txt": "# Project dependencies\n",
            ".gitignore": "__pycache__/\n*.py[cod]\nvenv/\n.env\n",
        },
        "web": {
            "index.html": '<!DOCTYPE html>\n<html lang="en">\n<head>\n  <meta charset="UTF-8">\n  <title>App</title>\n  <link rel="stylesheet" href="style.css">\n</head>\n<body>\n  <h1>Welcome</h1>\n  <script src="app.js"></script>\n</body>\n</html>\n',
            "style.css": "body {\n  font-family: system-ui, sans-serif;\n  margin: 40px;\n  background: #0f1015;\n  color: #fff;\n}\n",
            "app.js": 'console.log("Mitchell Web App initialized");\n',
            "README.md": "# Web App\n\nCreated with Mitchell Agentic IDE.\n",
        },
        "node": {
            "index.js": 'console.log("Hello from Node project!");\n',
            "package.json": json.dumps({"name": "mitchell-node-app", "version": "1.0.0", "main": "index.js", "scripts": {"start": "node index.js"}}, indent=2),
            "README.md": "# Node.js Project\n\nCreated with Mitchell Agentic IDE.\n",
            ".gitignore": "node_modules/\n.env\n",
        },
    }

    def __init__(self) -> None:
        self.projects_dir = Path(settings.data_dir) / "projects"
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_file = self.projects_dir / "projects_index.json"

    def create_project(
        self,
        name: str,
        template: str = "python",
        description: str = "",
        target_dir: Optional[str] = None,
    ) -> ProjectManifest:
        """Scaffold a new project from template."""
        clean_name = name.strip().replace(" ", "_").lower()
        project_root = Path(target_dir) if target_dir else (self.projects_dir / clean_name)
        project_root.mkdir(parents=True, exist_ok=True)

        files = self.TEMPLATES.get(template, self.TEMPLATES["python"])
        for rel_file, content in files.items():
            file_path = project_root / rel_file
            if not file_path.exists():
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content, encoding="utf-8")

        manifest = ProjectManifest(
            name=name,
            root_path=str(project_root.resolve()),
            project_type=template,
            description=description,
            entry_point="main.py" if template == "python" else ("index.js" if template == "node" else "index.html"),
        )
        self._record_project(manifest)

        event_log.log_event(
            "ide_project_created",
            source="project_scaffolder",
            data={"name": name, "type": template, "path": manifest.root_path},
        )
        logger.info("Project '{}' ({}) scaffolded at {}", name, template, manifest.root_path)
        return manifest

    def scan_project(self, folder_path: str) -> ProjectManifest:
        """Inspect an existing directory and detect its project type and dependencies."""
        root = Path(folder_path).resolve()
        if not root.exists():
            raise FileNotFoundError(f"Directory not found: {folder_path}")

        name = root.name
        ptype = "generic"
        entry = ""
        deps = []

        if (root / "pyproject.toml").exists() or (root / "requirements.txt").exists() or (root / "setup.py").exists():
            ptype = "python"
            entry = "main.py" if (root / "main.py").exists() else ("app.py" if (root / "app.py").exists() else "")
            if (root / "requirements.txt").exists():
                try:
                    deps = [
                        l.strip() for l in (root / "requirements.txt").read_text(encoding="utf-8").splitlines()
                        if l.strip() and not l.startswith("#")
                    ]
                except Exception:
                    pass
        elif (root / "package.json").exists():
            ptype = "node"
            entry = "index.js"
            try:
                pkg_data = json.loads((root / "package.json").read_text(encoding="utf-8"))
                entry = pkg_data.get("main", "index.js")
                deps = list(pkg_data.get("dependencies", {}).keys())
            except Exception:
                pass
        elif (root / "Cargo.toml").exists():
            ptype = "rust"
            entry = "src/main.rs"

        manifest = ProjectManifest(
            name=name,
            root_path=str(root),
            project_type=ptype,
            entry_point=entry,
            dependencies=deps,
        )
        self._record_project(manifest)
        return manifest

    def _record_project(self, manifest: ProjectManifest) -> None:
        """Save project to index."""
        projects = self.list_projects()
        projects = [p for p in projects if p["root_path"] != manifest.root_path]
        projects.append(manifest.model_dump(mode="json"))
        try:
            self.manifest_file.write_text(json.dumps(projects, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error("Failed to save project manifest index: {}", e)

    def list_projects(self) -> List[Dict[str, Any]]:
        """List all indexed projects."""
        if self.manifest_file.exists():
            try:
                return json.loads(self.manifest_file.read_text(encoding="utf-8"))
            except Exception:
                return []
        return []

    def get_directory_tree(self, root_path: str, max_depth: int = 4) -> Dict[str, Any]:
        """Generate a hierarchical JSON tree for the file explorer."""
        root = Path(root_path).resolve()
        if not root.exists():
            root = Path(os.getcwd()).resolve()

        ignore_names = {".git", "__pycache__", "node_modules", ".pytest_cache", ".venv", "venv", ".mitchell"}

        def _scan_dir(current_dir: Path, current_depth: int) -> Dict[str, Any]:
            children = []
            if current_depth <= max_depth:
                try:
                    for entry in sorted(current_dir.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
                        if entry.name in ignore_names:
                            continue
                        if entry.is_dir():
                            children.append(_scan_dir(entry, current_depth + 1))
                        else:
                            children.append({
                                "name": entry.name,
                                "path": str(entry.resolve()),
                                "type": "file",
                                "extension": entry.suffix.lstrip("."),
                                "size_bytes": entry.stat().st_size if entry.exists() else 0,
                            })
                except PermissionError:
                    pass

            return {
                "name": current_dir.name or str(current_dir),
                "path": str(current_dir.resolve()),
                "type": "directory",
                "children": children,
            }

        return _scan_dir(root, 1)


project_scaffolder = ProjectScaffolder()

__all__ = ["ProjectManifest", "ProjectScaffolder", "project_scaffolder"]

