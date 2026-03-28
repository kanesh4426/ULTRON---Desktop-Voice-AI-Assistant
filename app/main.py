import logging
import os
import sys
import traceback

# Ensure project root is on sys.path before importing app packages.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from PySide6.QtWidgets import QApplication

from app.orchestration.app_controller import AppController
from ui.pyside.main_window import UltronController, UltronMainWindow


class UnicodeStreamHandler(logging.StreamHandler):
    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stream
            stream.write(msg + self.terminator)
            self.flush()
        except UnicodeEncodeError:
            msg = self.format(record).encode("utf-8", errors="replace").decode("utf-8")
            stream = self.stream
            stream.write(msg + self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("data/logs/ultron.log", encoding="utf-8"),
        UnicodeStreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger(__name__)


def main() -> int:
    """
    Entry point for the PySide6 ULTRON desktop application.
    """
    logger.info("Starting ULTRON PySide6 application...")

    app = QApplication.instance() or QApplication(sys.argv)
    controller = UltronController(app_controller=AppController())
    window = UltronMainWindow(controller)
    window.show()

    try:
        return app.exec()
    except Exception as exc:
        logger.error("Unexpected error in Qt event loop: %s", exc)
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    from ultron import main as ultron_main

    sys.exit(ultron_main(["ui"]))
