import sys
import os

from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtCore import QTimer, Qt

from study_widget import Study
from themes import apply_theme  # optional if you use theming


# Ensure relative paths work
os.chdir(os.path.dirname(os.path.abspath(__file__)))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("rodopt+")
        self.resize(1100, 750)
        self.setWindowIcon(QIcon("images/logo.png"))

        # NEW: show logo first (same window), then swap in the real UI
        self._logo_label = QLabel()
        self._logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._logo_label.setStyleSheet("background: white;")
        self._logo_label.setPixmap(QPixmap("images/logo_no_canvas.png"))

        self.setCentralWidget(self._logo_label)

        QTimer.singleShot(1500, self._show_main_ui)

    def _show_main_ui(self) -> None:
        self.study_widget = Study()
        self.setCentralWidget(self.study_widget)


# ----------------------------------------------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)

    apply_theme(app, "neutral")  # optional theming system
    app.setWindowIcon(QIcon("images/logo.png"))

    w = MainWindow()
    w.show()

    sys.exit(app.exec())
