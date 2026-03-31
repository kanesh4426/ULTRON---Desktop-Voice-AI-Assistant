from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.orchestration.workflow_runner import AssistantEngine
from app.utils.config import AssistantConfig


def main() -> None:
    config = AssistantConfig.from_env(str(PROJECT_ROOT))
    engine = AssistantEngine(config)
    result = engine.ingest_documents(str(PROJECT_ROOT / "data"))
    print(result)


if __name__ == "__main__":
    from ultron import main as ultron_main

    sys.exit(ultron_main(["ingest"]))
