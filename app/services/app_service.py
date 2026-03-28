import os
import re
import shlex
import shutil
import subprocess
import sys
import time
import webbrowser
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


class AppController:
    """
    Fresh Windows-first app controller.
    Primary app access:
    1) AppOpener (open/close)
    2) winapps (installed discovery)
    3) system command/process fallback
    4) web fallback
    """

    def __init__(self) -> None:
        self.current_os = self.get_os()

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
                subprocess.run(command, shell=True, check=False, timeout=10)
                return True
            if command.endswith(".msc") or command.endswith(".cpl"):
                subprocess.run(f"start {command}", shell=True, check=False, timeout=10)
                return True
            subprocess.Popen(command, shell=True)
            return True
        except Exception:
            return False

    def _open_with_subprocess(self, app_name: str) -> bool:
        try:
            subprocess.Popen([app_name])
            return True
        except Exception:
            return False

    def open_application_smart(self, app_name: str) -> Dict[str, Any]:
        app_key = self._resolve_alias(app_name)
        display = app_name.strip() or app_key

        try:
            if self.current_os == "windows" and self._open_with_appopener(app_key):
                return {
                    "success": True,
                    "message": f"Opened {display} via AppOpener",
                    "type": "desktop",
                    "method": "appopener",
                }

            if self._start_system_app(app_key):
                return {
                    "success": True,
                    "message": f"Opened {display} via system command",
                    "type": "system",
                    "method": "system",
                }

            local = self.is_app_installed_locally(app_key)
            if local["installed"]:
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
                "error": f"Could not open '{display}'. App not resolved by AppOpener/winapps/system/web fallback.",
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
                        time.sleep(0.1)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            if closed > 0:
                return {"success": True, "message": f"Closed {closed} process(es) for {app_name}"}
            return {"success": False, "error": f"No running instances found for {app_name}"}
        except Exception as exc:
            return {"success": False, "error": f"Failed to close {app_name}: {exc}"}

    def is_app_running(self, app_name: str) -> Dict[str, Any]:
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
        return self.open_application_smart(app_name)

    def get_app_info(self, app_name: str) -> Dict[str, Any]:
        local = self.is_app_installed_locally(app_name)
        web = self.has_web_version(app_name)
        running = self.is_app_running(app_name)

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


def open_app(app_name: str) -> Dict[str, Any]:
    controller = AppController()
    return controller.open_application_smart(app_name)


def close_app(app_name: str) -> Dict[str, Any]:
    controller = AppController()
    return controller.close_application(app_name)


def process_command(command: str) -> Dict[str, Any]:
    controller = AppController()
    return controller.process_command(command)


def is_app_installed(app_name: str) -> Dict[str, Any]:
    controller = AppController()
    return controller.is_app_installed_locally(app_name)


def get_app_info(app_name: str) -> Dict[str, Any]:
    controller = AppController()
    return controller.get_app_info(app_name)
