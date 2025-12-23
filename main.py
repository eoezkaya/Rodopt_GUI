import sys
import os

from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtGui import QIcon

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

        # Directly open the DoE widget
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
