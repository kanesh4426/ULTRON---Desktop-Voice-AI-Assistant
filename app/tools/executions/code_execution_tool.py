import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict


class CodeExecutionTool:
    name = "code_execution_tool"

    def execute_python_code(self, code: str, timeout_sec: int = 10) -> Dict[str, Any]:
        with tempfile.TemporaryDirectory() as td:
            fp = Path(td) / "snippet.py"
            fp.write_text(code, encoding="utf-8")
            try:
                run = subprocess.run(
                    ["python", str(fp)],
                    capture_output=True,
                    text=True,
                    timeout=timeout_sec,
                )
                return {
                    "success": run.returncode == 0,
                    "stdout": run.stdout,
                    "stderr": run.stderr,
                    "returncode": run.returncode,
                }
            except subprocess.TimeoutExpired:
                return {"success": False, "error": f"Execution timed out after {timeout_sec}s"}
            except Exception as exc:
                return {"success": False, "error": f"Execution failed: {exc}"}

    def execute(self, action: str, **kwargs: Any) -> Dict[str, Any]:
        if action != "execute_python_code":
            return {"success": False, "error": f"Unsupported code action: {action}"}
        return self.execute_python_code(kwargs["code"], kwargs.get("timeout_sec", 10))

