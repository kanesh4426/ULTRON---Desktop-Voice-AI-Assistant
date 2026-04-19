import sys
import os
from PySide6.QtCore import QObject, Slot, Qt, QUrl
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel

class Bridge(QObject):
    """
    Bidirectional communication bridge between Python and React.
    Exposed to React via QWebChannel.
    """
    def __init__(self, window):
        super().__init__()
        self.window = window

    @Slot(str, result=str)
    def process_message(self, message: str) -> str:
        print(f"[PyBridge] Received message from React: {message}")
        # TODO: Implement your ULTRON AI logic here
        return f"ULTRON Backend processed: '{message}'"

    @Slot(int, int)
    def move_window(self, global_x: int, global_y: int):
        """
        Allows React to drag the frameless desktop window.
        """
        if self.window:
            self.window.move(global_x, global_y)

class FramelessWebWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ULTRON AI Wrapper")
        self.resize(1024, 768)

        # 1. Configure the frameless and translucent window
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowSystemMenuHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        # 2. Setup the WebEngineView
        self.view = QWebEngineView(self)
        self.view.page().setBackgroundColor(Qt.transparent)
        self.setCentralWidget(self.view)

        # 3. Setup QWebChannel and Register the Bridge
        self.channel = QWebChannel()
        self.bridge = Bridge(self)
        self.channel.registerObject("pyBridge", self.bridge)
        self.view.page().setWebChannel(self.channel)

        # 4. Load the existing React production build
        # Calculate the expected path to your React app's index.html
        script_dir = os.path.dirname(__file__)
        dist_path = os.path.abspath(os.path.join(script_dir, "..", "web", "ultron-react", "build", "index.html"))
        print(f"[Python] Expected React build path: {dist_path}")
        if os.path.exists(dist_path):
            self.view.setUrl(QUrl.fromLocalFile(dist_path))
        else:
            print(f"Error: React build not found at {dist_path}")
            self.view.setHtml(f"<h1 style='color: white;'>Build missing</h1><p style='color: white;'>Could not find: {dist_path}</p>")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FramelessWebWindow()
    window.show()
    sys.exit(app.exec())