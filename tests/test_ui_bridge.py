import os
import sys
from pathlib import Path

# Ensure the root directory is in the sys path
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from PySide6.QtCore import QCoreApplication
from unittest.mock import MagicMock
from app.run_wrapper import Bridge

def test_bridge_wiring():
    print("=========================================")
    print("🔌 REACT-PYTHON BRIDGE WIRING TEST 🔌")
    print("=========================================\n")
    
    # A QCoreApplication instance is required to instantiate PySide6 QObjects
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication(sys.argv)
        
    print("Initializing Mock Window and Python Bridge...")
    mock_window = MagicMock()
    bridge = Bridge(mock_window)
    
    # ---------------------------------------------------------
    # TEST 1: Message Processing (React -> Python -> React)
    # ---------------------------------------------------------
    print("\n--- Running Test 1: Message Processing ---")
    test_message = "Status Check from React!"
    print(f"Simulating React sending: '{test_message}'")
    
    response = bridge.process_message(test_message)
    print(f"Python Bridge returned: '{response}'")
    
    if response == f"ULTRON Backend processed: '{test_message}'":
        print("✅ PASS: process_message correctly received and responded.")
    else:
        print(f"❌ FAIL: process_message response mismatch. Got: {response}")

    # ---------------------------------------------------------
    # TEST 2: Window Movement (React Drag -> Python Window Move)
    # ---------------------------------------------------------
    print("\n--- Running Test 2: Window Movement ---")
    target_x, target_y = 500, 300
    print(f"Simulating React dragging window to global coordinates: ({target_x}, {target_y})")
    
    bridge.move_window(target_x, target_y)
    
    try:
        mock_window.move.assert_called_once_with(target_x, target_y)
        print("✅ PASS: move_window correctly forwarded coordinates to the PySide6 window.")
    except AssertionError as e:
        print(f"❌ FAIL: move_window did not call window.move correctly. {e}")

if __name__ == "__main__":
    test_bridge_wiring()