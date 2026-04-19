from __future__ import annotations

import os
import sys
# Set the remote debugging port *before* any other Qt modules are imported.
# This is crucial to ensure the setting is applied correctly.
os.environ["QTWEBENGINE_REMOTE_DEBUGGING"] = "9222"

import datetime
from typing import List, Dict, Any, Optional

from PySide6.QtCore import Qt, QObject, Slot, QUrl
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QListWidget,
    QListWidgetItem,
    QLineEdit,
    QPushButton,
    QLabel,
    QScrollArea,
    QFrame,
    QSizePolicy,
    QSpacerItem,
)
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView

from app.orchestration.app_controller import AppController
from app.services.tts import SpeakJARVIS as SpeakUltron
from app.services.stt import recognize_speech


class UltronController:
    """
    Thin adapter around AppController for use from the PySide6 UI.
    """

    def __init__(self, app_controller: Optional[AppController] = None) -> None:
        self.app: AppController = app_controller or AppController()

    # --- Chat management -------------------------------------------------

    def load_chats(self) -> List[Dict[str, Any]]:
        try:
            return self.app.load_chats() or []
        except Exception:
            return []

    def switch_chat(self, chat_id: int) -> List[Dict[str, Any]]:
        try:
            return self.app.switch_chat(chat_id)
        except Exception:
            return []

    def create_chat(self, name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        try:
            result = self.app.create_chat(name)
            return result if isinstance(result, dict) else None
        except Exception:
            return None

    def rename_chat(self, chat_id: int, new_name: str) -> bool:
        try:
            return self.app.rename_chat(chat_id, new_name)
        except Exception:
            return False

    def delete_chat(self, chat_id: int) -> bool:
        try:
            return self.app.delete_chat(chat_id)
        except Exception:
            return False

    def get_current_chat_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        try:
            return self.app.get_current_chat_history(limit=limit) or []
        except Exception:
            return []

    # --- Messaging / AI --------------------------------------------------

    def send_user_message(self, text: str) -> Dict[str, Any]:
        """
        Call the main assistant entrypoint and return its response dict.
        """
        return self.app.send_user_message(text)

    def rate_response(self, rating: int, conversation_id: Optional[int] = None) -> bool:
        """
        Map 1–5 star rating to RL reward and forward to assistant.
        """
        try:
            reward = (float(rating) - 3.0) / 2.0
            return self.app.rate_response(rating, conversation_id)
        except Exception:
            return False

    # --- Health / connection ---------------------------------------------

    def test_connection(self) -> Dict[str, Any]:
        return self.app.test_connection()


class PyBridge(QObject):
    """
    Bridge object exposed to the React frontend via QWebChannel.
    """
    def __init__(self, controller: UltronController, window: QMainWindow, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.window = window

    @Slot(int, int)
    def move_window(self, x: int, y: int):
        # Move window based on React global drag calculation
        self.window.move(x, y)

    @Slot(str, result=str)
    def process_message(self, message: str) -> str:
        if message == "Status Check from React!":
            health = self.controller.test_connection()
            ok = health.get("ok", False)
            return f"Connection OK: {health.get('message', '')}" if ok else "Connection Failed"
        
        try:
            response = self.controller.send_user_message(message)
            return str(response.get("response", "No response content"))
        except Exception as e:
            return f"Error: {str(e)}"


class ReactMainWindow(QMainWindow):
    """
    Window hosting the React UI via QWebEngineView.
    """
    def __init__(self, controller: UltronController, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.controller = controller

        self.setWindowTitle("U.L.T.R.O.N Assistant")
        self.resize(1100, 720)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self.web_view = QWebEngineView(self)
        self.web_view.page().setBackgroundColor(Qt.transparent)
        self.setCentralWidget(self.web_view)

        self.channel = QWebChannel()
        self.bridge = PyBridge(self.controller, self)
        self.channel.registerObject("pyBridge", self.bridge)
        self.web_view.page().setWebChannel(self.channel)

        # --- Load React App ---
        # This logic helps debug the common "white screen" issue.

        # First, let's try the 'dist' folder, which is a common standard.
        react_path = os.path.abspath("web/ultron-react/dist/index.html")

        if not os.path.exists(react_path):
            # If 'dist' doesn't exist, check for 'build', another common standard.
            build_path = os.path.abspath("web/ultron-react/build/index.html")
            if os.path.exists(build_path):
                react_path = build_path
            else:
                print(f"[ERROR] React build not found in 'dist' or 'build' directories.")
                error_html = f"<div style='background-color:#111; color:white; padding:2em; font-family:sans-serif;'><h1>React App Not Found</h1><p>Looked for <code>{react_path}</code> and <code>{build_path}</code>.</p><p>Please build the React app first (e.g., 'npm run build').</p></div>"
                self.web_view.setHtml(error_html)
                return

        print(f"[INFO] Loading React app from: {react_path}")
        self.web_view.load(QUrl.fromLocalFile(react_path))


class MessageWidget(QFrame):
    """
    Single chat message bubble with basic styling based on sender/content_type.
    """

    def __init__(
        self,
        sender: str,
        text: str,
        content_type: str = "normal",
        timestamp: Optional[str] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)

        self.setFrameShape(QFrame.NoFrame)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 4, 0, 4)

        bubble = QFrame(self)
        bubble_layout = QVBoxLayout(bubble)
        bubble_layout.setContentsMargins(12, 8, 12, 8)
        bubble_layout.setSpacing(4)

        header_layout = QHBoxLayout()
        sender_label = QLabel("You" if sender == "user" else "ULTRON", bubble)
        sender_label.setObjectName("senderLabel")

        type_label = QLabel(content_type.upper(), bubble)
        type_label.setObjectName("contentTypeBadge")

        ts = timestamp
        if not ts:
            ts = datetime.datetime.now().isoformat(timespec="minutes")
        time_label = QLabel(ts, bubble)
        time_label.setObjectName("timestampLabel")

        header_layout.addWidget(sender_label)
        header_layout.addStretch()
        if content_type != "normal":
            header_layout.addWidget(type_label)
        header_layout.addWidget(time_label)

        body_label = QLabel(text, bubble)
        body_label.setWordWrap(True)
        body_label.setTextInteractionFlags(
            Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse
        )

        bubble_layout.addLayout(header_layout)
        bubble_layout.addWidget(body_label)

        outer_layout.addWidget(bubble, alignment=self._alignment_for_sender(sender))

        # Apply a style class hint
        base_class = "messageBubble"
        extra_class = ""
        if sender == "user":
            extra_class = " userMessage"
        else:
            extra_class = " assistantMessage"
        if content_type in ("code", "content", "technical", "system"):
            extra_class += f" {content_type}Message"

        bubble.setProperty("class", base_class + extra_class)

    @staticmethod
    def _alignment_for_sender(sender: str) -> Qt.AlignmentFlag:
        return Qt.AlignRight if sender == "user" else Qt.AlignLeft


class MessagesView(QWidget):
    """
    Scrollable container for MessageWidget instances.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        self._scroll = QScrollArea(self)
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._content = QWidget(self._scroll)
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(8, 8, 8, 8)
        self._content_layout.setSpacing(4)
        self._content_layout.addItem(
            QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding)
        )

        self._scroll.setWidget(self._content)
        root_layout.addWidget(self._scroll)

    def clear_messages(self) -> None:
        while self._content_layout.count() > 1:
            item = self._content_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def add_message(
        self,
        sender: str,
        text: str,
        content_type: str = "normal",
        timestamp: Optional[str] = None,
    ) -> None:
        widget = MessageWidget(sender, text, content_type, timestamp, self._content)
        # Insert before the stretch spacer
        index = self._content_layout.count() - 1
        self._content_layout.insertWidget(index, widget)
        self._scroll_to_bottom()

    def _scroll_to_bottom(self) -> None:
        vs = self._scroll.verticalScrollBar()
        vs.setValue(vs.maximum())


class UltronMainWindow(QMainWindow):
    """
    Main desktop window hosting the ULTRON chat UI.
    """

    def __init__(self, controller: UltronController, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.controller = controller
        self.current_chat_id: Optional[int] = None

        self.setWindowTitle("U.L.T.R.O.N Assistant")
        self.resize(1100, 720)

        self._build_ui()
        self._apply_styles()
        self._load_initial_data()

    # --- UI construction -------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Sidebar
        sidebar = QFrame(central)
        sidebar.setObjectName("sidebar")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(12, 12, 12, 12)
        sidebar_layout.setSpacing(10)

        header_row = QHBoxLayout()
        icon_label = QLabel("🤖", sidebar)
        icon_label.setObjectName("sidebarIcon")
        title_label = QLabel("Chat Sections", sidebar)
        title_label.setObjectName("sidebarTitle")
        header_row.addWidget(icon_label)
        header_row.addWidget(title_label)
        header_row.addStretch()
        sidebar_layout.addLayout(header_row)

        self.chat_search = QLineEdit(sidebar)
        self.chat_search.setPlaceholderText("Search chats...")
        sidebar_layout.addWidget(self.chat_search)

        self.chat_list = QListWidget(sidebar)
        sidebar_layout.addWidget(self.chat_list, 1)

        self.new_chat_btn = QPushButton("+ New Chat", sidebar)
        self.new_chat_btn.setObjectName("newChatButton")
        sidebar_layout.addWidget(self.new_chat_btn)

        # Main panel
        main_panel = QFrame(central)
        main_panel.setObjectName("mainPanel")
        main_panel_layout = QVBoxLayout(main_panel)
        main_panel_layout.setContentsMargins(12, 12, 12, 12)
        main_panel_layout.setSpacing(10)

        # Header
        header = QFrame(main_panel)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)

        self.status_indicator = QLabel("", header)
        self.status_indicator.setObjectName("statusIndicator")
        self.status_indicator.setFixedSize(12, 12)

        self.chat_title = QLabel("U.L.T.R.O.N", header)
        self.chat_title.setObjectName("chatTitle")

        header_layout.addWidget(self.status_indicator)
        header_layout.addSpacing(8)
        header_layout.addWidget(self.chat_title)
        header_layout.addStretch()

        self.health_label = QLabel("", header)
        self.health_label.setObjectName("healthLabel")
        header_layout.addWidget(self.health_label)

        main_panel_layout.addWidget(header)

        # Messages
        self.messages_view = MessagesView(main_panel)
        main_panel_layout.addWidget(self.messages_view, 1)

        # Input row
        input_row = QFrame(main_panel)
        input_layout = QHBoxLayout(input_row)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(8)

        self.input_edit = QLineEdit(input_row)
        self.input_edit.setPlaceholderText("Type a message...")
        input_layout.addWidget(self.input_edit, 1)

        self.voice_btn = QPushButton("🎤", input_row)
        self.voice_btn.setToolTip("Voice input")
        self.voice_btn.setFixedWidth(40)
        input_layout.addWidget(self.voice_btn)

        self.send_btn = QPushButton("➤", input_row)
        self.send_btn.setToolTip("Send")
        self.send_btn.setFixedWidth(40)
        self.send_btn.setDefault(True)
        input_layout.addWidget(self.send_btn)

        main_panel_layout.addWidget(input_row)

        # Assemble
        main_layout.addWidget(sidebar, 0)
        main_layout.addWidget(main_panel, 1)

        # Wire events
        self.chat_list.itemClicked.connect(self._on_chat_clicked)
        self.new_chat_btn.clicked.connect(self._on_new_chat)
        self.chat_search.textChanged.connect(self._on_search_chats)

        self.send_btn.clicked.connect(self._on_send_clicked)
        self.input_edit.returnPressed.connect(self._on_send_clicked)
        self.voice_btn.clicked.connect(self._on_voice_clicked)

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow {
                background-color: #0f2027;
            }
            #sidebar {
                background-color: rgba(15, 32, 39, 0.95);
                border-radius: 10px;
            }
            #mainPanel {
                background-color: rgba(255, 255, 255, 0.05);
                border-radius: 10px;
            }
            #sidebarIcon {
                font-size: 22px;
            }
            #sidebarTitle {
                font-size: 16px;
                font-weight: 600;
                color: #ffffff;
            }
            #newChatButton {
                padding: 8px 12px;
                border-radius: 8px;
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00c6ff, stop:1 #0072ff);
                color: white;
                font-weight: 600;
                border: none;
            }
            #newChatButton:hover {
                background-color: #00c6ff;
            }
            QListWidget {
                background: transparent;
                border: none;
                color: #ffffff;
            }
            QListWidget::item {
                padding: 6px;
                border-radius: 6px;
            }
            QListWidget::item:selected {
                background-color: rgba(0, 198, 255, 0.3);
            }
            #statusIndicator {
                border-radius: 6px;
                background-color: #ffcc00;
            }
            #chatTitle {
                font-size: 20px;
                font-weight: 600;
                color: #ffffff;
            }
            #healthLabel {
                color: #cccccc;
                font-size: 11px;
            }
            QLineEdit {
                background-color: rgba(255, 255, 255, 0.08);
                border-radius: 18px;
                padding: 8px 12px;
                border: 1px solid rgba(255, 255, 255, 0.15);
                color: #ffffff;
            }
            QPushButton {
                background-color: rgba(255, 255, 255, 0.12);
                border-radius: 18px;
                border: none;
                color: #ffffff;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.22);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.28);
            }
            /* Message bubbles */
            QWidget[class~="messageBubble"] {
                background-color: rgba(255, 255, 255, 0.10);
                border-radius: 14px;
            }
            QWidget[class~="messageBubble"][class~="userMessage"] {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00c6ff, stop:1 #0072ff);
            }
            QWidget[class~="messageBubble"][class~="assistantMessage"] {
                background-color: rgba(255, 255, 255, 0.10);
            }
            QWidget[class~="messageBubble"][class~="codeMessage"] {
                border-left: 4px solid #007acc;
            }
            QWidget[class~="messageBubble"][class~="contentMessage"] {
                border-left: 4px solid #28a745;
            }
            QWidget[class~="messageBubble"][class~="technicalMessage"] {
                border-left: 4px solid #ffc107;
            }
            QWidget[class~="messageBubble"][class~="systemMessage"] {
                border-left: 4px solid #6c757d;
            }
            #senderLabel {
                font-size: 11px;
                color: #dddddd;
            }
            #contentTypeBadge {
                padding: 2px 6px;
                border-radius: 10px;
                font-size: 9px;
                color: #ffffff;
                background-color: #6c757d;
            }
            #timestampLabel {
                font-size: 9px;
                color: #bbbbbb;
            }
            """
        )

    # --- Data / events ---------------------------------------------------

    def _load_initial_data(self) -> None:
        chats = self.controller.load_chats()
        self._populate_chat_list(chats)

        # Choose first chat if available
        if chats:
            first = chats[0]
            self.current_chat_id = first.get("id")
            self.chat_title.setText(first.get("name", "Chat"))
            messages = self.controller.get_current_chat_history()
            self._render_messages(messages)
        else:
            self._show_welcome()

        # Connection indicator
        health = self.controller.test_connection()
        self._update_health_status(health)

    def _populate_chat_list(self, chats: List[Dict[str, Any]]) -> None:
        self.chat_list.clear()
        for chat in chats:
            item = QListWidgetItem(chat.get("name", "Chat"))
            item.setData(Qt.UserRole, chat.get("id"))
            self.chat_list.addItem(item)

    def _render_messages(self, messages: List[Dict[str, Any]]) -> None:
        self.messages_view.clear_messages()
        if not messages:
            self._show_welcome()
            return

        for msg in messages:
            sender = msg.get("sender", "assistant")
            text = msg.get("text", "")
            ctype = msg.get("content_type", "normal")
            ts = msg.get("timestamp")
            self.messages_view.add_message(sender, text, ctype, ts)

    def _show_welcome(self) -> None:
        self.messages_view.clear_messages()
        self.messages_view.add_message(
            "assistant",
            "U.L.T.R.O.N is online and ready. Start typing to begin a conversation.",
            "system",
        )

    def _update_health_status(self, health: Dict[str, Any]) -> None:
        ok = bool(health.get("ok"))
        message = health.get("message", "")
        if ok:
            self.status_indicator.setStyleSheet("background-color: #00ff88;")
        else:
            self.status_indicator.setStyleSheet("background-color: #ff4444;")
        self.health_label.setText(message)

    # --- Slots -----------------------------------------------------------

    def _on_chat_clicked(self, item: QListWidgetItem) -> None:
        chat_id = item.data(Qt.UserRole)
        if chat_id is None:
            return
        self.current_chat_id = chat_id
        self.chat_title.setText(item.text())
        messages = self.controller.switch_chat(chat_id)
        self._render_messages(messages)

    def _on_new_chat(self) -> None:
        result = self.controller.create_chat()
        if not result or not result.get("success"):
            self.messages_view.add_message(
                "assistant",
                "Failed to create new chat.",
                "system",
            )
            return

        chats = self.controller.load_chats()
        self._populate_chat_list(chats)

        self.current_chat_id = result.get("chat_id")
        self.chat_title.setText(result.get("chat_name", "Chat"))
        self.messages_view.clear_messages()
        self._show_welcome()

    def _on_search_chats(self, text: str) -> None:
        query = text.lower().strip()
        for i in range(self.chat_list.count()):
            item = self.chat_list.item(i)
            name = item.text().lower()
            item.setHidden(query not in name)

    def _on_send_clicked(self) -> None:
        text = self.input_edit.text().strip()
        if not text:
            return

        # Show user message immediately
        self.messages_view.add_message("user", text, "normal")
        self.input_edit.clear()

        try:
            response = self.controller.send_user_message(text)
        except Exception as exc:
            self.messages_view.add_message(
                "assistant",
                f"Error processing your request: {exc}",
                "system",
            )
            return

        if response and response.get("response"):
            ctype = response.get("content_type", "normal")
            self.messages_view.add_message(
                "assistant",
                response.get("response", ""),
                ctype,
            )

            # Basic TTS support: speak short non-code responses
            if response.get("should_speak", True) and ctype != "code":
                try:
                    SpeakUltron(response.get("response", ""))
                except Exception:
                    pass

    def _on_voice_clicked(self) -> None:
        """
        Simple STT integration: capture one utterance and put into input box.
        """
        self.messages_view.add_message(
            "assistant",
            "Listening for a short voice command...",
            "system",
        )
        try:
            text = recognize_speech()
        except Exception as exc:
            self.messages_view.add_message(
                "assistant",
                f"Voice input error: {exc}",
                "system",
            )
            return

        if not text:
            self.messages_view.add_message(
                "assistant",
                "I couldn't hear anything. Please try again.",
                "system",
            )
            return

        self.input_edit.setText(text)
        self.input_edit.setFocus()


def run_ultron_pyside() -> int:
    """
    Convenience entry point to start the PySide6 ULTRON UI.
    """
    app = QApplication.instance() or QApplication(sys.argv)
    controller = UltronController()
    window = ReactMainWindow(controller) # or UltronMainWindow(controller)
    window.show()
    return app.exec()


if __name__ == "__main__":
    from ultron import main as ultron_main

    sys.exit(ultron_main(["pyside-ui"]))
