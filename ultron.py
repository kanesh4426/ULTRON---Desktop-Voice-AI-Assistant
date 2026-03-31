from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable, Dict, List, Tuple


PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _print_help(commands: Dict[str, Tuple[str, Callable[[List[str]], int]]]) -> None:
    print("Ultron unified entrypoint")
    print("")
    print("Usage:")
    print("  python ultron.py <command> [args]")
    print("")
    print("Commands:")
    for name, (desc, _) in commands.items():
        print(f"  {name:<14} {desc}")


def _run_ui(_: List[str]) -> int:
    from app.main import main as ui_main

    return int(ui_main() or 0)


def _run_pyside_ui(_: List[str]) -> int:
    from ui.pyside.main_window import run_ultron_pyside

    return int(run_ultron_pyside() or 0)


def _run_ingest(_: List[str]) -> int:
    from scripts.ingest_docs import main as ingest_main

    ingest_main()
    return 0


def _run_example(_: List[str]) -> int:
    from examples.example_usage import main as example_main

    example_main()
    return 0


def _run_pyside_demo(_: List[str]) -> int:
    from examples.pyside_integration_example import main as demo_main

    demo_main()
    return 0


def _run_automation(args: List[str]) -> int:
    import app.services.automation_service as automation

    original_argv = sys.argv
    sys.argv = ["automation_service.py"] + list(args)
    try:
        automation.main()
        return 0
    finally:
        sys.argv = original_argv


def _run_tts_test(_: List[str]) -> int:
    from app.services.tts import main as tts_main

    tts_main()
    return 0


def _run_image_ui(_: List[str]) -> int:
    from app.services.image_service import main as image_main

    image_main()
    return 0


def _run_debugger(_: List[str]) -> int:
    from app.agents.roles.code_debugger import interactive_debugger

    interactive_debugger()
    return 0


COMMANDS: Dict[str, Tuple[str, Callable[[List[str]], int]]] = {
    "ui": ("Launch the main desktop UI", _run_ui),
    "pyside-ui": ("Launch the PySide UI directly", _run_pyside_ui),
    "ingest": ("Ingest documents into the RAG index", _run_ingest),
    "example": ("Run the CLI usage example", _run_example),
    "pyside-demo": ("Run the streaming PySide demo", _run_pyside_demo),
    "automation": ("Run automation service CLI", _run_automation),
    "tts-test": ("Run the TTS self-test", _run_tts_test),
    "image-ui": ("Launch the image generator UI", _run_image_ui),
    "debugger": ("Launch interactive code debugger", _run_debugger),
}


def main(argv: List[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        return _run_ui([])

    if args[0] in {"-h", "--help", "help"}:
        _print_help(COMMANDS)
        return 0

    command = args[0]
    handler = COMMANDS.get(command)
    if not handler:
        print(f"Unknown command: {command}")
        _print_help(COMMANDS)
        return 1

    return handler[1](args[1:])


if __name__ == "__main__":
    sys.exit(main())
