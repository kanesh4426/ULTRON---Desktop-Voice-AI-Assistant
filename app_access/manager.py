from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import time
import webbrowser
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

import psutil

try:
    import winapps
except Exception:
    winapps = None

try:
    from AppOpener import close as appopener_close
    from AppOpener import give_appnames as appopener_give_appnames
    from AppOpener import open as appopener_open
except Exception:
    appopener_open = None
    appopener_close = None
    appopener_give_appnames = None

from app.utils.logger import get_logger

from .security import CommandGuard
from .system import SystemCommandRunner


@dataclass
class AppManagerConfig:
    allow_system_commands: bool = False
    command_timeout_sec: int = 10
    require_command_confirmation: bool = True
    allow_web_fallback: bool = True
    prefer_appopener: bool = True


class AppManager:
    """
    Cross-platform app access manager with safe system commands.
    """

    def __init__(self, config: Optional[AppManagerConfig] = None) -> None:
        self.config = config or AppManagerConfig()
        self.logger = get_logger("assistant.app")
        self.current_os = self.get_os()
        self.command_runner = SystemCommandRunner(
            allow_shell=False,
            guard=CommandGuard(require_confirmation=self.config.require_command_confirmation),
        )

        self.web_apps: Dict[str, str] = {
            "youtube": "https://www.youtube.com",
            "whatsapp": "https://web.whatsapp.com",
            "spotify": "https://open.spotify.com",
            "discord": "https://discord.com/app",
            "telegram": "https://web.telegram.org",
            "gmail": "https://mail.google.com",
            "drive": "https://drive.google.com",
            "maps": "https://maps.google.com",
            "facebook": "https://www.facebook.com",
            "instagram": "https://www.instagram.com",
            "twitter": "https://twitter.com",
            "linkedin": "https://www.linkedin.com",
            "netflix": "https://www.netflix.com",
            "amazon": "https://www.amazon.com",
            "github": "https://github.com",
            "outlook": "https://outlook.live.com",
            "office": "https://www.office.com",
            "notion": "https://www.notion.so",
            "zoom": "https://zoom.us",
            "teams": "https://teams.microsoft.com",
        }
        self.app_aliases: Dict[str, str] = {
            "calculator": "calc",
            "paint": "mspaint",
            "sticky notes": "stikynot",
            "sticky": "stikynot",
            "notes": "stikynot",
            "snipping tool": "snippingtool",
            "magnifier": "magnify",
            "on screen keyboard": "osk",
            "character map": "charmap",
            "word pad": "wordpad",
            "device manager": "devmgmt.msc",
            "services": "services.msc",
            "disk management": "diskmgmt.msc",
            "event viewer": "eventvwr",
            "computer management": "compmgmt.msc",
            "system properties": "sysdm.cpl",
            "programs and features": "appwiz.cpl",
            "vs code": "code",
            "visual studio code": "code",
        }
        self.system_app_commands: Dict[str, str] = {
            "notepad": "notepad.exe",
            "calc": "calc.exe",
            "mspaint": "mspaint.exe",
            "paint": "mspaint.exe",
            "cmd": "cmd.exe",
            "powershell": "powershell.exe",
            "taskmgr": "taskmgr.exe",
            "explorer": "explorer.exe",
            "control": "control.exe",
            "settings": "start ms-settings:",
            "snippingtool": "SnippingTool.exe",
            "magnify": "magnify.exe",
            "osk": "osk.exe",
            "charmap": "charmap.exe",
            "wordpad": "wordpad.exe",
            "write": "write.exe",
            "devmgmt.msc": "devmgmt.msc",
            "services.msc": "services.msc",
            "diskmgmt.msc": "diskmgmt.msc",
            "eventvwr": "eventvwr.msc",
            "compmgmt.msc": "compmgmt.msc",
            "sysdm.cpl": "sysdm.cpl",
            "appwiz.cpl": "appwiz.cpl",
        }
        self.installed_index: Dict[str, Dict[str, Any]] = {}
        self.all_known_apps: List[str] = []
        self.refresh_app_index()

    @staticmethod
    def get_os() -> str:
        if sys.platform.startswith("win"):
            return "windows"
        if sys.platform.startswith("darwin"):
            return "mac"
        if sys.platform.startswith("linux"):
            return "linux"
        return "unknown"

    @staticmethod
    def _normalize(text: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()

    @staticmethod
    def _looks_like_url(text: str) -> bool:
        if not text:
            return False
        t = text.strip().lower()
        return t.startswith(("http://", "https://")) or "." in t

    def refresh_app_index(self) -> None:
        self.installed_index = {}

        if self.current_os == "windows" and winapps is not None:
            try:
                for app in winapps.list_installed():
                    raw_name = getattr(app, "name", None) or getattr(app, "display_name", None)
                    if not raw_name:
                        continue
                    key = self._normalize(raw_name)
                    self.installed_index[key] = {
                        "display_name": raw_name,
                        "install_location": getattr(app, "install_location", None),
                        "publisher": getattr(app, "publisher", None),
                        "source": "winapps",
                    }
            except Exception:
                pass

        if appopener_give_appnames is not None:
            try:
                names = appopener_give_appnames()
                if isinstance(names, dict):
                    iterable = names.keys()
                elif isinstance(names, list):
                    iterable = names
                else:
                    iterable = []
                for name in iterable:
                    key = self._normalize(str(name))
                    if key and key not in self.installed_index:
                        self.installed_index[key] = {
                            "display_name": str(name),
                            "install_location": None,
                            "publisher": None,
                            "source": "appopener",
                        }
            except Exception:
                pass

        combined = set(self.web_apps.keys())
        combined.update(self.app_aliases.keys())
        combined.update(self.system_app_commands.keys())
        combined.update(self.installed_index.keys())
        self.all_known_apps = sorted(combined, key=len, reverse=True)

    def list_installed_apps(self) -> Dict[str, Any]:
        self.refresh_app_index()
        apps = [{"key": k, **v} for k, v in self.installed_index.items()]
        return {"success": True, "count": len(apps), "applications": apps}

    def _resolve_alias(self, app_name: str) -> str:
        normalized = self._normalize(app_name)
        return self.app_aliases.get(normalized, normalized)

    def _resolve_installed(self, app_name: str) -> Optional[Dict[str, Any]]:
        normalized = self._normalize(app_name)
        if not normalized:
            return None

        if normalized in self.installed_index:
            return self.installed_index[normalized]

        for key, value in self.installed_index.items():
            if normalized == key or normalized in key or key in normalized:
                return value
        return None

    def is_app_installed_locally(self, app_name: str) -> Dict[str, Any]:
        app_key = self._resolve_alias(app_name)

        if app_key in self.system_app_commands:
            return {
                "installed": True,
                "path": self.system_app_commands[app_key],
                "type": "system",
                "source": "system",
            }

        discovered = self._resolve_installed(app_key)
        if discovered:
            return {
                "installed": True,
                "path": discovered.get("install_location"),
                "type": "desktop",
                "display_name": discovered.get("display_name"),
                "source": discovered.get("source"),
            }

        which_hit = shutil.which(app_key)
        if which_hit:
            return {
                "installed": True,
                "path": which_hit,
                "type": "desktop",
                "source": "path",
            }

        which_exe_hit = shutil.which(f"{app_key}.exe")
        if which_exe_hit:
            return {
                "installed": True,
                "path": which_exe_hit,
                "type": "desktop",
                "source": "path",
            }

        return {"installed": False, "path": None, "type": None, "source": None}

    def has_web_version(self, app_name: str) -> Dict[str, Any]:
        app_key = self._resolve_alias(app_name)
        if app_key in self.web_apps:
            return {"has_web": True, "url": self.web_apps[app_key], "name": app_key}

        for web_name, url in self.web_apps.items():
            if app_key in web_name or web_name in app_key:
                return {"has_web": True, "url": url, "name": web_name}
        return {"has_web": False, "url": None, "name": None}

    def open_website(self, target: str) -> Dict[str, Any]:
        if not target or not target.strip():
            return {"success": False, "error": "Empty website target"}
        key = self._resolve_alias(target.strip())
        if key in self.web_apps:
            url = self.web_apps[key]
        elif self._looks_like_url(key):
            url = key if key.startswith(("http://", "https://")) else f"https://{key}"
        else:
            return {"success": False, "error": f"Unknown website: {target}"}
        webbrowser.open(url)
        return {"success": True, "url": url, "message": f"Opened {url}", "type": "web"}

    def _open_with_appopener(self, app_name: str) -> bool:
        if appopener_open is None:
            return False
        try:
            appopener_open(app_name, match_closest=True, throw_error=True)
            return True
        except TypeError:
            try:
                appopener_open(app_name)
                return True
            except Exception:
                return False
        except Exception:
            return False

    def _close_with_appopener(self, app_name: str) -> bool:
        if appopener_close is None:
            return False
        try:
            appopener_close(app_name, match_closest=True, throw_error=True)
            return True
        except TypeError:
            try:
                appopener_close(app_name)
                return True
            except Exception:
                return False
        except Exception:
            return False

    def _start_system_app(self, app_key: str) -> bool:
        command = self.system_app_commands.get(app_key)
        if not command:
            return False
        try:
            if command.startswith("start "):
                subprocess.run(command, shell=True, check=False, timeout=self.config.command_timeout_sec)
                return True
            if command.endswith(".msc") or command.endswith(".cpl"):
                subprocess.run(f"start {command}", shell=True, check=False, timeout=self.config.command_timeout_sec)
                return True
            subprocess.Popen(command, shell=True)
            return True
        except Exception:
            return False

    def _open_with_subprocess(self, app_name: str, args: Optional[List[str]] = None) -> bool:
        try:
            cmd = [app_name] + (args or [])
            subprocess.Popen(cmd)
            return True
        except Exception:
            return False

    def _open_with_os_default(self, app_name: Optional[str] = None, file_path: Optional[str] = None) -> bool:
        try:
            if self.current_os == "mac":
                cmd = ["open"]
                if app_name:
                    cmd += ["-a", app_name]
                if file_path:
                    cmd.append(file_path)
                if len(cmd) == 1:
                    return False
                subprocess.run(cmd, check=False, timeout=self.config.command_timeout_sec)
                return True
            if self.current_os == "linux":
                if file_path and not app_name:
                    subprocess.run(["xdg-open", file_path], check=False, timeout=self.config.command_timeout_sec)
                    return True
                if app_name and file_path:
                    subprocess.Popen([app_name, file_path])
                    return True
                if app_name:
                    subprocess.Popen([app_name])
                    return True
                if file_path:
                    subprocess.run(["xdg-open", file_path], check=False, timeout=self.config.command_timeout_sec)
                    return True
        except Exception:
            return False
        return False

    def open_application(self, app_name: str) -> Dict[str, Any]:
        app_key = self._resolve_alias(app_name)
        display = app_name.strip() or app_key

        try:
            if self._looks_like_url(app_key):
                return self.open_website(app_key)

            if self.current_os == "windows" and self.config.prefer_appopener and self._open_with_appopener(app_key):
                return {
                    "success": True,
                    "message": f"Opened {display} via AppOpener",
                    "type": "desktop",
                    "method": "appopener",
                }

            if self.current_os == "windows" and self._start_system_app(app_key):
                return {
                    "success": True,
                    "message": f"Opened {display} via system command",
                    "type": "system",
                    "method": "system",
                }

            local = self.is_app_installed_locally(app_key)
            if local.get("installed"):
                path = local.get("path")
                if path and self._open_with_subprocess(path):
                    return {
                        "success": True,
                        "message": f"Opened {display} locally",
                        "type": local.get("type", "desktop"),
                        "method": "local_path",
                        "path": path,
                    }
                if self._open_with_subprocess(app_key):
                    return {
                        "success": True,
                        "message": f"Opened {display} locally",
                        "type": local.get("type", "desktop"),
                        "method": "local_name",
                    }

            if self._open_with_os_default(app_name=app_key):
                return {
                    "success": True,
                    "message": f"Opened {display} via OS default",
                    "type": "desktop",
                    "method": "os_default",
                }

            if self.config.allow_web_fallback:
                web = self.has_web_version(app_key)
                if web["has_web"]:
                    webbrowser.open(web["url"])
                    return {
                        "success": True,
                        "message": f"Opened {web['name']} web version",
                        "type": "web",
                        "method": "web",
                        "url": web["url"],
                    }

            return {
                "success": False,
                "error": f"Could not open '{display}'. App not resolved by appopener/system/local/web fallback.",
            }
        except Exception as exc:
            return {"success": False, "error": f"Failed to open {display}: {exc}"}

    @staticmethod
    def _process_name_candidates(app_name: str) -> Set[str]:
        key = re.sub(r"[^a-z0-9]+", "", (app_name or "").lower())
        candidates = {
            key,
            f"{key}.exe",
            app_name.lower(),
            f"{app_name.lower()}.exe",
        }

        special = {
            "calc": {"calculator.exe", "calc.exe"},
            "mspaint": {"mspaint.exe"},
            "paint": {"mspaint.exe"},
            "edge": {"msedge.exe"},
            "code": {"code.exe"},
        }
        candidates.update(special.get(key, set()))
        return {c for c in candidates if c}

    def close_application(self, app_name: str) -> Dict[str, Any]:
        app_key = self._resolve_alias(app_name)

        try:
            if self.current_os == "windows" and self._close_with_appopener(app_key):
                return {
                    "success": True,
                    "message": f"Closed {app_name} via AppOpener",
                    "method": "appopener",
                }

            candidates = self._process_name_candidates(app_key)
            closed = 0

            for proc in psutil.process_iter(["name", "exe"]):
                try:
                    name = (proc.info.get("name") or "").lower()
                    exe = os.path.basename(proc.info.get("exe") or "").lower()
                    if name in candidates or exe in candidates:
                        proc.terminate()
                        closed += 1
                        time.sleep(0.05)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            if closed > 0:
                return {"success": True, "message": f"Closed {closed} process(es) for {app_name}"}
            return {"success": False, "error": f"No running instances found for {app_name}"}
        except Exception as exc:
            return {"success": False, "error": f"Failed to close {app_name}: {exc}"}

    def is_application_running(self, app_name: str) -> Dict[str, Any]:
        app_key = self._resolve_alias(app_name)
        candidates = self._process_name_candidates(app_key)

        try:
            running: List[Dict[str, Any]] = []
            for proc in psutil.process_iter(["pid", "name", "exe"]):
                try:
                    name = (proc.info.get("name") or "").lower()
                    exe = os.path.basename(proc.info.get("exe") or "").lower()
                    if name in candidates or exe in candidates:
                        running.append(
                            {
                                "pid": proc.info.get("pid"),
                                "name": proc.info.get("name"),
                                "exe": proc.info.get("exe"),
                            }
                        )
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            return {
                "success": True,
                "running": len(running) > 0,
                "process_count": len(running),
                "processes": running,
            }
        except Exception as exc:
            return {"success": False, "error": f"Failed to check {app_name}: {exc}"}

    def list_running_applications(self, limit: int = 200) -> Dict[str, Any]:
        try:
            apps: List[Dict[str, Any]] = []
            for proc in psutil.process_iter(["pid", "name", "exe"]):
                try:
                    apps.append(
                        {
                            "pid": proc.info.get("pid"),
                            "name": proc.info.get("name"),
                            "exe": proc.info.get("exe"),
                        }
                    )
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return {"success": True, "count": len(apps), "applications": apps[:limit]}
        except Exception as exc:
            return {"success": False, "error": f"Failed to list running apps: {exc}"}

    def _extract_app_name(self, command: str) -> Optional[str]:
        cleaned = self._normalize(command)
        if not cleaned:
            return None

        action_words = {
            "open",
            "close",
            "start",
            "launch",
            "run",
            "stop",
            "quit",
            "exit",
            "please",
            "can",
            "you",
            "the",
        }
        words = [w for w in cleaned.split() if w not in action_words]
        if not words:
            return None

        joined = " ".join(words)
        for candidate in self.all_known_apps:
            if candidate and (candidate == joined or candidate in joined):
                return candidate

        return words[0]

    @staticmethod
    def _determine_action(command: str) -> str:
        text = (command or "").lower()
        close_words = ("close", "quit", "exit", "stop", "kill", "terminate")
        for token in close_words:
            if token in text:
                return "close"
        return "open"

    def process_command(self, command: str) -> Dict[str, Any]:
        if not command or not command.strip():
            return {"success": False, "error": "Empty command"}

        action = self._determine_action(command)
        app_name = self._extract_app_name(command)
        if not app_name:
            return {"success": False, "error": f"Could not identify app in '{command}'"}

        if action == "close":
            return self.close_application(app_name)
        return self.open_application(app_name)

    def run_system_command(
        self,
        command: str,
        *,
        timeout_sec: Optional[int] = None,
        confirm: bool = False,
    ) -> Dict[str, Any]:
        if not self.config.allow_system_commands:
            return {"success": False, "error": "System commands are disabled by configuration"}
        return self.command_runner.run(
            command,
            timeout_sec=timeout_sec or self.config.command_timeout_sec,
            confirm=confirm,
        )

    def get_app_info(self, app_name: str) -> Dict[str, Any]:
        local = self.is_app_installed_locally(app_name)
        web = self.has_web_version(app_name)
        running = self.is_application_running(app_name)

        methods: List[str] = []
        if local.get("installed"):
            methods.append("local")
        if web.get("has_web"):
            methods.append("web")

        return {
            "app_name": app_name,
            "local_installation": local,
            "web_version": web,
            "running_status": running,
            "available_methods": methods,
            "supports_appopener": appopener_open is not None,
            "supports_winapps": winapps is not None,
        }

