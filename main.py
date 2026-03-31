import sys
import os

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPalette, QColor
from src.app_state import AppState
from src.main_window import MainWindow

def setup_dark_theme(app: QApplication):
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(24, 24, 24))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Base, QColor(34, 34, 34))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(44, 44, 44))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Button, QColor(44, 44, 44))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
    palette.setColor(QPalette.ColorRole.Link, QColor(103, 58, 183))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(98, 0, 238))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    app.setPalette(palette)
    
if __name__ == "__main__":
    app = QApplication(sys.argv)
    setup_dark_theme(app)
    
    # Initialize basic data or load
    app_state = AppState(filepath="data.txt")
    if not app_state.classrooms:
        app_state.add_classroom("Software Engineering 101")
        app_state.add_assignment(app_state.classrooms[0].id, "Assignment 1")
    
    window = MainWindow(app_state)
    window.show()
    sys.exit(app.exec())
