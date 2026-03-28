import sys
from threading import Thread
from pathlib import Path

from PySide6.QtWidgets import QApplication, QHBoxLayout, QLineEdit, QPushButton, QTextEdit, QVBoxLayout, QWidget

from app.orchestration.workflow_runner import AssistantEngine
from app.models.generation_request import GenerationRequest
from app.utils.config import AssistantConfig

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class AssistantWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Assistant Streaming Demo")
        self.resize(800, 500)

        self.output = QTextEdit(self)
        self.output.setReadOnly(True)
        self.input = QLineEdit(self)
        self.send_btn = QPushButton("Send", self)

        row = QHBoxLayout()
        row.addWidget(self.input, 1)
        row.addWidget(self.send_btn)

        root = QVBoxLayout(self)
        root.addWidget(self.output, 1)
        root.addLayout(row)

        self.engine = AssistantEngine(AssistantConfig.from_env(str(PROJECT_ROOT)))
        self.send_btn.clicked.connect(self.on_send)

    def on_send(self):
        text = self.input.text().strip()
        if not text:
            return
        self.input.clear()
        self.output.append(f"\nYou: {text}\nAI: ")

        def worker():
            req = GenerationRequest(user_input=text, stream=True)

            def on_token(tok: str):
                # Minimal UI update pattern; for larger apps use Qt signals.
                self.output.insertPlainText(tok)

            self.engine.generate_stream_sync(req, on_token=on_token)

        Thread(target=worker, daemon=True).start()


def main():
    app = QApplication(sys.argv)
    w = AssistantWidget()
    w.show()
    return app.exec()


if __name__ == "__main__":
    from ultron import main as ultron_main

    sys.exit(ultron_main(["pyside-demo"]))
