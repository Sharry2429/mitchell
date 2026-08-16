import os
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import markdownify
import psutil
import requests
import win32con
import win32gui
import win32process
from fuzzywuzzy import fuzz, process

from mitchell.windows.config import get_config
from mitchell.windows.types import CommandResult, DirectoryListing, FileInfo

# --- app.py ---


__all__ = [
    "close_window",
    "focus_window",
    "is_app_running",
    "launch_executable",
    "list_installed_apps",
    "maximize_window",
    "minimize_window",
    "move_window",
    "open_app",
    "resize_window",
    "restore_window",
]


def _find_window(title: str, fuzzy: bool = True) -> int:
    """Helper to find a window handle by title."""
    hwnds = []

    def enum_windows_callback(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            window_text = win32gui.GetWindowText(hwnd)
            if window_text:
                hwnds.append((hwnd, window_text))

    win32gui.EnumWindows(enum_windows_callback, None)

    if not hwnds:
        return 0

    if not fuzzy:
        for hwnd, text in hwnds:
            if text == title:
                return hwnd
        return 0

    # Fuzzy matching
    titles = [t for _, t in hwnds]
    best_match = process.extractOne(title, titles, scorer=fuzz.partial_ratio)

    if best_match and best_match[1] > 70:
        match_title = best_match[0]
        for hwnd, text in hwnds:
            if text == match_title:
                return hwnd

    return 0


def open_app(name: str) -> CommandResult:
    """Open app by name. Use PowerShell Start-Process, or search Start Menu shortcuts."""
    # Try simple start first
    try:
        env = os.environ.copy()
        env["_APP_NAME_TO_START"] = name
        subprocess.Popen(
            ["powershell", "-NoProfile", "-Command", "Start-Process $env:_APP_NAME_TO_START"],
            env=env
        )
        return CommandResult(
            success=True, output=f"Launched {name}", error="", exit_code=0
        )
    except Exception as e:
        return CommandResult(success=False, output="", error=str(e), exit_code=1)


def launch_executable(
    path: str, args: list[str] | None = None, cwd: str | None = None
) -> CommandResult:
    """Launch by path using subprocess.Popen."""
    cmd = [path]
    if args:
        cmd.extend(args)

    try:
        subprocess.Popen(cmd, cwd=cwd)
        return CommandResult(
            success=True, output=f"Launched {path}", error="", exit_code=0
        )
    except Exception as e:
        return CommandResult(success=False, output="", error=str(e), exit_code=1)


def focus_window(title: str, fuzzy: bool = True) -> bool:
    """Bring window to foreground using win32gui.SetForegroundWindow."""
    hwnd = _find_window(title, fuzzy)
    if not hwnd:
        return False

    try:
        # Sometimes Windows prevents bringing to front unless we attach thread inputs
        foreground_hwnd = win32gui.GetForegroundWindow()
        if foreground_hwnd == hwnd:
            return True

        fg_tid, _ = win32process.GetWindowThreadProcessId(foreground_hwnd)
        our_tid, _ = win32process.GetWindowThreadProcessId(hwnd)

        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
        return True
    except Exception:
        return False


def close_window(title: str) -> bool:
    """Send WM_CLOSE via win32gui.PostMessage."""
    hwnd = _find_window(title, fuzzy=True)
    if not hwnd:
        return False

    try:
        win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
        return True
    except Exception:
        return False


def minimize_window(title: str) -> bool:
    """win32gui.ShowWindow SW_MINIMIZE."""
    hwnd = _find_window(title, fuzzy=True)
    if not hwnd:
        return False

    try:
        win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
        return True
    except Exception:
        return False


def maximize_window(title: str) -> bool:
    """win32gui.ShowWindow SW_MAXIMIZE."""
    hwnd = _find_window(title, fuzzy=True)
    if not hwnd:
        return False

    try:
        win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
        return True
    except Exception:
        return False


def restore_window(title: str) -> bool:
    """win32gui.ShowWindow SW_RESTORE."""
    hwnd = _find_window(title, fuzzy=True)
    if not hwnd:
        return False

    try:
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        return True
    except Exception:
        return False


def resize_window(title: str, width: int, height: int) -> bool:
    """win32gui.MoveWindow."""
    hwnd = _find_window(title, fuzzy=True)
    if not hwnd:
        return False

    try:
        rect = win32gui.GetWindowRect(hwnd)
        x = rect[0]
        y = rect[1]
        win32gui.MoveWindow(hwnd, x, y, width, height, True)
        return True
    except Exception:
        return False


def move_window(title: str, x: int, y: int) -> bool:
    """win32gui.MoveWindow."""
    hwnd = _find_window(title, fuzzy=True)
    if not hwnd:
        return False

    try:
        rect = win32gui.GetWindowRect(hwnd)
        width = rect[2] - rect[0]
        height = rect[3] - rect[1]
        win32gui.MoveWindow(hwnd, x, y, width, height, True)
        return True
    except Exception:
        return False


def list_installed_apps() -> list[dict[str, str]]:
    """Get from Start Menu + registry."""
    from mitchell.windows.system import get_installed_programs

    return get_installed_programs()


def is_app_running(name: str) -> bool:
    """Check via psutil process list."""
    name_lower = name.lower()
    for proc in psutil.process_iter(["name"]):
        try:
            if proc.info["name"] and name_lower in proc.info["name"].lower():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False


# --- filesystem.py ---
"""
File operations module.
"""


__all__ = [
    "copy",
    "delete",
    "exists",
    "file_info",
    "get_size",
    "list_dir",
    "make_dir",
    "move",
    "read_file",
    "search_files",
    "write_file",
]

from mitchell.core.audit import check_path, check_destructive


def file_info(path: str) -> FileInfo:
    """Get information about a file or directory."""
    p = Path(path)
    stat_result = p.stat()
    return FileInfo(
        path=str(p),
        name=p.name,
        is_file=p.is_file(),
        is_dir=p.is_dir(),
        size=stat_result.st_size,
        modified=datetime.fromtimestamp(stat_result.st_mtime),
        created=datetime.fromtimestamp(stat_result.st_ctime),
        accessed=datetime.fromtimestamp(stat_result.st_atime),
    )


def _get_files_recursive(p: Path, include_hidden: bool) -> list[FileInfo]:
    result = []
    for child in p.iterdir():
        if not include_hidden and child.name.startswith("."):
            continue
        result.append(file_info(str(child)))
        if child.is_dir():
            result.extend(_get_files_recursive(child, include_hidden))
    return result


def list_dir(
    path: str, recursive: bool = False, include_hidden: bool = False
) -> DirectoryListing:
    """List directory contents."""
    p = Path(path)
    if not p.is_dir():
        raise NotADirectoryError(f"{path} is not a directory.")

    files = []
    if recursive:
        files = _get_files_recursive(p, include_hidden)
    else:
        for child in p.iterdir():
            if not include_hidden and child.name.startswith("."):
                continue
            files.append(file_info(str(child)))

    return DirectoryListing(path=str(p), files=files)


def read_file(path: str, encoding: str = "utf-8", max_bytes: int = 0) -> str:
    """Read file content."""
    with open(path, "r", encoding=encoding) as f:
        if max_bytes > 0:
            return f.read(max_bytes)
        return f.read()


def write_file(
    path: str, content: str, encoding: str = "utf-8", append: bool = False
) -> FileInfo:
    """Write or append to a file."""
    check_path(path)
    mode = "a" if append else "w"
    with open(path, mode, encoding=encoding) as f:
        f.write(content)
    return file_info(path)


def copy(src: str, dst: str, overwrite: bool = False) -> FileInfo:
    """Copy file or directory."""
    check_path(dst)
    safeguards = get_config().get("safeguards", True)
    if not overwrite and os.path.exists(dst):
        if safeguards:
            raise FileExistsError(
                f"Destination {dst} already exists. Overwrite not permitted by safeguards."
            )

    src_path = Path(src)
    if src_path.is_dir():
        if os.path.exists(dst):
            if overwrite:
                shutil.rmtree(dst)
            else:
                raise FileExistsError(f"Directory {dst} already exists.")
        shutil.copytree(src, dst)
    else:
        shutil.copy2(src, dst)

    return file_info(dst)


def move(src: str, dst: str, overwrite: bool = False) -> FileInfo:
    """Move file or directory."""
    check_path(src)
    check_path(dst)
    safeguards = get_config().get("safeguards", True)
    if not overwrite and os.path.exists(dst):
        if safeguards:
            raise FileExistsError(
                f"Destination {dst} already exists. Overwrite not permitted by safeguards."
            )

    if overwrite and os.path.exists(dst):
        if Path(dst).is_dir():
            shutil.rmtree(dst)
        else:
            os.remove(dst)

    shutil.move(src, dst)
    return file_info(dst)


def delete(path: str, recursive: bool = False, confirm: bool = False) -> bool:
    """Delete a file or directory."""
    check_destructive("apps.delete", confirm)
    check_path(path)
    safeguards = get_config().get("safeguards", True)

    system_dirs = [
        "C:\\Windows",
        "C:\\Program Files",
        "C:\\Program Files (x86)",
        "C:\\Users",
    ]
    abs_path = os.path.abspath(path).lower()

    if safeguards:
        for sys_dir in system_dirs:
            if abs_path.startswith(sys_dir.lower()):
                raise PermissionError(
                    f"Cannot delete {path}: protected system directory."
                )

    p = Path(path)
    if not p.exists():
        return False

    if p.is_dir():
        if not recursive:
            os.rmdir(path)
        else:
            shutil.rmtree(path)
    else:
        os.remove(path)

    return True


def exists(path: str) -> bool:
    """Check if a path exists."""
    return os.path.exists(path)


def search_files(
    pattern: str, path: str = ".", recursive: bool = True
) -> list[FileInfo]:
    """Search for files matching a pattern."""
    p = Path(path)
    if recursive:
        matches = list(p.rglob(pattern))
    else:
        matches = list(p.glob(pattern))

    return [file_info(str(m)) for m in matches if m.exists()]


def make_dir(path: str, parents: bool = True) -> bool:
    """Create a directory."""
    try:
        Path(path).mkdir(parents=parents, exist_ok=True)
        return True
    except Exception:
        return False


def get_size(path: str) -> int:
    """Get the size of a file or directory in bytes."""
    p = Path(path)
    if p.is_file():
        return p.stat().st_size
    elif p.is_dir():
        total = 0
        for dirpath, _, filenames in os.walk(str(p)):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if not os.path.islink(fp):
                    total += os.path.getsize(fp)
        return total
    return 0


# --- scrape.py ---


__all__ = [
    "download_file",
    "get_page_links",
    "get_page_title",
    "scrape_text",
    "scrape_url",
]


def _validate_url(url: str):
    config = get_config()
    if config.safeguards:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"Safeguard blocked non-HTTP/HTTPS URL: {url}")
        if parsed.hostname in ("localhost", "127.0.0.1"):
            raise ValueError(f"Safeguard blocked local network URL: {url}")


def scrape_url(url: str, timeout: int = 10) -> str:
    _validate_url(url)
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    return markdownify.markdownify(resp.text)


def scrape_text(url: str, timeout: int = 10) -> str:
    _validate_url(url)
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    text = re.sub(r"<[^>]+>", " ", resp.text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def get_page_title(url: str, timeout: int = 10) -> str:
    _validate_url(url)
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    match = re.search(
        r"<title[^>]*>(.*?)</title>", resp.text, re.IGNORECASE | re.DOTALL
    )
    if match:
        return match.group(1).strip()
    return ""


def get_page_links(url: str, timeout: int = 10) -> list[dict[str, str]]:
    _validate_url(url)
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    links = []
    pattern = r'<a\s+(?:[^>]*?\s+)?href=["\']([^"\']*)["\'][^>]*>(.*?)</a>'
    matches = re.finditer(pattern, resp.text, re.IGNORECASE | re.DOTALL)
    for match in matches:
        href = match.group(1)
        text = re.sub(r"<[^>]+>", "", match.group(2)).strip()
        links.append({"text": text, "href": href})
    return links


def download_file(url: str, save_path: str, timeout: int = 30) -> FileInfo:
    _validate_url(url)
    resp = requests.get(url, stream=True, timeout=timeout)
    resp.raise_for_status()

    with open(save_path, "wb") as f:
        f.writelines(resp.iter_content(chunk_size=8192))

    size = os.path.getsize(save_path)
    return FileInfo(path=save_path, size=size)
